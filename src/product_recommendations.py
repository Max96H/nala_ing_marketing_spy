"""
ING Banking Campaigns Comparator — Product Recommendations pipeline

For every (ING page, competitor's best page) pair within each analyzed
product category, generates a short, specific, business-facing
recommendation via an LLM — replacing the old rule-based version, which
only had a handful of template phrasings and read as repetitive. The model
is explicitly instructed to vary its phrasing across pairs and ground each
recommendation in the actual tone/value-proposition differences (not just
which boolean signals are present/absent), which is what makes each one
read as specific rather than templated.

Pairs, not pages, are the unit of work here: for each product category,
every ING page in that category is compared against every competitor
bank's best (most substantial) page in that category. At the current
scope (4 priority categories, a handful of ING products each, ~5 banks)
this stays small — dozens of pairs, not thousands — so it's cheap even
though it's LLM-generated per pair rather than a static rule.

Depends on both analyst.py (tone/value_proposition) and ux_score.py (the
UX score used to ground "is ING actually behind here") having already run
for the relevant pages — pairs missing either are skipped with a note.

Usage:
    python product_recommendations.py
"""

import json
import sqlite3
import sys

from llm_client import get_client

TEMPERATURE = 0.6  # higher than extraction — this is advisory phrasing, variety matters here
BATCH_SIZE = 6

SYSTEM_PROMPT = """You are a marketing strategy advisor for ING, writing short recommendations \
for business stakeholders comparing ING's product pages against competitors' equivalent pages.

You will receive several ING-vs-competitor PAIRS in one request, each with both pages' tone, \
value proposition, UX score (0-10, from a deterministic scoring pipeline), whether each has a \
concrete offer, and each page's call-to-action text.

For each pair, write ONE short (1-2 sentence) recommendation for ING. Rules:
- Ground it in the ACTUAL differences shown (tone, value proposition wording, UX score, offer, \
CTA) — reference something specific to that pair, not a generic template.
- VARY your phrasing and sentence openers across different pairs in this batch — do not reuse \
the same opening words or structure repeatedly (avoid starting every recommendation the same way).
- Be measured, not hype: phrase as "worth exploring" / "consider" / "an opportunity to", not as \
certainties. Never invent a promise you're not shown.
- When ING's page is already as strong or stronger, say so plainly and specifically (referencing \
why), rather than a flat "no action needed" every time — vary that phrasing too.

Respond with ONLY a JSON object, no other text, no markdown fences:
{"results": [{"pair_id": <int exactly as given>, "recommendation": "<1-2 sentences>"}]}"""


def init_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS product_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ing_page_id INTEGER,
            competitor_page_id INTEGER,
            recommendation TEXT,
            generated_date TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE(ing_page_id, competitor_page_id)
        )
    """)
    conn.commit()


def pick_best(pages: list[sqlite3.Row]) -> sqlite3.Row:
    """Same heuristic as the frontend's picker — most substantial page by
    content length, a proxy for the flagship page over a thin stub."""
    return max(pages, key=lambda p: len(p["raw_text"] or ""))


def build_pairs(conn: sqlite3.Connection) -> list[dict]:
    pages = conn.execute(
        "SELECT id, bank, page_type, tone, value_proposition, has_numeric_offer, cta_text, "
        "raw_text FROM pages WHERE tone IS NOT NULL AND tone != ''"
    ).fetchall()

    scores = {row["page_id"]: row["total_score"] for row in
              conn.execute("SELECT page_id, total_score FROM ux_scores").fetchall()}

    by_category: dict[str, dict[str, list]] = {}
    for p in pages:
        cat = p["page_type"] or "uncategorized"
        bank = (p["bank"] or "").lower()
        by_category.setdefault(cat, {}).setdefault(bank, []).append(p)

    pairs = []
    for cat, banks in by_category.items():
        ing_pages = banks.get("ing", [])
        if not ing_pages:
            continue
        competitor_bests = {b: pick_best(pgs) for b, pgs in banks.items() if b != "ing"}
        for ing_page in ing_pages:
            for bank, comp_page in competitor_bests.items():
                pairs.append({
                    "ing": ing_page, "ing_score": scores.get(ing_page["id"]),
                    "competitor": comp_page, "competitor_score": scores.get(comp_page["id"]),
                })
    return pairs


def _pair_prompt_line(pair_id: int, pair: dict) -> str:
    ing, comp = pair["ing"], pair["competitor"]
    return (
        f"PAIR_ID: {pair_id}\n"
        f"ING page — tone: {ing['tone']}, value proposition: {ing['value_proposition']}, "
        f"UX score: {pair['ing_score']}, offer: {bool(ing['has_numeric_offer'])}, "
        f"CTA: {ing['cta_text']!r}\n"
        f"{comp['bank']} page — tone: {comp['tone']}, value proposition: {comp['value_proposition']}, "
        f"UX score: {pair['competitor_score']}, offer: {bool(comp['has_numeric_offer'])}, "
        f"CTA: {comp['cta_text']!r}"
    )


def generate_batch(client, model: str, pairs: list[dict]) -> dict[int, str]:
    prompt = "\n---\n".join(_pair_prompt_line(i, p) for i, p in enumerate(pairs))
    response = client.chat.completions.create(
        model=model,
        max_tokens=250 * len(pairs) + 200,
        temperature=TEMPERATURE,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    results = json.loads(response.choices[0].message.content.strip()).get("results", [])
    return {r["pair_id"]: r["recommendation"] for r in results}


def run(db_path: str = "data/bank_analysis.db") -> None:
    try:
        client, model = get_client()
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_table(conn)

    pairs = build_pairs(conn)
    if not pairs:
        print("No ING-vs-competitor pairs found. Run analyst.py first (and ux_score.py for "
              "score grounding).")
        conn.close()
        return

    batches = [pairs[i:i + BATCH_SIZE] for i in range(0, len(pairs), BATCH_SIZE)]
    print(f"Generating recommendations for {len(pairs)} pair(s) in {len(batches)} batch(es) "
          f"via {model}...")

    written = 0
    for batch_num, batch in enumerate(batches, start=1):
        try:
            results = generate_batch(client, model, batch)
        except Exception as exc:
            print(f"[fail] batch {batch_num}/{len(batches)}: {exc}", file=sys.stderr)
            continue

        for local_id, pair in enumerate(batch):
            recommendation = results.get(local_id)
            if not recommendation:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO product_recommendations "
                "(ing_page_id, competitor_page_id, recommendation) VALUES (?, ?, ?)",
                (pair["ing"]["id"], pair["competitor"]["id"], recommendation),
            )
            written += 1
        conn.commit()
        print(f"[batch {batch_num}/{len(batches)} done]")

    conn.close()
    print(f"\nDone. {written}/{len(pairs)} recommendation(s) written to {db_path}.")


if __name__ == "__main__":
    run()