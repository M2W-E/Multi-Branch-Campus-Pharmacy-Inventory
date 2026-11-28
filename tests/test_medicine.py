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

    def test_price_input_is_not_rounded_by_decimal_context(self):
        for medicine_class in MEDICINE_CLASSES:
            with self.subTest(cls=medicine_class.__name__):
                with localcontext() as context:
                    context.prec = 2
                    medicine = medicine_class("M1", "Demo", "123.456789", 0)
                self.assertEqual(medicine.unit_price, Decimal("123.456789"))

    def test_medicine_instances_have_independent_values(self):
        first = OrdinaryMedicine("M1", "First", "1.25", 1)
        second = OrdinaryMedicine("M2", "Second", "1.25", 1)
        first.name = "Changed"
        first.unit_price = "2.50"
        self.assertEqual(second.name, "Second")
        self.assertEqual(second.unit_price, Decimal("1.25"))

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


class MedicineAuthorizationTests(unittest.TestCase):
    """Check overriding, polymorphism, and exact allow-list matching."""

    def setUp(self):
        self.ordinary = OrdinaryMedicine("M1", "Ordinary demo", 1, 0)
        self.controlled = ControlledMedicine("M2", "Controlled demo", 2, 0)
        self.allowed = {"PRESC-DEMO-OK", "PRESC-DEMO-OTHER"}

    def test_ordinary_medicine_requires_no_authorization(self):
        self.assertTrue(self.ordinary.can_dispense())
        self.assertTrue(self.ordinary.can_dispense(None, set()))
        self.assertTrue(self.ordinary.can_dispense("UNKNOWN", self.allowed))
        self.assertTrue(self.ordinary.can_dispense("", self.allowed))

    def test_ordinary_medicine_ignores_malformed_authorization_inputs(self):
        self.assertTrue(self.ordinary.can_dispense(True, "invalid allow-list"))

    def test_controlled_medicine_accepts_authorized_code(self):
        for code in self.allowed:
            with self.subTest(code=code):
                self.assertIs(
                    self.controlled.can_dispense(code, self.allowed), True
                )

    def test_controlled_medicine_rejects_unknown_code(self):
        self.assertIs(
            self.controlled.can_dispense("UNKNOWN", self.allowed), False
        )

    def test_controlled_medicine_rejects_missing_or_invalid_code(self):
        for code in (None, "", " ", "\t\n", True, False, 123, []):
            with self.subTest(code=code):
                self.assertIs(
                    self.controlled.can_dispense(code, self.allowed), False
                )

    def test_controlled_medicine_rejects_missing_or_empty_allow_list(self):
        self.assertFalse(self.controlled.can_dispense())
        self.assertFalse(self.controlled.can_dispense("PRESC-DEMO-OK"))
        self.assertFalse(self.controlled.can_dispense("PRESC-DEMO-OK", set()))

    def test_controlled_authorization_is_exact_and_case_sensitive(self):
        for code in ("presc-demo-ok", "PRESC", "PRESC-DEMO-OK "):
            with self.subTest(code=code):
                self.assertFalse(
                    self.controlled.can_dispense(code, self.allowed)
                )

    def test_controlled_medicine_supports_standard_code_collections(self):
        for allowed in (
            ["PRESC-DEMO-OK"], ("PRESC-DEMO-OK",),
            {"PRESC-DEMO-OK"}, frozenset({"PRESC-DEMO-OK"}),
        ):
            with self.subTest(collection=type(allowed).__name__):
                self.assertTrue(
                    self.controlled.can_dispense("PRESC-DEMO-OK", allowed)
                )

    def test_single_string_cannot_authorize_by_substring(self):
        for allowed in ("PRESC-DEMO-OK", b"PRESC-DEMO-OK"):
            with self.subTest(allowed=allowed):
                with self.assertRaisesRegex(TypeError, "collection"):
                    self.controlled.can_dispense("PRESC", allowed)

    def test_non_collection_allow_lists_are_rejected(self):
        for allowed in (True, 1, iter(["PRESC-DEMO-OK"])):
            with self.subTest(allowed=allowed):
                with self.assertRaisesRegex(TypeError, "collection"):
                    self.controlled.can_dispense("PRESC-DEMO-OK", allowed)

    def test_malformed_allow_list_entries_are_rejected(self):
        for allowed, exception in (
            ([None], TypeError), ([True], TypeError),
            ([123], TypeError), ([""], ValueError), ([" "], ValueError),
        ):
            with self.subTest(allowed=allowed):
                with self.assertRaisesRegex(exception, "prescriber code"):
                    self.controlled.can_dispense("PRESC-DEMO-OK", allowed)

    def test_authorization_does_not_modify_supplied_allow_list(self):
        previous = self.allowed.copy()
        self.controlled.can_dispense("PRESC-DEMO-OK", self.allowed)
        self.assertEqual(self.allowed, previous)

    def test_allow_list_revocation_is_observed_on_next_call(self):
        self.assertTrue(
            self.controlled.can_dispense("PRESC-DEMO-OK", self.allowed)
        )
        self.allowed.remove("PRESC-DEMO-OK")
        self.assertFalse(
            self.controlled.can_dispense("PRESC-DEMO-OK", self.allowed)
        )

    def test_both_concrete_classes_inherit_from_medicine(self):
        self.assertIsInstance(self.ordinary, Medicine)
        self.assertIsInstance(self.controlled, Medicine)

    def test_parent_is_abstract(self):
        with self.assertRaises(TypeError):
            Medicine("M1", "Demo", 1, 0, "ordinary")

    def test_polymorphic_calls_use_each_medicine_policy(self):
        medicines: list[Medicine] = [self.ordinary, self.controlled]
        self.assertEqual(
            [item.can_dispense() for item in medicines], [True, False]
        )
        self.assertEqual(
            [
                item.can_dispense("PRESC-DEMO-OK", self.allowed)
                for item in medicines
            ],
            [True, True],
        )


if __name__ == "__main__":
    unittest.main()
