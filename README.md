# Nala ING Marketing Spy

## Overview

Nala ING Marketing Spy is a reproducible web-crawling project designed to collect and compare the online marketing communication of Belgian banks around youth current accounts.

The project focuses on publicly available web pages and captures both the technical content of the pages and the elements needed for later marketing analysis.

The initial scope covers:

- ING Belgium
- KBC
- Belfius
- BNP Paribas Fortis

The architecture is designed so that additional banks or URLs can be added mainly through configuration, without creating new Python crawler classes.

---

## Research objective

The objective is to build a structured historical dataset of public marketing pages in order to analyse, over time:

- product positioning
- value proposition
- messaging
- tone of communication
- headings and copy
- calls to action
- visual content
- page structure
- links and navigation
- changes in marketing communication

The crawler is therefore intended as a data collection layer. Marketing analysis is performed separately from the crawling process.

---

# Methodology

## 1. Central configuration

All bank-specific information is stored in:

config/banks.yaml

The configuration contains information such as:

- bank name
- domain
- seed URLs
- sitemap URLs
- supported languages
- product keywords
- exclusion keywords

This separates configuration from crawler logic.

Adding a new bank should normally require only an update to banks.yaml.

---

## 2. Generic crawler architecture

The project uses one generic crawler:

src/crawler/base.py

The crawler is implemented through the BankCrawler class.

There are no separate crawler classes for each bank.

The same crawling logic is used for every bank.

The bank name is passed to the generic crawler:

    crawler = BankCrawler(bank_name)

This avoids duplicating crawling logic between banks.

---

## 3. Browser automation

The project uses:

- Playwright
- Firefox

The crawler opens the configured URL in a real browser context rather than relying only on raw HTTP requests.

This is important because modern banking websites may contain:

- JavaScript-rendered content
- dynamically loaded elements
- lazy-loaded images
- client-side navigation
- responsive page components

The crawler waits for the page to load and then scrolls through the page to trigger lazy-loaded content.

---

## 4. Page rendering process

For each configured URL, the crawler performs the following workflow:

    URL
     |
     v
    Playwright / Firefox
     |
     v
    Page navigation
     |
     v
    Wait for page rendering
     |
     v
    Scroll through page
     |
     v
    Full-page screenshot
     |
     v
    Retrieve rendered HTML
     |
     v
    Extract structured content
     |
     v
    Save raw HTML
     |
     v
    Save metadata and extracted content to SQLite

The crawler records the HTTP status code and final URL in order to detect cases such as redirects or unavailable pages.

---

# Data collection

## 5. Screenshots

A full-page screenshot is created for every crawl.

Screenshots are stored under:

data/screenshots/

with one directory per bank:

data/screenshots/
├── ing/
├── kbc/
├── belfius/
└── bnp/

Screenshots include a timestamp and URL hash.

Example:

2026-09-18_14-18-23_77b1f6c2.png

The timestamp makes it possible to preserve multiple versions of the same page over time.

---

## 6. Raw HTML archival

The complete rendered HTML is stored for every crawl.

The storage structure is:

data/raw/
├── ing/
│   └── 2026-09-18/
├── kbc/
│   └── 2026-09-18/
├── belfius/
│   └── 2026-09-18/
└── bnp/
    └── 2026-09-18/

Each HTML file contains the rendered state of the page at the time of collection.

A SHA-256 content hash is also calculated.

This allows the project to identify whether the retrieved HTML content has changed between crawls.

---

# Content extraction

## 7. Playwright-based parser

Structured information is extracted directly from the Playwright page.

The parser is located in:

src/extraction/page_parser.py

No BeautifulSoup dependency is used.

The parser currently extracts:

### Page metadata

- page title
- meta description

### Text

- H1 headings
- H2 headings
- H3 headings
- paragraphs

### Links

- visible link text
- link URL

### Images

- image source
- alternative text

The extracted structure is returned as a Python dictionary.

Example structure:

    {
        "title": "...",
        "meta_description": "...",
        "headings": [...],
        "paragraphs": [...],
        "links": [...],
        "images": [...]
    }

The parser is designed to tolerate missing elements. For example, a page without a meta description should not cause the entire crawl to fail.

---

# Database

## 8. SQLite storage

The project uses SQLite to create a local historical database:

data/crawler.db

The database is managed by:

src/storage/database.py

The main table is:

pages

It stores:

- bank
- original URL
- final URL
- crawl timestamp
- HTTP status
- title
- meta description
- screenshot path
- raw HTML path
- content hash

Extracted content is stored in related tables:

- page_headings
- page_paragraphs
- page_links
- page_images

