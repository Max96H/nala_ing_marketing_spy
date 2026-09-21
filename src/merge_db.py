"""
ING Banking Campaigns Comparator — Merge

Combines multiple teammates' campaigns.db files (each with a `pages` table
in the shared schema) into one central database. Rows are deduplicated on
(bank, page_url, scrape_date) — if two people accidentally scraped the same
page on the same day, only the first one is kept.

Since teammates aren't running the Analyst step (only Uzair uses an LLM),
most merged-in rows will have empty tone/value_proposition/topics. That's
expected — run analyst.py on the merged database afterward to fill those in
for everyone's data in one consistent pass.

Usage:
    python merge_db.py --sources teammate1.db teammate2.db teammate3.db --output db/campaigns.db
"""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
import collector  # reuse the exact same SCHEMA_FIELDS so merge and collect never drift apart


def merge(sources: list[str], output: str) -> None:
    out_conn = collector.init_db(output)

    total_inserted = 0
    total_skipped = 0

    for source_path in sources:
        if not Path(source_path).exists():
            print(f"[skip] {source_path} not found", file=sys.stderr)
            continue

        src_conn = sqlite3.connect(source_path)
        src_conn.row_factory = sqlite3.Row

        # Only pull columns that exist in our shared schema — protects against a teammate's
        # db having extra/renamed columns we don't expect.
        cols = ", ".join(f'"{f}"' for f in collector.SCHEMA_FIELDS)
        try:
            rows = src_conn.execute(f"SELECT {cols} FROM pages").fetchall()
        except sqlite3.OperationalError as exc:
            print(f"[fail] {source_path}: {exc} — check its schema matches collector.SCHEMA_FIELDS",
                  file=sys.stderr)
            src_conn.close()
            continue

        inserted = skipped = 0
        for row in rows:
            row = dict(row)
            exists = out_conn.execute(
                "SELECT 1 FROM pages WHERE bank = ? AND page_url = ? AND scrape_date = ?",
                (row["bank"], row["page_url"], row["scrape_date"]),
            ).fetchone()
            if exists:
                skipped += 1
                continue
            placeholders = ", ".join("?" for _ in collector.SCHEMA_FIELDS)
            values = [row[f] for f in collector.SCHEMA_FIELDS]
            out_conn.execute(f"INSERT INTO pages ({cols}) VALUES ({placeholders})", values)
            inserted += 1

        out_conn.commit()
        src_conn.close()
        print(f"[ok] {source_path}: {inserted} inserted, {skipped} duplicate(s) skipped")
        total_inserted += inserted
        total_skipped += skipped

    out_conn.close()
    print(f"\nDone. {total_inserted} row(s) merged into {output}, {total_skipped} duplicate(s) skipped.")
    print("Next: run 'python analyst.py' on the merged database to fill in tone/value_proposition/topics "
          "for the rows your teammates scraped without an LLM.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge teammates' campaigns.db files into one.")
    parser.add_argument("--sources", nargs="+", required=True,
                         help="Paths to teammates' campaigns.db files (space-separated).")
    parser.add_argument("--output", default="db/campaigns.db",
                         help="Path to the central database to merge into (default: db/campaigns.db).")
    args = parser.parse_args()
    merge(args.sources, args.output)


if __name__ == "__main__":
    main()