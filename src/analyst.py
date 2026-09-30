"""
ING Banking Campaigns Comparator — Analyst (LLM feature extraction)

Reads rows from data/bank_analysis.db that don't have tone/value_proposition
filled in yet, and sends them to an LLM in BATCHES rather than one call per
page — at ~3,000 pages, one-call-per-page would exhaust free-tier rate
limits fast. Batches are grouped by page_type (via the ORDER BY below) so
each batch is mostly one product category, keeping the model's judgments
comparable rather than jumping between unrelated products call to call.

Only processes a priority subset of page_type categories by default (the
ones that are actually campaign/marketing content) — run with no arguments
to work through DEFAULT_CATEGORIES in priority order; pass --categories to
target specific ones instead. If a rate limit is hit partway through, the
run stops cleanly (everything analyzed so far is already committed) rather
than burning through retries — re-run later, or against a different
category, to pick up where it left off.

Uses src/llm_client.py, so this works with either Groq or Gemini depending
on the LLM_PROVIDER env var — no code change needed to switch.

Hallucination check: the model must return a verbatim quote from the source
text backing each of "tone" and "value_proposition". Each quote is checked
against that page's raw_text after the call — if it doesn't actually
appear, that's flagged loudly rather than silently trusted.

Tone vocabulary: prompted explicitly to use business-relevant descriptors
(e.g. "value-led, price-focused", "trust & security-focused") rather than
academic/linguistic terms — this is meant to be read by marketing
stakeholders, not analyzed further as text.

Handles multi-language input directly — French/Dutch text goes straight to
the model, English output is enforced by the prompt. No separate
translation step.

Setup:
    pip install openai python-dotenv --break-system-packages
    export LLM_PROVIDER=groq        # or "gemini"
    export GROQ_API_KEY=gsk_...     # or GEMINI_API_KEY, matching LLM_PROVIDER
    (free Groq key: https://console.groq.com — free Gemini key: https://aistudio.google.com)

Usage:
    python analyst.py                                   # DEFAULT_CATEGORIES, in priority order
    python analyst.py --categories savings_investments   # just one category
    python analyst.py --categories all                   # every page_type, no filter
"""

import argparse
import json
import re
import sqlite3
import sys

import openai

from llm_client import get_client

TEMPERATURE = 0.2  # low — this is extraction, not creative writing; consistency over variety
BATCH_SIZE = 8  # pages per LLM call — tune down if a provider's context window complains
CHARS_PER_PAGE = 1200  # per-page raw_text cap when batching — enough for tone/value-prop, not a novel

# Run in this priority order by default — the categories that are actually campaign/marketing
# content, most important first. Categories like utility_security_legal, marketing_editorial,
# customer_segments, daily_services_other are excluded by default (legal pages, contact pages,
# news articles — not campaign content, not worth spending LLM calls on).
DEFAULT_CATEGORIES = [
    "current_accounts",
    "youth_account",
    "payment_cards",
    "savings_investments",
]

SYSTEM_PROMPT = """You are analysing bank marketing/product web pages for a competitive \
comparison study read by ING's MARKETING TEAM, not technical staff. Page text may be in \
English, French, or Dutch — read each in its original language, but ALWAYS respond in English.

TONE VOCABULARY — use descriptors a marketer would find immediately useful for a competitive \
comparison, not academic linguistics terms. Good examples: "value-led, price-focused", \
"trust & security-focused", "premium, aspirational", "youth & lifestyle-led", "simplicity-led, \
minimal jargon", "urgency-driven, limited-time offers", "family-oriented, reassuring". Avoid \
vague or purely technical terms like "formal register" or "imperative mood" — describe the \
FEEL of the page the way a marketer would.

GROUNDING — to avoid inventing claims:
- "tone_evidence" and "value_proposition_evidence" must each be an exact, verbatim quote \
copied directly from that page's text (under 20 words) supporting your "tone" and \
"value_proposition" answers. Copy exactly — do not paraphrase, translate, or clean it up.
- "topics" must only include topics clearly present in the text itself, not general knowledge \
about the bank.

You will receive several pages in one request, each marked with its PAGE_ID. Respond with ONLY \
a JSON object, no other text, no markdown fences, matching exactly:
{
  "results": [
    {
      "page_id": <the integer PAGE_ID exactly as given>,
      "tone": "<2-5 words, business-relevant, e.g. 'value-led, price-focused'>",
      "tone_evidence": "<exact verbatim quote from that page's text>",
      "value_proposition": "<one sentence, in English, what's offered and why>",
      "value_proposition_evidence": "<exact verbatim quote from that page's text>",
      "topics": ["<keyword1>", "<keyword2>", "..."]
    }
  ]
}
One result object per page given, in any order, matched back by page_id."""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def evidence_verified(evidence: str, source_text: str) -> bool:
    """True if the quoted evidence genuinely appears in the source text
    (whitespace/case-insensitive substring match). False means the model
    likely invented or paraphrased rather than quoted."""
    if not evidence or not source_text:
        return False
    return _normalize(evidence) in _normalize(source_text)


def _build_batch_prompt(pages: list[sqlite3.Row]) -> str:
    parts = []
    for p in pages:
        text = (p["raw_text"] or "")[:CHARS_PER_PAGE]
        parts.append(
            f"PAGE_ID: {p['id']}\nBANK: {p['bank']}\nPAGE_TYPE: {p['page_type'] or 'unknown'}\n"
            f"TEXT: {text}"
        )
    return "\n---\n".join(parts)