The relationship is:

    pages
     ├── page_headings
     ├── page_paragraphs
     ├── page_links
     └── page_images

Each crawl creates a new record.

This is intentional: the project is designed to preserve historical versions of marketing pages rather than simply keeping the latest version.

---

# Pipeline

## 9. Main pipeline

The main orchestration script is:

src/pipeline.py

It performs the following tasks:

1. Load banks.yaml
2. Create required data directories
3. Select the bank or banks to crawl
4. Initialize SQLite
5. Instantiate the generic BankCrawler
6. Crawl the configured seed URLs
7. Save screenshots
8. Save raw HTML
9. Extract structured content
10. Save the crawl result in SQLite
11. Display a summary of the database

---

## 10. Running the crawler

From PowerShell, make sure the virtual environment is activated and the src directory is available on the Python path.

    $env:PYTHONPATH = "$PWD\src"

To crawl one bank:

    python -m pipeline --bank ing

To crawl all configured banks:

    python -m pipeline --bank all

or:

    python -m pipeline

The available bank names are generated dynamically from banks.yaml.

---

# Project structure

    nala_ing_marketing_spy/
    |
    ├── config/
    │   ├── banks.yaml
    │   └── features.yaml
    |
    ├── data/
    │   ├── raw/
    │   ├── screenshots/
    │   └── crawler.db
    |
    ├── src/
    │   ├── crawler/
    │   │   └── base.py
    │   │
    │   ├── extraction/
    │   │   └── page_parser.py
    │   │
    │   ├── storage/
    │   │   ├── database.py
    │   │   └── raw.py
    │   │
    │   └── pipeline.py
    |
    └── README.md

---

# Reproducibility principles

The project follows several principles to make the collection process reproducible.

### Configuration-driven

Bank-specific information is kept in YAML rather than hard-coded in crawler classes.

### Generic crawling logic

All banks use the same crawler implementation.

### Historical storage

Every crawl creates a separate record rather than overwriting previous data.

### Raw data preservation

The rendered HTML is archived so that later analyses can refer back to the original collected material.

### Visual preservation

Full-page screenshots preserve the visual state of the page at collection time.

### Structured extraction

Relevant page elements are stored separately in SQLite, making later analysis easier.

### Local and public data only

The crawler is designed to collect publicly accessible web content and does not target personal user data.

---

# Quality checks

Before considering a crawl successful, the following elements should be checked:

    HTTP status
         |
         v
    Final URL
         |
         v
    Screenshot created
         |
         v
    Raw HTML created
         |
         v
    Page title extracted
         |
         v
    Headings extracted
         |
         v
    Paragraphs extracted
         |
         v
    Links extracted
         |
         v
    Images extracted
         |
         v
    SQLite record created

A successful HTTP request does not necessarily mean that the target marketing page is valid.

For example, an HTTP 200 response may still correspond to an unexpected page.

The final URL, title and extracted content should therefore also be inspected.

---

# Future analysis layer

The current crawler is primarily a data collection and storage layer.

Marketing analysis can be added later without modifying the crawling mechanism.

Potential future variables include:

- communication tone
- target audience
- value proposition
- product benefits
- pricing claims
- promotional mechanics
- calls to action
- emotional appeals
- trust signals
- visual themes
- colours
- imagery
- page layout
- product features
- eligibility conditions
- age ranges
- competitive positioning

These variables should be extracted or analysed in a separate analysis layer rather than hard-coded into the crawler.

This separation keeps the collection pipeline stable while allowing the research framework to evolve.

---

# Scope

The project currently focuses on youth and children's current accounts and payment accounts, rather than savings accounts.

The objective is to compare how Belgian banks publicly present these products online.

The project is not intended to reproduce private customer journeys, authenticated banking areas, or personal data.

---

# Summary

The methodology can be summarized as:

    BANK CONFIGURATION
            |
            v
       banks.yaml
            |
            v
      GENERIC CRAWLER
            |
            v
     PLAYWRIGHT / FIREFOX
            |
            v
      RENDERED WEB PAGE
            |
       +----+----+
       |    |    |
       v    v    v
      HTML PNG CONTENT
       |    |    |
       v    v    v
      RAW SCREENSHOT
       |         |
       +----+----+
            |
            v
         SQLITE
            |
            v
     HISTORICAL DATASET
            |
            v
      MARKETING ANALYSIS

The key architectural principle is:

Bank-specific configuration belongs in banks.yaml; crawling logic belongs in the generic BankCrawler; analysis belongs in a separate layer.

This makes the project easier to maintain, extend and reproduce.