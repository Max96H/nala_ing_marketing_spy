"""
ING Banking Campaigns Comparator — Analyst (LLM feature extraction)

Reads rows from data/bank_analysis.db that don't have tone/value_proposition
filled in yet, sends each page's raw_text to an LLM (via Groq's free API)
with a fixed JSON schema, and writes the result back: tone and
value_proposition go on the pages row itself; topics go into the
page_topics junction table (one row per topic, matching the team's schema).

Handles multi-language input directly — French/Dutch text goes straight to
the model, English output is enforced by the prompt. No separate
translation step.

Setup:
    pip install groq python-dotenv --break-system-packages
    export GROQ_API_KEY=gsk_...
    (free key: https://console.groq.com)

Usage:
    python analyst.py
"""

import json
import os
import sqlite3
import sys

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "openai/gpt-oss-120b"  # llama-3.3-70b-versatile was decommissioned Aug 2026

SYSTEM_PROMPT = """You are analysing a bank's marketing/product web page for a competitive \
comparison study. The page text may be in English, French, or Dutch — read it in its \
original language, but ALWAYS respond in English regardless of the source language.

Respond with ONLY a JSON object, no other text, no markdown fences, matching exactly:
{
  "tone": "<2-5 words describing tone, e.g. 'promotional, numbers-driven'>",
  "value_proposition": "<one sentence, in English, summarizing what's being offered and why>",
  "topics": ["<keyword1>", "<keyword2>", "..."]
}"""


def analyze_text(client: Groq, raw_text: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=500,
        response_format={"type": "json_object"},  # Groq/OpenAI-style JSON mode, enforces valid JSON
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text[:8000]},  # keep prompts small/cheap
        ],
    )
    text = response.choices[0].message.content.strip()
    return json.loads(text)


def run(db_path: str = "data/bank_analysis.db") -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: set GROQ_API_KEY before running this script.", file=sys.stderr)
        sys.exit(1)

    client = Groq(api_key=api_key)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT id, bank, page_url, raw_text FROM pages "
        "WHERE (tone IS NULL OR tone = '') AND raw_text IS NOT NULL AND raw_text != ''"
    ).fetchall()

    if not rows:
        print("Nothing to analyze — every row already has tone/value_proposition filled in.")
        conn.close()
        return

    for row in rows:
        try:
            result = analyze_text(client, row["raw_text"])

            conn.execute(
                "UPDATE pages SET tone = ?, value_proposition = ? WHERE id = ?",
                (result["tone"], result["value_proposition"], row["id"]),
            )

            topics = result.get("topics", [])
            for topic in topics:
                conn.execute(
                    "INSERT OR IGNORE INTO page_topics (page_id, topic) VALUES (?, ?)",
                    (row["id"], topic),
                )

            conn.commit()
            print(f"[ok] {row['bank']} — {row['page_url']} -> tone: {result['tone']} "
                  f"({len(topics)} topic(s))")
        except Exception as exc:
            print(f"[fail] {row['bank']} — {row['page_url']}: {exc}", file=sys.stderr)

    conn.close()
    print("\nDone. tone / value_proposition / topics updated in", db_path)


if __name__ == "__main__":
    run()