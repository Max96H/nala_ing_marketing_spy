"""
ING Banking Campaigns Comparator — main entry point

Default run (`python main.py`, no flags) does everything EXCEPT scraping —
data collection is the team's side of the pipeline (src/collect.py) and is
only run when explicitly asked for with --only collect:

  1. Analyst    — send each row's raw_text to an LLM (via Groq/Gemini), fill
                   in tone / value_proposition, and topics into page_topics.
                   Only a priority subset of page_type categories runs by
                   default — see --categories.
  2. UX score   — deterministic UI/UX score per page (no LLM — see
                   src/ux_score.py), independent of the analyst stage
  3. Analysis   — compute the positioning map, radar scores, gap-finder, and
                   recommendations from the analyzed data (src/analysis.py)
  4. Product recs — diverse, LLM-written ING-vs-competitor recommendations
                   for the Compare Products tab (src/product_recommendations.py)
  5. Watchdog   — compare today's rows to the previous snapshot (if any)
                   and flag what changed into the 'changes' table

Run this in your OWN environment with normal internet access, and with
GROQ_API_KEY or GEMINI_API_KEY set (matching LLM_PROVIDER). See README.md
for full setup.

Usage:
    python main.py                                # analyst -> ux_score -> analysis -> watchdog
    python main.py --skip-analyst                 # ux_score -> analysis -> watchdog only
    python main.py --only collect --scroll         # scrape (team's stage) — never runs by default
    python main.py -b ing kbc --only collect       # scrape only ING and KBC
    python main.py --only analyst --categories savings_investments   # one category only
    python main.py --only ux_score                # re-run just the UI/UX scores
    python main.py --only analysis                # re-run just the positioning/radar/gaps
    python main.py --only watchdog                 # re-run just one stage
    python main.py --only assistant                # launch the interactive chatbot
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import collect
import analyst
import ux_score
import analysis
import product_recommendations
import change_watcher
import assistant
import collect_n26


# Default run: everything except collect — the team runs that separately.
# 'collect' and 'assistant' are only ever run explicitly via --only.
STAGES = ["analyst", "ux_score", "analysis", "product_recommendations", "watchdog"]
ALL_CHOICES = ["collect"] + STAGES + ["assistant"]


def main() -> None:
    banks = collect.load_bank_config()
    available_banks = [b.lower() for b in banks.keys()]

    parser = argparse.ArgumentParser(description="Run the ING campaign comparator pipeline.")
    parser.add_argument(
        "-b", "--banks",
        nargs="+",
        type=str.lower,
        choices=available_banks,
        default=available_banks,
        help=f"Specific bank(s) to scrape (only relevant with --only collect). "
             f"Choices: {', '.join(available_banks)}. Default: all.",
    )
    parser.add_argument(
        "--scroll",
        action="store_true",
        help="Scroll down the page to trigger lazy-loaded elements before taking a screenshot. "
             "Default: False",
    )
    parser.add_argument(
        "--categories", nargs="+", default=None,
        help=f"page_type categories for the analyst stage, in priority order (only relevant "
             f"with the analyst stage). Default: {' '.join(analyst.DEFAULT_CATEGORIES)}. "
             f"Pass 'all' for no filter.",
    )
    parser.add_argument(
        "--skip-analyst", action="store_true",
        help="Skip the LLM analysis step (useful if you don't have an API key set yet).",
    )
    parser.add_argument(
        "--only", choices=ALL_CHOICES,
        help="Run only one stage instead of the full pipeline. 'assistant' launches the "
             "interactive chatbot and is never part of the default automated run.",
    )
    args = parser.parse_args()

    selected_banks = {name: cfg for name, cfg in banks.items() if name.lower() in args.banks}

    stages_to_run = [args.only] if args.only else list(STAGES)
    scrolling = args.scroll
    print("Will scroll to load the page before screenshot." if scrolling else "Run without scrolling.")
    if args.skip_analyst and "analyst" in stages_to_run and not args.only:
        stages_to_run.remove("analyst")

    for stage in stages_to_run:
        print(f"\n===== Running {stage} =====")
        try:
            if stage == "collect":
                if selected_banks[0] == "n26":
                    collect_n26.run(selected_banks, scrolling)
                else:
                    collect.run(selected_banks, scrolling)

            elif stage == "analyst":
                analyst.run(categories=args.categories)
            elif stage == "ux_score":
                ux_score.run()  # no LLM cost, so score every page by default, not just --categories
            elif stage == "analysis":
                analysis.run()
            elif stage == "product_recommendations":
                product_recommendations.run()
            elif stage == "watchdog":
                change_watcher.run()
            elif stage == "assistant":
                assistant.run()
        except Exception as exc:
            print(f"[stage failed] {stage}: {exc}", file=sys.stderr)
            print("Stopping — fix the error above before continuing.", file=sys.stderr)
            sys.exit(1)

    print("\n===== Pipeline complete =====")


if __name__ == "__main__":
    main()