"""
ING Banking Campaigns Comparator — Collector + Analyst (deterministic part)

Uses Playwright to render every page like a real browser would, then extracts
the same shared schema for all 5 banks (ING, KBC, BNP Paribas Fortis,
Belfius, Revolut). Also saves a full-page screenshot per page and extracts
its dominant colours.

Run this in your OWN environment with normal internet access — it will NOT
run inside this sandboxed chat (network here is restricted to a small
allowlist that does not include bank websites).

Setup:
    pip install playwright beautifulsoup4 colorthief --break-system-packages
    playwright install chromium

Usage:
    python collector.py
"""

import re
import sqlite3
import sys
from dataclasses import dataclass, asdict, field
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup
from colorthief import ColorThief
from playwright.sync_api import sync_playwright

USER_AGENT = "ING-CampaignComparator-Bootcamp/1.0 (+student research project)"
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)
PAGE_TIMEOUT_MS = 20000
DB_DIR = Path("db")
DB_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Shared schema — unchanged from before
# ---------------------------------------------------------------------------

SCHEMA_FIELDS = [
    "bank", "page_url", "page_type", "language", "scrape_date",
    "headline", "subtitle", "tone", "value_proposition", "topics",
    "has_numeric_offer", "cta_text", "cta_count", "image_count",
    "dominant_colors", "raw_text", "screenshot_path", "source_type",
]


@dataclass
class PageRecord:
    bank: str
    page_url: str
    page_type: str
    language: str
    scrape_date: str = field(default_factory=lambda: date.today().isoformat())
    headline: str = ""
    subtitle: str = ""
    tone: str = ""                # filled later by the LLM analyst step
    value_proposition: str = ""   # filled later by the LLM analyst step
    topics: str = ""              # filled later by the LLM analyst step (JSON list as text)
    has_numeric_offer: bool = False
    cta_text: str = ""
    cta_count: int = 0
    image_count: int = 0
    dominant_colors: str = ""     # hex codes, comma-separated
    raw_text: str = ""
    screenshot_path: str = ""
    source_type: str = "playwright_render"


NUMERIC_OFFER_RE = re.compile(r"(€\s?\d+|EUR\s?\d+|\d+(\.\d+)?\s?%|\d+\s?(days|months|years))", re.I)
CTA_WORDS_RE = re.compile(r"\b(open|discover|start|learn more|compare|apply|join|sign up)\b", re.I)


def detect_numeric_offer(text: str) -> bool:
    return bool(NUMERIC_OFFER_RE.search(text))


def extract_dominant_colors(image_path: Path, count: int = 4) -> str:
    try:
        palette = ColorThief(str(image_path)).get_palette(color_count=count)
        return ", ".join("#%02x%02x%02x" % rgb for rgb in palette)
    except Exception as exc:
        print(f"[warn] colour extraction failed for {image_path}: {exc}", file=sys.stderr)
        return ""


# ---------------------------------------------------------------------------
# Core fetch — render with Playwright, parse the resulting HTML
# ---------------------------------------------------------------------------

def fetch_page(browser, url: str, bank: str, page_type: str, language: str) -> PageRecord:
    page = browser.new_page(user_agent=USER_AGENT, viewport={"width": 1440, "height": 900})
    page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="networkidle")

    # Give lazy-loaded content (common on SPA product pages) a moment to settle
    page.wait_for_timeout(1500)

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    headline = h1.get_text(strip=True) if h1 else ""
    h2 = soup.find("h2")
    subtitle = h2.get_text(strip=True) if h2 else ""

    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    raw_text = soup.get_text(" ", strip=True)

    ctas = [a.get_text(strip=True) for a in soup.find_all("a")
            if a.get_text(strip=True) and CTA_WORDS_RE.search(a.get_text())]
    cta_count = len(ctas)
    cta_text = ctas[0] if ctas else ""

    image_count = len(soup.find_all("img"))

    safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", f"{bank}_{page_type}").strip("_").lower()
    screenshot_path = SCREENSHOT_DIR / f"{safe_name}_{date.today().isoformat()}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)

    dominant_colors = extract_dominant_colors(screenshot_path)

    page.close()

    return PageRecord(
        bank=bank,
        page_url=url,
        page_type=page_type,
        language=language,
        headline=headline,
        subtitle=subtitle,
        has_numeric_offer=detect_numeric_offer(raw_text),
        cta_text=cta_text,
        cta_count=cta_count,
        image_count=image_count,
        dominant_colors=dominant_colors,
        raw_text=raw_text[:20000],  # cap stored raw text to keep rows manageable
        screenshot_path=str(screenshot_path),
    )


# ---------------------------------------------------------------------------
# Storage — SQLite
# ---------------------------------------------------------------------------

def init_db(db_path: str = "db/campaigns.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {", ".join(f'"{f}" TEXT' for f in SCHEMA_FIELDS)}
        )
    """)
    conn.commit()
    return conn


def save_record(conn: sqlite3.Connection, record: PageRecord) -> None:
    row = asdict(record)
    placeholders = ", ".join("?" for _ in SCHEMA_FIELDS)
    cols = ", ".join(f'"{f}"' for f in SCHEMA_FIELDS)
    values = [str(row[f]) for f in SCHEMA_FIELDS]
    conn.execute(f"INSERT INTO pages ({cols}) VALUES ({placeholders})", values)
    conn.commit()


# ---------------------------------------------------------------------------
# Page list — the MVP scope. Extend as you add more banks/pages.
# ---------------------------------------------------------------------------

PAGES = [
    # (url, bank, page_type, language)
    ("https://www.ing.be/en/individuals/current-accounts-packs", "ING", "current account", "en"),
    ("https://www.ing.be/en/individuals/saving/classic-savings-account", "ING", "savings", "en"),
    ("https://www.ing.be/en/individuals/credit-cards", "ING", "credit cards", "en"),
    ("https://www.kbc.be/retail/en.html", "KBC", "homepage/campaign", "en"),
    ("https://www.bnpparibasfortis.be/en/public/individuals", "BNP Paribas Fortis", "homepage/campaign", "en"),
    ("https://www.belfius.be/site/retail/fr/produits/epargner", "Belfius", "savings", "fr"),
    ("https://www.revolut.com/", "Revolut", "homepage/campaign", "en"),
]


def run() -> None:
    conn = init_db()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for url, bank, page_type, lang in PAGES:
            try:
                record = fetch_page(browser, url, bank, page_type, lang)
                save_record(conn, record)
                print(f"[ok] {bank} — {url}")
            except Exception as exc:
                print(f"[fail] {bank} — {url}: {exc}", file=sys.stderr)
        browser.close()
    conn.close()
    print("\nDone. Data in campaigns.db, screenshots in screenshots/")


if __name__ == "__main__":
    run()