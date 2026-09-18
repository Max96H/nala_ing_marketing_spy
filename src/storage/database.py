import sqlite3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# DATABASE PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_DIR = PROJECT_ROOT / "data"

DATABASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_PATH = DATABASE_DIR / "crawler.db"


# ============================================================
# CONNECTION
# ============================================================

def get_connection():
    """
    Return a SQLite connection.
    """

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():
    """
    Create the database tables if they do not already exist.
    """

    connection = get_connection()

    cursor = connection.cursor()

    # ========================================================
    # PAGES
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            bank TEXT NOT NULL,

            page_url TEXT NOT NULL,

            final_url TEXT,

            scrape_timestamp TEXT NOT NULL,

            status_code INTEGER,

            title TEXT,

            meta_description TEXT,

            screenshot_path TEXT,

            raw_html_path TEXT,

            content_hash TEXT

        )
        """
    )

    # ========================================================
    # HEADINGS
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS page_headings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            page_id INTEGER NOT NULL,

            heading TEXT NOT NULL,

            FOREIGN KEY (
                page_id
            )
            REFERENCES pages(id)
            ON DELETE CASCADE

        )
        """
    )

    # ========================================================
    # PARAGRAPHS
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS page_paragraphs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            page_id INTEGER NOT NULL,

            paragraph TEXT NOT NULL,

            FOREIGN KEY (
                page_id
            )
            REFERENCES pages(id)
            ON DELETE CASCADE

        )
        """
    )

    # ========================================================
    # LINKS
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS page_links (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            page_id INTEGER NOT NULL,

            link_text TEXT,

            href TEXT,

            FOREIGN KEY (
                page_id
            )
            REFERENCES pages(id)
            ON DELETE CASCADE

        )
        """
    )

    # ========================================================
    # IMAGES
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS page_images (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            page_id INTEGER NOT NULL,

            src TEXT,

            alt TEXT,

            FOREIGN KEY (
                page_id
            )
            REFERENCES pages(id)
            ON DELETE CASCADE

        )
        """
    )

    connection.commit()
    connection.close()


# ============================================================
# SAVE PAGE
# ============================================================

def save_page(
    bank,
    page_url,
    final_url=None,
    status_code=None,
    title=None,
    meta_description=None,
    headings=None,
    paragraphs=None,
    links=None,
    images=None,
    screenshot_path=None,
    raw_html_path=None,
    content_hash=None,
    scrape_timestamp=None,
):
    """
    Save one crawl result in SQLite.

    Each crawl is stored as a separate record.

    This is intentional: the project needs to preserve
    historical versions of marketing pages.
    """

    init_db()

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    if scrape_timestamp is None:

        scrape_timestamp = datetime.now(
            ZoneInfo("Europe/Brussels")
        ).isoformat()

    connection = get_connection()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # Save main page record
    # --------------------------------------------------------

    cursor.execute(
        """
        INSERT INTO pages (
            bank,
            page_url,
            final_url,
            scrape_timestamp,
            status_code,
            title,
            meta_description,
            screenshot_path,
            raw_html_path,
            content_hash
        )
        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            bank,
            page_url,
            final_url,
            scrape_timestamp,
            status_code,
            title,
            meta_description,
            screenshot_path,
            raw_html_path,
            content_hash,
        ),
    )

    page_id = cursor.lastrowid

    # --------------------------------------------------------
    # Save headings
    # --------------------------------------------------------

    if headings:

        for heading in headings:

            if not heading:
                continue

            heading = str(
                heading
            ).strip()

            if not heading:
                continue

            cursor.execute(
                """
                INSERT INTO page_headings (
                    page_id,
                    heading
                )
                VALUES (
                    ?,
                    ?
                )
                """,
                (
                    page_id,
                    heading,
                ),
            )

    # --------------------------------------------------------
    # Save paragraphs
    # --------------------------------------------------------

    if paragraphs:

        for paragraph in paragraphs:

            if not paragraph:
                continue

            paragraph = str(
                paragraph
            ).strip()

            if not paragraph:
                continue

            cursor.execute(
                """
                INSERT INTO page_paragraphs (
                    page_id,
                    paragraph
                )
                VALUES (
                    ?,
                    ?
                )
                """,
                (
                    page_id,
                    paragraph,
                ),
            )

    # --------------------------------------------------------
    # Save links
    # --------------------------------------------------------

    if links:

        for link in links:

            cursor.execute(
                """
                INSERT INTO page_links (
                    page_id,
                    link_text,
                    href
                )
                VALUES (
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    page_id,
                    link.get("text"),
                    link.get("href"),
                ),
            )

    # --------------------------------------------------------
    # Save images
    # --------------------------------------------------------

    if images:

        for image in images:

            cursor.execute(
                """
                INSERT INTO page_images (
                    page_id,
                    src,
                    alt
                )
                VALUES (
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    page_id,
                    image.get("src"),
                    image.get("alt"),
                ),
            )

    # --------------------------------------------------------
    # Commit
    # --------------------------------------------------------

    connection.commit()
    connection.close()

    return page_id


