from crawler.base import BankCrawler


class BelfiusCrawler(BankCrawler):

    def __init__(self):

        super().__init__(
            bank_name="belfius",
            domain="belfius.be",
            include_keywords=[
                "young",
                "youth",
                "jeune",
                "jeunes",
                "junior",
                "child",
                "children",
                "enfant",
                "enfants",
                "minor",
                "moins de 25",
                "25 ans",
                "compte",
                "compte bancaire",
                "compte de paiement",
                "beats",
                "beats new",
                "debit card",
                "carte de débit",
                "mastercard",
            ],
            exclude_keywords=[
                "savings",
                "épargne",
                "investment",
                "investissement",
                "mortgage",
                "hypothèque",
                "insurance",
                "assurance",
                "credit",
                "crédit",
            ],
        )