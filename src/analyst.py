"""
ING Banking Campaigns Comparator — Analyst (LLM feature extraction)

Reads rows from campaigns.db that don't have tone/value_proposition/topics
filled in yet, sends each page's raw_text to an LLM (via Groq's free API)
with a fixed JSON schema, and writes the structured result back to the
database.

Handles multi-language input directly (see note in README) — French/Dutch
text goes straight to the model, English output is enforced by the prompt.
No separate translation step.

Setup:
    pip install groq --break-system-packages
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

MODEL = "openai/gpt-oss-120b"  # solid free-tier model on Groq; swap here if you prefer another

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


def run(db_path: str = "db/campaigns.db") -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: set GROQ_API_KEY before running this script.", file=sys.stderr)
        sys.exit(1)

    client = Groq(api_key=api_key)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT id, bank, page_url, raw_text FROM pages "
        "WHERE (tone IS NULL OR tone = '') AND raw_text IS NOT NULL AND raw_text != ''"
    ).fetchall()

    if not rows:
        print("Nothing to analyze — every row already has tone/value_proposition/topics.")
        return

    for row in rows:
        try:
            result = analyze_text(client, row["raw_text"])
            conn.execute(
                "UPDATE pages SET tone = ?, value_proposition = ?, topics = ? WHERE id = ?",
                (result["tone"], result["value_proposition"], json.dumps(result["topics"]), row["id"]),
            )
            conn.commit()
            print(f"[ok] {row['bank']} — {row['page_url']} -> tone: {result['tone']}")
        except Exception as exc:
            print(f"[fail] {row['bank']} — {row['page_url']}: {exc}", file=sys.stderr)

    conn.close()
    print("\nDone. tone / value_proposition / topics updated in campaigns.db")


if __name__ == "__main__":
    run()