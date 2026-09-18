from datetime import datetime
import json
import re
import sqlite3
from playwright.sync_api import sync_playwright
from config import banks
from extract_colors import extract_page_colors, save_colors_to_sqlite
from cookies import handle_cookie_banner


# Targeted Marketing URL
bank = "kbc"
url = banks[bank]["url"]
outpath = banks[bank]["outpath"]

def extract_marketing_data(page):
    # 1. Headline (Primary H1 or fallback to page title)
    h1_locator = page.locator("h1").first
    headline = h1_locator.inner_text().strip() if h1_locator.count() > 0 else page.title()

    # 2. Subtitle (H2 or first visible paragraph)
    h2_locator = page.locator("h2").first
    if h2_locator.count() > 0:
        subtitle = h2_locator.inner_text().strip()
    else:
        p_locator = page.locator("main p, body p").first
        subtitle = p_locator.inner_text().strip() if p_locator.count() > 0 else None

    # 3. Raw Text (Clean readable body text via inner_text)
    # page.inner_text("body") automatically ignores hidden text, <script>, and <style> tags
    raw_text = page.inner_text("body")
    # Clean up excessive newlines/spaces
    raw_text_cleaned = " ".join(raw_text.split())

    # 4. Has Numeric Offer
    numeric_pattern = re.compile(
        r"(\d+[\.,]?\d*\s*[%€$])|([%€$]\s*\d+[\.,]?\d*)|(\b\d+\b\s*(euro|eur|percent))", 
        re.IGNORECASE
    )
    has_numeric_offer = 1 if numeric_pattern.search(raw_text_cleaned) else 0

    # 5. Main CTA Text & CTA Count
    cta_selector = "a.btn, button.btn, a[class*='cta'], button[class*='cta'], main a.button"
    cta_locators = page.locator(cta_selector)
    cta_count = cta_locators.count()
    
    cta_text = None
    if cta_count > 0:
        all_cta_texts = cta_locators.all_inner_texts()

        # 2. Clean extra whitespace/newlines from each button text and drop empty strings
        cleaned_ctas = [text.strip() for text in all_cta_texts if text.strip()]

        # 3. Join unique or all CTA texts into a single string (comma-separated or '|' separated)
        # Using list(dict.fromkeys(...)) preserves order while deduplicating identical CTAs
        unique_ctas = list(dict.fromkeys(cleaned_ctas))
        cta_text = " | ".join(unique_ctas) if unique_ctas else None

    # 6. Image Count
    image_count = page.locator("img").count()

    return {
        "headline": headline,
        "subtitle": subtitle,
        "has_numeric_offer": has_numeric_offer,
        "cta_text": cta_text,
        "cta_count": cta_count,
        "image_count": image_count,
        "raw_text": raw_text_cleaned
    }


def save_to_sqlite(data, db_path="./data/bank_analysis.db"):
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


def run_scraper():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="en-US"
        )
        page = context.new_page()

        print(f"Navigating to {url}...")
        page.goto(url, wait_until="networkidle")

        if "/maintenance" in (link:=page.url):
            print("Redirected to maintenance page. url :", link)
            browser.close()
            return
        print("Found :", link)
        # print("Giving time for the cookies pop up to load...")
        # page.wait_for_timeout(2000)

        # matches = page.get_by_text("Accept all", exact=False)
        # count = matches.count()

        # print(f"\nFound {count} elements matching 'Accept all':")

        # for i in range(count):
        #     el = matches.nth(i)
        #     tag = el.evaluate("el => el.tagName")
        #     text = el.inner_text().strip().replace("\n", " ")
        #     print(f"  [{i}] <{tag}> Text: '{text}'")

        # # Proceed with the first one
        # cookie_trigger = matches.first

        # if cookie_trigger.is_visible():
        #     cookie_trigger.click()
        #     print("Cookies accepted, waiting 3 seconds...")
        #     page.wait_for_timeout(3000)
        handle_cookie_banner(page)

        print("Page loaded successfully:", page.title())
        page.screenshot(path=f"./screenshots/{outpath}_design.png", full_page=True)

        # Extract targeted marketing fields
        scraped_data = extract_marketing_data(page)

        # Output preview to console
        print("\n--- Extracted Marketing Data ---")
        for key, val in scraped_data.items():
            if key == "raw_text":
                print(f"{key}: {val[:120]}... (truncated)")
            else:
                print(f"{key}: {val}")

        # Save record
        save_to_sqlite(scraped_data)

        unique_hex_colors = extract_page_colors(page)
        print("\nExtracted Unique HEX Colors:")
        print(unique_hex_colors)

        # Save to database
        save_colors_to_sqlite(url, unique_hex_colors)
        browser.close()


if __name__ == "__main__":
    run_scraper()