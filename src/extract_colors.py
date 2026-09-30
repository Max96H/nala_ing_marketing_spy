import re
import sqlite3
from playwright.sync_api import sync_playwright
from collections import Counter
from PIL import Image
import io

def extract_dominant_colors(
        screenshot,
        color_count: int = 5,
    ) -> list[str]:
        """
        Extract dominant colors from the screenshot.

        Returns hexadecimal values such as:
            ['#ffffff', '#ff6200', '#000000']
        """

        # No screenshot means no color analysis is possible.
        if not screenshot:
            return []

        try:

            # Open the screenshot using Pillow.
            with Image.open(io.BytesIO(screenshot)) as img:
                # 1. Handle transparency: paste onto a white background
                if img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
                ):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(
                        img, mask=img.convert("RGBA").split()[3]
                    )  # 3 is the alpha channel
                    image = background
                else:
                    image = img.convert("RGB")

                # 2. Downscale image for speed (800x800 is plenty of detail)
                image.thumbnail((800, 800))

                # 3. Quantize to 32 colors
                quantized = image.quantize(colors=32).convert("RGB")

                # 4. Use getcolors() instead of list(getdata()) for speed & memory safety
                # maxcolors must be >= the total pixels in thumbnail
                width, height = quantized.size
                color_counts = quantized.getcolors(maxcolors=width * height)

                if not color_counts:
                    return []

                # 5. Sort by frequency (highest count first)
                sorted_colors = sorted(color_counts, key=lambda x: x[0], reverse=True)

                # 6. Convert top N RGB tuples to Hex format
                dominant_colors = []
                for count, rgb in sorted_colors[:color_count]:
                    hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                    dominant_colors.append(hex_color)

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