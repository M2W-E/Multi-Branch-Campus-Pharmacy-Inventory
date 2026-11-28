"""Tests for prescription values, validation, composition, and lifecycle."""

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from prescription import PrescriptionLine, PrescriptionStatus


class PrescriptionStatusTests(unittest.TestCase):
    """Verify exact database status representations."""

    def test_status_values_match_database(self):
        self.assertEqual(
            {status.value for status in PrescriptionStatus},
            {"pending", "dispensed", "cancelled"},
        )

    def test_valid_strings_reconstruct_status(self):
        for status in PrescriptionStatus:
            with self.subTest(status=status.value):
                self.assertIs(PrescriptionStatus(status.value), status)

    def test_invalid_status_values_are_rejected(self):
        for value in ("", "PENDING", "unknown", "pending ", None, True, 1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    PrescriptionStatus(value)


class PrescriptionLineTests(unittest.TestCase):
    """Verify validated immutable medicine/quantity values."""

    def test_valid_line(self):
        line = PrescriptionLine("MED-DEMO-001", 2)
        self.assertEqual(line.medicine_code, "MED-DEMO-001")
        self.assertEqual(line.quantity, 2)

    def test_minimum_quantity(self):
        self.assertEqual(PrescriptionLine("M1", 1).quantity, 1)

    def test_large_integer_quantity(self):
        quantity = 2**63 - 1
        self.assertEqual(PrescriptionLine("M1", quantity).quantity, quantity)

    def test_zero_and_negative_quantities_are_rejected(self):
        for quantity in (0, -1, -100):
            with self.subTest(quantity=quantity):
                with self.assertRaisesRegex(ValueError, "quantity"):
                    PrescriptionLine("M1", quantity)

    def test_boolean_quantities_are_rejected(self):
        for quantity in (True, False):
            with self.subTest(quantity=quantity):
                with self.assertRaisesRegex(TypeError, "quantity"):
                    PrescriptionLine("M1", quantity)

    def test_other_non_integer_quantities_are_rejected(self):
        for quantity in (
            1.0, 1.5, "1", Decimal("1"), None, [], float("inf"), float("nan")
        ):
            with self.subTest(quantity=quantity):
                with self.assertRaisesRegex(TypeError, "quantity"):
                    PrescriptionLine("M1", quantity)

    def test_blank_medicine_codes_are_rejected(self):
        for code in ("", " ", "\t\n"):
            with self.subTest(code=code):
                with self.assertRaisesRegex(ValueError, "medicine_code"):
                    PrescriptionLine(code, 1)

    def test_non_string_medicine_codes_are_rejected(self):
        for code in (None, True, 1, b"M1", []):
            with self.subTest(code=code):
                with self.assertRaisesRegex(TypeError, "medicine_code"):
                    PrescriptionLine(code, 1)

    def test_identifier_is_not_silently_normalized(self):
        self.assertEqual(PrescriptionLine(" M1 ", 1).medicine_code, " M1 ")

    def test_quantity_is_immutable(self):
        line = PrescriptionLine("M1", 1)
        with self.assertRaises(FrozenInstanceError):
            line.quantity = 2
        self.assertEqual(line.quantity, 1)

    def test_medicine_code_is_immutable(self):
        line = PrescriptionLine("M1", 1)
        with self.assertRaises(FrozenInstanceError):
            line.medicine_code = "M2"
        self.assertEqual(line.medicine_code, "M1")

    def test_fields_cannot_be_deleted(self):
        line = PrescriptionLine("M1", 1)
        with self.assertRaises(FrozenInstanceError):
            del line.quantity

    def test_equal_values_compare_equal_and_are_hashable(self):
        self.assertEqual(PrescriptionLine("M1", 1), PrescriptionLine("M1", 1))
        self.assertEqual(len({PrescriptionLine("M1", 1)}), 1)


if __name__ == "__main__":
    unittest.main()