def analyze_batch(client, model: str, pages: list[sqlite3.Row]) -> list[dict]:
    response = client.chat.completions.create(
        model=model,
        max_tokens=400 * len(pages) + 200,  # scale with batch size
        temperature=TEMPERATURE,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_batch_prompt(pages)},
        ],
    )
    text = response.choices[0].message.content.strip()
    return json.loads(text).get("results", [])


def _fetch_rows(conn: sqlite3.Connection, categories: list[str] | None) -> list[sqlite3.Row]:
    base_query = (
        "SELECT id, bank, page_url, page_type, raw_text FROM pages "
        "WHERE (tone IS NULL OR tone = '' OR tone = 'error, technical' OR tone = 'error page, no content') AND raw_text IS NOT NULL AND raw_text != ''"
    )
    params: list = []

    if categories:  # None or [] both mean "no filter, everything"
        placeholders = ", ".join("?" for _ in categories)
        base_query += f" AND page_type IN ({placeholders})"
        params.extend(categories)
        # Respect the given list's order as processing priority, unmatched/other
        # categories (only relevant when categories is None, so unused here) go last.
        case_parts = " ".join(f"WHEN ? THEN {i}" for i in range(len(categories)))
        base_query += f" ORDER BY CASE page_type {case_parts} ELSE {len(categories)} END, bank"
        params.extend(categories)
    else:
        base_query += " ORDER BY page_type, bank"  # groups same-category pages into the same batch

    return conn.execute(base_query, params).fetchall()


def run(db_path: str = "data/bank_analysis.db", categories: list[str] | None = None) -> None:
    if categories is None:
        categories = DEFAULT_CATEGORIES
    elif categories == ["all"]:
        categories = None  # explicit opt-out of filtering

    try:
        client, model = get_client()
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row

    rows = _fetch_rows(conn, categories)

    if not rows:
        scope = ", ".join(categories) if categories else "all categories"
        print(f"Nothing to analyze for {scope} — already done, or none scraped yet.")
        conn.close()
        return

    batches = [rows[i:i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]
    scope = ", ".join(categories) if categories else "all categories"
    print(f"Analyzing {len(rows)} page(s) [{scope}] in {len(batches)} batch(es) of up to "
          f"{BATCH_SIZE} via {model}...")

    unverified_count = 0
    analyzed_count = 0
    stopped_early = False

    for batch_num, batch in enumerate(batches, start=1):
        by_id = {row["id"]: row for row in batch}
        try:
            results = analyze_batch(client, model, batch)
        except openai.RateLimitError as exc:
            print(f"\n[stopped] Rate limit hit on batch {batch_num}/{len(batches)}: {exc}",
                  file=sys.stderr)
            print(f"{analyzed_count} page(s) already analyzed and saved. Re-run later (same "
                  f"command) to continue where this left off, or switch LLM_PROVIDER.",
                  file=sys.stderr)
            stopped_early = True
            break
        except Exception as exc:
            print(f"[fail] batch {batch_num}/{len(batches)}: {exc} — "
                  f"these {len(batch)} page(s) stay unanalyzed, will retry next run",
                  file=sys.stderr)
            continue

        for result in results:
            page_id = result.get("page_id")
            row = by_id.get(page_id)
            if row is None:
                print(f"[warn] batch {batch_num}: got a result for unknown page_id {page_id}, skipping",
                      file=sys.stderr)
                continue

            tone_ok = evidence_verified(result.get("tone_evidence", ""), row["raw_text"])
            vp_ok = evidence_verified(result.get("value_proposition_evidence", ""), row["raw_text"])

            conn.execute(
                "UPDATE pages SET tone = ?, value_proposition = ? WHERE id = ?",
                (result.get("tone", ""), result.get("value_proposition", ""), page_id),
            )
            for topic in result.get("topics", []):
                conn.execute(
                    "INSERT OR IGNORE INTO page_topics (page_id, topic) VALUES (?, ?)",
                    (page_id, topic),
                )
            conn.commit()

            status = "verified" if (tone_ok and vp_ok) else "UNVERIFIED"
            analyzed_count += 1
            print(f"[ok] {row['bank']} — {row['page_url']} -> tone: {result.get('tone')} [{status}]")

            if not tone_ok:
                unverified_count += 1
                print(f"  [warn] tone_evidence not found verbatim — "
                      f"quote: {result.get('tone_evidence', '')!r}", file=sys.stderr)
            if not vp_ok:
                unverified_count += 1
                print(f"  [warn] value_proposition_evidence not found verbatim — "
                      f"quote: {result.get('value_proposition_evidence', '')!r}", file=sys.stderr)

        print(f"[batch {batch_num}/{len(batches)} done]")

    conn.close()
    print(f"\nDone. {analyzed_count}/{len(rows)} page(s) analyzed in {db_path}"
          + (" (stopped early — see above)" if stopped_early else ""))
    if unverified_count:
        print(f"[warn] {unverified_count} field(s) across this run had evidence that couldn't be "
              f"matched to the source text — worth a manual spot-check on those pages.",
              file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tone/value_proposition extraction.")
    parser.add_argument(
        "--categories", nargs="+", default=None,
        help=f"page_type categories to analyze, in priority order (space-separated). "
             f"Default: {' '.join(DEFAULT_CATEGORIES)}. Pass 'all' for no filter.",
    )
    args = parser.parse_args()
    run(categories=args.categories)