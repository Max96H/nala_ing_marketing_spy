"""
ING Banking Campaigns Comparator — Watchdog (change detector)

The team's schema upserts one row per page_url (ON CONFLICT DO UPDATE in
insertion_db.py) — re-scraping a page overwrites it, so there's no
built-in history to compare "today" against "last week". This script
keeps its own history instead: a `page_snapshots` table (created here,
not in schema.sql) that stores one row per page per time this script
runs. Each run compares the current `pages` row to the most recent stored
snapshot, flags what changed into `changes`, then stores a fresh snapshot
for next time.

Run this AFTER collect.py has been run and analyzed at least once. The
first run establishes the baseline (0 changes, expected) — changes only
show up from the second run onward.

Usage:
    python change_watcher.py
"""

import difflib
import sqlite3
from datetime import date


def init_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank TEXT,
            page_url TEXT,
            detected_date TEXT,
            previous_snapshot_date TEXT,
            current_snapshot_date TEXT,
            field_changed TEXT,
            previous_value TEXT,
            current_value TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS page_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_url TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            bank TEXT,
            headline TEXT,
            cta_text TEXT,
            has_numeric_offer INTEGER,
            raw_text TEXT
        )
    """)
    conn.commit()


def text_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def run(db_path: str = "data/bank_analysis.db") -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_tables(conn)

    pages = conn.execute("SELECT * FROM pages").fetchall()
    today = date.today().isoformat()
    flagged = 0

    for current in pages:
        url = current["page_url"]

        previous = conn.execute(
            "SELECT * FROM page_snapshots WHERE page_url = ? "
            "ORDER BY snapshot_date DESC LIMIT 1", (url,)
        ).fetchone()

        if previous:
            checks = [
                ("headline", previous["headline"], current["headline"]),
                ("cta_text", previous["cta_text"], current["cta_text"]),
                ("has_numeric_offer", previous["has_numeric_offer"], current["has_numeric_offer"]),
            ]
            for field_name, prev_val, curr_val in checks:
                if prev_val != curr_val:
                    conn.execute(
                        "INSERT INTO changes (bank, page_url, detected_date, "
                        "previous_snapshot_date, current_snapshot_date, field_changed, "
                        "previous_value, current_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (current["bank"], url, today, previous["snapshot_date"], today,
                         field_name, str(prev_val), str(curr_val)),
                    )
                    flagged += 1
                    print(f"[change] {current['bank']} — {field_name}: '{prev_val}' -> '{curr_val}'")

            similarity = text_similarity(previous["raw_text"] or "", current["raw_text"] or "")
            if similarity < 0.85:
                conn.execute(
                    "INSERT INTO changes (bank, page_url, detected_date, "
                    "previous_snapshot_date, current_snapshot_date, field_changed, "
                    "previous_value, current_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (current["bank"], url, today, previous["snapshot_date"], today,
                     "raw_text", f"similarity={similarity:.2f}", "substantial content change"),
                )
                flagged += 1
                print(f"[change] {current['bank']} — page content changed substantially "
                      f"(similarity={similarity:.2f})")

        # Always store today's state as the new baseline for next time.
        conn.execute(
            "INSERT INTO page_snapshots (page_url, snapshot_date, bank, headline, "
            "cta_text, has_numeric_offer, raw_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (url, today, current["bank"], current["headline"], current["cta_text"],
             current["has_numeric_offer"], current["raw_text"]),
        )

    conn.commit()
    conn.close()
    print(f"\nDone. {flagged} change(s) flagged in the 'changes' table.")


if __name__ == "__main__":
    run()