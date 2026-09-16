
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime


URL = (
    "https://www.belfius.be/site/retail/fr/"
    "produits/paiement/"
    "compte-bancaire-pour-jeunes"
)


# --------------------------------------------------
# Téléchargement et nettoyage
# --------------------------------------------------

def get_soup(url):
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def clean_text(soup):
    for tag in soup(
        ["script", "style", "noscript", "svg"]
    ):
        tag.decompose()

    elements = soup.find_all([
        "h1", "h2", "h3", "h4", "p", "li"
    ])

    return [
        element.get_text(" ", strip=True)
        for element in elements
        if element.get_text(" ", strip=True)
    ]


def normalize(text):
    """Uniformise les espaces et les caractères."""
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------
# Produit
# --------------------------------------------------

def extract_product_name(soup, texts):
    # Recherche dans les titres
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = normalize(tag.get_text(" ", strip=True))

        if re.search(r"beats\s+new", text, re.I):
            return "Beats New"

    # Recherche dans l'ensemble du texte
    full_text = " ".join(texts)

    if re.search(r"\bbeats\s+new\b", full_text, re.I):
        return "Beats New"

    return None


def extract_age(texts):
    """
    Extrait l'âge associé à la gratuité,
    sans utiliser les âges de la promotion.
    """

    for text in texts:
        text_lower = text.lower()

        if "gratuit" not in text_lower:
            continue

        match = re.search(
            r"moins de\s+(\d{1,2})\s+ans",
            text_lower
        )

        if match:
            return {
                "min": None,
                "max": int(match.group(1)),
                "max_inclusive": False
            }

    return {
        "min": None,
        "max": 25,
        "max_inclusive": False
    }


def extract_free(texts):
    full_text = " ".join(texts).lower()

    if re.search(
        r"gratuit|sans frais|gratuité",
        full_text
    ):
        return True

    return None


# --------------------------------------------------
# Promotion
# --------------------------------------------------

MONTHS = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12
}


def extract_dates(text):
    """
    Retourne les dates trouvées au format ISO.
    Reconnaît notamment :
    18 mai 2026 et 30 septembre 2026.
    """

    pattern = (
        r"\b(\d{1,2})\s+"
        r"(janvier|février|fevrier|mars|avril|mai|juin|"
        r"juillet|août|aout|septembre|octobre|"
        r"novembre|décembre|decembre)\s+"
        r"(\d{4})\b"
    )

    dates = []

    for day, month, year in re.findall(
        pattern, text, re.IGNORECASE
    ):
        month_num = MONTHS.get(month.lower())

        if not month_num:
            continue

        try:
            date_obj = datetime(
                int(year),
                month_num,
                int(day)
            )
            dates.append(date_obj.date().isoformat())
        except ValueError:
            continue

    # Supprime les doublons et trie chronologiquement
    return sorted(set(dates))


