import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# ============================================================
# CONFIGURATION
# ============================================================

URL = (
    "https://www.belfius.be/site/retail/fr/produits/"
    "paiement/compte-bancaire-pour-jeunes"
)

OUTPUT_FILE = "belfius_beats_new.json"

# Nombre maximum d'éléments visuels détaillés à conserver
# dans le JSON.
MAX_VISUAL_ELEMENTS = 500


# ============================================================
# OUTILS GÉNÉRAUX
# ============================================================

def clean_text(text):
    """
    Nettoie un texte :
    - supprime les espaces multiples
    - supprime les retours à la ligne inutiles
    """
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def normalize_color(color):
    """
    Normalise une couleur CSS.

    Exemples :
        rgb(0, 0, 0) -> rgb(0, 0, 0)
        rgba(0, 0, 0, 0) -> rgba(0, 0, 0, 0)

    On conserve volontairement le format retourné
    par le navigateur.
    """
    if not color:
        return ""

    return color.strip().lower()


def remove_empty_values(value):
    """
    Supprime récursivement :
        - None
        - ""
        - []
        - {}

    Objectif :
        ne JAMAIS avoir de valeur null dans le JSON.
    """

    if isinstance(value, dict):

        result = {}

        for key, item in value.items():

            cleaned = remove_empty_values(item)

            if cleaned is None:
                continue

            if cleaned == "":
                continue

            if cleaned == []:
                continue

            if cleaned == {}:
                continue

            result[key] = cleaned

        return result

    if isinstance(value, list):

        result = []

        for item in value:

            cleaned = remove_empty_values(item)

            if cleaned is None:
                continue

            if cleaned == "":
                continue

            result.append(cleaned)

        return result

    return value


def add_unique(items, value):
    """
    Ajoute une valeur à une liste si elle n'existe pas déjà.
    """

    if value and value not in items:
        items.append(value)


# ============================================================
# EXTRACTION DU TEXTE
# ============================================================

def get_page_text(page):
    """
    Récupère le texte visible de la page.
    """

    try:
        return clean_text(
            page.locator("body").inner_text()
        )

    except Exception:
        return ""


# ============================================================
# EXTRACTION DES INFORMATIONS PRODUIT
# ============================================================

