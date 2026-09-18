from pathlib import Path
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from extraction.page_parser import extract_page
from storage.raw import save_raw_html


class BankCrawler:
    """
    Generic crawler used for all banks.

    Bank-specific configuration is stored in banks.yaml.
    This class only contains the crawling logic.

    The crawler:
    1. Opens a page with Firefox.
    2. Waits for the page to load.
    3. Scrolls through the page to trigger lazy-loaded content.
    4. Takes a full-page screenshot.
    5. Retrieves the final HTML.
    6. Extracts structured information with Playwright.
    7. Saves the raw HTML.

    No bank-specific crawling logic should be added here.
    """

    def __init__(self, bank_name: str):
        """
        Initialize the crawler for one bank.

        Parameters
        ----------
        bank_name:
            Identifier used in banks.yaml, for example:
            "ing", "kbc", "belfius" or "bnp".
        """

        self.bank_name = bank_name

    def fetch(self, url: str) -> dict:
        """
        Open, render and extract one webpage.

        Returns
        -------
        dict
            Contains:
            - final URL
            - HTTP status code
            - raw HTML
            - screenshot path
            - extracted page content
        """

        with sync_playwright() as p:

            # --------------------------------------------------
            # Launch Firefox
            # --------------------------------------------------
            #
            # Firefox is used for the entire project.
            # Headless=True means that no browser window is shown.
            #

            browser = p.firefox.launch(
                headless=True
            )

            # --------------------------------------------------
            # Create browser context
            # --------------------------------------------------

            context = browser.new_context(
                locale="en-BE"
            )

            page = context.new_page()

            # --------------------------------------------------
            # Navigate to the target URL
            # --------------------------------------------------

            print()
            print("===== NAVIGATION =====")
            print("URL:", url)

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )

            status_code = (
                response.status
                if response
                else None
            )

            print(
                "Initial response:",
                status_code
            )

            print(
                "Current URL:",
                page.url
            )

            # --------------------------------------------------
            # Wait for JavaScript-rendered content
            # --------------------------------------------------
            #
            # Banking websites often load content dynamically.
            # This gives JavaScript time to render additional
            # elements before extraction.
            #

            page.wait_for_timeout(10_000)

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

            # --------------------------------------------------
            # Generate screenshot filename
            # --------------------------------------------------
            #
            # Belgian local time is used.
            #
            # Example:
            #
            # 2026-09-18_14-37-52_a81f42c9.png
            #
            # The URL hash prevents different URLs captured
            # at the same second from overwriting each other.
            #

            timestamp = datetime.now(
                ZoneInfo("Europe/Brussels")
            ).strftime(
                "%Y-%m-%d_%H-%M-%S"
            )

            url_hash = hashlib.sha256(
                url.encode("utf-8")
            ).hexdigest()[:8]

            screenshot_dir = (
                Path("data")
                / "screenshots"
                / self.bank_name
            )

            screenshot_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            screenshot_path = (
                screenshot_dir
                / f"{timestamp}_{url_hash}.png"
            )

            # --------------------------------------------------
            # Save full-page screenshot
            # --------------------------------------------------

            page.screenshot(
                path=str(screenshot_path),
                full_page=True
            )

            print(
                "Screenshot saved:",
                screenshot_path
            )

            # --------------------------------------------------
            # Return to the top of the page
            # --------------------------------------------------

            page.evaluate(
                "window.scrollTo(0, 0)"
            )

            page.wait_for_timeout(1_000)

            # --------------------------------------------------
            # Retrieve final HTML
            # --------------------------------------------------
            #
            # page.content() gives us the DOM after JavaScript
            # execution.
            #

            html = page.content()

            print(
                "HTML length:",
                len(html)
            )

            # --------------------------------------------------
            # Extract structured information
            # --------------------------------------------------
            #
            # Extraction is performed while the Playwright page
            # is still open.
            #

            extracted = extract_page(page)

            # --------------------------------------------------
            # Store final URL before closing the browser
            # --------------------------------------------------

            final_url = page.url

            # --------------------------------------------------
            # Close browser session
            # --------------------------------------------------

            context.close()
            browser.close()

        # ------------------------------------------------------
        # Return complete crawl result
        # ------------------------------------------------------

        return {
            "url": final_url,
            "status_code": status_code,
            "html": html,
            "screenshot_path": str(
                screenshot_path
            ),
            "content": extracted,
        }

    def process_page(self, url: str) -> dict:
        """
        Crawl, store and parse one webpage.

        Workflow:

        1. Fetch and render the webpage with Firefox.
        2. Save the raw HTML.
        3. Save the crawl result in SQLite.
        4. Return the extracted content.
        """

        result = self.fetch(url)

        # --------------------------------------------------------
        # SAVE RAW HTML
        # --------------------------------------------------------

        raw = save_raw_html(
            bank=self.bank_name,
            url=url,
            html=result["html"],
        )

        # --------------------------------------------------------
        # SAVE DATABASE RECORD
        # --------------------------------------------------------

        content = result["content"]

        page_id = save_page(
            bank=self.bank_name,
            page_url=url,
            final_url=result["url"],
            status_code=result["status_code"],
            title=content["title"],
            meta_description=content["meta_description"],
            headings=content["headings"],
            paragraphs=content["paragraphs"],
            links=content["links"],
            images=content["images"],
            screenshot_path=result["screenshot_path"],
            raw_html_path=raw["path"],
            content_hash=raw["content_hash"],
        )

        print(
            "Database page ID:",
            page_id
        )

        # --------------------------------------------------------
        # RETURN RESULT
        # --------------------------------------------------------

        return {
            "url": result["url"],
            "status_code": result["status_code"],
            "raw": raw,
            "screenshot_path": result["screenshot_path"],
            "content": content,
            "page_id": page_id,
        }