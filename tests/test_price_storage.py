import unittest
from decimal import Decimal
from price_storage import sqlite_price

class PriceStorageTests(unittest.TestCase):
    def test_prices(self):
        for text in ("500", "12.50", "0.01", "99.99"):
            self.assertEqual(Decimal(str(sqlite_price(text))), Decimal(text))

    def test_bad_prices(self):
        for value in (0, -1, "NaN", "Infinity", "abc", "1E-1000", "1E+1000", "1.1234567890123456789"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sqlite_price(value)
        with self.assertRaises(TypeError):
            sqlite_price(True)