def extract_product(page):

    text = get_page_text(page)

    product = {}

    # --------------------------------------------------------
    # NOM
    # --------------------------------------------------------

    if re.search(r"\bBeats New\b", text, re.IGNORECASE):
        product["name"] = "Beats New"

    # --------------------------------------------------------
    # TYPE
    # --------------------------------------------------------

    if re.search(
        r"Compte de paiement pour jeunes",
        text,
        re.IGNORECASE
    ):
        product["type"] = "Compte de paiement pour jeunes"

    # --------------------------------------------------------
    # ÉLIGIBILITÉ
    # --------------------------------------------------------

    eligibility = {}

    match = re.search(
        r"moins de\s+(\d+)\s*ans",
        text,
        re.IGNORECASE
    )

    if match:

        max_age = int(match.group(1))

        eligibility["max"] = max_age
        eligibility["max_inclusive"] = False

    if eligibility:
        product["eligibility"] = eligibility

    # --------------------------------------------------------
    # PRIX
    # --------------------------------------------------------

    pricing = {}

    if re.search(
        r"Beats New gratuit",
        text,
        re.IGNORECASE
    ):

        pricing["free"] = True

    if re.search(
        r"Gratuit pour les jeunes de moins de 25 ans",
        text,
        re.IGNORECASE
    ):

        pricing["details"] = (
            "Gratuit pour les jeunes de moins de 25 ans"
        )

    if pricing:
        product["pricing"] = pricing

    # --------------------------------------------------------
    # DÉCOUVERT
    # --------------------------------------------------------

    overdraft = {}

    if re.search(
        r"aucun risque de découvert",
        text,
        re.IGNORECASE
    ) or re.search(
        r"ne peut pas descendre en négatif",
        text,
        re.IGNORECASE
    ):

        overdraft["allowed"] = False

    if overdraft:
        product["overdraft"] = overdraft

    # --------------------------------------------------------
    # AVANTAGES
    # --------------------------------------------------------

    benefits = []

    benefit_rules = [

        (
            r"solde.*opérations.*historique",
            "Consultation du solde, des opérations et de l’historique"
        ),

        (
            r"aucun risque de découvert|ne peut pas descendre en négatif",
            "Pas de découvert autorisé"
        ),

        (
            r"limites de carte sécurisées",
            "Limites de carte adaptables"
        ),

        (
            r"100 euros par semaine",
            "Plafond de carte : 100 € par semaine"
        ),

        (
            r"œil sur ses finances via l’app Belfius",
            "Suivi des finances via l’application Belfius"
        ),

        (
            r"gérer son argent en toute sécurité",
            "Gestion de l'argent en toute sécurité"
        ),

        (
            r"Rembour.*?amis.*?Wero",
            "Remboursement des amis via Wero"
        ),

        (
            r"Apple Pay.*?Google Pay",
            "Paiement avec Apple Pay et Google Pay à partir de 13 ans"
        ),

        (
            r"tickets De Lijn",
            "Achat de tickets De Lijn via l'application Belfius"
        ),

        (
            r"itsme",
            "Activation du compte itsme via Belfius"
        ),

        (
            r"Hey Belfius",
            "Assistance via Hey Belfius"
        ),

        (
            r"mode sombre",
            "Personnalisation de l'application"
        ),

        (
            r"Personnaliser sa carte",
            "Personnalisation de la carte de paiement"
        ),

        (
            r"retirer gratuitement.*?euro",
            "Retrait gratuit d'euros dans la zone euro"
        )
    ]

    for pattern, benefit in benefit_rules:

        if re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL
        ):

            add_unique(
                benefits,
                benefit
            )

    if benefits:
        product["benefits"] = benefits

    return product


# ============================================================
# EXTRACTION DE LA PROMOTION
# ============================================================

def extract_promotion(page):

    text = get_page_text(page)

    promotion = {}

    # --------------------------------------------------------
    # EXISTENCE
    # --------------------------------------------------------

    has_promotion = bool(
        re.search(
            r"50\s*(?:€|euros).*argent de poche",
            text,
            re.IGNORECASE
        )
    )

    promotion["exists"] = has_promotion

    if not has_promotion:
        return promotion

    # --------------------------------------------------------
    # TYPE
    # --------------------------------------------------------

    promotion["type"] = "Prime de bienvenue"

    # --------------------------------------------------------
    # MONTANT
    # --------------------------------------------------------

    promotion["amount_eur"] = 50

    # --------------------------------------------------------
    # DATES
    # --------------------------------------------------------

    date_match = re.search(
        r"(\d{1,2})\s+mai\s+au\s+"
        r"(\d{1,2})\s+septembre\s+(\d{4})",
        text,
        re.IGNORECASE
    )

    if date_match:

        start_day = int(date_match.group(1))
        end_day = int(date_match.group(2))
        year = int(date_match.group(3))

        promotion["valid_from"] = (
            f"{year}-05-{start_day:02d}"
        )

        promotion["valid_until"] = (
            f"{year}-09-{end_day:02d}"
        )

    # --------------------------------------------------------
    # ÂGES
    # --------------------------------------------------------

    age_match = re.search(
        r"de\s+(\d+)\s+à\s+(\d+)\s+ans",
        text,
        re.IGNORECASE
    )

    if age_match:

        promotion["eligible_age_min"] = int(
            age_match.group(1)
        )

        promotion["eligible_age_max"] = int(
            age_match.group(2)
        )

    # --------------------------------------------------------
    # CONDITIONS
    # --------------------------------------------------------

    conditions = []

    if re.search(
        r"25\s+euros.*?ouverture",
        text,
        re.IGNORECASE | re.DOTALL
    ):

        conditions.append(
            "25 € sont versés à l'ouverture du compte Beats New"
        )

    if re.search(
        r"25\s+euros.*?premier paiement ou achat",
        text,
        re.IGNORECASE | re.DOTALL
    ):

        conditions.append(
            "25 € sont versés lors d'un premier paiement ou achat"
        )

    if conditions:
        promotion["conditions"] = conditions

    return promotion


