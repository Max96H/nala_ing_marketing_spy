import re

def handle_cookie_banner(page):
    """Finds, logs, and clicks the cookie acceptance trigger regardless of HTML tag type."""
    # Matches common variations in English, Dutch, and French
    text_pattern = re.compile(
        r"^(accept|accept all|accept cookies|alle cookies accepteren|accepter tout)$",
        re.IGNORECASE,
    )

    # 1. Try finding interactive roles first (buttons/links)
    for role in ["button", "link"]:
        trigger = page.get_by_role(role, name=text_pattern).first
        if trigger.is_visible():
            tag = trigger.evaluate("el => el.tagName")
            print(f"✓ Clicked cookie {role} <{tag}>: '{trigger.inner_text()}'")
            trigger.click(force=True)
            page.wait_for_timeout(2000)
            return True

    # 2. Fallback: Search all clickable tags using CSS + text filtering
    fallback_locator = page.locator(
        "button, a, [role='button'], ing-button, [class*='btn']"
    ).filter(has_text=re.compile(r"accept", re.IGNORECASE))

    if fallback_locator.count() > 0:
        trigger = fallback_locator.first
        if trigger.is_visible():
            tag = trigger.evaluate("el => el.tagName")
            print(f"✓ Clicked fallback <{tag}>: '{trigger.inner_text()}'")
            trigger.click(force=True)
            page.wait_for_timeout(2000)
            return True

    print("ℹ No cookie banner detected or already accepted.")
    return False