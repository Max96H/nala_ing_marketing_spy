import re
import sqlite3
from playwright.sync_api import sync_playwright

URL = "https://www.bnpparibasfortis.be/en/public/individuals/daily-banking/accounts/current-account/youth-account"


def rgb_to_hex(rgb_str):
    """Converts 'rgb(r, g, b)' or 'rgba(r, g, b, a)' strings to HEX format (#RRGGBB)."""
    nums = re.findall(r"\d+", rgb_str)
    if len(nums) >= 3:
        r, g, b = map(int, nums[:3])
        return f"#{r:02x}{g:02x}{b:02x}".upper()
    return None


def extract_page_colors(page):
    """Extracts unique visible colors from all DOM elements on the page."""
    # Execute JS in the browser to collect all computed text and background colors
    raw_colors = page.evaluate(
        """
        () => {
            const colors = new Set();
            const elements = document.querySelectorAll('body *');

            elements.forEach(el => {
                const style = window.getComputedStyle(el);
                
                // Filter out fully transparent backgrounds (rgba(0, 0, 0, 0))
                if (style.color && style.color !== 'rgba(0, 0, 0, 0)') {
                    colors.add(style.color);
                }
                if (style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)') {
                    colors.add(style.backgroundColor);
                }
            });

            return Array.from(colors);
        }
    """
    )

    # Convert RGB/RGBA values to HEX and deduplicate
    hex_colors = set()
    for color in raw_colors:
        hex_val = rgb_to_hex(color)
        if hex_val:
            hex_colors.add(hex_val)

    return list(hex_colors)


def save_colors_to_sqlite(page_url, color_list, db_path="./data/bank_analysis.db"):
    """Inserts extracted colors into the page_colors junction table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Fetch the corresponding page_id from the pages table
    cursor.execute("SELECT id FROM pages WHERE page_url = ?", (page_url,))
    row = cursor.fetchone()

    if not row:
        print(
            f"Error: Page URL '{page_url}' not found in 'pages' table. Please run main scraper first."
        )
        conn.close()
        return

    page_id = row[0]

    # 2. Prepare batch tuples (page_id, color_hex)
    color_records = [(page_id, color) for color in color_list]

    # 3. Bulk insert using INSERT OR IGNORE to prevent duplicate primary key errors
    cursor.executemany(
        """
        INSERT OR IGNORE INTO page_colors (page_id, color_hex)
        VALUES (?, ?);
    """,
        color_records,
    )

    conn.commit()
    conn.close()
    print(
        f"Successfully inserted {len(color_records)} colors for page ID {page_id} into 'page_colors'."
    )


def run():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="en-US"
        )
        page = context.new_page()

        print(f"Navigating to {URL}...")
        page.goto(URL, wait_until="networkidle")

        # Handle cookie banner to prevent overlay colors from skewing results
        cookie_trigger = page.locator(
            '#cookies_all_accept_btn, button:has-text("Accept"), a:has-text("Accept")'
        ).first
        if cookie_trigger.is_visible():
            cookie_trigger.click()
            page.wait_for_timeout(1000)

        # Extract & process colors
        unique_hex_colors = extract_page_colors(page)

        print("\nExtracted Unique HEX Colors:")
        print(unique_hex_colors)

        # Save to database
        save_colors_to_sqlite(URL, unique_hex_colors)

        browser.close()


if __name__ == "__main__":
    run()