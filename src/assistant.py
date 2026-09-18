"""
ING Banking Campaigns Comparator — Assistant (chatbot layer)

An interactive command-line chatbot that answers questions about the
scraped campaign data — e.g. "how does our tone compare to Revolut's?" or
"what changed this week?" — grounded entirely in campaigns.db. Uses Groq's
free-tier API.

The dataset is small (a handful of pages per bank), so this uses a simple
approach: load every row as compact context, plus recent watchdog changes,
and hand it all to the model with the user's question. No vector search
needed at this scale — if the dataset grows into the hundreds of pages,
that's the point to add retrieval instead of stuffing everything in.

Setup:
    pip install groq --break-system-packages
    export GROQ_API_KEY=gsk_...
    (free key: https://console.groq.com)

Usage:
    python assistant.py
    (then just type questions; type 'exit' or 'quit' to stop)
"""

import os
import sqlite3
import sys

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are a marketing analyst assistant for ING, helping ING staff understand how \
their bank's campaigns compare to competitors (KBC, BNP Paribas Fortis, Belfius, Revolut).

You will be given structured data scraped from each bank's product/campaign pages, plus any \
recently detected changes. Answer questions using ONLY this data — if something isn't in the \
data, say so plainly rather than guessing. Keep answers concise and business-relevant; this is \
for people deciding on ING's marketing strategy, not a technical audience.

Always respond in English, even though some of the source data is in French or Dutch."""


def load_context(conn: sqlite3.Connection) -> str:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT bank, page_url, page_type, language, scrape_date, headline, subtitle, "
        "tone, value_proposition, topics, has_numeric_offer, cta_text, dominant_colors "
        "FROM pages ORDER BY bank, page_type"
    ).fetchall()

    if not rows:
        return "No page data has been scraped yet."

    lines = ["## Scraped campaign data\n"]
    for r in rows:
        lines.append(
            f"- **{r['bank']} — {r['page_type']}** ({r['language']}, scraped {r['scrape_date']})\n"
            f"  URL: {r['page_url']}\n"
            f"  Headline: {r['headline']!r} | Subtitle: {r['subtitle']!r}\n"
            f"  Tone: {r['tone'] or 'not analyzed yet'} | "
            f"Value proposition: {r['value_proposition'] or 'not analyzed yet'}\n"
            f"  Topics: {r['topics'] or 'not analyzed yet'} | "
            f"Numeric offer present: {r['has_numeric_offer']} | CTA: {r['cta_text']!r}\n"
            f"  Dominant colours: {r['dominant_colors'] or 'not extracted yet'}\n"
        )

    changes = conn.execute(
        "SELECT bank, page_url, field_changed, previous_value, current_value, detected_date "
        "FROM changes ORDER BY detected_date DESC LIMIT 20"
    ).fetchall() if _table_exists(conn, "changes") else []

    if changes:
        lines.append("\n## Recently detected changes (most recent first)\n")
        for c in changes:
            lines.append(
                f"- {c['bank']} — {c['page_url']} — {c['field_changed']} changed from "
                f"{c['previous_value']!r} to {c['current_value']!r} (detected {c['detected_date']})"
            )
    else:
        lines.append("\nNo changes detected yet (need at least two scrape runs to compare).")

    return "\n".join(lines)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def run(db_path: str = "db/campaigns.db") -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: set GROQ_API_KEY before running this script.", file=sys.stderr)
        sys.exit(1)

    client = Groq(api_key=api_key)
    conn = sqlite3.connect(db_path)

    context = load_context(conn)
    conn.close()

    print("ING Campaign Comparator Assistant — ask a question, or type 'exit' to quit.\n")

    history = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{context}"}]
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        history.append({"role": "user", "content": question})
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=1000,
            messages=history,
        )
        answer = response.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": answer})
        print(f"\nAssistant: {answer}\n")


if __name__ == "__main__":
    run()