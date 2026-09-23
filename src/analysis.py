"""
ING Banking Campaigns Comparator — Analysis

Reads the analyzed pages (must have been through analyst.py first — needs
tone/value_proposition filled in, and page_topics populated) from
data/bank_analysis.db and computes three things, writing each into its own
table in the same database:

  - `positioning`   — one (x, y) point per page, from TF-IDF + PCA over
                       tone + value_proposition + topics. Pages with similar
                       language end up near each other.
  - `radar_scores`  — one row per (bank, dimension), five dimensions per
                       bank matching the brief: promo_intensity (tone &
                       messaging proxy), visual_richness, colour_vibrancy,
                       content_density (layout & structure proxy), and
                       topic_diversity (topics & value proposition proxy).
                       All normalized 0-1 across banks so they're
                       comparable on one radar chart.
  - `gaps`          — topics used by at least one bank but NOT by ING —
                       candidate whitespace/opportunity flags.
  - `recommendations` — one short, business-facing recommendation per gap,
                       generated in a single batched LLM call (the gap list
                       is small even at thousands of pages, so this stays
                       cheap regardless of scrape size).

Topics and colours are read by joining the pages table against the
page_topics and page_colors junction tables (the team's normalized
schema) — not from flat string columns.

These are proxy metrics built from what's actually scraped (image count,
numeric offers, colour saturation, text length, topic overlap) — not a
claim of ground truth. Worth saying so explicitly in the data-audience
writeup.

Usage:
    python analysis.py
"""

import colorsys
import json
import sqlite3
import sys

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer

from llm_client import get_client

