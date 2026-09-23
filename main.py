"""
ING Banking Campaigns Comparator — main entry point

Default run (`python main.py`, no flags) does everything EXCEPT scraping —
data collection is the team's side of the pipeline (src/collect.py) and is
only run when explicitly asked for with --only collect:

  1. Analyst    — send each row's raw_text to an LLM (via Groq), fill in
                   tone / value_proposition, and topics into page_topics
  2. Analysis   — compute the positioning map, radar scores, and gap-finder
                   from the analyzed data (src/analysis.py)
  3. Watchdog   — compare today's rows to the previous snapshot (if any)
                   and flag what changed into the 'changes' table

Run this in your OWN environment with normal internet access, and with
GROQ_API_KEY set. See README.md for full setup.

Usage:
    python main.py                        # analyst -> analysis -> watchdog (no scraping)
    python main.py --skip-analyst          # analysis -> watchdog only
    python main.py --only collect          # scrape only (team's stage) — never runs by default
    python main.py -b ing kbc --only collect   # scrape only ING and KBC
    python main.py --only analysis         # re-run just the positioning/radar/gaps
    python main.py --only watchdog         # re-run just one stage
    python main.py --only assistant        # launch the interactive chatbot
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import collect
import analyst
import analysis
import change_watcher
import assistant


# Default run: everything except collect — the team runs that separately.
# 'collect' and 'assistant' are only ever run explicitly via --only.
STAGES = ["analyst", "analysis", "watchdog"]
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
        action="store_true",  # <--- Automatically sets args.scroll to True when present, False when absent
        help="Scroll down the page to trigger lazy-loaded elements before taking a screenshot. Default: False",
    )
    
    parser.add_argument(
        "--skip-analyst", action="store_true",
        help="Skip the LLM analysis step (useful if you don't have GROQ_API_KEY set yet).",
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
    if scrolling:
        print("Will scroll to load the page before screenshot.")
    else:
        print("Run without scrolling.")
    if args.skip_analyst and "analyst" in stages_to_run and not args.only:
        stages_to_run.remove("analyst")

    for stage in stages_to_run:
        print(f"\n===== Running {stage} =====")
        try:
            if stage == "collect":
                collect.run(selected_banks, scrolling)
            elif stage == "analyst":
                analyst.run()
            elif stage == "analysis":
                analysis.run()
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