"""
ING Banking Campaigns Comparator — Watchdog (change detector)

Compares each page's latest scrape to its previous scrape (same page_url,
earlier scrape_date) and flags meaningful changes: headline, CTA text,
whether a numeric offer appeared/disappeared, or the raw text changing
substantially. Writes flagged changes into a `changes` table so the
Assistant/chatbot layer can surface them later.

Run this AFTER collector.py has been run at least twice for the same pages
(e.g. once this week, once last week) — with only one snapshot there's
nothing to compare against yet.

Usage:
    python watchdog.py
"""

import difflib
import sqlite3
from datetime import date


def init_changes_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank TEXT,
            page_url TEXT,
            detected_date TEXT,
            previous_scrape_date TEXT,
            current_scrape_date TEXT,
            field_changed TEXT,
            previous_value TEXT,
            current_value TEXT
        )
    """)
    conn.commit()


def text_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def run(db_path: str = "db/campaigns.db") -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_changes_table(conn)

    page_urls = [r["page_url"] for r in conn.execute("SELECT DISTINCT page_url FROM pages")]

    flagged = 0
    for url in page_urls:
        rows = conn.execute(
            "SELECT * FROM pages WHERE page_url = ? ORDER BY scrape_date ASC", (url,)
        ).fetchall()
        if len(rows) < 2:
            continue  # need at least two snapshots to compare

        previous, current = rows[-2], rows[-1]

        checks = [
            ("headline", previous["headline"], current["headline"]),
            ("cta_text", previous["cta_text"], current["cta_text"]),
            ("has_numeric_offer", previous["has_numeric_offer"], current["has_numeric_offer"]),
        ]
        for field_name, prev_val, curr_val in checks:
            if prev_val != curr_val:
                conn.execute(
                    "INSERT INTO changes (bank, page_url, detected_date, previous_scrape_date, "
                    "current_scrape_date, field_changed, previous_value, current_value) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (current["bank"], url, date.today().isoformat(),
                     previous["scrape_date"], current["scrape_date"],
                     field_name, str(prev_val), str(curr_val)),
                )
                flagged += 1
                print(f"[change] {current['bank']} — {field_name}: '{prev_val}' -> '{curr_val}'")

        # raw_text: only flag if it changed substantially (avoid noise from tiny formatting diffs)
        similarity = text_similarity(previous["raw_text"] or "", current["raw_text"] or "")
        if similarity < 0.85:
            conn.execute(
                "INSERT INTO changes (bank, page_url, detected_date, previous_scrape_date, "
                "current_scrape_date, field_changed, previous_value, current_value) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (current["bank"], url, date.today().isoformat(),
                 previous["scrape_date"], current["scrape_date"],
                 "raw_text", f"similarity={similarity:.2f}", "substantial content change"),
            )
            flagged += 1
            print(f"[change] {current['bank']} — page content changed substantially "
                  f"(similarity={similarity:.2f})")

    conn.commit()
    conn.close()
    print(f"\nDone. {flagged} change(s) flagged in the 'changes' table.")


if __name__ == "__main__":
    run()