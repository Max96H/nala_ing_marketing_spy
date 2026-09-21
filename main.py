from playwright.sync_api import sync_playwright
from config import banks
from src.extract_colors import extract_dominant_colors, save_colors_to_sqlite
from src.cookies import handle_cookie_banner
from src.insertion_db import save_to_sqlite
from src.html_scraper import extract_marketing_data
import argparse

def parse_arguments():
    """Parses command-line arguments for targeting specific banks."""
    parser = argparse.ArgumentParser(
        description="Scrape bank marketing pages and save design/content data to SQLite."
    )

    # Convert bank keys in config to lower-case for case-insensitive matching
    available_banks = [b.lower() for b in banks.keys()]

    parser.add_argument(
        "-b",
        "--banks",
        nargs="+",  # Accepts one or more bank names separated by space
        type=str.lower,  # Automatically converts inputs to lowercase
        choices=available_banks,
        default=available_banks,  # Defaults to processing all banks
        help=f"Specific bank(s) to scrape. Choices: {', '.join(available_banks)}. Default: all.",
    )

    return parser.parse_args()

def main():
    args = parse_arguments()

    # Filter the banks dictionary based on user selection
    selected_banks = {
        name: config
        for name, config in banks.items()
        if name.lower() in args.banks
    }

    print(f"Targeting banks: {', '.join(selected_banks.keys())}")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)

        for bank, dic in selected_banks.items():
            url = dic["url"]
            outpath = dic["outpath"]

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080}, locale="en-US"
            )
            page = context.new_page()

            try:

                print(f"\n--- Navigating to {url} ---")
                page.goto(url, wait_until="networkidle")

                if "/maintenance" in (link:=page.url):
                    print("Redirected to maintenance page. url :", link)
                    browser.close()
                    return
                print("Found :", link)

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
                save_to_sqlite(url, bank, scraped_data)

                unique_hex_colors = extract_dominant_colors(f"./screenshots/{outpath}_design.png")
                print("\nExtracted Unique HEX Colors:")
                print(unique_hex_colors)

                # Save to database
                save_colors_to_sqlite(url, unique_hex_colors)

            except Exception as e:
                print(f"Failed to scrape {url}: {e}")

            finally:
                context.close()

        browser.close()


if __name__ == "__main__":
    main()
