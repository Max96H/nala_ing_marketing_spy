<div align="center">

# 🏦 ING Banking Campaigns Comparator

**A data-driven competitive intelligence platform comparing how banks present marketing campaigns online.**

Built during the BeCode AI & Data Science Bootcamp, in partnership with ING.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-scraping-2EAD33?style=flat&logo=playwright&logoColor=white)](https://playwright.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-database-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-Academic%20Project-lightgrey?style=flat)]()

[Overview](#-overview) • [Key Numbers](#-key-numbers) • [How It Works](#%EF%B8%8F-how-it-works) • [Features](#-features) • [Setup](#-setup--installation) • [Team](#-team)

</div>

<br>

![Product Overview](assets/hero-overview.png)
<p align="center"><i>The Overview tab: Dataset scale at a glance before diving into any single comparison.</i></p>

<br>

## 📌 Overview

In Belgium, banks don't present themselves the same way. Traditional players (ING, KBC, BNP Paribas Fortis) and challenger neobanks (Revolut, N26, bunq) use very different tones, visuals, and value propositions to attract customers.

This project answers, with data rather than opinion:

- **Where does ING stand compared to competitors?**
- **Is ING closer to traditional banks or to challenger banks?**
- **Which banks communicate similarly, and where do campaigns actually differ?**
- **Where are the concrete opportunities for ING to improve?**

It does this by scraping publicly available campaign pages, using an LLM to extract structured, comparable features from each page (tone, value proposition, topics), computing deterministic scores grounded in established usability principles, and surfacing everything through an interactive web app — including a chatbot that answers questions grounded in the actual scraped data.

This is not a one-off report. It's a reusable **feature-extraction framework**: a webpage in, a structured row out — designed to extend to social ads, app banners, and larger-scale automated analysis beyond this project's scope.

<br>

## 📊 Key Numbers

<div align="center">

| Metric | Value |
|---|---|
| 🏦 Banks analyzed | **8** (5 traditional, 3 neobanks) |
| 📄 Campaign pages scraped | **3,000+** |
| 🗂️ Page-type categories (taxonomy) | **12** |
| 🎯 Priority categories analyzed by LLM | **4** (current accounts, youth, cards, savings & investments) |
| 🧭 Radar scoring dimensions | **5** (promo intensity, visual richness, colour vibrancy, content density, topic diversity) |
| ✅ UX sub-scores per page | **6** (value clarity, CTA clarity, hierarchy, scannability, visual balance, accessibility/contrast) |
| 🤖 LLM providers supported | **2** (Groq + Gemini, hot-swappable) |
| 🌍 Languages handled natively | **3** (English, French, Dutch) |

</div>

<br>

## 🗺️ How It Works

The pipeline runs end-to-end, from raw public web pages to an interactive comparison tool:

```mermaid
flowchart TD
    A["🌐 Public bank websites\n(ING, KBC, BNP, Argenta, Crelan,\nRevolut, N26, bunq)"] -->|"robots.txt + sitemap-respecting crawl"| B["🕷️ Collector\ncollect.py + html_scraper.py\nPlaywright · cookie handling · screenshots"]
    B --> C[("🗄️ SQLite Database\nbank_analysis.db")]

    C --> D["🏷️ Page Classifier\nupdate_page_types.py\n12-category rule-based taxonomy"]
    D --> C

    C --> E["🧠 Analyst (LLM)\nanalyst.py\nTone · Value Proposition · Topics\nverbatim-evidence hallucination checks"]
    E --> C

    C --> F["📐 UX Scorer\nux_score.py\nDeterministic — WCAG 2.1 contrast,\nNielsen heuristics, Hick's Law"]
    F --> C

    C --> G["📈 Analysis Engine\nanalysis.py\nPositioning (TF-IDF + PCA) · Radar\nGap Finder · Recommendations"]
    G --> C

    C --> H["🔍 Product Recommender (LLM)\nproduct_recommendations.py\nING-vs-competitor page pairs"]
    H --> C

    C --> I["⚡ FastAPI Backend\napi.py — REST endpoints"]
    I --> J["💻 React Frontend\nOverview · Positioning Map · Radar\nCompare Products · Gaps · Methodology"]
    I --> K["💬 Assistant / Chatbot\nBounded, grounded context\nnever sends the full database"]

    style A fill:#FFF3E0,stroke:#E67E22
    style C fill:#E8EAF6,stroke:#3F51B5
    style J fill:#E0F7FA,stroke:#00838F
    style K fill:#E0F7FA,stroke:#00838F
```

**In short:** scrape responsibly → classify pages → let an LLM read each page the way a marketer would → score what can be measured deterministically → surface it all through a web app a business stakeholder can actually use.

<br>

## ✨ Features

| Module | What it answers |
|---|---|
| 🏠 **Overview** | How many pages, banks, and categories are in scope — the dataset at a glance |
| 🧭 **Positioning Map** | Who does ING communicate *like*? Pages plotted by similarity in tone, topic, and messaging |
| 📊 **Radar** | How does ING *score* on each dimension compared to competitors — strengths and weaknesses |
| ⚖️ **Compare Products** | Side-by-side ING vs. competitor pages per product category, with a deterministic UX score and an LLM-generated, evidence-grounded recommendation |
| 🕳️ **Gaps** | Topics competitors cover that ING currently doesn't — candidate whitespace, each with a measured (not hyped) recommendation |
| 💬 **Ask** | A chatbot that answers questions about the dataset, grounded in real scraped content — never a hallucinated guess |
| 📖 **Methodology** | Full transparency for a data/technical audience — how every score is computed, and its limitations |

<br>

## 🖼️ Visuals

A walkthrough of what each module actually looks like, and what it's showing.

<br>

<p align="center"><img src="assets/positioning-map.png" alt="Positioning Map" width="85%"></p>

**Positioning Map.** Every dot is one scraped page, plotted in 2D using TF-IDF + PCA over its tone, value proposition, and topics — pages that read alike sit close together, regardless of bank. Colour marks the bank. This is the fastest way to see the headline finding at a glance: whether ING's dots cluster nearer the traditional banks or drift toward the neobank cluster, and which competitor ING most resembles in a given product category. The category filter above the chart narrows this to one product line at a time (e.g. only savings pages), since "similar" only means something within a comparable category.

<br>

<p align="center"><img src="assets/radar-chart.png" alt="Radar Chart" width="85%"></p>

**Radar.** Where the Positioning Map shows *similarity*, this shows *strength* — each bank's shape across five dimensions (promo intensity, visual richness, colour vibrancy, content density, topic diversity), normalized 0–1 so every bank is comparable on one chart. A bank's shape leaning outward on an axis means it leads competitors there; leaning inward flags a relative weak point. Read this alongside the Positioning Map: positioning tells you who ING resembles, radar tells you what to actually do differently from them.

<br>

<p align="center"><img src="assets/compare-products.png" alt="Compare Products" width="85%"></p>

**Compare Products.** The most actionable tab for a business audience. Pick a category, and ING's page sits next to the closest competitor equivalent, each with a deterministic UX score (grounded in WCAG 2.1 contrast rules, Nielsen's usability heuristics, and Hick's Law — not an LLM's opinion) and a specific, LLM-generated recommendation on what the competitor does differently and worth considering. This is designed to answer "so what should we actually change?" directly, rather than leaving that inference to the reader.

<br>

<p align="center"><img src="assets/chatbot.png" alt="Assistant Chatbot" width="85%"></p>

**Ask (Assistant).** A chatbot scoped to this dataset only — every answer is grounded in the actual scraped page content it retrieves for that question, not a general knowledge guess, and it never sends the full multi-thousand-page database to the model (that would blow the context window; instead it retrieves only the pages relevant to what's asked). Useful for exploring a question live in a meeting rather than pre-building every chart someone might ask for.

<br>

## 🧱 Tech Stack

## 🧱 Tech Stack

<div align="center">

| Layer | Technology |
|---|---|
| Scraping | Playwright (Firefox), Python |
| Storage | SQLite |
| Feature extraction | LLM (Groq / Gemini, OpenAI-compatible API), verbatim-evidence verification |
| Scoring | Deterministic Python — WCAG 2.1 contrast math, Nielsen's heuristics, Hick's Law |
| Analysis | pandas, scikit-learn (TF-IDF, PCA) |
| Backend | FastAPI |
| Frontend | React (Vite), Recharts |

</div>

<br>

## ⚖️ Legal & Data Scope

Only publicly available content was collected. Before scraping, each bank's `robots.txt` and sitemap were reviewed and respected — no restricted paths were accessed, no personal data was collected, and no access restrictions were bypassed. See [Methodology](#-features) in-app for the full per-bank compliance notes.

<br>

## 🚀 Setup & Installation

```bash
# 1. Clone and enter the project
git clone https://github.com/UzairSaeedKhan/ing-campaigns-comparator.git
cd ing-campaigns-comparator

# 2. Python environment
pip install -r requirements.txt --break-system-packages
playwright install firefox

# 3. Configure an LLM provider (either works)
export LLM_PROVIDER=groq          # or "gemini"
export GROQ_API_KEY=gsk_...       # or GEMINI_API_KEY

# 4. Run the pipeline
python main.py --banks all --scroll

# 5. Frontend
cd app
npm install
npm run dev

# 6. Backend API
uvicorn api:app --reload
```

<br>

## 📁 Project Structure

```
.
├── config/
│   ├── banks.yaml            # bank definitions, sitemap links, keywords
│   └── page_types.yaml       # 12-category page classification taxonomy
├── src/
│   ├── collect.py            # scraping orchestration
│   ├── cookies.py            # cross-platform cookie-consent handling
│   ├── html_scraper.py       # content extraction
│   ├── insertion_db.py       # database writes
│   ├── extract_colors.py     # dominant color extraction
│   ├── llm_client.py         # Groq / Gemini abstraction
│   ├── analyst.py            # LLM feature extraction (tone, value prop, topics)
│   ├── analysis.py           # positioning, radar, gaps, recommendations
│   ├── ux_score.py           # deterministic UX scoring
│   ├── product_recommendations.py
│   └── assistant.py          # grounded, bounded-context chatbot logic
├── app/                      # React frontend
├── api.py                    # FastAPI backend
├── main.py                   # pipeline entrypoint
├── data/
│   └── bank_analysis.db      # SQLite database
└── assets/                   # README images
```

**Images used in this README:**
| File | Used in |
|---|---|
| `hero-overview.png` | Top banner — Overview tab |
| `positioning-map.png` | Visuals — Positioning Map |
| `radar-chart.png` | Visuals — Radar |
| `compare-products.png` | Visuals — Compare Products |
| `chatbot.png` | Visuals — Ask (Assistant) |

<br>

## 👥 Team

<div align="center">

| | Name | Role | Links |
|---|---|---|---|
| 🧭 | **Uzair Saeed Khan** | Team Lead | [![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/UzairSaeedKhan) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/uzairsaeedkhan/) |
| 👩‍💻 | **Iness Khatiri** | Contributor | [![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/Happiness910) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/iness-khatiri-14392a258/) |
| 👨‍💻 | **Max Huberland** | Contributor | [![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/Max96H) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/max96h/) |
| 👩‍💻 | **Hiba Amellal** | Contributor | [![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/amellalajiba-sys) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/amellal-hiba-7a636940a/) |

</div>

<br>

## 📄 License

Academic project — built for BeCode's AI & Data Science Bootcamp in collaboration with ING.

<div align="center">

<br>

**Built with 🧡 by the ING Campaigns Comparator team**

</div>