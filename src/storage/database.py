import sqlite3
from pathlib import Path
from datetime import date


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
    Create all database tables if they do not already exist.
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

            page_type TEXT,

            language TEXT,

            scrape_date DATE NOT NULL,

            headline TEXT,

            subtitle TEXT,

            tone TEXT,

            value_proposition TEXT,

            has_numeric_offer BOOLEAN,

            cta_text TEXT,

            cta_count INTEGER,

            image_count INTEGER,

            raw_text TEXT,

            screenshot_path TEXT,

            source_type TEXT,

            UNIQUE (
                bank,
                page_url,
                scrape_date
            )
        )
        """
    )

    # ========================================================
    # PAGE COLORS
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS page_colors (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            page_id INTEGER NOT NULL,

            color TEXT NOT NULL,

            rank INTEGER NOT NULL,

            FOREIGN KEY (
                page_id
            )
            REFERENCES pages(id)
            ON DELETE CASCADE,

            UNIQUE (
                page_id,
                color
            )
        )
        """
    )

    # ========================================================
    # PAGE TOPICS
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS page_topics (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            page_id INTEGER NOT NULL,

            topic TEXT NOT NULL,

            FOREIGN KEY (
                page_id
            )
            REFERENCES pages(id)
            ON DELETE CASCADE,

            UNIQUE (
                page_id,
                topic
            )
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
    language=None,
    page_type=None,
    headline=None,
    subtitle=None,
    tone=None,
    value_proposition=None,
    has_numeric_offer=None,
    cta_text=None,
    cta_count=0,
    image_count=0,
    dominant_colors=None,
    topics=None,
    raw_text=None,
    screenshot_path=None,
    source_type=None,
    scrape_date=None,
):
    """
    Save a crawled page.

    Colors are stored in page_colors.
    Topics are stored in page_topics.
    """

    init_db()

    if scrape_date is None:
        scrape_date = date.today().isoformat()

    connection = get_connection()

    cursor = connection.cursor()

    # ========================================================
    # SAVE PAGE
    # ========================================================

    cursor.execute(
        """
        INSERT INTO pages (
            bank,
            page_url,
            page_type,
            language,
            scrape_date,
            headline,
            subtitle,
            tone,
            value_proposition,
            has_numeric_offer,
            cta_text,
            cta_count,
            image_count,
            raw_text,
            screenshot_path,
            source_type
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
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        ON CONFLICT (
            bank,
            page_url,
            scrape_date
        )
        DO UPDATE SET
            page_type = excluded.page_type,
            language = excluded.language,
            headline = excluded.headline,
            subtitle = excluded.subtitle,
            tone = excluded.tone,
            value_proposition = excluded.value_proposition,
            has_numeric_offer = excluded.has_numeric_offer,
            cta_text = excluded.cta_text,
            cta_count = excluded.cta_count,
            image_count = excluded.image_count,
            raw_text = excluded.raw_text,
            screenshot_path = excluded.screenshot_path,
            source_type = excluded.source_type
        """,
        (
            bank,
            page_url,
            page_type,
            language,
            scrape_date,
            headline,
            subtitle,
            tone,
            value_proposition,
            has_numeric_offer,
            cta_text,
            cta_count,
            image_count,
            raw_text,
            screenshot_path,
            source_type,
        ),
    )

    # ========================================================
    # GET PAGE ID
    # ========================================================

    cursor.execute(
        """
        SELECT id
        FROM pages
        WHERE bank = ?
        AND page_url = ?
        AND scrape_date = ?
        """,
        (
            bank,
            page_url,
            scrape_date,
        ),
    )

    row = cursor.fetchone()

    if row is None:
        connection.close()
        raise RuntimeError(
            "Could not retrieve page_id after saving page."
        )

    page_id = row["id"]

    # ========================================================
    # SAVE COLORS
    # ========================================================

    cursor.execute(
        """
        DELETE FROM page_colors
        WHERE page_id = ?
        """,
        (page_id,),
    )

    if dominant_colors:

        for rank, color in enumerate(
            dominant_colors,
            start=1,
        ):

            if not color:
                continue

            cursor.execute(
                """
                INSERT INTO page_colors (
                    page_id,
                    color,
                    rank
                )
                VALUES (
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    page_id,
                    color,
                    rank,
                ),
            )

    # ========================================================
    # SAVE TOPICS
    # ========================================================

    cursor.execute(
        """
        DELETE FROM page_topics
        WHERE page_id = ?
        """,
        (page_id,),
    )

    if topics:

        for topic in topics:

            if not topic:
                continue

            topic = str(topic).strip()

            if not topic:
                continue

            cursor.execute(
                """
                INSERT OR IGNORE INTO page_topics (
                    page_id,
                    topic
                )
                VALUES (
                    ?,
                    ?
                )
                """,
                (
                    page_id,
                    topic,
                ),
            )

    # ========================================================
    # COMMIT
    # ========================================================

    connection.commit()

    connection.close()

    return page_id


# ============================================================
# GET PAGE
# ============================================================

def get_page(page_id):
    """
    Return one page with its colors and topics.
    """

    connection = get_connection()

    cursor = connection.cursor()

    # ========================================================
    # PAGE
    # ========================================================

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

    # ========================================================
    # COLORS
    # ========================================================

    cursor.execute(
        """
        SELECT color, rank
        FROM page_colors
        WHERE page_id = ?
        ORDER BY rank ASC
        """,
        (page_id,),
    )

    colors = cursor.fetchall()

    # ========================================================
    # TOPICS
    # ========================================================

    cursor.execute(
        """
        SELECT topic
        FROM page_topics
        WHERE page_id = ?
        ORDER BY topic ASC
        """,
        (page_id,),
    )

    topics = cursor.fetchall()

    connection.close()

    return {
        "page": dict(page),
        "colors": [
            dict(color)
            for color in colors
        ],
        "topics": [
            topic["topic"]
            for topic in topics
        ],
    }


# ============================================================
# GET PAGE HISTORY
# ============================================================

def get_page_history(
    bank,
    page_url,
):
    """
    Return the complete scraping history of a page.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM pages
        WHERE bank = ?
        AND page_url = ?
        ORDER BY scrape_date DESC
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
        ORDER BY scrape_date DESC
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# GET PAGE COLORS
# ============================================================

def get_page_colors(page_id):
    """
    Return all dominant colors for a page.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT color, rank
        FROM page_colors
        WHERE page_id = ?
        ORDER BY rank ASC
        """,
        (page_id,),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# GET PAGE TOPICS
# ============================================================

def get_page_topics(page_id):
    """
    Return all topics for a page.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT topic
        FROM page_topics
        WHERE page_id = ?
        ORDER BY topic ASC
        """,
        (page_id,),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        row["topic"]
        for row in rows
    ]


