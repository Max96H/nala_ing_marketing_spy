import re
import sqlite3
from playwright.sync_api import sync_playwright
from collections import Counter
from PIL import Image

def extract_dominant_colors(
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

def save_colors_to_sqlite(page_url, color_list, db_path="./data/bank_analysis.db"):
    """Inserts extracted colors into the page_colors junction table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Fetch the corresponding page_id from the pages table
    cursor.execute("SELECT id FROM pages WHERE page_url = ?", (page_url,))
    row = cursor.fetchone()

    if not row:
        print(
            f"Error: Page URL '{page_url}' not found in 'pages' table. Please run main scraper first."
        )
        conn.close()
        return

    page_id = row[0]

    # 2. Prepare batch tuples (page_id, color_hex)
    color_records = [(page_id, color) for color in color_list]

    # 3. Bulk insert using INSERT OR IGNORE to prevent duplicate primary key errors
    cursor.executemany(
        """
        INSERT OR IGNORE INTO page_colors (page_id, color_hex)
        VALUES (?, ?);
    """,
        color_records,
    )

    conn.commit()
    conn.close()
    print(
        f"Successfully inserted {len(color_records)} colors for page ID {page_id} into 'page_colors'."
    )