from pathlib import Path
from datetime import date
from collections import Counter
import re

from PIL import Image
from playwright.sync_api import sync_playwright, Page

from storage.database import save_page
from storage.raw import save_raw_html


class BankCrawler:

    def __init__(
        self,
        bank_name: str,
        domain: str,
        include_keywords: list[str],
        exclude_keywords: list[str],
    ):
        # Store the bank-specific configuration.
        # These values can also be used later by the discovery layer.
        self.bank_name = bank_name
        self.domain = domain
        self.include_keywords = include_keywords
        self.exclude_keywords = exclude_keywords

    # =========================================================
    # COOKIE DEBUG
    # =========================================================

    def debug_cookie_banner(
        self,
        page: Page,
    ) -> None:
        """
        Diagnose cookie banners on the page.

        The method checks the main page and all iframes
        and prints visible buttons and links.

        This is mainly a diagnostic tool used when a new
        cookie consent system (CMP) is encountered.
        """

        print()
        print("===== COOKIE DEBUG =====")

        # Cookie banners are sometimes rendered inside iframes,
        # so every available frame must be inspected.
        for i, frame in enumerate(page.frames):

            print()
            print(f"--- FRAME {i} ---")
            print("URL:", frame.url)

            # -------------------------------------------------
            # BUTTONS
            # -------------------------------------------------

            try:

                buttons = frame.locator(
                    "button"
                ).all()

                print(
                    "Buttons:",
                    len(buttons),
                )

                for j, button in enumerate(buttons):

                    try:

                        # Ignore hidden buttons.
                        if not button.is_visible():
                            continue

                        text = (
                            button.inner_text()
                            .strip()
                        )

                        if text:

                            print(
                                f"BUTTON {j}: {text!r}"
                            )

                    except Exception:
                        # Ignore elements that cannot be inspected.
                        continue

            except Exception as e:

                print(
                    "BUTTON DEBUG ERROR:",
                    e,
                )

            # -------------------------------------------------
            # LINKS
            # -------------------------------------------------

            try:

                links = frame.locator(
                    "a"
                ).all()

                print(
                    "Links:",
                    len(links),
                )

                for j, link in enumerate(links):

                    try:

                        # Ignore hidden links.
                        if not link.is_visible():
                            continue

                        text = (
                            link.inner_text()
                            .strip()
                        )

                        if text:

                            print(
                                f"LINK {j}: {text!r}"
                            )

                    except Exception:
                        # Ignore elements that cannot be inspected.
                        continue

            except Exception as e:

                print(
                    "LINK DEBUG ERROR:",
                    e,
                )

        print(
            "========================"
        )

    # =========================================================
    # COOKIE BANNER
    # =========================================================

    def handle_cookie_banner(
        self,
        page: Page,
    ) -> bool:
        """
        Try to automatically accept the cookie banner.

        Strategy:
        1. Search for explicit "accept all" phrases.
        2. Search buttons.
        3. Search links.
        4. Search the main page and all iframes.
        5. Never click an explicit rejection option.
        6. Return True when an acceptance element was clicked.
        """

        print()
        print("===== COOKIE BANNER =====")

        # -----------------------------------------------------
        # ACCEPT ALL TEXTS
        # -----------------------------------------------------

        # Known phrases used by cookie consent systems.
        # This list can be extended when a new CMP is encountered.
        accept_cookie_texts = [

            # English
            "Accept all cookies",
            "Accept all",
            "Allow all cookies",
            "Allow all",
            "I agree to all",
            "Agree to all",
            "Accept cookies",
            "Allow cookies",

            # French
            "Accepter tous les cookies",
            "Accepter tout",
            "Tout accepter",
            "J'accepte",
            "J’accepte",

            # Dutch
            "Alle cookies accepteren",
            "Alles accepteren",
            "Accepteer alles",
            "Alle cookies toestaan",
            "Alles toestaan",

            # German
            "Alle Cookies akzeptieren",
            "Alle akzeptieren",
            "Alles akzeptieren",
            "Cookies akzeptieren",

            # Spanish
            "Aceptar todas las cookies",
            "Aceptar todo",
            "Permitir todo",
            "Aceptar cookies",

            # Italian
            "Accetta tutti i cookie",
            "Accetta tutto",
            "Consenti tutto",
            "Accetta cookie",
        ]

        # -----------------------------------------------------
        # EXPLICIT DENY / ESSENTIAL TEXTS
        # -----------------------------------------------------

        # These phrases are deliberately ignored.
        # This prevents the crawler from clicking "reject all"
        # or "essential cookies only".
        reject_cookie_texts = [

            # English
            "Essential cookies only",
            "Only essential cookies",
            "Essential cookies",
            "Reject all",
            "Reject all cookies",
            "Decline all",
            "Decline",

            # French
            "Cookies essentiels uniquement",
            "Uniquement les cookies essentiels",
            "Cookies strictement nécessaires",
            "Refuser tout",
            "Tout refuser",
            "Refuser",

            # Dutch
            "Alleen essentiële cookies",
            "Essentiële cookies",
            "Alles weigeren",
            "Weiger alles",
            "Weigeren",

            # German
            "Nur notwendige Cookies",
            "Nur essenzielle Cookies",
            "Alle ablehnen",
            "Ablehnen",

            # Spanish
            "Solo cookies esenciales",
            "Rechazar todas",
            "Rechazar",

            # Italian
            "Solo cookie essenziali",
            "Rifiuta tutto",
            "Rifiuta",
        ]

        # -----------------------------------------------------
        # NORMALISATION
        # -----------------------------------------------------

        # Normalize text so comparisons are not affected
        # by capitalization or repeated whitespace.
        def normalize_text(
            text: str,
        ) -> str:

            if not text:
                return ""

            text = text.strip().lower()

            text = re.sub(
                r"\s+",
                " ",
                text,
            )

            return text

        # Normalize the known phrases once before searching.
        normalized_accept_texts = [
            normalize_text(text)
            for text in accept_cookie_texts
        ]

        normalized_reject_texts = [
            normalize_text(text)
            for text in reject_cookie_texts
        ]

        # -----------------------------------------------------
        # TRY SINGLE ELEMENT
        # -----------------------------------------------------

        def try_click_element(
            element,
            element_type: str,
            frame_url: str,
        ) -> bool:

            # -------------------------------------------------
            # VISIBILITY
            # -------------------------------------------------

            # Only interact with visible elements.
            try:

                if not element.is_visible():
                    return False

            except Exception:

                return False

            # -------------------------------------------------
            # TEXT
            # -------------------------------------------------

            # Read the visible text of the element.
            try:

                text = (
                    element.inner_text()
                    .strip()
                )

            except Exception:

                return False

            if not text:
                return False

            normalized_text = normalize_text(
                text
            )

            # -------------------------------------------------
            # NEVER CLICK REJECTION
            # -------------------------------------------------

            # Safety rule:
            # never click an explicit rejection option.
            if any(
                reject_text == normalized_text
                or reject_text in normalized_text
                for reject_text in normalized_reject_texts
            ):

                print(
                    "Ignoring cookie rejection:",
                    repr(text),
                )

                return False

            # -------------------------------------------------
            # SEARCH ACCEPT TEXT
            # -------------------------------------------------

            matched_text = None

            # Search for a known acceptance phrase.
            for accept_text in normalized_accept_texts:

                if (
                    accept_text == normalized_text
                    or accept_text in normalized_text
                ):

                    matched_text = accept_text
                    break

            if not matched_text:
                return False

            # -------------------------------------------------
            # CLICK
            # -------------------------------------------------

            print(
                "Cookie accept button found:",
                repr(text),
            )

            print(
                "Matched text:",
                repr(matched_text),
            )

            print(
                "Element type:",
                element_type,
            )

            print(
                "Frame:",
                frame_url,
            )

            try:

                # Click the cookie acceptance element.
                element.click(
                    timeout=5000
                )

                print(
                    "Cookie button clicked."
                )

                # Give the CMP time to update the page.
                page.wait_for_timeout(
                    1000
                )

                return True

            except Exception as e:

                print(
                    "Cookie click failed:",
                    e,
                )

                return False

        # -----------------------------------------------------
        # SEARCH FRAMES
        # -----------------------------------------------------

        # Inspect every frame because cookie banners
        # can be rendered inside iframes.
        for frame in page.frames:

            print(
                "Checking cookie frame:",
                frame.url,
            )

            # -------------------------------------------------
            # BUTTONS
            # -------------------------------------------------

            try:

                buttons = frame.locator(
                    "button"
                ).all()

                # Check buttons first because most CMPs
                # use button elements for consent actions.
                for button in buttons:

                    if try_click_element(
                        button,
                        "button",
                        frame.url,
                    ):

                        return True

            except Exception as e:

                print(
                    "Cookie button search error:",
                    e,
                )

            # -------------------------------------------------
            # LINKS
            # -------------------------------------------------

            try:

                links = frame.locator(
                    "a"
                ).all()

                # Some CMPs implement consent actions as links.
                for link in links:

                    if try_click_element(
                        link,
                        "link",
                        frame.url,
                    ):

                        return True

            except Exception as e:

                print(
                    "Cookie link search error:",
                    e,
                )

        # -----------------------------------------------------
        # NOTHING FOUND
        # -----------------------------------------------------

        print(
            "No cookie acceptance button handled."
        )

        return False

    # =========================================================
    # COOKIE BANNER VISIBILITY CHECK
    # =========================================================

    def cookie_banner_still_visible(
        self,
        page: Page,
    ) -> bool:
        """
        Check whether a cookie banner still appears to be visible.

        The search is performed in all frames.
        """

        # Common phrases that may indicate that
        # the cookie banner is still displayed.
        cookie_texts = [

            # English
            "Accept all cookies",
            "Accept all",
            "Allow all cookies",
            "Allow all",
            "Essential cookies only",
            "Only essential cookies",

            # French
            "Accepter tous les cookies",
            "Accepter tout",
            "Tout accepter",

            # Dutch
            "Alle cookies accepteren",
            "Alles accepteren",

            # German
            "Alle Cookies akzeptieren",
            "Alle akzeptieren",

            # Spanish
            "Aceptar todas las cookies",
            "Aceptar todo",

            # Italian
            "Accetta tutti i cookie",
            "Accetta tutto",
        ]

        # Search every frame.
        for frame in page.frames:

            for text in cookie_texts:

                try:

                    locator = frame.get_by_text(
                        text,
                        exact=False,
                    )

                    count = locator.count()

                    if count == 0:
                        continue

                    for i in range(count):

                        element = locator.nth(i)

                        try:

                            if element.is_visible():
                                return True

                        except Exception:
                            continue

                except Exception:
                    continue

        return False

    # =========================================================
    # VERIFY COOKIE BANNER
    # =========================================================

    def verify_cookie_banner(
        self,
        page: Page,
        retries: int = 2,
    ) -> bool:
        """
        Verify that the cookie banner has actually disappeared.

        If it is still visible, wait and check again.

        Returns:
            True  -> banner is no longer visible
            False -> banner is still visible
        """

        # Cookie CMPs sometimes need a short delay after the click.
        for attempt in range(
            retries + 1
        ):

            still_visible = (
                self.cookie_banner_still_visible(
                    page
                )
            )

            if not still_visible:

                print(
                    "Cookie banner successfully removed."
                )

                return True

            print(
                f"WARNING: Cookie banner is still visible "
                f"(check {attempt + 1}/{retries + 1})."
            )

            if attempt < retries:

                page.wait_for_timeout(
                    1500
                )

        return False

    # =========================================================
    # SCREENSHOT
    # =========================================================

    def save_screenshot(
        self,
        page: Page,
        url: str,
    ) -> str | None:
        """
        Save a full-page screenshot.

        Screenshots provide a visual record of the page
        at the moment it was crawled.
        """

        try:

            # Resolve the project root from this source file.
            project_root = Path(
                __file__
            ).resolve().parents[2]

            # Store screenshots separately for each bank.
            screenshot_dir = (
                project_root
                / "data"
                / "screenshots"
                / self.bank_name
            )

            screenshot_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            # Use the crawl date as the filename.
            filename = (
                f"{date.today().isoformat()}.png"
            )

            screenshot_path = (
                screenshot_dir
                / filename
            )

            # Capture the entire page, not only the viewport.
            page.screenshot(
                path=str(screenshot_path),
                full_page=True,
            )

            print(
                "Screenshot:",
                screenshot_path,
            )

            return str(
                screenshot_path
            )

        except Exception as e:

            print(
                "SCREENSHOT ERROR:",
                e,
            )

            return None

    # =========================================================
    # DOMINANT COLORS
    # =========================================================

    def extract_dominant_colors(
        self,
        screenshot_path: str | None,
        color_count: int = 5,
    ) -> list[str]:
        """
        Extract dominant colors from the screenshot.

        Returns hexadecimal values such as:
            ['#ffffff', '#ff6200', '#000000']
        """

        # No screenshot means no color analysis is possible.
        if not screenshot_path:
            return []

        try:

            # Open the screenshot using Pillow.
            image = Image.open(
                screenshot_path
            )

            # Use RGB for consistent color processing.
            image = image.convert(
                "RGB"
            )

            # Reduce the image size to make the analysis faster.
            image.thumbnail(
                (800, 800)
            )

            # Reduce the number of colors to a manageable palette.
            quantized = image.quantize(
                colors=32
            ).convert(
                "RGB"
            )

            pixels = list(
                quantized.getdata()
            )

            # Count how frequently each RGB color appears.
            counter = Counter(
                pixels
            )

            dominant_colors = []

            # Keep the most frequent colors.
            for rgb, _count in counter.most_common(
                color_count
            ):

                hex_color = (
                    "#{:02x}{:02x}{:02x}".format(
                        rgb[0],
                        rgb[1],
                        rgb[2],
                    )
                )

                dominant_colors.append(
                    hex_color
                )

            return dominant_colors

        except Exception as e:

            print(
                "COLOR EXTRACTION ERROR:",
                e,
            )

            return []

    # =========================================================
    # NUMERIC OFFER
    # =========================================================

    def detect_numeric_offer(
        self,
        text: str,
    ) -> bool:
        """
        Detect whether the page contains a concrete numeric offer.

        Examples:
            €50
            4%
            4.00%
            50 EUR
            50€
        """

        # Empty text cannot contain an offer.
        if not text:
            return False

        # Regular expressions for common financial offers.
        patterns = [

            # Euro symbol before the amount.
            r"€\s?\d+(?:[.,]\d+)?",

            # Euro symbol after the amount.
            r"\d+(?:[.,]\d+)?\s?€",

            # Percentage values.
            r"\d+(?:[.,]\d+)?\s?%",

            # Amount followed by EUR/euro/euros.
            r"\d+(?:[.,]\d+)?\s?(?:EUR|euro|euros)",
        ]

        # Return True as soon as a supported pattern is found.
        for pattern in patterns:

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):

                return True

        return False

    # =========================================================
    # CTA EXTRACTION
    # =========================================================

    def extract_ctas(
        self,
        page: Page,
    ) -> list[dict]:
        """
        Extract visible CTA-like links and buttons.

        CTAs are useful for identifying the main marketing
        actions presented to visitors.
        """

        ctas = []

        # -----------------------------------------------------
        # BUTTONS
        # -----------------------------------------------------

        # Extract visible buttons first.
        for element in page.locator(
            "button"
        ).all():

            try:

                if not element.is_visible():
                    continue

                text = (
                    element.inner_text()
                    .strip()
                )

            except Exception:

                continue

            if text:

                ctas.append({
                    "text": text,
                    "type": "button",
                })

        # -----------------------------------------------------
        # LINKS
        # -----------------------------------------------------

        # Keywords used to detect links that act as CTAs.
        cta_keywords = [

            "open",
            "apply",
            "start",
            "get",
            "discover",
            "learn",
            "calculate",
            "contact",
            "request",
            "become",
            "sign up",
            "register",

        ]

        # Extract visible links with an href attribute.
        for element in page.locator(
            "a[href]"
        ).all():

            try:

                if not element.is_visible():
                    continue

                text = (
                    element.inner_text()
                    .strip()
                )

            except Exception:

                continue

            if not text:
                continue

            text_lower = text.lower()

            # Keep the link when its text contains
            # at least one CTA keyword.
            if any(
                keyword in text_lower
                for keyword in cta_keywords
            ):

                href = element.get_attribute(
                    "href"
                )

                ctas.append({
                    "text": text,
                    "href": href,
                    "type": "link",
                })

        return ctas

    # =========================================================
    # EXTRACTION FROM PLAYWRIGHT RENDERED DOM
    # =========================================================

    def extract_page_from_browser(
        self,
        page: Page,
    ) -> dict:
        """
        Extract content directly from the live Playwright DOM.

        This is preferred over page.content() because modern
        websites can rely heavily on JavaScript, Web Components,
        and dynamic rendering.
        """

        # -----------------------------------------------------
        # TITLE
        # -----------------------------------------------------

        # Read the browser page title.
        title = page.title()

        # -----------------------------------------------------
        # META DESCRIPTION
        # -----------------------------------------------------

        # Extract the SEO meta description when available.
        meta_description = None

        meta = page.locator(
            'meta[name="description"]'
        )

        if meta.count() > 0:

            meta_description = (
                meta.first.get_attribute(
                    "content"
                )
            )

        # -----------------------------------------------------
        # HEADINGS
        # -----------------------------------------------------

        headings = []

        # Extract H1, H2 and H3 headings.
        for element in page.locator(
            "h1, h2, h3"
        ).all():

            try:

                text = (
                    element.inner_text()
                    .strip()
                )

            except Exception:

                continue

            if text:

                headings.append(
                    text
                )

        # -----------------------------------------------------
        # PARAGRAPHS
        # -----------------------------------------------------

        paragraphs = []

        # Extract visible paragraph text.
        for element in page.locator(
            "p"
        ).all():

            try:

                text = (
                    element.inner_text()
                    .strip()
                )

            except Exception:

                continue

            if text:

                paragraphs.append(
                    text
                )

        # -----------------------------------------------------
        # LINKS
        # -----------------------------------------------------

        links = []

        # Extract links and their destination URLs.
        for element in page.locator(
            "a[href]"
        ).all():

            try:

                href = (
                    element.get_attribute(
                        "href"
                    )
                )

                text = (
                    element.inner_text()
                    .strip()
                )

            except Exception:

                continue

            if href:

                links.append({
                    "text": text,
                    "href": href,
                })

        # -----------------------------------------------------
        # IMAGES
        # -----------------------------------------------------

        images = []

        # Extract image source and alternative text.
        for element in page.locator(
            "img"
        ).all():

            try:

                src = (
                    element.get_attribute(
                        "src"
                    )
                )

                alt = (
                    element.get_attribute(
                        "alt"
                    )
                )

            except Exception:

                continue

            images.append({
                "src": src,
                "alt": alt,
            })

        # -----------------------------------------------------
        # CTA
        # -----------------------------------------------------

        # Reuse the CTA extraction logic.
        ctas = self.extract_ctas(
            page
        )

        # -----------------------------------------------------
        # RAW TEXT
        # -----------------------------------------------------

        # Extract visible text from the entire page body.
        raw_text = ""

        try:

            raw_text = (
                page.locator(
                    "body"
                )
                .inner_text()
                .strip()
            )

        except Exception as e:

            print(
                "RAW TEXT ERROR:",
                e,
            )

        # -----------------------------------------------------
        # NUMERIC OFFER
        # -----------------------------------------------------

        # Search the visible page text for concrete financial offers.
        has_numeric_offer = (
            self.detect_numeric_offer(
                raw_text
            )
        )

        # -----------------------------------------------------
        # RETURN
        # -----------------------------------------------------

        return {
            "title": title,
            "meta_description": meta_description,
            "headings": headings,
            "paragraphs": paragraphs,
            "links": links,
            "images": images,
            "ctas": ctas,
            "raw_text": raw_text,
            "has_numeric_offer": has_numeric_offer,
        }

    # =========================================================
    # FETCH + JAVASCRIPT RENDERING
    # =========================================================

    def fetch(
        self,
        url: str,
    ) -> dict:
        """
        Open and render a page with Playwright.

        Main workflow:

            navigation
                ↓
            JavaScript rendering
                ↓
            cookie handling
                ↓
            diagnostics
                ↓
            screenshot
                ↓
            color analysis
                ↓
            content extraction
                ↓
            HTML snapshot
        """

        with sync_playwright() as p:

            # Launch Chromium in headless mode.
            browser = p.chromium.launch(
                headless=True
            )

            # Create a browser page with Belgian English locale.
            page = browser.new_page(
                locale="en-BE"
            )

            # -------------------------------------------------
            # LOG API / JSON RESPONSES
            # -------------------------------------------------

            # Modern websites often load content through APIs.
            # This listener helps identify JSON/API responses.
            def log_response(response):

                content_type = (
                    response.headers.get(
                        "content-type",
                        "",
                    ).lower()
                )

                if (
                    "json" in content_type
                    or "api" in response.url.lower()
                ):

                    print(
                        "DATA:",
                        response.status,
                        content_type,
                        response.url,
                    )

            page.on(
                "response",
                log_response,
            )

            # -------------------------------------------------
            # NAVIGATION
            # -------------------------------------------------

            print()
            print("===== NAVIGATION =====")

            # Load the page and wait until the initial DOM is ready.
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=120_000,
            )

            print(
                "Initial response:",
                response.status
                if response
                else None,
            )

            print(
                "URL:",
                page.url,
            )

            # -------------------------------------------------
            # WAIT FOR JAVASCRIPT APPLICATION
            # -------------------------------------------------

            # Allow client-side applications and Web Components
            # enough time to finish rendering.
            page.wait_for_timeout(
                10_000
            )

            # -------------------------------------------------
            # COOKIE DEBUG
            # -------------------------------------------------

            self.debug_cookie_banner(
                page
            )

            # -------------------------------------------------
            # COOKIES
            # -------------------------------------------------

            # Try to automatically accept all cookies.
            cookie_clicked = (
                self.handle_cookie_banner(
                    page
                )
            )

            # -------------------------------------------------
            # VERIFY COOKIE
            # -------------------------------------------------

            if cookie_clicked:

                print()
                print(
                    "===== COOKIE VERIFICATION ====="
                )

                # Confirm that the consent banner actually disappeared.
                cookie_removed = (
                    self.verify_cookie_banner(
                        page,
                        retries=2,
                    )
                )

                if not cookie_removed:

                    print(
                        "WARNING: Cookie banner could not "
                        "be confirmed as removed."
                    )

            else:

                print(
                    "No cookie acceptance action performed."
                )

                # Even when no click was made,
                # check whether a banner is still visible.
                if self.cookie_banner_still_visible(
                    page
                ):

                    print(
                        "WARNING: Cookie banner is still visible!"
                    )

                else:

                    print(
                        "No cookie banner detected."
                    )

            # -------------------------------------------------
            # ALLOW PAGE TO UPDATE
            # -------------------------------------------------

            # Give the page a short additional moment
            # to react to the cookie state.
            page.wait_for_timeout(
                1_000
            )

            # -------------------------------------------------
            # PAGE STATE
            # -------------------------------------------------

            print()
            print("===== PAGE STATE =====")

            print(
                "Title:",
                page.title(),
            )

            print(
                "Frames:",
                len(page.frames),
            )

            # Print all frame URLs for diagnostics.
            for frame in page.frames:

                print(
                    "FRAME:",
                    frame.url,
                )

            # -------------------------------------------------
            # DOM DIAGNOSTICS
            # -------------------------------------------------

            print()
            print("===== DOM DIAGNOSTICS =====")

            # Count important elements in the rendered DOM.
            h1_count = page.locator(
                "h1"
            ).count()

            h2_count = page.locator(
                "h2"
            ).count()

            p_count = page.locator(
                "p"
            ).count()

            a_count = page.locator(
                "a"
            ).count()

            img_count = page.locator(
                "img"
            ).count()

            print(
                "H1:",
                h1_count,
            )

            print(
                "H2:",
                h2_count,
            )

            print(
                "P:",
                p_count,
            )

            print(
                "A:",
                a_count,
            )

            print(
                "IMG:",
                img_count,
            )

            # -------------------------------------------------
            # VISIBLE TEXT
            # -------------------------------------------------

            # Read visible page text for diagnostics.
            body_text = ""

            try:

                body_text = (
                    page.locator(
                        "body"
                    ).inner_text()
                )

            except Exception as e:

                print(
                    "BODY TEXT ERROR:",
                    e,
                )

            print(
                "Visible text length:",
                len(body_text),
            )

            print()

            # Print only a limited preview in the console.
            if body_text:

                print(
                    body_text[:3000]
                )

            # -------------------------------------------------
            # FINAL COOKIE CHECK BEFORE SCREENSHOT
            # -------------------------------------------------

            print()
            print(
                "===== FINAL COOKIE CHECK ====="
            )

            # Make sure the cookie banner is not visible
            # in the final screenshot.
            if self.cookie_banner_still_visible(
                page
            ):

                print(
                    "WARNING: Cookie banner is still visible "
                    "before screenshot!"
                )

            else:

                print(
                    "Cookie banner is not visible before screenshot."
                )

            # -------------------------------------------------
            # SCREENSHOT
            # -------------------------------------------------

            # Capture the final rendered page.
            screenshot_path = (
                self.save_screenshot(
                    page,
                    url,
                )
            )

            # -------------------------------------------------
            # DOMINANT COLORS
            # -------------------------------------------------

            # Analyze the screenshot to identify
            # the main visual colors of the page.
            dominant_colors = (
                self.extract_dominant_colors(
                    screenshot_path
                )
            )

            print()
            print(
                "Dominant colors:",
                dominant_colors,
            )

            # -------------------------------------------------
            # PLAYWRIGHT EXTRACTION
            # -------------------------------------------------

            # Extract content directly from the live browser DOM.
            extracted = (
                self.extract_page_from_browser(
                    page
                )
            )

            print()
            print("===== EXTRACTION =====")

            print(
                "Title:",
                extracted["title"],
            )

            print(
                "Headings:",
                len(
                    extracted["headings"]
                ),
            )

            print(
                "Paragraphs:",
                len(
                    extracted["paragraphs"]
                ),
            )

            print(
                "Links:",
                len(
                    extracted["links"]
                ),
            )

            print(
                "Images:",
                len(
                    extracted["images"]
                ),
            )

            print(
                "CTAs:",
                len(
                    extracted["ctas"]
                ),
            )

            print(
                "Numeric offer:",
                extracted[
                    "has_numeric_offer"
                ],
            )

            print(
                "Raw text length:",
                len(
                    extracted["raw_text"]
                ),
            )

            print(
                "======================"
            )

            # -------------------------------------------------
            # HTML SNAPSHOT
            # -------------------------------------------------

            # Save the serialized page HTML for archival/debugging.
            #
            # The main extraction does NOT depend on this snapshot.
            # Playwright locators are used because modern websites
            # can rely on JavaScript and Web Components.
            html = page.content()

            # -------------------------------------------------
            # BROWSER CLOSE
            # -------------------------------------------------

            # Close the browser after all extraction is complete.
            browser.close()

        # -----------------------------------------------------
        # RESULT
        # -----------------------------------------------------

        return {
            "html": html,
            "content": extracted,
            "screenshot_path": screenshot_path,
            "dominant_colors": dominant_colors,
        }

    # =========================================================
    # PROCESS PAGE
    # =========================================================

    def process_page(
        self,
        url: str,
    ):
        """
        Process one page from start to finish.

        Steps:
        1. Fetch and render the page.
        2. Extract structured content.
        3. Save structured data to SQLite.
        4. Save raw HTML to disk.
        5. Return the collected result.
        """

        # -----------------------------------------------------
        # FETCH PAGE
        # -----------------------------------------------------

        result = self.fetch(
            url
        )

        html = result["html"]

        extracted = result["content"]

        # -----------------------------------------------------
        # HEADLINE
        # -----------------------------------------------------

        # Use the first heading as the main headline.
        headline = None

        if extracted["headings"]:

            headline = (
                extracted["headings"][0]
            )

        # -----------------------------------------------------
        # MAIN CTA
        # -----------------------------------------------------

        # Use the first CTA as the main CTA.
        cta_text = None

        if extracted["ctas"]:

            cta_text = (
                extracted["ctas"][0]["text"]
            )

        # -----------------------------------------------------
        # SAVE TO SQLITE
        # -----------------------------------------------------

        # Store the structured page information in the database.
        save_page(
            bank=self.bank_name,
            page_url=url,
            language="en",
            headline=headline,
            has_numeric_offer=(
                extracted[
                    "has_numeric_offer"
                ]
            ),
            cta_text=cta_text,
            cta_count=len(
                extracted["ctas"]
            ),
            image_count=len(
                extracted["images"]
            ),
            dominant_colors=result[
                "dominant_colors"
            ],
            topics=None,
            raw_text=extracted[
                "raw_text"
            ],
            screenshot_path=result[
                "screenshot_path"
            ],
            source_type="html",
        )

        # -----------------------------------------------------
        # SAVE RAW HTML
        # -----------------------------------------------------

        # Save the original HTML separately.
        # This allows future debugging or re-processing
        # without crawling the website again.
        raw = save_raw_html(
            bank=self.bank_name,
            url=url,
            html=html,
        )

        # -----------------------------------------------------
        # FINAL RESULT
        # -----------------------------------------------------

        # Return all important results and storage references.
        return {
            "url": url,
            "status_code": 200,
            "raw": raw,
            "content": extracted,
            "screenshot_path": result[
                "screenshot_path"
            ],
            "dominant_colors": result[
                "dominant_colors"
            ],
        }