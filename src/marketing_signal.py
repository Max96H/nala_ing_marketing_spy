
import re


def extract_marketing_signals(raw_text):
    """
    Extract marketing signals from already scraped page text.

    This function is bank-independent and can be used
    for ING, KBC, Belfius, BNP Paribas Fortis and Revolut.
    """

    text = raw_text or ""

    patterns = {

        # -----------------------------------------------------
        # MONEY
        # -----------------------------------------------------

        "amounts": r"""
            (?<!\w)
            \d+(?:[.,]\d+)?
            \s?
            (?:€|EUR|euros?)
        """,

        # -----------------------------------------------------
        # PERCENTAGES
        # -----------------------------------------------------

        "percentages": r"""
            \d+(?:[.,]\d+)?\s?%
        """,

        # -----------------------------------------------------
        # FREE
        # -----------------------------------------------------

        "free_mentions": r"""
            \b
            (?:free|gratuit|gratuite|gratis)
            \b
        """,

        # -----------------------------------------------------
        # PROMOTIONS
        # -----------------------------------------------------

        "promotion_mentions": r"""
            \b
            (?:
                offer|
                promotion|
                promo|
                bonus|
                reward|
                welcome|
                deal|
                offre|
                prime|
                récompense|
                cadeau
            )
            \b
        """,

        # -----------------------------------------------------
        # AGE
        # -----------------------------------------------------

        "age_mentions": r"""
            \b
            (?:
                under\s*18|
                under-18|
                moins\s+de\s+18\s+ans|
                \d{1,2}\s*(?:-|to|à)\s*\d{1,2}
                \s*(?:years|ans)
            )
            \b
        """,

        # -----------------------------------------------------
        # YOUTH
        # -----------------------------------------------------

        "youth_mentions": r"""
            \b
            (?:
                youth|
                young|
                child|
                children|
                kid|
                kids|
                teen|
                teenager|
                junior|
                jeune|
                jeunes|
                enfant|
                enfants|
                adolescent|
                adolescents
            )
            \b
        """,

        # -----------------------------------------------------
        # PAYMENT / CARD
        # -----------------------------------------------------

        "payment_mentions": r"""
            \b
            (?:
                card|
                debit-card|
                debit card|
                payment|
                payments|
                carte|
                paiement|
                paiements
            )
            \b
        """,
    }

    signals = {}

    for name, pattern in patterns.items():

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE | re.VERBOSE
        )

        # Remove duplicates while preserving order
        signals[name] = list(dict.fromkeys(matches))

    return signals

