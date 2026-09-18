import re


def handle_cookie_banner(page):
    """Finds, logs, and clicks cookie banners across OneTrust, ING, BNP Paribas Fortis, and KBC."""
    # --------------------------------------------------
    # Scroll through the page
    # --------------------------------------------------
    #
    # Some websites use lazy loading.
    # We simulate a progressive scroll so that images
    # and other dynamic content have a chance to load.
    #

    print()
    print("===== SCROLLING PAGE =====")

    page.evaluate(
        """
        async () => {

            await new Promise((resolve) => {

                let totalHeight = 0;
                const distance = 500;
                const delay = 500;

                const timer = setInterval(() => {

                    window.scrollBy(
                        0,
                        distance
                    );

                    totalHeight += distance;

                    if (
                        totalHeight >=
                        document.body.scrollHeight
                    ) {
                        clearInterval(timer);
                        resolve();
                    }

                }, delay);
            });
        }
        """
    )

    # Give lazy-loaded elements a little more time
    # to appear after scrolling.

    page.wait_for_timeout(3_000)

    final_scroll_height = page.evaluate(
        "document.body.scrollHeight"
    )

    print(
        "Final scroll height:",
        final_scroll_height
    )

    # 1. High-Precision ID & Component Selectors (OneTrust, ING Web Components, Standard ARIA roles)
    known_cookie_selectors = [
        "#onetrust-accept-btn-handler",  # Universal OneTrust Accept ID (BNP, KBC, etc.)
        "#cookies_all_accept_btn",  # Common bank custom ID
        "ing-button:has-text('Accept')",  # ING custom web component
        "ing-button:has-text('Accepteer')",  # ING Dutch component
        "ing-button:has-text('Accepter')",  # ING French component
    ]


    for selector in known_cookie_selectors:
        trigger = page.locator(selector).first
        if trigger.is_visible():
            tag = trigger.evaluate("el => el.tagName")
            text = trigger.inner_text().strip().replace("\n", " ")
            print(f"✓ Clicked targeted cookie banner <{tag}>: '{text}'")
            trigger.click(force=True)
            page.wait_for_timeout(2000)
            return True

    # 2. Multilingual Role Matching (Button / Link)
    # Covers English, Dutch, and French variations
    text_pattern = re.compile(
        r"^(accept|accept all|accept cookies|j’accepte|accepter tout|alle cookies accepteren|accepteren)$",
        re.IGNORECASE,
    )

    for role in ["button", "link"]:
        trigger = page.get_by_role(role, name=text_pattern).first
        if trigger.is_visible():
            tag = trigger.evaluate("el => el.tagName")
            text = trigger.inner_text().strip().replace("\n", " ")
            print(f"✓ Clicked cookie {role} <{tag}>: '{text}'")
            trigger.click(force=True)
            page.wait_for_timeout(2000)
            return True

    # 3. Generic Fallback for unstandardized <div>, <a>, or <button> tags containing 'accept'
    fallback_locator = page.locator(
        "button, a, [role='button'], [class*='btn'], [class*='cookie']"
    ).filter(
        has_text=re.compile(
            r"(accept|accepter|accepteren|j’accepte)", re.IGNORECASE
        )
    )

    if fallback_locator.count() > 0:
        trigger = fallback_locator.first
        if trigger.is_visible():
            tag = trigger.evaluate("el => el.tagName")
            text = trigger.inner_text().strip().replace("\n", " ")
            print(f"✓ Clicked fallback cookie banner <{tag}>: '{text}'")
            trigger.click(force=True)
            page.wait_for_timeout(2000)
            return True

    print("ℹ No cookie banner detected or already accepted.")
    return False