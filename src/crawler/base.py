from pathlib import Path

from playwright.sync_api import sync_playwright

from extraction.page_parser import extract_page
from storage.raw import save_raw_html


class BankCrawler:

    def __init__(
        self,
        bank_name: str,
        domain: str,
        include_keywords: list[str],
        exclude_keywords: list[str],
    ):
        self.bank_name = bank_name
        self.domain = domain
        self.include_keywords = include_keywords
        self.exclude_keywords = exclude_keywords

    def fetch(self, url: str) -> str:

        with sync_playwright() as p:

            browser = p.firefox.launch(
                headless=True
            )

            page = browser.new_page(
                locale="en-BE"
            )

            # DEBUG : erreurs JavaScript
            page.on(
                "console",
                lambda msg: print(
                    "CONSOLE:",
                    msg.type,
                    msg.text
                )
            )

            page.on(
                "pageerror",
                lambda exc: print(
                    "PAGE ERROR:",
                    exc
                )
            )

            # DEBUG : réponses réseau
            def log_response(response):

                content_type = response.headers.get(
                    "content-type",
                    ""
                ).lower()

                if (
                    "json" in content_type
                    or "api" in response.url.lower()
                ):
                    print(
                        "DATA:",
                        response.status,
                        content_type,
                        response.url
                    )

            page.on(
                "response",
                log_response
            )

            print()
            print("===== NAVIGATION =====")

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )

            print(
                "Initial response:",
                response.status if response else None
            )

            print(
                "URL:",
                page.url
            )

            page.wait_for_timeout(10_000)

            # Scroll progressif
            print()
            print("===== SCROLLING PAGE =====")

            page.evaluate("""
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
            """)

            page.wait_for_timeout(3_000)

            final_scroll_height = page.evaluate(
                "document.body.scrollHeight"
            )

            print(
                "Final scroll height:",
                final_scroll_height
            )

            # Screenshot complet
            screenshot_dir = Path(
                "data/screenshots"
            ) / self.bank_name

            screenshot_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            screenshot_path = (
                screenshot_dir / "page_full.png"
            )

            page.screenshot(
                path=str(screenshot_path),
                full_page=True
            )

            print(
                "Full screenshot:",
                screenshot_path
            )

            # Retour en haut
            page.evaluate(
                "window.scrollTo(0, 0)"
            )

            page.wait_for_timeout(1_000)

            # Etat de la page
            print()
            print("===== PAGE STATE =====")

            print(
                "Title:",
                page.title()
            )

            print(
                "Frames:",
                len(page.frames)
            )

            for frame in page.frames:
                print(
                    "FRAME:",
                    frame.url
                )

            # HTML final
            html = page.content()

            print(
                "HTML length:",
                len(html)
            )

            # BODY
            body = page.locator("body")

            print(
                "Body exists:",
                body.count()
            )

            if body.count() > 0:

                body_html = body.inner_html()

                print(
                    "Body HTML length:",
                    len(body_html)
                )

                print()
                print("===== BODY HTML =====")

                print(
                    body_html[:5_000]
                )

                print(
                    "====================="
                )

                body_text = body.inner_text()

                print()
                print(
                    "Visible text length:",
                    len(body_text)
                )

                print(
                    body_text[:3_000]
                )

            print()
            print("=====================")

            browser.close()

        return html

    def process_page(self, url: str):

        html = self.fetch(url)

        raw = save_raw_html(
            bank=self.bank_name,
            url=url,
            html=html,
        )

        extracted = extract_page(html)

        return {
            "url": url,
            "status_code": 200,
            "raw": raw,
            "content": extracted,
        }