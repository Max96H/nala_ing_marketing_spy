import argparse
import importlib
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

    # Make sure the configuration file exists.
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Bank configuration not found: {CONFIG_PATH}"
        )

    # Read the YAML configuration file.
    with open(
        CONFIG_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        config = yaml.safe_load(file)

    # Reject an empty configuration file.
    if not config:
        raise ValueError(
            "banks.yaml is empty."
        )

    # The configuration must contain a "banks" section.
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

    This means you do not need to manually create folders
    when adding a new bank.

    Example:

        data/
        ├── raw/
        │   ├── ing/
        │   ├── kbc/
        │   ├── belfius/
        │   └── bnp/
        │
        └── screenshots/
            ├── ing/
            ├── kbc/
            ├── belfius/
            └── bnp/

    A new bank added to banks.yaml will automatically receive
    its corresponding directories the next time the pipeline runs.
    """

    # Define the two main storage roots.
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

    # Create the root directories if they do not exist.
    raw_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    screenshots_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Create one directory for each configured bank.
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
# LOAD CRAWLER CLASS
# ============================================================

def load_crawler_class(bank_name):
    """
    Dynamically load the crawler class for a bank.

    Example:

        bank_name = "ing"

        -> crawler.ing
        -> INGCrawler

    The crawler module must contain exactly one class
    inheriting from BankCrawler.
    """

    module_name = f"crawler.{bank_name}"

    try:

        # Import the bank-specific crawler module dynamically.
        module = importlib.import_module(
            module_name
        )

    except ModuleNotFoundError as error:

        raise RuntimeError(
            f"Could not find crawler module "
            f"'{module_name}'. "
            f"Expected file: "
            f"src/crawler/{bank_name}.py"
        ) from error

    crawler_classes = []

    # Inspect all attributes defined in the module.
    for attribute_name in dir(module):

        attribute = getattr(
            module,
            attribute_name,
        )

        # Ignore anything that is not a class.
        if not isinstance(attribute, type):
            continue

        # Ignore the base BankCrawler class itself.
        if attribute is BankCrawler:
            continue

        # Keep only classes inheriting from BankCrawler.
        if issubclass(
            attribute,
            BankCrawler,
        ):

            crawler_classes.append(
                attribute
            )

    # A crawler module must contain one BankCrawler subclass.
    if not crawler_classes:

        raise RuntimeError(
            f"No BankCrawler subclass found "
            f"in {module_name}."
        )

    if len(crawler_classes) > 1:

        raise RuntimeError(
            f"Multiple BankCrawler subclasses "
            f"found in {module_name}. "
            f"Expected exactly one."
        )

    return crawler_classes[0]


# ============================================================
# RUN ONE BANK
# ============================================================

def crawl_bank(
    bank_name,
    bank_config,
):
    """
    Crawl one bank using its YAML configuration.
    """

    print()
    print("==============================")
    print(f"CRAWLING: {bank_name.upper()}")
    print("==============================")

    # --------------------------------------------------------
    # LOAD CRAWLER
    # --------------------------------------------------------

    # Load the bank-specific crawler dynamically.
    crawler_class = load_crawler_class(
        bank_name
    )

    # Create an instance of the crawler.
    crawler = crawler_class()

    # --------------------------------------------------------
    # GET SEEDS
    # --------------------------------------------------------

    # Seeds are the initial URLs configured for the bank.
    seeds = bank_config.get(
        "seeds",
        []
    )

    # Stop early if no seed URLs are configured.
    if not seeds:

        print(
            f"No seeds configured for "
            f"{bank_name}."
        )

        return

    # --------------------------------------------------------
    # CRAWL SEEDS
    # --------------------------------------------------------

    # Process every configured seed URL.
    for url in seeds:

        print()
        print(f"URL: {url}")

        # Run the complete crawler workflow for the page.
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
    # LOAD BANKS FIRST
    # --------------------------------------------------------

    # Load all bank configurations from YAML.
    banks = load_bank_config()

    # --------------------------------------------------------
    # CREATE DATA DIRECTORIES
    # --------------------------------------------------------

    # Automatically create raw and screenshot directories
    # for every bank defined in banks.yaml.
    #
    # This means adding a new bank to YAML is enough to create
    # its corresponding storage folders.
    create_bank_directories(
        banks
    )

    # Extract the configured bank names dynamically.
    bank_names = list(
        banks.keys()
    )

    # --------------------------------------------------------
    # ARGUMENTS
    # --------------------------------------------------------

    # Build the CLI choices directly from banks.yaml.
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

    # Initialize the SQLite database before crawling.
    init_db()

    # --------------------------------------------------------
    # CRAWL
    # --------------------------------------------------------

    if args.bank == "all":

        # Crawl every bank defined in banks.yaml.
        for bank_name, bank_config in banks.items():

            crawl_bank(
                bank_name,
                bank_config,
            )

    else:

        # Crawl only the bank selected from the command line.
        crawl_bank(
            args.bank,
            banks[args.bank],
        )

    # --------------------------------------------------------
    # PRINT DATABASE
    # --------------------------------------------------------

    # Display the current database contents after crawling.
    print_all_pages()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()