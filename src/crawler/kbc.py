from crawler.base import BankCrawler


class KBCCrawler(BankCrawler):

    def __init__(self):

        super().__init__(
            bank_name="kbc",
            domain="kbc.be",
            include_keywords=[
                "youth",
                "young",
                "child",
                "children",
                "kid",
                "kids",
                "junior",
                "minor",
                "account",
                "current-account",
                "debit-card",
            ],
            exclude_keywords=[
                "savings",
                "investment",
                "mortgage",
                "insurance",
            ],
        )