# ============================================================
# EXTRACTION D'UN STYLE CSS RÉELLEMENT RENDU
# ============================================================

def get_computed_style(element):
    """
    Récupère les styles réellement calculés par le navigateur.

    C'est différent de simplement lire l'attribut "style".
    """

    return element.evaluate("""
        element => {

            const style = window.getComputedStyle(element);

            return {

                font_family: style.fontFamily,

                font_size_px:
                    parseFloat(style.fontSize) || 0,

                font_weight:
                    style.fontWeight,

                font_style:
                    style.fontStyle,

                line_height:
                    style.lineHeight,

                color:
                    style.color,

                background_color:
                    style.backgroundColor,

                border_top_color:
                    style.borderTopColor,

                border_right_color:
                    style.borderRightColor,

                border_bottom_color:
                    style.borderBottomColor,

                border_left_color:
                    style.borderLeftColor,

                border_top_width_px:
                    parseFloat(style.borderTopWidth) || 0,

                border_right_width_px:
                    parseFloat(style.borderRightWidth) || 0,

                border_bottom_width_px:
                    parseFloat(style.borderBottomWidth) || 0,

                border_left_width_px:
                    parseFloat(style.borderLeftWidth) || 0,

                border_radius_px:
                    parseFloat(style.borderRadius) || 0,

                letter_spacing:
                    style.letterSpacing,

                word_spacing:
                    style.wordSpacing,

                text_align:
                    style.textAlign,

                text_transform:
                    style.textTransform,

                text_decoration:
                    style.textDecoration,

                opacity:
                    style.opacity,

                display:
                    style.display,

                position:
                    style.position,

                width_px:
                    parseFloat(style.width) || 0,

                height_px:
                    parseFloat(style.height) || 0,

                margin_top_px:
                    parseFloat(style.marginTop) || 0,

                margin_right_px:
                    parseFloat(style.marginRight) || 0,

                margin_bottom_px:
                    parseFloat(style.marginBottom) || 0,

                margin_left_px:
                    parseFloat(style.marginLeft) || 0,

                padding_top_px:
                    parseFloat(style.paddingTop) || 0,

                padding_right_px:
                    parseFloat(style.paddingRight) || 0,

                padding_bottom_px:
                    parseFloat(style.paddingBottom) || 0,

                padding_left_px:
                    parseFloat(style.paddingLeft) || 0
            };
        }
    """)


# ============================================================
# EXTRACTION DES ÉLÉMENTS VISUELS
# ============================================================

def extract_visual_elements(page):
    """
    Extrait les principaux éléments contenant du texte
    et leurs styles calculés.
    """

    selectors = [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "li",
        "a",
        "button",
        "label",
        "span"
    ]

    elements_data = []

    for selector in selectors:

        locator = page.locator(selector)

        try:
            count = locator.count()

        except Exception:
            continue

        for index in range(count):

            if len(elements_data) >= MAX_VISUAL_ELEMENTS:
                return elements_data

            element = locator.nth(index)

            try:

                text = clean_text(
                    element.inner_text()
                )

                if not text:
                    continue

                style = get_computed_style(element)

                # Classes CSS
                classes = element.get_attribute("class")

                # ID
                element_id = element.get_attribute("id")

                # Tag HTML
                tag_name = selector

                item = {
                    "tag": tag_name,
                    "text": text,
                    "style": style
                }

                if classes:
                    item["classes"] = classes

                if element_id:
                    item["id"] = element_id

                elements_data.append(item)

            except Exception:
                continue

    return elements_data


