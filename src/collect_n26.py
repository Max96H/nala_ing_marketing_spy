import random
import time
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

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


def run(selected_banks: dict, scrolling: bool) -> None:
    """Scrape every seed URL for the given banks with stealth anti-bot protections
    and save results to the database."""
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    print(f"Targeting banks: {', '.join(selected_banks.keys())}")

    with sync_playwright() as p:
        # Launch Chromium with anti-automation flags disabled.
        # Set headless=False if Cloudflare still challenges the connection.
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )

        for bank, config in selected_banks.items():
            urls = config.get("sitemap_links", [])
            if not urls:
                print(f"No URLs found for bank: {bank}")
                continue

            # Create ONE persistent context per bank to reuse session cookies
            # and avoid looking like a new bot connecting on every URL request
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                timezone_id="Europe/Brussels",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;"
                        "q=0.9,image/avif,image/webp,*/*;q=0.8"
                    ),
                },
            )

            # Reuse a single tab/page for the bank run
            page = context.new_page()

            # Apply stealth evasions to mask Playwright/automation flags
            Stealth().apply_stealth_sync(page)

            for i, url in enumerate(urls):
                try:
                    print(f"\n--- Navigating to {url} ---")
                    # domcontentloaded avoids hanging on Cloudflare long-polling requests
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)

                    # Give JavaScript and dynamic tokens time to load
                    page.wait_for_timeout(3000)

                    if "/maintenance" in (link := page.url):
                        print("Redirected to maintenance page. url:", link)
                        continue
                    print("Found:", link)

                    handle_cookie_banner(page, scrolling)

                    print("Page loaded successfully:", page.title())
                    screenshot = page.screenshot(full_page=True)

                    scraped_data = extract_marketing_data(page)

                    print("\n--- Extracted Marketing Data ---")
                    for key, val in scraped_data.items():
                        if key == "raw_text":
                            print(f"{key}: {val[:120]}... (truncated)")
                        else:
                            print(f"{key}: {val}")

                    save_to_sqlite(url, bank, scraped_data)

                    unique_hex_colors = extract_dominant_colors(screenshot)
                    print("\nExtracted Unique HEX Colors:")
                    print(unique_hex_colors)

                    save_colors_to_sqlite(url, unique_hex_colors)

                    # Random pause between 3 and 6 seconds to prevent IP rate-limiting
                    delay = random.uniform(3.0, 6.0)
                    print(f"Waiting {delay:.1f}s before next request...")
                    time.sleep(delay)

                except Exception as e:
                    print(f"Failed to scrape {url}: {e}")

            context.close()

        browser.close()