def extract_amount(text):
    """
    Reconnaît 50 €, 50 euros, 50,00 €.
    """

    match = re.search(
        r"(\d+(?:[.,]\d{1,2})?)\s*"
        r"(?:€|euros?)",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    amount = float(
        match.group(1).replace(",", ".")
    )

    return int(amount) if amount.is_integer() else amount


def extract_promo_ages(text):
    """
    Extrait la tranche d'âge de la promotion.
    """

    patterns = [
        r"de\s+(\d{1,2})\s+à\s+"
        r"(\d{1,2})\s+ans",

        r"entre\s+(\d{1,2})\s+et\s+"
        r"(\d{1,2})\s+ans"
    ]

    for pattern in patterns:
        match = re.search(
            pattern, text, re.IGNORECASE
        )

        if match:
            return (
                int(match.group(1)),
                int(match.group(2))
            )

    return None, None


def extract_conditions(text):
    conditions = []

    if re.search(
        r"ouverture.{0,100}compte|"
        r"compte.{0,100}ouverture",
        text,
        re.IGNORECASE
    ):
        conditions.append(
            "Une partie de la prime est versée "
            "à l'ouverture du compte"
        )

    if re.search(
        r"premier\s+(?:paiement|achat)|"
        r"première\s+(?:transaction|opération)",
        text,
        re.IGNORECASE
    ):
        conditions.append(
            "Une partie de la prime est versée "
            "lors d'un premier paiement ou achat"
        )

    return conditions


def extract_promotion(texts):
    """
    Recherche les passages liés à la campagne.
    """

    promo_texts = [
        text for text in texts
        if re.search(
            r"promotion|campagne|prime|"
            r"recevez|argent de poche|"
            r"offert|offerte|offerts|offertes",
            text,
            re.IGNORECASE
        )
    ]

    if not promo_texts:
        return {"exists": False}

    text = " ".join(promo_texts)

    amount = extract_amount(text)
    dates = extract_dates(text)
    age_min, age_max = extract_promo_ages(text)
    conditions = extract_conditions(text)

    # Les dates sont triées : la plus ancienne
    # est le début, la suivante est la fin.
    valid_from = dates[0] if len(dates) >= 1 else None
    valid_until = dates[1] if len(dates) >= 2 else None

    return {
        "exists": True,
        "type": "Prime de bienvenue",
        "amount_eur": amount,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "eligible_age_min": age_min,
        "eligible_age_max": age_max,
        "conditions": conditions
    }


# --------------------------------------------------
# Avantages
# --------------------------------------------------

def extract_benefits(texts):
    full_text = " ".join(texts).lower()

    benefits = []

    rules = [
        (
            r"solde.{0,100}(opération|transaction)"
            r".{0,100}(historique|historique)",
            "Consultation du solde, des opérations "
            "et de l'historique"
        ),
        (
            r"ne peut pas.{0,50}(négatif|negatif)|"
            r"pas de découvert|"
            r"aucun découvert",
            "Pas de découvert autorisé"
        ),
        (
            r"limites? de carte|"
            r"plafond.{0,50}carte",
            "Limites de carte adaptables"
        ),
        (
            r"100\s*(?:€|euros?)\s*"
            r"(?:par|/)\s*semaine",
            "Plafond de carte mentionné : "
            "100 € par semaine"
        ),
        (
            r"notifications?.{0,100}(parent|parents)|"
            r"(parent|parents).{0,100}notifications?",
            "Choix des notifications reçues "
            "par le parent"
        ),
        (
            r"application belfius|app belfius",
            "Suivi des finances via l'application Belfius"
        ),
        (
            r"gérer son argent|"
            r"gestion de l'argent|"
            r"apprendre.{0,50}argent",
            "Accompagnement dans la gestion de l'argent"
        )
    ]

    for pattern, benefit in rules:
        if re.search(pattern, full_text):
            benefits.append(benefit)

    # Évite les doublons
    return list(dict.fromkeys(benefits))


# --------------------------------------------------
# Fonction principale
# --------------------------------------------------

def extract_product(url):
    soup = get_soup(url)
    texts = clean_text(soup)

    name = extract_product_name(soup, texts)
    age = extract_age(texts)
    free = extract_free(texts)

    promotion = extract_promotion(texts)
    benefits = extract_benefits(texts)

    # Le découvert est extrait directement
    # de la liste des avantages.
    overdraft_allowed = (
        False
        if "Pas de découvert autorisé" in benefits
        else None
    )

    return {
        "bank": "Belfius",
        "product": {
            "name": name,
            "type": "Compte de paiement pour jeunes",
            "eligibility": age,
            "pricing": {
                "free": free,
                "details": (
                    "Gratuit pour les jeunes "
                    "de moins de 25 ans"
                    if free
                    else None
                )
            },
            "overdraft": {
                "allowed": overdraft_allowed
            },
            "benefits": benefits
        },
        "promotion": promotion
    }


# --------------------------------------------------
# Exécution et export JSON
# --------------------------------------------------

if __name__ == "__main__":
    try:
        result = extract_product(URL)

        print(json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ))

        with open(
            "belfius_beats_new.json",
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                result,
                file,
                ensure_ascii=False,
                indent=2
            )

        print("\nFichier JSON créé.")

    except requests.RequestException as error:
        print(
            "Erreur lors du téléchargement :",
            error
        )