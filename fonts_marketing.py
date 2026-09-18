from playwright.sync_api import sync_playwright
import sqlite3


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

URL = "https://www.belfius.be/site/retail/fr/produits/paiement/compte-bancaire-pour-jeunes"
DB_NAME = "marketing_spy.db"


# ------------------------------------------------------------
# EXTRACTION DES ÉLÉMENTS VISUELS IMPORTANTS
# ------------------------------------------------------------

def extract_visual_elements(page):

    selectors = "h1, h2, h3, h4, h5, h6, p, button, a"

    return page.locator(selectors).evaluate_all("""
        elements => elements
            .map(element => {

                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();

                return {
                    tag: element.tagName.toLowerCase(),

                    text: element.innerText
                        .replace(/\\s+/g, ' ')
                        .trim(),

                    font_family: style.fontFamily,
                    font_size_px: parseFloat(style.fontSize),
                    font_weight: style.fontWeight,

                    color: style.color,
                    background_color: style.backgroundColor,

                    x_position: Math.round(rect.x),
                    y_position: Math.round(rect.y),

                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                };
            })

            // On garde uniquement les éléments
            // qui contiennent du texte
            .filter(element => element.text.length > 0)
    """)


# ------------------------------------------------------------
# CREATION DE LA BASE SQL
# ------------------------------------------------------------

def create_database():

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS page_elements (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            page_url TEXT NOT NULL,

            tag TEXT,

            text TEXT,

            font_family TEXT,

            font_size_px REAL,

            font_weight TEXT,

            color TEXT,

            background_color TEXT,

            x_position REAL,

            y_position REAL,

            width REAL,

            height REAL
        )
    """)

    connection.commit()

    return connection


# ------------------------------------------------------------
# INSERTION DES DONNÉES
# ------------------------------------------------------------

def save_to_database(connection, page_url, elements):

    cursor = connection.cursor()

    for element in elements:

        cursor.execute("""
            INSERT INTO page_elements (
                page_url,
                tag,
                text,
                font_family,
                font_size_px,
                font_weight,
                color,
                background_color,
                x_position,
                y_position,
                width,
                height
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            page_url,
            element["tag"],
            element["text"],
            element["font_family"],
            element["font_size_px"],
            element["font_weight"],
            element["color"],
            element["background_color"],
            element["x_position"],
            element["y_position"],
            element["width"],
            element["height"]
        ))

    connection.commit()


# ------------------------------------------------------------
# SCRAPING
# ------------------------------------------------------------

def scrape_page(url):

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1920,
                "height": 1080
            }
        )

        page.goto(
            url,
            wait_until="networkidle"
        )

        elements = extract_visual_elements(page)

        browser.close()

    return elements


# ------------------------------------------------------------
# PROGRAMME PRINCIPAL
# ------------------------------------------------------------

if __name__ == "__main__":

    connection = create_database()

    elements = scrape_page(URL)

    save_to_database(
        connection,
        URL,
        elements
    )

    connection.close()

    print(
        f"{len(elements)} éléments enregistrés dans la base de données."
    )
