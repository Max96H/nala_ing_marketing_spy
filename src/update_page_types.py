import argparse
from pathlib import Path
import re
import sqlite3
import yaml

# Project directory paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "bank_analysis.db"
YAML_PATH = ROOT_DIR / "config" / "page_types.yaml"


def load_category_rules(yaml_path: Path) -> dict:
    """Loads classification rules from the page_types.yaml file."""
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML config file not found at: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("categories", {})


def classify_page(
    url: str,
    headline: str | None,
    raw_text: str | None,
    rules: dict,
) -> str:
    """Classifies a single page using URL path matching first, then content keywords."""
    url_lower = url.lower()
    text_corpus = f"{headline or ''} {raw_text or ''}".lower()

    # Pass 1: Strict URL pattern matching (Order in YAML is respected)
    for category_key, criteria in rules.items():
        for pattern in criteria.get("url_patterns", []):
            pattern_clean = pattern.strip().lower()
            if pattern_clean in url_lower:
                return category_key

    # Pass 2: Keyword matching on headline / page text fallback
    for category_key, criteria in rules.items():
        for kw in criteria.get("keywords", []):
            kw_clean = kw.strip().lower()
            # Match whole word to avoid false positives in substrings
            if re.search(r"\b" + re.escape(kw_clean) + r"\b", text_corpus):
                return category_key

    # Fallback default if no patterns or keywords matched
    return "other_marketing"


def update_database_page_types(db_path: Path, yaml_path: Path):
    """Fetches pages from SQLite, classifies them, and bulk updates page_type."""
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return

    print(f"📖 Loading taxonomy from: {yaml_path}")
    rules = load_category_rules(yaml_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query all pages from database
    cursor.execute("SELECT id, page_url, headline, raw_text FROM pages")
    rows = cursor.fetchall()

    if not rows:
        print("⚠️ No pages found in database to update.")
        conn.close()
        return

    print(f"🔄 Classifying {len(rows)} database records...")

    updates = []
    stats = {}

    for page_id, page_url, headline, raw_text in rows:
        category = classify_page(page_url, headline, raw_text, rules)
        updates.append((category, page_id))
        stats[category] = stats.get(category, 0) + 1

    # Execute bulk update inside a transaction
    cursor.executemany(
        "UPDATE pages SET page_type = ? WHERE id = ?", updates
    )
    conn.commit()
    conn.close()

    print("\n✅ Successfully updated database!")
    print("--- Categorization Summary ---")
    for cat, count in sorted(
        stats.items(), key=lambda item: item[1], reverse=True
    ):
        label = rules.get(cat, {}).get("label", cat)
        print(f"  • {cat} ({label}): {count} pages")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update SQLite page_type fields based on page_types.yaml."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help="Path to SQLite database file.",
    )
    parser.add_argument(
        "--yaml",
        type=Path,
        default=YAML_PATH,
        help="Path to page_types.yaml configuration file.",
    )

    args = parser.parse_args()
    update_database_page_types(args.db, args.yaml)