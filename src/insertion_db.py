import sqlite3


def save_to_sqlite(url, bank, data, db_path="./data/bank_analysis.db"):
    """Inserts scraped marketing metrics into SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure foreign keys are enabled
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Insert page record
    query = """
    INSERT INTO pages (
        bank, page_url, page_type, language, headline, subtitle,
        has_numeric_offer, cta_text, cta_count, image_count, raw_text, source_type
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(page_url) DO UPDATE SET
        scrape_date=excluded.scrape_date,
        headline=excluded.headline,
        subtitle=excluded.subtitle,
        has_numeric_offer=excluded.has_numeric_offer,
        cta_text=excluded.cta_text,
        cta_count=excluded.cta_count,
        image_count=excluded.image_count,
        raw_text=excluded.raw_text;
    """

    record = (
        bank,
        url,
        "youth_account",
        "en",
        data["headline"],
        data["subtitle"],
        data["has_numeric_offer"],
        data["cta_text"],
        data["cta_count"],
        data["image_count"],
        data["raw_text"],
        "html",
    )

    cursor.execute(query, record)
    conn.commit()
    conn.close()
    print(f"Data successfully saved to {db_path}")