# ============================================================
# EXTRACTION DES COULEURS
# ============================================================

def extract_colors(page):
    """
    Construit une liste des couleurs réellement utilisées
    par les éléments visibles de la page.
    """

    text_colors = Counter()
    background_colors = Counter()
    border_colors = Counter()

    locator = page.locator(
        "body *"
    )

    try:
        count = locator.count()

    except Exception:
        return {}

    for index in range(count):

        try:

            element = locator.nth(index)

            style = get_computed_style(
                element
            )

            text = clean_text(
                element.inner_text()
            )

            # Couleur du texte :
            # on s'intéresse surtout aux éléments
            # qui contiennent effectivement du texte.
            if text:

                color = normalize_color(
                    style.get("color")
                )

                if color:
                    text_colors[color] += 1

            # Background
            background = normalize_color(
                style.get("background_color")
            )

            if background and background != "rgba(0, 0, 0, 0)":
                background_colors[background] += 1

            # Bordures
            border_values = [
                style.get("border_top_color"),
                style.get("border_right_color"),
                style.get("border_bottom_color"),
                style.get("border_left_color")
            ]

            for border in border_values:

                border = normalize_color(border)

                if border:
                    border_colors[border] += 1

        except Exception:
            continue

    return {
        "text": [
            {
                "value": color,
                "usage_count": count
            }
            for color, count in text_colors.most_common()
        ],

        "background": [
            {
                "value": color,
                "usage_count": count
            }
            for color, count in background_colors.most_common()
        ],

        "border": [
            {
                "value": color,
                "usage_count": count
            }
            for color, count in border_colors.most_common()
        ]
    }


# ============================================================
# EXTRACTION DES POLICES
# ============================================================

def extract_fonts(page):
    """
    Regroupe les polices utilisées sur la page.

    On obtient par exemple :

        {
            "family": "...",
            "size_px": 16,
            "weight": "400",
            "style": "normal"
        }
    """

    fonts = Counter()

    locator = page.locator(
        "body *"
    )

    try:
        count = locator.count()

    except Exception:
        return []

    for index in range(count):

        try:

            element = locator.nth(index)

            text = clean_text(
                element.inner_text()
            )

            if not text:
                continue

            style = get_computed_style(
                element
            )

            key = (
                style.get("font_family"),
                style.get("font_size_px"),
                style.get("font_weight"),
                style.get("font_style"),
                style.get("line_height")
            )

            fonts[key] += 1

        except Exception:
            continue

    result = []

    for key, usage_count in fonts.most_common():

        family, size, weight, font_style, line_height = key

        result.append({

            "family": family,

            "size_px": size,

            "weight": weight,

            "style": font_style,

            "line_height": line_height,

            "usage_count": usage_count
        })

    return result


# ============================================================
# EXTRACTION DES VARIABLES CSS
# ============================================================

def extract_css_variables(page):
    """
    Récupère les variables CSS définies sur :root.

    Exemple :

        --primary-color: #123456;
        --font-size: 16px;
    """

    return page.evaluate("""
        () => {

            const root =
                getComputedStyle(document.documentElement);

            const variables = {};

            for (let i = 0; i < document.styleSheets.length; i++) {

                try {

                    const rules =
                        document.styleSheets[i].cssRules;

                    for (const rule of rules) {

                        if (!rule.style) {
                            continue;
                        }

                        for (let j = 0;
                             j < rule.style.length;
                             j++) {

                            const property =
                                rule.style[j];

                            if (
                                property.startsWith("--")
                            ) {

                                const value =
                                    rule.style
                                        .getPropertyValue(property)
                                        .trim();

                                if (value) {
                                    variables[property] = value;
                                }
                            }
                        }
                    }

                } catch (e) {
                    // Certaines feuilles externes
                    // peuvent être inaccessibles.
                }
            }

            // Variables calculées sur :root
            for (let i = 0;
                 i < root.length;
                 i++) {

                const property = root[i];

                if (
                    property.startsWith("--")
                ) {

                    const value =
                        root.getPropertyValue(property)
                            .trim();

                    if (value) {
                        variables[property] = value;
                    }
                }
            }

            return variables;
        }
    """)