DB_PATH = "data/bank_analysis.db"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(hexcode: str):
    hexcode = hexcode.strip().lstrip("#")
    if len(hexcode) != 6:
        return None
    try:
        return tuple(int(hexcode[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _avg_saturation(hex_list: list) -> float | None:
    if not hex_list:
        return None
    sats = []
    for hexcode in hex_list:
        rgb = _hex_to_rgb(hexcode)
        if rgb:
            _, s, _ = colorsys.rgb_to_hsv(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
            sats.append(s)
    return sum(sats) / len(sats) if sats else None


def _normalize(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return series.fillna(0.5) * 0 + 0.5
    return (series.fillna(series.mean()) - lo) / (hi - lo)


def load_pages_with_joins(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load pages plus their topics and colours from the junction tables,
    as list columns — this replaces the old flat topics/dominant_colors
    string columns from the earlier schema."""
    pages = pd.read_sql_query("SELECT * FROM pages", conn)
    if pages.empty:
        return pages

    topics = pd.read_sql_query("SELECT page_id, topic FROM page_topics", conn)
    colors = pd.read_sql_query("SELECT page_id, color_hex FROM page_colors", conn)

    topics_by_page = topics.groupby("page_id")["topic"].apply(list) if not topics.empty else pd.Series(dtype=object)
    colors_by_page = colors.groupby("page_id")["color_hex"].apply(list) if not colors.empty else pd.Series(dtype=object)

    pages["topics_list"] = pages["id"].map(topics_by_page).apply(lambda v: v if isinstance(v, list) else [])
    pages["colors_list"] = pages["id"].map(colors_by_page).apply(lambda v: v if isinstance(v, list) else [])
    return pages


# ---------------------------------------------------------------------------
# Positioning map
# ---------------------------------------------------------------------------

def compute_positioning(df: pd.DataFrame) -> pd.DataFrame:
    text_blob = (
        df["tone"].fillna("") + " " +
        df["value_proposition"].fillna("") + " " +
        df["topics_list"].apply(lambda t: " ".join(t))
    )
    if text_blob.str.strip().eq("").all():
        return pd.DataFrame()

    vectorizer = TfidfVectorizer(max_features=200, stop_words="english")
    matrix = vectorizer.fit_transform(text_blob)

    n_components = min(2, matrix.shape[0] - 1, matrix.shape[1])
    if n_components < 2:
        print("[warn] Not enough analyzed pages yet for a 2D positioning map "
              "(need at least 3 pages with tone/topics filled in).", file=sys.stderr)
        return pd.DataFrame()

    coords = PCA(n_components=2, random_state=42).fit_transform(matrix.toarray())
    result = df[["bank", "page_url", "page_type"]].copy()
    result["pca_x"] = coords[:, 0]
    result["pca_y"] = coords[:, 1]
    return result


# ---------------------------------------------------------------------------
# Radar scores
# ---------------------------------------------------------------------------

def compute_radar(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for bank, group in df.groupby("bank"):
        promo = pd.to_numeric(group["has_numeric_offer"], errors="coerce").fillna(0).mean()
        visuals = pd.to_numeric(group["image_count"], errors="coerce").mean()
        sat_values = group["colors_list"].apply(_avg_saturation).dropna()
        colour = sat_values.mean() if len(sat_values) else None
        density = group["raw_text"].fillna("").apply(lambda t: len(t.split())).mean()

        all_topics = [t for topics in group["topics_list"] for t in topics]
        diversity = (len(set(all_topics)) / len(group)) if len(group) else 0.0

        records.append({
            "bank": bank,
            "promo_intensity": promo,
            "visual_richness": visuals,
            "colour_vibrancy": colour,
            "content_density": density,
            "topic_diversity": diversity,
        })

    radar_df = pd.DataFrame(records).set_index("bank")
    for col in ["visual_richness", "colour_vibrancy", "content_density", "topic_diversity"]:
        radar_df[col] = _normalize(radar_df[col])
    radar_df = radar_df.reset_index()

    long_rows = []
    for _, row in radar_df.iterrows():
        for dim in ["promo_intensity", "visual_richness", "colour_vibrancy",
                    "content_density", "topic_diversity"]:
            long_rows.append({"bank": row["bank"], "dimension": dim, "score": row[dim]})
    return pd.DataFrame(long_rows)


# ---------------------------------------------------------------------------
# Gap finder — topics other banks use that ING doesn't
# ---------------------------------------------------------------------------

def find_gaps(df: pd.DataFrame, focus_bank: str = "ING") -> pd.DataFrame:
    bank_topics = {}
    for _, row in df.iterrows():
        bank_topics.setdefault(row["bank"], set()).update(row["topics_list"])

    all_topics = set()
    for topics in bank_topics.values():
        all_topics |= topics

    focus_topics = bank_topics.get(focus_bank, set())
    gaps = []
    for topic in sorted(all_topics):
        banks_using = sorted(b for b, t in bank_topics.items() if topic in t)
        if topic not in focus_topics and banks_using:
            gaps.append({"topic": topic, "used_by": ", ".join(banks_using)})
    return pd.DataFrame(gaps)


# ---------------------------------------------------------------------------
# Recommendations — one short business recommendation per gap
# ---------------------------------------------------------------------------

RECOMMENDATION_SYSTEM_PROMPT = """You are a marketing strategy advisor for ING, writing for \
business stakeholders (not technical staff). You'll be given a list of topics that ING's \
competitor banks use in their campaigns but ING currently does not.

For each topic, write ONE short, concrete, business-facing recommendation (1-2 sentences) on \
whether and how ING might explore it. Be measured, not hype: these are candidates worth a look, \
not proven wins — phrase recommendations as "worth exploring" / "consider testing", not as \
certainties. If a topic seems like a poor fit for ING specifically (e.g. clashes with a bank's \
positioning), it's fine to say so plainly rather than force a positive spin.

Respond with ONLY a JSON object, no other text, no markdown fences:
{"recommendations": [{"topic": "<topic exactly as given>", "recommendation": "<1-2 sentences>"}]}"""


def generate_recommendations(gaps: pd.DataFrame, focus_bank: str = "ING") -> pd.DataFrame:
    """One batched LLM call covering every gap at once — the gap list stays
    small (one row per missing topic) regardless of how many pages were
    scraped, so this is cheap even at thousands of pages."""
    if gaps.empty:
        return pd.DataFrame()

    try:
        client, model = get_client()
    except (RuntimeError, ValueError) as exc:
        print(f"[warn] skipping recommendations — {exc}", file=sys.stderr)
        return pd.DataFrame()

    gap_list = "\n".join(f"- {row['topic']} (used by: {row['used_by']})"
                          for _, row in gaps.iterrows())
    prompt = f"Topics {focus_bank} is missing that competitors use:\n{gap_list}"

    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=200 * len(gaps) + 200,
            temperature=0.4,  # a little more room than extraction — this is advisory phrasing
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        results = json.loads(response.choices[0].message.content.strip()).get("recommendations", [])
    except Exception as exc:
        print(f"[warn] recommendation generation failed: {exc}", file=sys.stderr)
        return pd.DataFrame()

    rec_by_topic = {r.get("topic"): r.get("recommendation", "") for r in results}
    out = gaps.copy()
    out["recommendation"] = out["topic"].map(rec_by_topic).fillna("")
    return out


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def save_results(conn: sqlite3.Connection, positioning: pd.DataFrame, radar: pd.DataFrame,
                  gaps: pd.DataFrame, recommendations: pd.DataFrame) -> None:
    if not positioning.empty:
        positioning.to_sql("positioning", conn, if_exists="replace", index=False)
    if not radar.empty:
        radar.to_sql("radar_scores", conn, if_exists="replace", index=False)
    if not gaps.empty:
        gaps.to_sql("gaps", conn, if_exists="replace", index=False)
    if not recommendations.empty:
        recommendations.to_sql("recommendations", conn, if_exists="replace", index=False)
    conn.commit()


def run(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    df = load_pages_with_joins(conn)

    if df.empty:
        print("No pages found — run collect.py first.")
        conn.close()
        return

    analyzed = df[df["tone"].fillna("") != ""]
    if analyzed.empty:
        print("No pages have been analyzed yet (tone/value_proposition are empty). "
              "Run analyst.py first, then re-run this script.")
        conn.close()
        return
    if len(analyzed) < len(df):
        print(f"[note] {len(df) - len(analyzed)} page(s) not yet analyzed — "
              f"proceeding with the {len(analyzed)} that are.")

    positioning = compute_positioning(analyzed)
    radar = compute_radar(analyzed)
    gaps = find_gaps(analyzed)
    recommendations = generate_recommendations(gaps)

    save_results(conn, positioning, radar, gaps, recommendations)
    conn.close()

    print(f"Done. positioning: {len(positioning)} row(s), "
          f"radar_scores: {len(radar)} row(s), gaps: {len(gaps)} row(s), "
          f"recommendations: {len(recommendations)} row(s) — written to {db_path}")


if __name__ == "__main__":
    run()