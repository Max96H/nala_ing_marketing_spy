import re

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
