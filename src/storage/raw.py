from datetime import datetime, timezone
from pathlib import Path
import hashlib


def save_raw_html(
    bank: str,
    url: str,
    html: str,
) -> dict:
    """
    Save the raw HTML of a crawled page to disk.

    Purpose:
    - Keep the original HTML returned by the crawler.
    - Allow future re-processing without crawling the website again.
    - Provide a reliable source for debugging and historical comparisons.
    - Store raw HTML separately from the structured SQLite database.

    Storage structure:

        data/
        └── raw/
            └── <bank>/
                └── <YYYY-MM-DD>/
                    └── <url_hash>.html

    Example:

        data/raw/ing/2026-09-16/a81f3e9c4d2b71aa.html

    Returns metadata about the stored HTML file.
    """

    # Use a timezone-aware UTC timestamp.
    # This is preferred over the deprecated/naive datetime.utcnow().
    timestamp = datetime.now(timezone.utc)

    # Generate a deterministic hash from the page URL.
    # The hash is used as a short and filesystem-safe filename.
    url_hash = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:16]

    # Build the directory where the raw HTML will be stored.
    # Files are organized by bank and retrieval date.
    directory = (
        Path("data")
        / "raw"
        / bank
        / timestamp.strftime("%Y-%m-%d")
    )

    # Create the directory if it does not already exist.
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Create the final HTML file path.
    path = directory / f"{url_hash}.html"

    # Save the original HTML content to disk.
    path.write_text(
        html,
        encoding="utf-8",
    )

    # Calculate a hash of the HTML content.
    # This can later be used to detect page content changes.
    content_hash = hashlib.sha256(
        html.encode("utf-8")
    ).hexdigest()

    # Return metadata about the saved page.
    return {
        "url": url,
        "path": str(path),
        "retrieved_at": timestamp.isoformat(),
        "content_hash": content_hash,
    }