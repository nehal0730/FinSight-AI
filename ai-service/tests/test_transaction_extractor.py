import unittest
from app.services.fraud import TransactionExtractor


class TransactionExtractorTests(unittest.TestCase):
    def test_extract_transactions_from_bank_statement_text(self):
        text = """
        05 Jan 2025 POS Debit ₹45000 CasinoXYZ
        06 Jan 2025 UPI DR INR 1200 GroceryMart
        07/01/2025 Salary Credit ₹85000 ACME_PAYROLL
        2025-01-08 IMPS CR 3500 RefundFromMerchant
        """.strip()

        transactions = TransactionExtractor.extract_transactions(text)

        self.assertEqual(len(transactions), 4)

        self.assertEqual(
            transactions[0],
            {
                "date": "2025-01-05",
                "amount": 45000.0,
                "type": "debit",
                "merchant": "CasinoXYZ",
            },
        )

        self.assertEqual(transactions[1]["type"], "debit")
        self.assertEqual(transactions[1]["merchant"], "GroceryMart")

        self.assertEqual(transactions[2]["type"], "credit")
        self.assertEqual(transactions[2]["merchant"], "ACME_PAYROLL")

        self.assertEqual(transactions[3]["date"], "2025-01-08")
        self.assertEqual(transactions[3]["amount"], 3500.0)
        self.assertEqual(transactions[3]["type"], "credit")

    def test_extract_transactions_ignores_non_transaction_lines(self):
        text = """
        Statement period: 01 Jan 2025 to 31 Jan 2025
        Opening Balance: ₹120000
        Thank you for banking with us.
        """.strip()

        transactions = TransactionExtractor.extract_transactions(text)

        self.assertEqual(transactions, [])

    def test_to_dataframe_requires_pandas_or_returns_dataframe(self):
        rows = [
            {
                "date": "2025-01-05",
                "amount": 45000.0,
                "type": "debit",
                "merchant": "CasinoXYZ",
            }
        ]

        try:
            df = TransactionExtractor.to_dataframe(rows)
            self.assertEqual(list(df.columns), ["date", "amount", "type", "merchant"])
            self.assertEqual(len(df), 1)
        except ImportError:
            self.skipTest("pandas not installed in environment")

