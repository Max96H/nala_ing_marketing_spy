"""
ING Banking Campaigns Comparator — Assistant (chatbot layer)

An interactive command-line chatbot that answers questions about the
scraped campaign data — grounded in data/bank_analysis.db. Uses Groq or
Gemini (via llm_client.py) depending on LLM_PROVIDER.

Context is now BOUNDED regardless of database size — at 3,000+ pages,
dumping every row into the prompt blew past reasonable context limits (and
cost/latency). Each question now gets:
  1. A small summary block (page/bank/category counts) — always included,
     stays cheap no matter how large the database grows.
  2. Up to 15 pages matched to the question's keywords against
     bank/page_type/tone/value_proposition/headline/topics.
  3. If no keywords match (a broad/general question), a representative
     sample instead — one page per bank — so there's still something
     concrete to answer from.
  4. Recent watchdog changes (already a small table).

This keeps answers grounded (same evidence-based principle as before) while
staying well within any provider's context window at any database size.

Trustworthiness note: a conversational answer can't be verified the
mechanical way analyst.py verifies its quotes, so this relies on
prompting — every claim must be tied to a specific bank/page shown in
context, general brand knowledge is forbidden, and "not in the data" is
required when context doesn't cover the question. Temperature stays low.

Setup:
    pip install openai python-dotenv --break-system-packages
    export LLM_PROVIDER=groq          # or "gemini"
    export GROQ_API_KEY=gsk_...       # or GEMINI_API_KEY, matching LLM_PROVIDER

Usage:
    python assistant.py
    (then just type questions; type 'exit' or 'quit' to stop)
"""

import re
import sqlite3
import sys

from llm_client import get_client

TEMPERATURE = 0.3  # low-ish — factual grounded answers, not creative ones
MAX_RELEVANT_PAGES = 15

SYSTEM_PROMPT = """You are a marketing analyst assistant for ING, helping ING staff understand how \
their bank's campaigns compare to competitors.

You will be given a SUMMARY of the full dataset (counts, not full detail) plus a SUBSET of \
individual pages most relevant to the current question — not the entire database. Ground every \
answer in this data only:
- Every specific claim you make must be traceable to a bank/page shown below — name which
bank(s) it comes from.
- Do NOT draw on general knowledge, assumptions, or reputation about these banks beyond what's \
in the data below, even if you're confident it's true.
- If the specific pages needed to answer aren't in the subset shown, say so plainly and suggest \
the question be narrowed (e.g. to a specific bank or product category) rather than guessing.
- The summary counts ARE reliable for aggregate questions ("how many pages do we have for KBC") \
even when the specific pages aren't in the detailed subset.
- When comparing banks, base it directly on the tone/value proposition wording shown — don't \
rely on brand reputation.

Keep answers concise and business-relevant; this is for people deciding on ING's marketing \
strategy, not a technical audience. Always respond in English, even though some of the source \
data is in French or Dutch."""

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "in", "on", "for", "to", "and", "or",
    "how", "what", "which", "does", "do", "did", "compare", "compared", "with", "vs", "versus",
    "our", "their", "than", "we", "us", "it", "its", "this", "that", "these", "those", "about",
}


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS and len(w) > 2]


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def build_summary(conn: sqlite3.Connection) -> str:
    total = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    analyzed = conn.execute(
        "SELECT COUNT(*) FROM pages WHERE tone IS NOT NULL AND tone != ''"
    ).fetchone()[0]

    bank_counts = conn.execute(
        "SELECT bank, COUNT(*) FROM pages WHERE tone IS NOT NULL AND tone != '' GROUP BY bank"
    ).fetchall()
    category_counts = conn.execute(
        "SELECT page_type, COUNT(*) FROM pages WHERE tone IS NOT NULL AND tone != '' "
        "GROUP BY page_type"
    ).fetchall()

    lines = [
        f"## Dataset summary",
        f"{total} total pages scraped, {analyzed} analyzed (tone/value proposition filled in).",
        "Analyzed pages by bank: " + ", ".join(f"{b} ({c})" for b, c in bank_counts),
        "Analyzed pages by category: " + ", ".join(f"{t or 'uncategorized'} ({c})" for t, c in category_counts),
    ]
    return "\n".join(lines)


