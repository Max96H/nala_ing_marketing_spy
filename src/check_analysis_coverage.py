import argparse
import sqlite3
import sys
from pathlib import Path

# Update DB path if your SQLite file is named or located elsewhere
ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "bank_analysis.db"


def format_page_type(label: str) -> str:
    """Formats 'utility_security_legal' -> 'Utility Security Legal'."""
    if not label or label.strip() == "":
        return "Uncategorized"
    return " ".join(word.capitalize() for word in label.split("_"))


def check_coverage_by_page_type(bank_name: str, db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    target_bank = bank_name.strip().lower()

    # Query metrics grouped by page_type for the target bank
    cursor.execute(
        """
        SELECT 
            COALESCE(page_type, 'uncategorized') AS category,
            COUNT(*) AS total_pages,
            SUM(CASE WHEN tone IS NULL OR TRIM(tone) = '' THEN 1 ELSE 0 END) AS empty_tone,
            SUM(CASE WHEN value_proposition IS NULL OR TRIM(value_proposition) = '' THEN 1 ELSE 0 END) AS empty_val_prop,
            SUM(CASE WHEN (tone IS NULL OR TRIM(tone) = '') 
                      AND (value_proposition IS NULL OR TRIM(value_proposition) = '') THEN 1 ELSE 0 END) AS empty_both
        FROM pages
        WHERE LOWER(bank) = ?
        GROUP BY COALESCE(page_type, 'uncategorized')
        ORDER BY total_pages DESC
        """,
        (target_bank,),
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f"\nNo pages found in database for bank: '{bank_name}'")
        return

    # Calculate overall totals across all page types
    bank_total_pages = sum(r["total_pages"] for r in rows)
    bank_total_empty_tone = sum(r["empty_tone"] for r in rows)
    bank_total_empty_val_prop = sum(r["empty_val_prop"] for r in rows)
    bank_total_empty_both = sum(r["empty_both"] for r in rows)

    # Print Report Header
    print(f"\n==========================================================================================")
    print(f" ANALYSIS COVERAGE BY PAGE TYPE: {target_bank.upper()}")
    print(f"==========================================================================================")
    print(f"{'Page Type':<28} | {'Total':<6} | {'Empty Tone':<14} | {'Empty Val Prop':<14} | {'Empty Both':<10}")
    print(f"------------------------------------------------------------------------------------------")

    # Print row breakdown per page_type
    for r in rows:
        page_type_name = format_page_type(r["category"])
        tot = r["total_pages"]
        e_tone = r["empty_tone"]
        e_vp = r["empty_val_prop"]
        e_both = r["empty_both"]

        tone_pct = (e_tone / tot * 100) if tot > 0 else 0
        vp_pct = (e_vp / tot * 100) if tot > 0 else 0

        tone_str = f"{e_tone} ({tone_pct:.0f}%)"
        vp_str = f"{e_vp} ({vp_pct:.0f}%)"

        print(
            f"{page_type_name:<28} | {tot:<6} | {tone_str:<14} | {vp_str:<14} | {e_both:<10}"
        )

    # Print Summary Footer
    print(f"------------------------------------------------------------------------------------------")
    tone_total_pct = (bank_total_empty_tone / bank_total_pages * 100) if bank_total_pages > 0 else 0
    vp_total_pct = (bank_total_empty_val_prop / bank_total_pages * 100) if bank_total_pages > 0 else 0

    print(
        f"{'TOTAL BANK SUMMARY':<28} | {bank_total_pages:<6} | "
        f"{f'{bank_total_empty_tone} ({tone_total_pct:.0f}%)':<14} | "
        f"{f'{bank_total_empty_val_prop} ({vp_total_pct:.0f}%)':<14} | "
        f"{bank_total_empty_both:<10}"
    )
    print(f"==========================================================================================\n")


def main():
    parser = argparse.ArgumentParser(
        description="Check empty cell counts in 'tone' and 'value_proposition' columns grouped by page_type."
    )
    parser.add_argument(
        "--bank",
        "-b",
        type=str,
        required=True,
        help="Bank key/name to check (e.g., ing, kbc, belfius)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=DB_PATH,
        help=f"Path to SQLite database file (default: {DB_PATH})",
    )

    args = parser.parse_args()

    try:
        check_coverage_by_page_type(bank_name=args.bank, db_path=args.db)
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()