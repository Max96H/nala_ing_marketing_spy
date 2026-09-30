import argparse
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
import yaml
from playwright.sync_api import sync_playwright
import robotexclusionrulesparser

# 1. Setup absolute paths using pathlib
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent if SCRIPT_DIR.name == "src" else SCRIPT_DIR
YAML_PATH = ROOT_DIR / "config" / "banks.yaml"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def parse_arguments(available_banks: list[str]):
    """Configures argparse to select specific banks from the YAML config."""
    parser = argparse.ArgumentParser(
        description="Extract sitemap links for banks defined in YAML."
    )
    parser.add_argument(
        "-b",
        "--banks",
        nargs="+",
        type=str.lower,
        choices=available_banks,
        default=available_banks,
        help=f"Specific bank(s) to process. Choices: {', '.join(available_banks)}. Default: all.",
    )
    return parser.parse_args()


def load_yaml_config(filepath: Path) -> dict:
    """Loads the YAML configuration file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml_config(data: dict, filepath: Path):
    """Saves the updated dictionary back to the YAML file."""
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_robots_parser(base_url: str):
    """Fetches and parses robots.txt using a modern wildcard-compliant parser."""
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    rerp = robotexclusionrulesparser.RobotExclusionRulesParser()
    try:
        rerp.fetch(robots_url)
        print(f"  ✓ Parsed robots.txt rules from: {robots_url}")
    except Exception as e:
        print(
            f"  ⚠ Could not fetch robots.txt ({e}). Defaulting to ALLOW all."
        )

    return rerp


def fetch_sitemap_with_playwright(sitemap_url: str) -> bytes | None:
    """Fallback method: Uses Playwright to bypass WAF blocking/timeouts."""
    print(f"  ⚡ Retrying with Playwright: {sitemap_url}")
    try:
        with sync_playwright() as p:
            # Launch browser with custom user-agent
            browser = p.firefox.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()

            # Navigate directly to the sitemap endpoint
            response = page.goto(
                sitemap_url, wait_until="networkidle", timeout=60000
            )


            if response and response.ok:
                content = response.body()  # Returns raw bytes
                browser.close()
                return content

            print(
                f"  ❌ Playwright fetch failed with status: {response.status if response else 'No response'}"
            )
            browser.close()
            return None
    except Exception as e:
        print(f"  ❌ Playwright fetch exception: {e}")
        return None


def extract_urls_from_sitemap(sitemap_url: str) -> list[str]:
    """Fetches a sitemap using requests, falling back to Playwright on timeout/blocking."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    xml_content = None

    # Step 1: Attempt standard fast HTTP fetch via requests
    try:
        response = requests.get(sitemap_url, headers=headers, timeout=15)
        response.raise_for_status()
        xml_content = response.content
    except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        print(f"  ⚠️ requests failed for {sitemap_url} ({e}). Switching to Playwright...")
        xml_content = fetch_sitemap_with_playwright(sitemap_url)
    except requests.RequestException as e:
        print(f"  ❌ Network error fetching {sitemap_url}: {e}")
        return []

    if not xml_content:
        print(f"  ❌ Unable to retrieve content for {sitemap_url}")
        return []
    
    soup = BeautifulSoup(xml_content, "xml")
    sub_sitemaps = soup.find_all(["sitemap", "SITEMAP"])
    url_tags = soup.find_all(["url", "URL"])

    print(
        f"  🔍 Diagnostic: Found {len(sub_sitemaps)} sub-sitemaps and {len(url_tags)} URL tags in parsed content."
    )

    if len(sub_sitemaps) == 0 and len(url_tags) == 0:
        print(
            f"  ⚠️ Content Preview (First 300 chars):\n{soup.prettify()[:300]}..."
        )
    urls = []

    # Case A: Sitemap Index containing sub-sitemaps (<sitemap><loc>...</loc></sitemap>)
    if sub_sitemaps:
        for sitemap in sub_sitemaps:
            loc = sitemap.find("loc")
            if loc and loc.text:
                urls.extend(extract_urls_from_sitemap(loc.text.strip()))
        return urls

    # Case B: Standard Sitemap containing page URLs (<url><loc>...</loc></url>)
    for url_entry in url_tags:
        loc = url_entry.find("loc")
        if loc and loc.text:
            urls.append(loc.text.strip())

    return urls


def process_bank_sitemaps(bank_key: str, bank_data: dict) -> list[str]:
    """Processes sitemaps for a single bank, filtering by roots and robots.txt."""
    sitemap_urls = bank_data.get("sitemap_urls", [])
    sitemap_roots = bank_data.get("sitemap_roots", [])

    if not sitemap_urls:
        print(f"  ℹ No sitemap_urls configured for '{bank_key}'. Skipping.")
        return []

    # Fetch robots.txt parser based on the first sitemap domain
    rp = get_robots_parser(sitemap_urls[0])

    extracted_links = []

    for sitemap_url in sitemap_urls:
        print(f"  Fetching: {sitemap_url}")
        raw_urls = extract_urls_from_sitemap(sitemap_url)

        for url in raw_urls:
            # 1. Ensure URL starts with one of the allowed sitemap_roots (if roots are specified)
            matches_root = (
                any(url.startswith(root) for root in sitemap_roots)
                if sitemap_roots
                else True
            )

            # 2. Check if robots.txt allows fetching this URL
            # if matches_root and rp.can_fetch(USER_AGENT, url):
            #     extracted_links.append(url)
            can_fetch = rp.is_allowed(USER_AGENT, url)

            if not matches_root:
                print(f"  ❌ Failed root check: {url}")
            elif not can_fetch:
                print(f"  ❌ Blocked by robots.txt: {url}")
            else:
                extracted_links.append(url)

    return extracted_links


def main():
    config = load_yaml_config(YAML_PATH)
    all_banks = config.get("banks", {})

    if not all_banks:
        print("❌ No banks found in config.yaml.")
        return

    available_bank_keys = [k.lower() for k in all_banks.keys()]
    args = parse_arguments(available_bank_keys)

    # Filter banks based on CLI arguments
    selected_banks = {
        k: v for k, v in all_banks.items() if k.lower() in args.banks
    }

    print(f"Targeting banks: {', '.join(selected_banks.keys())}\n")

    for bank_key, bank_data in selected_banks.items():
        print(f"--- Processing Bank: {bank_data.get('name', bank_key)} ---")

        # Get existing sitemap_links from config (or default to empty list)
        existing_links = bank_data.get("sitemap_links", [])

        # Extract & filter new links from sitemaps
        new_discovered_links = process_bank_sitemaps(bank_key, bank_data)

        # Merge new links into existing links while preserving order and preventing duplicates
        merged_links = list(dict.fromkeys(existing_links + new_discovered_links))

        added_count = len(merged_links) - len(existing_links)
        print(
            f"  ✓ Found {len(new_discovered_links)} matching links. Added {added_count} new unique links."
        )

        # Update bank dictionary in memory
        config["banks"][bank_key]["sitemap_links"] = merged_links

    # Save updated config back to config.yaml
    save_yaml_config(config, YAML_PATH)
    print(f"\n✓ Successfully updated '{YAML_PATH}'.")


if __name__ == "__main__":
    main()