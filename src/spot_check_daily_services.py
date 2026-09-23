import argparse
from pathlib import Path
import sqlite3

# Define default paths relative to script location
ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "bank_analysis.db"
OUTPUT_FILE = ROOT_DIR / "data" / "daily_services_other_spot_check.txt"


def spot_check_category(
    category: str = "daily_services_other",
    db_path: Path = DB_PATH,
    output_file: Path = OUTPUT_FILE,
):
    """Exports records of a specific page_type to a text file for manual auditing."""
    if not db_path.exists():
        print(f"❌ Database file not found at: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query target category pages grouped by bank and ordered by URL
    query = """
        SELECT id, bank, page_url, headline
        FROM pages
        WHERE page_type = ?
        ORDER BY bank ASC, page_url ASC
    """

    cursor.execute(query, (category,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ No records found with page_type = '{category}'")
        return

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Format and write out the results
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"=== SPOT CHECK REPORT: {category} ({len(rows)} pages) ===\n")
        f.write("=" * 80 + "\n\n")

        current_bank = None
        for page_id, bank, url, headline in rows:
            # Add bank header section
            if bank != current_bank:
                current_bank = bank
                f.write(f"\n{"="*30} BANK: {current_bank.upper()} {"="*30}\n\n")

            clean_headline = (headline or "N/A").strip().replace("\n", " ")
            f.write(f"ID: {page_id}\n")
            f.write(f"URL: {url}\n")
            f.write(f"Headline: {clean_headline}\n")
            f.write("-" * 80 + "\n")

    print(
        f"✓ Successfully exported {len(rows)} records to: {output_file}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export specific page_type records from SQLite to text for spot-checking."
    )
    parser.add_argument(
        "-c",
        "--category",
        type=str,
        default="daily_services_other",
        help="Category to spot check (default: 'daily_services_other')",
    )

    args = parser.parse_args()
    spot_check_category(args.category, DB_PATH, OUTPUT_FILE)