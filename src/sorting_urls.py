import argparse
from pathlib import Path
import sqlite3

# Default project paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "bank_analysis.db"
OUTPUT_DIR = ROOT_DIR / "data" / "url_exports"


def export_sorted_urls(bank_query: str, db_path: Path):
    """Fetches unique URLs for a given bank, sorts them alphabetically, and writes to a txt file."""
    if not db_path.exists():
        print(f"❌ Database file not found at: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query matching bank name or URLs containing the bank domain term
    # Uses 'DISTINCT' to deduplicate automatically
    query = """
        SELECT DISTINCT page_url 
        FROM pages 
        WHERE LOWER(bank) LIKE ?
        ORDER BY page_url ASC
    """
    search_term = f"%{bank_query.lower()}%"

    cursor.execute(query, (search_term,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ No URLs found matching bank filter: '{bank_query}'")
        return

    urls = [row[0] for row in rows]

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{bank_query.lower()}_urls.txt"

    # Write URLs to txt file
    with open(output_file, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(f"{url}\n")

    print(
        f"✓ Successfully exported {len(urls)} sorted URLs for '{bank_query}' -> {output_file}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export alphabetically sorted bank URLs from SQLite to a text file."
    )
    parser.add_argument(
        "-b",
        "--bank",
        type=str,
        required=True,
        help="Bank identifier or search term (e.g., 'bnp', 'ing', 'kbc', 'belfius')",
    )

    args = parser.parse_args()
    export_sorted_urls(args.bank, DB_PATH)