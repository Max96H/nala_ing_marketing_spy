from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


# ============================================================
# SAVE RAW HTML
# ============================================================

def save_raw_html(
    bank: str,
    url: str,
    html: str,
) -> dict:
    """
    Save the raw HTML of a crawled page to disk.

    Each crawl creates a separate HTML file.

    Storage structure:

        data/
        └── raw/
            └── <bank>/
                └── <YYYY-MM-DD>/
                    └── <timestamp>_<url_hash>.html

    Example:

        data/raw/ing/2026-09-18/
            2026-09-18_14-37-52_a81f3e9c4d2b71aa.html

    Keeping every crawl allows the project to compare
    how a marketing page changes over time.

    Returns
    -------
    dict
        Metadata about the stored HTML file.
    """

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------
    #
    # Use Belgian local time so that filenames are easy to
    # understand when reviewing the crawl history.
    #

    timestamp = datetime.now(
        ZoneInfo("Europe/Brussels")
    )

    timestamp_string = timestamp.strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    # --------------------------------------------------------
    # URL hash
    # --------------------------------------------------------
    #
    # The URL hash creates a short and filesystem-safe
    # identifier for the crawled page.
    #

    url_hash = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:16]

    # --------------------------------------------------------
    # Directory
    # --------------------------------------------------------
    #
    # Organize files by bank and crawl date.
    #

    directory = (
        RAW_DATA_DIR
        / bank
        / timestamp.strftime("%Y-%m-%d")
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # File path
    # --------------------------------------------------------

    filename = (
        f"{timestamp_string}_{url_hash}.html"
    )

    path = directory / filename

    # --------------------------------------------------------
    # Save HTML
    # --------------------------------------------------------

    path.write_text(
        html,
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # HTML content hash
    # --------------------------------------------------------
    #
    # This hash represents the actual HTML content.
    #
    # It can later be used to determine whether a page has
    # changed between two crawls.
    #

    content_hash = hashlib.sha256(
        html.encode("utf-8")
    ).hexdigest()

    # --------------------------------------------------------
    # Return metadata
    # --------------------------------------------------------

    return {
        "url": url,
        "path": str(path),
        "retrieved_at": timestamp.isoformat(),
        "content_hash": content_hash,
    }