# ============================================================
# GET PAGE
# ============================================================

def get_page(page_id):
    """
    Return one page and its extracted content.
    """

    connection = get_connection()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # Main page
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM pages
        WHERE id = ?
        """,
        (page_id,),
    )

    page = cursor.fetchone()

    if page is None:
        connection.close()
        return None

    # --------------------------------------------------------
    # Headings
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT heading
        FROM page_headings
        WHERE page_id = ?
        ORDER BY id ASC
        """,
        (page_id,),
    )

    headings = [
        row["heading"]
        for row in cursor.fetchall()
    ]

    # --------------------------------------------------------
    # Paragraphs
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT paragraph
        FROM page_paragraphs
        WHERE page_id = ?
        ORDER BY id ASC
        """,
        (page_id,),
    )

    paragraphs = [
        row["paragraph"]
        for row in cursor.fetchall()
    ]

    # --------------------------------------------------------
    # Links
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT link_text, href
        FROM page_links
        WHERE page_id = ?
        ORDER BY id ASC
        """,
        (page_id,),
    )

    links = [
        dict(row)
        for row in cursor.fetchall()
    ]

    # --------------------------------------------------------
    # Images
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT src, alt
        FROM page_images
        WHERE page_id = ?
        ORDER BY id ASC
        """,
        (page_id,),
    )

    images = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    # --------------------------------------------------------
    # Return complete page
    # --------------------------------------------------------

    return {
        "page": dict(page),
        "headings": headings,
        "paragraphs": paragraphs,
        "links": links,
        "images": images,
    }


# ============================================================
# GET ALL PAGES
# ============================================================

def get_all_pages():
    """
    Return all crawled pages.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM pages
        ORDER BY scrape_timestamp DESC
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# GET PAGE HISTORY
# ============================================================

def get_page_history(
    bank,
    page_url,
):
    """
    Return the complete crawl history of one page.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM pages
        WHERE bank = ?
        AND page_url = ?
        ORDER BY scrape_timestamp DESC
        """,
        (
            bank,
            page_url,
        ),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# PRINT ALL PAGES
# ============================================================

def print_all_pages():
    """
    Display all crawled pages.
    """

    pages = get_all_pages()

    print()
    print("==============================")
    print("DATABASE")
    print("==============================")

    for page in pages:

        print()
        print(f"ID: {page['id']}")
        print(f"Bank: {page['bank']}")
        print(f"URL: {page['page_url']}")
        print(f"Final URL: {page['final_url']}")
        print(f"Status: {page['status_code']}")
        print(
            f"Scraped at: "
            f"{page['scrape_timestamp']}"
        )
        print(f"Title: {page['title']}")
        print(
            f"Meta description: "
            f"{page['meta_description']}"
        )
        print(
            f"Screenshot: "
            f"{page['screenshot_path']}"
        )
        print(
            f"Raw HTML: "
            f"{page['raw_html_path']}"
        )
        print(
            f"Content hash: "
            f"{page['content_hash']}"
        )

    print()
    print("==============================")