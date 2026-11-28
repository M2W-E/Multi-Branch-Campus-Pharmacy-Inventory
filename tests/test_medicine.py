"""Unit tests for medicine validation and simulated authorization.

Run from the project root:
    python -B -m unittest discover -s tests -p test_medicine.py -v
"""

import unittest
from decimal import Decimal, InvalidOperation, localcontext

from medicine import ControlledMedicine, Medicine, OrdinaryMedicine


MEDICINE_CLASSES = (OrdinaryMedicine, ControlledMedicine)


class MedicineValidationTests(unittest.TestCase):
    """Exercise shared validation through both concrete medicine classes."""

    def test_valid_ordinary_medicine(self):
        medicine = OrdinaryMedicine("MED-001", "Paracetamol", "500.25", 10)
        self.assertEqual(medicine.medicine_code, "MED-001")
        self.assertEqual(medicine.name, "Paracetamol")
        self.assertEqual(medicine.unit_price, Decimal("500.25"))
        self.assertIsInstance(medicine.unit_price, Decimal)
        self.assertEqual(medicine.reorder_level, 10)
        self.assertEqual(medicine.medicine_type, "ordinary")

    def test_valid_controlled_medicine(self):
        medicine = ControlledMedicine("MED-002", "Codeine", Decimal("8000"), 5)
        self.assertEqual(medicine.medicine_code, "MED-002")
        self.assertEqual(medicine.name, "Codeine")
        self.assertEqual(medicine.unit_price, Decimal("8000"))
        self.assertEqual(medicine.reorder_level, 5)
        self.assertEqual(medicine.medicine_type, "controlled")

    def test_supported_price_inputs_become_decimal(self):
        for medicine_class in MEDICINE_CLASSES:
            for price in (12, 12.5, "12.50", Decimal("12.50")):
                with self.subTest(cls=medicine_class.__name__, price=price):
                    medicine = medicine_class("M1", "Demo", price, 0)
                    self.assertIsInstance(medicine.unit_price, Decimal)
                    self.assertEqual(medicine.unit_price, Decimal(str(price)))

    def test_float_conversion_avoids_binary_expansion(self):
        medicine = OrdinaryMedicine("M1", "Demo", 0.1, 0)
        self.assertEqual(medicine.unit_price, Decimal("0.1"))

    def test_zero_and_negative_prices_are_rejected(self):
        for medicine_class in MEDICINE_CLASSES:
            for price in (0, 0.0, "-0", Decimal("-0"), -1, -0.01, "-2.5"):
                with self.subTest(cls=medicine_class.__name__, price=price):
                    with self.assertRaisesRegex(ValueError, "unit_price"):
                        medicine_class("M1", "Demo", price, 0)

    def test_non_numeric_price_strings_are_rejected(self):
        for medicine_class in MEDICINE_CLASSES:
            for price in ("", " ", "free", "12.3.4"):
                with self.subTest(cls=medicine_class.__name__, price=price):
                    with self.assertRaisesRegex(ValueError, "unit_price"):
                        medicine_class("M1", "Demo", price, 0)

    def test_unsupported_price_types_are_rejected(self):
        for medicine_class in MEDICINE_CLASSES:
            for price in (None, True, False, complex(1, 2), [], {}, b"10"):
                with self.subTest(cls=medicine_class.__name__, price=price):
                    with self.assertRaisesRegex(TypeError, "unit_price"):
                        medicine_class("M1", "Demo", price, 0)

    def test_non_finite_prices_are_rejected(self):
        prices = (
            float("inf"), float("-inf"), float("nan"), "Infinity",
            "-Infinity", "NaN", Decimal("Infinity"), Decimal("-Infinity"),
            Decimal("NaN"), Decimal("sNaN"), Decimal("-NaN"),
        )
        for medicine_class in MEDICINE_CLASSES:
            for price in prices:
                with self.subTest(cls=medicine_class.__name__, price=price):
                    with self.assertRaisesRegex(ValueError, "unit_price"):
                        medicine_class("M1", "Demo", price, 0)

    def test_malformed_price_rejected_with_decimal_trap_disabled(self):
        with localcontext() as context:
            context.traps[InvalidOperation] = False
            with self.assertRaisesRegex(ValueError, "unit_price"):
                OrdinaryMedicine("M1", "Demo", "invalid", 0)

    def test_positive_price_boundaries_preserve_precision(self):
        for medicine_class in MEDICINE_CLASSES:
            for price in (
                "0.000001", "1E-1000", "1E+1000", "123.456789012345"
            ):
                with self.subTest(cls=medicine_class.__name__, price=price):
                    medicine = medicine_class("M1", "Demo", price, 0)
                    self.assertEqual(medicine.unit_price, Decimal(price))

    def test_reorder_level_accepts_zero_and_positive_integers(self):
        for medicine_class in MEDICINE_CLASSES:
            for level in (0, 1, 100, 2**63 - 1):
                with self.subTest(cls=medicine_class.__name__, level=level):
                    medicine = medicine_class("M1", "Demo", 1, level)
                    self.assertEqual(medicine.reorder_level, level)

    def test_negative_reorder_level_is_rejected(self):
        for medicine_class in MEDICINE_CLASSES:
            with self.subTest(cls=medicine_class.__name__):
                with self.assertRaisesRegex(ValueError, "reorder_level"):
                    medicine_class("M1", "Demo", 1, -1)

    def test_non_integer_reorder_levels_are_rejected(self):
        for medicine_class in MEDICINE_CLASSES:
            for level in (
                True, False, 0.0, 1.0, 1.5, "1", Decimal("1"), None,
                float("inf"), float("nan"), [],
            ):
                with self.subTest(cls=medicine_class.__name__, level=level):
                    with self.assertRaisesRegex(TypeError, "reorder_level"):
                        medicine_class("M1", "Demo", 1, level)

    def test_blank_codes_and_names_are_rejected(self):
        for medicine_class in MEDICINE_CLASSES:
            for field in ("medicine_code", "name"):
                for value in ("", " ", "\t\n"):
                    with self.subTest(
                        cls=medicine_class.__name__, field=field, value=value
                    ):
                        arguments = dict(
                            medicine_code="M1", name="Demo",
                            unit_price=1, reorder_level=0,
                        )
                        arguments[field] = value
                        with self.assertRaisesRegex(ValueError, field):
                            medicine_class(**arguments)

    def test_non_string_codes_and_names_are_rejected(self):
        for medicine_class in MEDICINE_CLASSES:
            for field in ("medicine_code", "name"):
                for value in (None, True, 123, [], b"M1"):
                    with self.subTest(
                        cls=medicine_class.__name__, field=field, value=value
                    ):
                        arguments = dict(
                            medicine_code="M1", name="Demo",
                            unit_price=1, reorder_level=0,
                        )
                        arguments[field] = value
                        with self.assertRaisesRegex(TypeError, field):
                            medicine_class(**arguments)

    def test_non_blank_text_is_preserved_exactly(self):
        medicine = OrdinaryMedicine(" MED-001 ", " Demo medicine ", 1, 0)
        self.assertEqual(medicine.medicine_code, " MED-001 ")
        self.assertEqual(medicine.name, " Demo medicine ")

    def test_valid_attribute_updates(self):
        for medicine_class in MEDICINE_CLASSES:
            with self.subTest(cls=medicine_class.__name__):
                medicine = medicine_class("M1", "Old name", 1, 1)
                medicine.medicine_code = "M2"
                medicine.name = "New name"
                medicine.unit_price = "0.01"
                medicine.reorder_level = 0
                self.assertEqual(medicine.medicine_code, "M2")
                self.assertEqual(medicine.name, "New name")
                self.assertEqual(medicine.unit_price, Decimal("0.01"))
                self.assertEqual(medicine.reorder_level, 0)

    def test_invalid_updates_preserve_previous_values(self):
        updates = (
            ("medicine_code", "", ValueError),
            ("medicine_code", None, TypeError),
            ("name", "\t", ValueError),
            ("name", 10, TypeError),
            ("unit_price", 0, ValueError),
            ("unit_price", -1, ValueError),
            ("unit_price", "invalid", ValueError),
            ("unit_price", Decimal("NaN"), ValueError),
            ("unit_price", Decimal("Infinity"), ValueError),
            ("unit_price", True, TypeError),
            ("reorder_level", -1, ValueError),
            ("reorder_level", 1.5, TypeError),
            ("reorder_level", False, TypeError),
        )
        for medicine_class in MEDICINE_CLASSES:
            medicine = medicine_class("M1", "Demo", "10.50", 2)
            for field, value, exception in updates:
                with self.subTest(
                    cls=medicine_class.__name__, field=field, value=value
                ):
                    previous = getattr(medicine, field)
                    with self.assertRaisesRegex(exception, field):
                        setattr(medicine, field, value)
                    self.assertEqual(getattr(medicine, field), previous)

    def test_medicine_type_cannot_be_changed(self):
        for medicine_class in MEDICINE_CLASSES:
            medicine = medicine_class("M1", "Demo", 1, 0)
            original_type = medicine.medicine_type
            for value in ("ordinary", "controlled", "unknown", None):
                with self.subTest(cls=medicine_class.__name__, value=value):
                    with self.assertRaises(AttributeError):
                        medicine.medicine_type = value
                    self.assertEqual(medicine.medicine_type, original_type)


if __name__ == "__main__":
    unittest.main()
