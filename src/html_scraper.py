# import re

# def extract_marketing_data(page):
#     # 1. Headline (Primary H1 or fallback to page title)
#     h1_locator = page.locator("h1").first
#     headline = h1_locator.inner_text().strip() if h1_locator.count() > 0 else page.title()

#     # 2. Subtitle (H2 or first visible paragraph)
#     h2_locator = page.locator("h2").first
#     if h2_locator.count() > 0:
#         subtitle = h2_locator.inner_text().strip()
#     else:
#         p_locator = page.locator("main p, body p").first
#         subtitle = p_locator.inner_text().strip() if p_locator.count() > 0 else None

#     # 3. Raw Text (Clean readable body text via inner_text)
#     # page.inner_text("body") automatically ignores hidden text, <script>, and <style> tags
#     raw_text = page.inner_text("body")
#     # Clean up excessive newlines/spaces
#     raw_text_cleaned = " ".join(raw_text.split())

#     # 4. Has Numeric Offer
#     numeric_pattern = re.compile(
#         r"(\d+[\.,]?\d*\s*[%€$])|([%€$]\s*\d+[\.,]?\d*)|(\b\d+\b\s*(euro|eur|percent))", 
#         re.IGNORECASE
#     )
#     has_numeric_offer = 1 if numeric_pattern.search(raw_text_cleaned) else 0

#     # 5. Main CTA Text & CTA Count
#     cta_selector = "a.btn, button.btn, a[class*='cta'], button[class*='cta'], main a.button"
#     cta_locators = page.locator(cta_selector)
#     cta_count = cta_locators.count()
    
#     cta_text = None
#     if cta_count > 0:
#         all_cta_texts = cta_locators.all_inner_texts()

#         # 2. Clean extra whitespace/newlines from each button text and drop empty strings
#         cleaned_ctas = [text.strip() for text in all_cta_texts if text.strip()]

#         # 3. Join unique or all CTA texts into a single string (comma-separated or '|' separated)
#         # Using list(dict.fromkeys(...)) preserves order while deduplicating identical CTAs
#         unique_ctas = list(dict.fromkeys(cleaned_ctas))
#         cta_text = " | ".join(unique_ctas) if unique_ctas else None

#     # 6. Image Count
#     image_count = page.locator("img").count()

#     return {
#         "headline": headline,
#         "subtitle": subtitle,
#         "has_numeric_offer": has_numeric_offer,
#         "cta_text": cta_text,
#         "cta_count": cta_count,
#         "image_count": image_count,
#         "raw_text": raw_text_cleaned
#     }








# def extract_revolut_marketing_signals(raw_text):
#     """
#     Extract simple marketing signals from the text
#     already collected by the existing scraper.

#     This does not replace extract_marketing_data().
#     """

#     text = raw_text or ""

#     patterns = {
#         "amounts": (
#             r"(?<!\w)\d+(?:[.,]\d+)?\s*"
#             r"(?:€|EUR|euros?)"
#         ),
#         "percentages": (
#             r"\d+(?:[.,]\d+)?\s*%"
#         ),
#         "free_mentions": (
#             r"\b(?:free|gratuit|gratuite|gratis)\b"
#         ),
#         "promotion_mentions": (
#             r"\b(?:offer|promotion|promo|"
#             r"bonus|reward|welcome|"
#             r"offre|prime|récompense)\b"
#         ),
#         "age_mentions": (
#             r"\b(?:under\s*18|"
#             r"moins\s+de\s+18\s+ans|"
#             r"\d{1,2}\s*(?:-|to)\s*\d{1,2}"
#             r"\s*(?:years|ans))\b"
#         ),
#     }

#     signals = {}

#     for name, pattern in patterns.items():
#         matches = re.findall(
#             pattern,
#             text,
#             flags=re.IGNORECASE
#         )

#         signals[name] = list(dict.fromkeys(matches))

#     return signals



import re


def extract_marketing_data(page):
    """
    Extract generic marketing information from a rendered webpage.

    This function is bank-independent.
    It can therefore be used for ING, KBC, Belfius,
    BNP Paribas Fortis and Revolut.
    """

    # ---------------------------------------------------------
    # 1. HEADLINE
    # ---------------------------------------------------------

    h1_locator = page.locator("h1").first

    if h1_locator.count() > 0:
        headline = h1_locator.inner_text().strip()
    else:
        headline = page.title().strip()

    # ---------------------------------------------------------
    # 2. SUBTITLE
    # ---------------------------------------------------------

    h2_locator = page.locator("h2").first

    if h2_locator.count() > 0:
        subtitle = h2_locator.inner_text().strip()

    else:
        p_locator = page.locator("main p, body p").first

        if p_locator.count() > 0:
            subtitle = p_locator.inner_text().strip()
        else:
            subtitle = None

    # ---------------------------------------------------------
    # 3. RAW TEXT
    # ---------------------------------------------------------

    raw_text = page.locator("body").inner_text()

    raw_text_cleaned = " ".join(raw_text.split())

    # ---------------------------------------------------------
    # 4. NUMERIC OFFERS
    # ---------------------------------------------------------

    numeric_pattern = re.compile(
        r"""
        (
            \d+(?:[.,]\d+)?\s?(?:€|EUR|euros?)
        )
        |
        (
            \d+(?:[.,]\d+)?\s?%
        )
        |
        (
            \b\d+\b\s?(?:days?|months?|years?|ans|mois|jours)
        )
        """,
        re.IGNORECASE | re.VERBOSE
    )

    numeric_matches = numeric_pattern.findall(raw_text_cleaned)

    has_numeric_offer = 1 if numeric_matches else 0

    # ---------------------------------------------------------
    # 5. CTA
    # ---------------------------------------------------------

    cta_selector = """
        a.btn,
        button.btn,
        a[class*="cta"],
        button[class*="cta"],
        a[class*="button"],
        button[class*="button"],
        main a
    """

    cta_locators = page.locator(cta_selector)

    all_cta_texts = cta_locators.all_inner_texts()

    cleaned_ctas = [
        text.strip()
        for text in all_cta_texts
        if text.strip()
    ]

    # Remove duplicates while keeping original order
    unique_ctas = list(dict.fromkeys(cleaned_ctas))

    cta_count = len(unique_ctas)

    cta_text = (
        " | ".join(unique_ctas)
        if unique_ctas
        else None
    )

    # ---------------------------------------------------------
    # 6. IMAGE COUNT
    # ---------------------------------------------------------

    image_count = page.locator("img").count()

    # ---------------------------------------------------------
    # 7. RETURN DATA
    # ---------------------------------------------------------

    return {
        "headline": headline,
        "subtitle": subtitle,
        "has_numeric_offer": has_numeric_offer,
        "cta_text": cta_text,
        "cta_count": cta_count,
        "image_count": image_count,
        "raw_text": raw_text_cleaned,
    }

