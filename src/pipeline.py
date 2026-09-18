import argparse
from pathlib import Path

import yaml

from crawler.base import BankCrawler

from storage.database import (
    init_db,
    print_all_pages,
)


# ============================================================
# CONFIGURATION
# ============================================================

# Resolve the project root from this file.
#
# Example:
#   project/
#   ├── config/
#   ├── data/
#   └── src/
#       └── pipeline.py
#
# parents[1] points to the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Path to the central bank configuration file.
CONFIG_PATH = PROJECT_ROOT / "config" / "banks.yaml"


# ============================================================
# LOAD BANK CONFIGURATION
# ============================================================

def load_bank_config():
    """
    Load all bank configurations from banks.yaml.

    The YAML file is the central configuration source for
    the multi-bank crawler.
    """

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Bank configuration not found: {CONFIG_PATH}"
        )

    with open(
        CONFIG_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        config = yaml.safe_load(file)

    if not config:
        raise ValueError(
            "banks.yaml is empty."
        )

    banks = config.get("banks")

    if not banks:
        raise ValueError(
            "No 'banks' section found in banks.yaml."
        )

    return banks


# ============================================================
# CREATE BANK DIRECTORIES
# ============================================================

def create_bank_directories(
    banks,
) -> None:
    """
    Automatically create the required data directories
    for every bank defined in banks.yaml.
    """

    raw_root = (
        PROJECT_ROOT
        / "data"
        / "raw"
    )

    screenshots_root = (
        PROJECT_ROOT
        / "data"
        / "screenshots"
    )

    raw_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    screenshots_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    for bank_name in banks:

        raw_bank_dir = (
            raw_root
            / bank_name
        )

        screenshot_bank_dir = (
            screenshots_root
            / bank_name
        )

        raw_bank_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        screenshot_bank_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(
            f"Data directories ready for bank: {bank_name}"
        )


# ============================================================
# RUN ONE BANK
# ============================================================

def crawl_bank(
    bank_name,
    bank_config,
):
    """
    Crawl one bank using its YAML configuration.

    The crawler itself is generic.
    Bank-specific information comes from banks.yaml.
    """

    print()
    print("==============================")
    print(f"CRAWLING: {bank_name.upper()}")
    print("==============================")

    # --------------------------------------------------------
    # CREATE GENERIC CRAWLER
    # --------------------------------------------------------

    # All banks use the same crawling logic.
    #
    # The bank name is passed to the crawler so that
    # files are stored in the correct bank directory.
    crawler = BankCrawler(
        bank_name
    )

    # --------------------------------------------------------
    # GET SEEDS
    # --------------------------------------------------------

    # Seeds are the initial URLs configured for the bank.
    seeds = bank_config.get(
        "seeds",
        []
    )

    if not seeds:

        print(
            f"No seeds configured for "
            f"{bank_name}."
        )

        return

    # --------------------------------------------------------
    # CRAWL SEEDS
    # --------------------------------------------------------

    for url in seeds:

        print()
        print(f"URL: {url}")

        # Run the complete crawler workflow.
        result = crawler.process_page(
            url
        )

        # Print a short extraction summary.
        print(
            "Title:",
            result["content"]["title"]
        )

        print(
            "Headings:",
            len(
                result["content"]["headings"]
            )
        )

        print(
            "Paragraphs:",
            len(
                result["content"]["paragraphs"]
            )
        )

        print(
            "Links:",
            len(
                result["content"]["links"]
            )
        )

        print(
            "Images:",
            len(
                result["content"]["images"]
            )
        )

    print()


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Multi-bank marketing crawler"
        )
    )

    # --------------------------------------------------------
    # LOAD BANKS
    # --------------------------------------------------------

    banks = load_bank_config()

    # --------------------------------------------------------
    # CREATE DATA DIRECTORIES
    # --------------------------------------------------------

    create_bank_directories(
        banks
    )

    # Extract bank names dynamically from banks.yaml.
    bank_names = list(
        banks.keys()
    )

    # --------------------------------------------------------
    # ARGUMENTS
    # --------------------------------------------------------

    parser.add_argument(
        "--bank",
        choices=[
            *bank_names,
            "all",
        ],
        default="all",
        help="Bank to crawl",
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # INITIALIZE DATABASE
    # --------------------------------------------------------

    init_db()

    # --------------------------------------------------------
    # CRAWL
    # --------------------------------------------------------

    if args.bank == "all":

        for bank_name, bank_config in banks.items():

            crawl_bank(
                bank_name,
                bank_config,
            )

    else:

        crawl_bank(
            args.bank,
            banks[args.bank],
        )

    # --------------------------------------------------------
    # PRINT DATABASE
    # --------------------------------------------------------

    print_all_pages()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()