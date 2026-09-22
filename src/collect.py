"""
ING Banking Campaigns Comparator — Collect

Data collection stage, owned by the team's scraping code. Loads bank
configuration from config/banks.yaml and scrapes each selected bank's seed
URLs with Playwright (Firefox): dismisses cookie banners (cookies.py),
extracts marketing content (html_scraper.py), saves it to
data/bank_analysis.db (insertion_db.py), then extracts and saves the
screenshot's dominant colors (extract_colors.py).

Everything downstream of this (analyst.py, analysis.py, change_watcher.py,
assistant.py) is Uzair's side of the pipeline and reads from the same
database this stage writes to.
"""

from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

from cookies import handle_cookie_banner
from extract_colors import extract_dominant_colors, save_colors_to_sqlite
from html_scraper import extract_marketing_data
from insertion_db import save_to_sqlite

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # src/ -> project root
CONFIG_PATH = PROJECT_ROOT / "config" / "banks.yaml"
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"


def load_bank_config() -> dict:
    """Load all bank configurations from banks.yaml — the central config
    source for the multi-bank crawler. No bank names/URLs are hard-coded
    in the crawler itself; add a bank by editing the YAML only."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Bank configuration not found: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not config:
        raise ValueError("banks.yaml is empty.")

    banks = config.get("banks")
    if not banks:
        raise ValueError("No 'banks' section found in banks.yaml.")

    return banks


def run(selected_banks: dict) -> None:
    """Scrape every seed URL for the given banks (a filtered dict from
    load_bank_config()) and save results to the database."""
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    print(f"Targeting banks: {', '.join(selected_banks.keys())}")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)

        for bank, config in selected_banks.items():
            urls = config.get("seeds")
            outpaths = config.get("outpaths")

            for i, url in enumerate(urls):
                outpath = outpaths[i]
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080}, locale="en-US"
                )
                page = context.new_page()

                try:
                    print(f"\n--- Navigating to {url} ---")
                    page.goto(url, wait_until="networkidle")

                    if "/maintenance" in (link := page.url):
                        print("Redirected to maintenance page. url:", link)
                        browser.close()
                        return
                    print("Found:", link)

                    handle_cookie_banner(page)

                    print("Page loaded successfully:", page.title())
                    screenshot_path = SCREENSHOT_DIR / f"{outpath}_design.png"
                    page.screenshot(path=str(screenshot_path), full_page=True)

                    scraped_data = extract_marketing_data(page)

                    print("\n--- Extracted Marketing Data ---")
                    for key, val in scraped_data.items():
                        if key == "raw_text":
                            print(f"{key}: {val[:120]}... (truncated)")
                        else:
                            print(f"{key}: {val}")

                    save_to_sqlite(url, bank, scraped_data)

                    unique_hex_colors = extract_dominant_colors(str(screenshot_path))
                    print("\nExtracted Unique HEX Colors:")
                    print(unique_hex_colors)

                    save_colors_to_sqlite(url, unique_hex_colors)

                except Exception as e:
                    print(f"Failed to scrape {url}: {e}")

                finally:
                    context.close()

        browser.close()