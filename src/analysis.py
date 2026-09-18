"""
ING Banking Campaigns Comparator — Analysis

Reads the analyzed pages table (must have been through analyst.py first —
this needs tone/value_proposition/topics filled in) and computes three
things, writing each into its own table in campaigns.db:

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

These are proxy metrics built from what we actually scrape (image count,
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

DB_PATH = "db/campaigns.db"


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


def _avg_saturation(dominant_colors: str):
    if not dominant_colors:
        return None
    sats = []
    for part in dominant_colors.split(","):
        rgb = _hex_to_rgb(part)
        if rgb:
            _, s, _ = colorsys.rgb_to_hsv(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
            sats.append(s)
    return sum(sats) / len(sats) if sats else None


def _normalize(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return series.fillna(0.5) * 0 + 0.5
    return (series.fillna(series.mean()) - lo) / (hi - lo)


def _parse_topics(topics_str: str) -> list:
    if not topics_str:
        return []
    try:
        return json.loads(topics_str)
    except (json.JSONDecodeError, TypeError):
        return []


# ---------------------------------------------------------------------------
# Positioning map
# ---------------------------------------------------------------------------

def compute_positioning(df: pd.DataFrame) -> pd.DataFrame:
    text_blob = (df["tone"].fillna("") + " " + df["value_proposition"].fillna("") + " " +
                 df["topics"].fillna(""))
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
        promo = group["has_numeric_offer"].apply(lambda v: 1.0 if str(v) == "True" else 0.0).mean()
        visuals = pd.to_numeric(group["image_count"], errors="coerce").mean()
        sat_values = group["dominant_colors"].apply(_avg_saturation).dropna()
        colour = sat_values.mean() if len(sat_values) else None
        density = group["raw_text"].fillna("").apply(lambda t: len(t.split())).mean()

        all_topics = []
        for t in group["topics"]:
            all_topics += _parse_topics(t)
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

    # long format: one row per (bank, dimension) — easier for charting later
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
        bank_topics.setdefault(row["bank"], set()).update(_parse_topics(row["topics"]))

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
# Storage
# ---------------------------------------------------------------------------

def save_results(conn: sqlite3.Connection, positioning: pd.DataFrame,
                  radar: pd.DataFrame, gaps: pd.DataFrame) -> None:
    if not positioning.empty:
        positioning.to_sql("positioning", conn, if_exists="replace", index=False)
    if not radar.empty:
        radar.to_sql("radar_scores", conn, if_exists="replace", index=False)
    if not gaps.empty:
        gaps.to_sql("gaps", conn, if_exists="replace", index=False)
    conn.commit()


def run(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM pages", conn)

    if df.empty:
        print("No pages found — run collector.py (and merge_db.py, if applicable) first.")
        conn.close()
        return

    analyzed = df[df["tone"].fillna("") != ""]
    if analyzed.empty:
        print("No pages have been analyzed yet (tone/value_proposition/topics are empty). "
              "Run analyst.py first, then re-run this script.")
        conn.close()
        return
    if len(analyzed) < len(df):
        print(f"[note] {len(df) - len(analyzed)} page(s) not yet analyzed — "
              f"proceeding with the {len(analyzed)} that are.")

    positioning = compute_positioning(analyzed)
    radar = compute_radar(analyzed)
    gaps = find_gaps(analyzed)

    save_results(conn, positioning, radar, gaps)
    conn.close()

    print(f"Done. positioning: {len(positioning)} row(s), "
          f"radar_scores: {len(radar)} row(s), gaps: {len(gaps)} row(s) — "
          f"written to {db_path}")


if __name__ == "__main__":
    run()