# ============================================================
# EXTRACTION DES FEUILLES CSS
# ============================================================

def extract_stylesheets(page):
    """
    Récupère les URLs des feuilles CSS chargées.
    """

    return page.evaluate("""
        () => {

            return Array.from(
                document.querySelectorAll(
                    'link[rel="stylesheet"]'
                )
            )
            .map(link => link.href)
            .filter(Boolean);
        }
    """)


# ============================================================
# EXTRACTION DE LA STRUCTURE HTML
# ============================================================

def extract_html_structure(page):
    """
    Extrait une structure simplifiée du contenu.
    """

    html = page.content()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    body = soup.body

    if not body:
        return []

    result = []

    for element in body.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "li"
        ]
    ):

        text = clean_text(
            element.get_text(
                " ",
                strip=True
            )
        )

        if not text:
            continue

        item = {
            "tag": element.name,
            "text": text
        }

        classes = element.get("class")

        if classes:
            item["classes"] = classes

        element_id = element.get("id")

        if element_id:
            item["id"] = element_id

        result.append(item)

    return result


# ============================================================
# EXTRACTION DES MÉTADONNÉES
# ============================================================

def extract_metadata(page):

    metadata = {}

    title = page.title()

    if title:
        metadata["title"] = title

    description = page.locator(
        'meta[name="description"]'
    )

    try:

        if description.count() > 0:

            content = description.first.get_attribute(
                "content"
            )

            if content:
                metadata["description"] = clean_text(
                    content
                )

    except Exception:
        pass

    canonical = page.locator(
        'link[rel="canonical"]'
    )

    try:

        if canonical.count() > 0:

            href = canonical.first.get_attribute(
                "href"
            )

            if href:
                metadata["canonical"] = href

    except Exception:
        pass

    return metadata


# ============================================================
# SCRAPER PRINCIPAL
# ============================================================

def scrape():

    with sync_playwright() as playwright:

        # ----------------------------------------------------
        # Lancement du navigateur
        # ----------------------------------------------------

        browser = playwright.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            viewport={
                "width": 1440,
                "height": 1000
            },

            device_scale_factor=1
        )

        page = context.new_page()

        # ----------------------------------------------------
        # Chargement
        # ----------------------------------------------------

        page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        # Laisse le JavaScript et les composants
        # dynamiques terminer leur rendu.
        page.wait_for_timeout(3000)

        # ----------------------------------------------------
        # Extraction
        # ----------------------------------------------------

        result = {

            "source": {
                "url": page.url
            },

            "metadata":
                extract_metadata(page),

            "bank":
                "Belfius",

            "product":
                extract_product(page),

            "promotion":
                extract_promotion(page),

            "visual": {

                "colors":
                    extract_colors(page),

                "fonts":
                    extract_fonts(page),

                "css_variables":
                    extract_css_variables(page),

                "stylesheets":
                    extract_stylesheets(page),

                "elements":
                    extract_visual_elements(page)
            },

            "html_structure":
                extract_html_structure(page)
        }

        # ----------------------------------------------------
        # Fermeture
        # ----------------------------------------------------

        browser.close()

    # --------------------------------------------------------
    # Suppression de TOUS les null / valeurs vides
    # --------------------------------------------------------

    result = remove_empty_values(
        result
    )

    # --------------------------------------------------------
    # Sauvegarde JSON
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    return result


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

if __name__ == "__main__":

    try:

        data = scrape()

        print(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            )
        )

        print(
            "\n----------------------------------------"
        )

        print(
            f"JSON sauvegardé dans : {OUTPUT_FILE}"
        )

    except Exception as error:

        print(
            "\nERREUR :"
        )

        print(error)