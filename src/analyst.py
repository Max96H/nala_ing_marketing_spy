"""
ING Banking Campaigns Comparator — Analyst (LLM feature extraction)

Reads rows from data/bank_analysis.db that don't have tone/value_proposition
filled in yet, sends each page's raw_text to an LLM (via Groq's free API)
with a fixed JSON schema, and writes the result back: tone and
value_proposition go on the pages row itself; topics go into the
page_topics junction table.

Hallucination check: the model must return a verbatim quote from the source
text backing each of "tone" and "value_proposition". Each quote is checked
against raw_text after the call — if it doesn't actually appear in the
source, that's a strong signal the judgment was invented rather than
grounded, and it's flagged loudly rather than silently trusted. This is a
real check (a substring match after normalizing whitespace/case), not a
cosmetic field the model can fill with anything.

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
import re
import sqlite3
import sys

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "openai/gpt-oss-120b"  # llama-3.3-70b-versatile was decommissioned Aug 2026
TEMPERATURE = 0.2  # low — this is extraction, not creative writing; consistency over variety

SYSTEM_PROMPT = """You are analysing a bank's marketing/product web page for a competitive \
comparison study. The page text may be in English, French, or Dutch — read it in its \
original language, but ALWAYS respond in English regardless of the source language.

To avoid inventing claims, ground every judgment in the text you were given:
- "tone_evidence" and "value_proposition_evidence" must each be an exact, verbatim quote \
copied directly from the page text below (under 20 words) that supports your "tone" and \
"value_proposition" answers. Copy it exactly as it appears — do not paraphrase, translate, \
or clean it up.
- "topics" must only include topics clearly present in the text itself, not things you know \
about this bank from general knowledge.

Respond with ONLY a JSON object, no other text, no markdown fences, matching exactly:
{
  "tone": "<2-5 words describing tone, e.g. 'promotional, numbers-driven'>",
  "tone_evidence": "<exact verbatim quote from the text supporting the tone>",
  "value_proposition": "<one sentence, in English, summarizing what's being offered and why>",
  "value_proposition_evidence": "<exact verbatim quote from the text supporting the value proposition>",
  "topics": ["<keyword1>", "<keyword2>", "..."]
}"""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def evidence_verified(evidence: str, source_text: str) -> bool:
    """True if the quoted evidence genuinely appears in the source text
    (whitespace/case-insensitive substring match). False means the model
    likely invented or paraphrased rather than quoted."""
    if not evidence or not source_text:
        return False
    return _normalize(evidence) in _normalize(source_text)


def analyze_text(client: Groq, raw_text: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=600,
        temperature=TEMPERATURE,
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

    unverified_count = 0

    for row in rows:
        try:
            result = analyze_text(client, row["raw_text"])

            tone_ok = evidence_verified(result.get("tone_evidence", ""), row["raw_text"])
            vp_ok = evidence_verified(result.get("value_proposition_evidence", ""), row["raw_text"])

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

            status = "verified" if (tone_ok and vp_ok) else "UNVERIFIED"
            print(f"[ok] {row['bank']} — {row['page_url']} -> tone: {result['tone']} "
                  f"({len(topics)} topic(s)) [{status}]")

            if not tone_ok:
                unverified_count += 1
                print(f"  [warn] tone_evidence not found verbatim in raw_text — "
                      f"quote: {result.get('tone_evidence', '')!r}", file=sys.stderr)
            if not vp_ok:
                unverified_count += 1
                print(f"  [warn] value_proposition_evidence not found verbatim in raw_text — "
                      f"quote: {result.get('value_proposition_evidence', '')!r}", file=sys.stderr)

        except Exception as exc:
            print(f"[fail] {row['bank']} — {row['page_url']}: {exc}", file=sys.stderr)

    conn.close()
    print(f"\nDone. tone / value_proposition / topics updated in {db_path}")
    if unverified_count:
        print(f"[warn] {unverified_count} field(s) across this run had evidence that couldn't be "
              f"matched to the source text — worth a manual spot-check on those pages.",
              file=sys.stderr)


if __name__ == "__main__":
    run()