from crawler.base import BankCrawler


class BNPCrawler(BankCrawler):

    def __init__(self):

        super().__init__(
            bank_name="bnp",
            domain="bnpparibasfortis.be",
            include_keywords=[
                "youth",
                "young",
                "youth-account",
                "young-account",
                "child",
                "children",
                "kid",
                "kids",
                "junior",
                "minor",
                "teenager",
                "teen",
                "account",
                "current-account",
                "debit-card",
                "payment",
                "payments",
            ],
            exclude_keywords=[
                "savings",
                "investment",
                "mortgage",
                "insurance",
                "loan",
                "credit",
            ],
        )