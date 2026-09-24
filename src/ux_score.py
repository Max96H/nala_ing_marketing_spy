"""
ING Banking Campaigns Comparator — UI/UX Score pipeline

Computes a deterministic UI/UX score (0-10) per page, grounded in named,
established UX/accessibility principles rather than an arbitrary rubric.
No LLM involved — every sub-score comes from fields already scraped
(headline, subtitle, cta_text, cta_count, image_count, has_numeric_offer,
raw_text, and the page's dominant colours from page_colors). Independent
of analyst.py — can run on any scraped page, analyzed or not.

Six sub-scores, each tied to a specific principle:

  value_clarity (0-2)         Concrete, quantified offers reduce ambiguity
                               for the reader (conversion-copywriting best
                               practice: specific numbers beat vague claims).
  cta_clarity (0-2)           A clear call-to-action helps orientation
                               (Nielsen's "visibility of system status" /
                               clear affordance); too many competing CTAs
                               hurts it (Hick's Law — more choices, slower,
                               worse decisions).
  content_hierarchy (0-1)     A headline AND a supporting subtitle give the
                               page a visual hierarchy a reader can scan
                               (Nielsen's heuristics, "recognition rather
                               than recall").
  scannability (0-1)          Body text in a healthy length range — long
                               enough to inform, short enough to scan
                               (plain-language / readability best practice).
  visual_balance (0-2)        Some supporting imagery, not an overwhelming
                               wall of it (Nielsen's "aesthetic and
                               minimalist design").
  accessibility_contrast (0-2) WCAG 2.1 contrast ratio between the page's
                               two most dominant colours: >=4.5:1 (AA,
                               normal text) scores full, >=3:1 (AA, large
                               text/UI only) scores half, below fails.

Results (including the sub-scores, not just the total) are written to a
ux_scores table (self-created here, not in the team's schema.sql) so the
"why" behind a score is always inspectable, not a black box.

Usage:
    python ux_score.py
    python ux_score.py --categories current_accounts youth_account  # optional filter
"""

import argparse
import colorsys
import sqlite3
import sys


def _hex_to_rgb(hexcode: str):
    hexcode = hexcode.strip().lstrip("#")
    if len(hexcode) != 6:
        return None
    try:
        return tuple(int(hexcode[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _relative_luminance(hexcode: str) -> float | None:
    rgb = _hex_to_rgb(hexcode)
    if rgb is None:
        return None

    def channel(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex_a: str, hex_b: str) -> float | None:
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    if la is None or lb is None:
        return None
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def score_value_clarity(page: sqlite3.Row) -> float:
    return 2.0 if page["has_numeric_offer"] else 0.0


def score_cta_clarity(page: sqlite3.Row) -> float:
    if not page["cta_text"]:
        return 0.0
    cta_count = page["cta_count"] or 0
    if cta_count > 6:  # Hick's Law — too many competing calls-to-action
        return 1.0
    return 2.0


def score_content_hierarchy(page: sqlite3.Row) -> float:
    has_headline = bool((page["headline"] or "").strip())
    has_subtitle = bool((page["subtitle"] or "").strip())
    if has_headline and has_subtitle:
        return 1.0
    if has_headline or has_subtitle:
        return 0.5
    return 0.0


def score_scannability(page: sqlite3.Row) -> float:
    word_count = len((page["raw_text"] or "").split())
    return 1.0 if 40 <= word_count <= 800 else 0.0


def score_visual_balance(page: sqlite3.Row) -> float:
    images = page["image_count"] or 0
    if 1 <= images <= 20:
        return 2.0
    if images > 20:
        return 1.0
    return 0.0  # zero images — nothing breaking up the text


def score_accessibility_contrast(colors: list[str]) -> float:
    if len(colors) < 2:
        return 1.0  # not enough data to assess — neutral, not penalized
    ratio = _contrast_ratio(colors[0], colors[1])
    if ratio is None:
        return 1.0
    if ratio >= 4.5:  # WCAG 2.1 AA, normal text
        return 2.0
    if ratio >= 3.0:  # WCAG 2.1 AA, large text/UI components only
        return 1.0
    return 0.0


def score_page(page: sqlite3.Row, colors: list[str]) -> dict:
    sub_scores = {
        "value_clarity": score_value_clarity(page),
        "cta_clarity": score_cta_clarity(page),
        "content_hierarchy": score_content_hierarchy(page),
        "scannability": score_scannability(page),
        "visual_balance": score_visual_balance(page),
        "accessibility_contrast": score_accessibility_contrast(colors),
    }
    sub_scores["total_score"] = round(sum(sub_scores.values()), 1)
    return sub_scores


def init_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ux_scores (
            page_id INTEGER PRIMARY KEY,
            bank TEXT,
            page_url TEXT,
            page_type TEXT,
            value_clarity REAL,
            cta_clarity REAL,
            content_hierarchy REAL,
            scannability REAL,
            visual_balance REAL,
            accessibility_contrast REAL,
            total_score REAL
        )
    """)
    conn.commit()


def run(db_path: str = "data/bank_analysis.db", categories: list[str] | None = None) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_table(conn)

    query = "SELECT id, bank, page_url, page_type, headline, subtitle, cta_text, cta_count, " \
            "image_count, has_numeric_offer, raw_text FROM pages"
    params: list = []
    if categories and categories != ["all"]:
        placeholders = ", ".join("?" for _ in categories)
        query += f" WHERE page_type IN ({placeholders})"
        params = categories

    pages = conn.execute(query, params).fetchall()
    if not pages:
        print("No pages found to score.")
        conn.close()
        return

    print(f"Scoring {len(pages)} page(s)...")
    for page in pages:
        colors = [r["color_hex"] for r in conn.execute(
            "SELECT color_hex FROM page_colors WHERE page_id = ?", (page["id"],)
        ).fetchall()]

        scores = score_page(page, colors)
        conn.execute(
            "INSERT OR REPLACE INTO ux_scores "
            "(page_id, bank, page_url, page_type, value_clarity, cta_clarity, "
            "content_hierarchy, scannability, visual_balance, accessibility_contrast, total_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (page["id"], page["bank"], page["page_url"], page["page_type"],
             scores["value_clarity"], scores["cta_clarity"], scores["content_hierarchy"],
             scores["scannability"], scores["visual_balance"], scores["accessibility_contrast"],
             scores["total_score"]),
        )

    conn.commit()
    conn.close()
    print(f"Done. {len(pages)} page(s) scored in {db_path}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute deterministic UI/UX scores for pages.")
    parser.add_argument("--categories", nargs="+", default=None,
                         help="page_type categories to score (default: all pages).")
    args = parser.parse_args()
    run(categories=args.categories)