def _page_detail_lines(conn: sqlite3.Connection, pages: list[sqlite3.Row]) -> str:
    if not pages:
        return ""

    page_ids = [p["id"] for p in pages]
    placeholders = ", ".join("?" for _ in page_ids)

    topics_by_page = {}
    for row in conn.execute(
        f"SELECT page_id, topic FROM page_topics WHERE page_id IN ({placeholders})", page_ids
    ):
        topics_by_page.setdefault(row["page_id"], []).append(row["topic"])

    lines = ["\n## Relevant pages for this question\n"]
    for r in pages:
        topics = topics_by_page.get(r["id"], [])
        lines.append(
            f"- **{r['bank']} — {r['page_type'] or 'uncategorized'}** ({r['language']}, "
            f"scraped {r['scrape_date']})\n"
            f"  Headline: {r['headline']!r}\n"
            f"  Tone: {r['tone'] or 'not analyzed'} | "
            f"Value proposition: {r['value_proposition'] or 'not analyzed'}\n"
            f"  Topics: {', '.join(topics) if topics else 'none'} | "
            f"Numeric offer: {bool(r['has_numeric_offer'])} | CTA: {r['cta_text']!r}\n"
        )
    return "\n".join(lines)


def find_relevant_pages(conn: sqlite3.Connection, query: str) -> list[sqlite3.Row]:
    """Keyword match against bank/category/tone/value_proposition/headline —
    simple, explainable, and enough at this scale without adding a vector
    search dependency. Returns [] if the query has no usable keywords or
    nothing matches, so the caller can fall back to a representative sample."""
    words = _tokenize(query or "")
    if not words:
        return []

    candidates = conn.execute(
        "SELECT id, bank, page_url, page_type, language, scrape_date, headline, tone, "
        "value_proposition, has_numeric_offer, cta_text FROM pages "
        "WHERE tone IS NOT NULL AND tone != ''"
    ).fetchall()

    scored = []
    for p in candidates:
        blob = " ".join(str(p[k] or "") for k in
                         ("bank", "page_type", "tone", "value_proposition", "headline")).lower()
        score = sum(1 for w in words if w in blob)
        if score > 0:
            scored.append((score, p))

    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:MAX_RELEVANT_PAGES]]


def representative_sample(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Fallback for broad/general questions with no keyword match — one
    page per bank (most recently scraped) so there's still something
    concrete, rather than nothing."""
    return conn.execute(
        "SELECT id, bank, page_url, page_type, language, scrape_date, headline, tone, "
        "value_proposition, has_numeric_offer, cta_text FROM pages "
        "WHERE tone IS NOT NULL AND tone != '' "
        "GROUP BY bank HAVING MAX(scrape_date)"
    ).fetchall()


def load_context(conn: sqlite3.Connection, query: str | None = None) -> str:
    conn.row_factory = sqlite3.Row

    if conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0] == 0:
        return "No page data has been scraped yet."

    summary = build_summary(conn)

    relevant = find_relevant_pages(conn, query or "")
    used_fallback = False
    if not relevant:
        relevant = representative_sample(conn)
        used_fallback = True

    detail = _page_detail_lines(conn, relevant)
    if used_fallback and relevant:
        detail += ("\n(No specific keyword match for this question — showing one representative "
                    "page per bank instead. Ask about a specific bank or product category for "
                    "more targeted detail.)\n")

    changes_block = ""
    if _table_exists(conn, "changes"):
        changes = conn.execute(
            "SELECT bank, page_url, field_changed, previous_value, current_value, detected_date "
            "FROM changes ORDER BY detected_date DESC LIMIT 20"
        ).fetchall()
        if changes:
            changes_block = "\n## Recently detected changes (most recent first)\n" + "\n".join(
                f"- {c['bank']} — {c['page_url']} — {c['field_changed']} changed from "
                f"{c['previous_value']!r} to {c['current_value']!r} (detected {c['detected_date']})"
                for c in changes
            )

    return summary + detail + changes_block


def run(db_path: str = "data/bank_analysis.db") -> None:
    try:
        client, model = get_client()
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)

    print("ING Campaign Comparator Assistant — ask a question, or type 'exit' to quit.\n")

    history = []
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        # Context rebuilt fresh per question, scoped to that question — not once for
        # the whole conversation — so it stays bounded no matter how the database grows.
        context = load_context(conn, question)
        history.append({"role": "user", "content": question})
        messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{context}"}] + history

        response = client.chat.completions.create(
            model=model, max_tokens=1000, temperature=TEMPERATURE, messages=messages,
        )
        answer = response.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": answer})
        print(f"\nAssistant: {answer}\n")

    conn.close()


if __name__ == "__main__":
    run()