# ============================================================
# GET PAGES BY TOPIC
# ============================================================

def get_pages_by_topic(topic):
    """
    Return all pages associated with a topic.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT pages.*
        FROM pages
        INNER JOIN page_topics
            ON page_topics.page_id = pages.id
        WHERE page_topics.topic = ?
        ORDER BY pages.scrape_date DESC
        """,
        (topic,),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# PRINT DATABASE
# ============================================================

def print_all_pages():
    """
    Display pages, colors and topics.
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
        print(f"Page type: {page['page_type']}")
        print(f"Language: {page['language']}")
        print(f"Scrape date: {page['scrape_date']}")
        print(f"Headline: {page['headline']}")
        print(f"Subtitle: {page['subtitle']}")
        print(f"Tone: {page['tone']}")
        print(
            f"Value proposition: "
            f"{page['value_proposition']}"
        )
        print(
            f"Numeric offer: "
            f"{page['has_numeric_offer']}"
        )
        print(f"CTA: {page['cta_text']}")
        print(f"CTA count: {page['cta_count']}")
        print(f"Image count: {page['image_count']}")
        print(
            f"Screenshot: "
            f"{page['screenshot_path']}"
        )
        print(
            f"Source type: "
            f"{page['source_type']}"
        )

        # ----------------------------------------------------
        # COLORS
        # ----------------------------------------------------

        colors = get_page_colors(
            page["id"]
        )

        print("Colors:")

        for color in colors:

            print(
                f"  {color['rank']}. "
                f"{color['color']}"
            )

        # ----------------------------------------------------
        # TOPICS
        # ----------------------------------------------------

        topics = get_page_topics(
            page["id"]
        )

        print("Topics:")

        for topic in topics:

            print(
                f"  - {topic}"
            )

    print()
    print("==============================")