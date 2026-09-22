"""
ING Banking Campaigns Comparator — main entry point

Runs the pipeline end to end:
  1. Collector  — render each page with Playwright, extract deterministic
                   features, save screenshots, write raw rows to bank_analysis.db
  2. Analyst    — send each row's raw_text to an LLM (via Groq), fill in
                   tone / value_proposition / topics
  3. Watchdog   — compare today's rows to the previous snapshot (if any)
                   and flag what changed into the 'changes' table

Run this in your OWN environment with normal internet access, and with
GROQ_API_KEY set. See README.md for full setup.

Usage:
    python main.py                # run everything
    python main.py --skip-analyst # scrape only, skip the LLM step (e.g. no API key handy yet)
    python main.py --only watchdog  # re-run just one stage
"""

import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import collector
import analyst
import change_watcher
import assistant


STAGES = ["collector", "analyst", "watchdog"]
ALL_CHOICES = STAGES + ["assistant"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ING campaign comparator pipeline.")
    parser.add_argument("--skip-analyst", action="store_true",
                         help="Skip the LLM analysis step (useful if you don't have an API key set yet).")
    parser.add_argument("--only", choices=ALL_CHOICES,
                         help="Run only one stage instead of the full pipeline. "
                              "'assistant' launches the interactive chatbot and is never part of "
                              "the default automated run.")
    args = parser.parse_args()

    stages_to_run = [args.only] if args.only else STAGES
    if args.skip_analyst and "analyst" in stages_to_run and not args.only:
        stages_to_run.remove("analyst")

    for stage in stages_to_run:
        print(f"\n===== Running {stage} =====")
        try:
            if stage == "collector":
                collector.run()
            elif stage == "analyst":
                analyst.run()
            elif stage == "watchdog":
                change_watcher.run()
            elif stage == "assistant":
                assistant.run()
        except Exception as exc:
            print(f"[stage failed] {stage}: {exc}", file=sys.stderr)
            print(f"Stopping — fix the error above before continuing.", file=sys.stderr)
            sys.exit(1)

    print("\n===== Pipeline complete =====")
    print("Data: bank_analysis.db  |  Screenshots: screenshots/  |  Changes: 'changes' table in bank_analysis.db")


if __name__ == "__main__":
    main()