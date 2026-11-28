"""Tests for prescription values, validation, composition, and lifecycle."""

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from prescription import Prescription, PrescriptionLine, PrescriptionStatus


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


class PrescriptionConstructionTests(unittest.TestCase):
    """Verify complete prescriptions and their composition invariants."""

    def make_prescription(self, **changes):
        arguments = dict(
            prescription_id="RX-DEMO-001", patient_id="PAT-DEMO-001",
            branch_id="BR-MAIN", lines=[PrescriptionLine("M1", 2)],
        )
        arguments.update(changes)
        return Prescription(**arguments)

    def test_valid_default_prescription(self):
        prescription = self.make_prescription()
        self.assertEqual(prescription.prescription_id, "RX-DEMO-001")
        self.assertEqual(prescription.patient_id, "PAT-DEMO-001")
        self.assertEqual(prescription.branch_id, "BR-MAIN")
        self.assertIsNone(prescription.prescriber_code)
        self.assertIs(prescription.status, PrescriptionStatus.PENDING)
        self.assertEqual(prescription.lines, (PrescriptionLine("M1", 2),))

    def test_valid_optional_prescriber_code(self):
        prescription = self.make_prescription(prescriber_code="PRESC-DEMO-OK")
        self.assertEqual(prescription.prescriber_code, "PRESC-DEMO-OK")

    def test_blank_optional_prescriber_becomes_none(self):
        for code in (None, "", " ", "\t\n"):
            with self.subTest(code=code):
                prescription = self.make_prescription(prescriber_code=code)
                self.assertIsNone(prescription.prescriber_code)

    def test_invalid_prescriber_types_are_rejected(self):
        for code in (True, 1, [], b"PRESC-DEMO-OK"):
            with self.subTest(code=code):
                with self.assertRaisesRegex(TypeError, "prescriber_code"):
                    self.make_prescription(prescriber_code=code)

    def test_blank_required_identifiers_are_rejected(self):
        for field in ("prescription_id", "patient_id", "branch_id"):
            for value in ("", " ", "\t\n"):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, field):
                        self.make_prescription(**{field: value})

    def test_non_string_required_identifiers_are_rejected(self):
        for field in ("prescription_id", "patient_id", "branch_id"):
            for value in (None, True, 1, [], b"ID"):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(TypeError, field):
                        self.make_prescription(**{field: value})

    def test_non_blank_identifiers_are_preserved_exactly(self):
        prescription = self.make_prescription(
            prescription_id=" RX1 ", patient_id=" P1 ", branch_id=" B1 ",
            prescriber_code=" PRESC-DEMO-OK ",
        )
        self.assertEqual(prescription.prescription_id, " RX1 ")
        self.assertEqual(prescription.patient_id, " P1 ")
        self.assertEqual(prescription.branch_id, " B1 ")
        self.assertEqual(prescription.prescriber_code, " PRESC-DEMO-OK ")

    def test_multiple_different_medicine_lines(self):
        lines = [PrescriptionLine("M1", 2), PrescriptionLine("M2", 3)]
        self.assertEqual(
            self.make_prescription(lines=lines).lines, tuple(lines)
        )

    def test_tuple_and_generator_line_inputs(self):
        lines = (PrescriptionLine("M1", 1), PrescriptionLine("M2", 2))
        self.assertEqual(self.make_prescription(lines=lines).lines, lines)
        self.assertEqual(
            self.make_prescription(lines=(line for line in lines)).lines, lines
        )

    def test_empty_line_collections_are_rejected(self):
        for lines in ([], (), iter(())):
            with self.subTest(lines=lines):
                with self.assertRaisesRegex(ValueError, "at least one line"):
                    self.make_prescription(lines=lines)

    def test_non_iterable_lines_are_rejected(self):
        for lines in (None, True, 1):
            with self.subTest(lines=lines):
                with self.assertRaisesRegex(TypeError, "lines"):
                    self.make_prescription(lines=lines)

    def test_invalid_line_items_are_rejected(self):
        for line in (None, True, "M1", ("M1", 2), {"medicine_code": "M1"}):
            with self.subTest(line=line):
                with self.assertRaisesRegex(TypeError, "PrescriptionLine"):
                    self.make_prescription(lines=[line])

    def test_mixed_valid_and_invalid_lines_are_rejected(self):
        with self.assertRaisesRegex(TypeError, "PrescriptionLine"):
            self.make_prescription(lines=[PrescriptionLine("M1", 1), None])

    def test_duplicate_medicine_codes_are_summed(self):
        prescription = self.make_prescription(lines=[
            PrescriptionLine("M1", 3), PrescriptionLine("M1", 3),
        ])
        self.assertEqual(prescription.lines, (PrescriptionLine("M1", 6),))
        # Member 4 must compare this total (6) against stock, not each 3.
        self.assertGreater(prescription.lines[0].quantity, 5)

    def test_duplicate_consolidation_keeps_first_seen_order(self):
        prescription = self.make_prescription(lines=[
            PrescriptionLine("M2", 1), PrescriptionLine("M1", 2),
            PrescriptionLine("M2", 4), PrescriptionLine("M3", 1),
        ])
        self.assertEqual(prescription.lines, (
            PrescriptionLine("M2", 5), PrescriptionLine("M1", 2),
            PrescriptionLine("M3", 1),
        ))

    def test_distinct_case_and_whitespace_codes_are_not_combined(self):
        lines = [
            PrescriptionLine("M1", 1), PrescriptionLine("m1", 1),
            PrescriptionLine(" M1 ", 1),
        ]
        self.assertEqual(
            self.make_prescription(lines=lines).lines, tuple(lines)
        )

    def test_external_list_edits_do_not_change_prescription(self):
        lines = [PrescriptionLine("M1", 1)]
        prescription = self.make_prescription(lines=lines)
        lines.clear()
        self.assertEqual(prescription.lines, (PrescriptionLine("M1", 1),))

    def test_prescription_lines_tuple_cannot_be_edited(self):
        prescription = self.make_prescription()
        with self.assertRaises(TypeError):
            prescription.lines[0] = PrescriptionLine("M2", 1)
        with self.assertRaises(FrozenInstanceError):
            prescription.lines[0].quantity = 3

    def test_public_properties_cannot_be_reassigned(self):
        prescription = self.make_prescription()
        for field, value in (
            ("prescription_id", "RX2"), ("patient_id", "P2"),
            ("branch_id", "B2"), ("prescriber_code", "NEW"), ("lines", ()),
        ):
            with self.subTest(field=field):
                previous = getattr(prescription, field)
                with self.assertRaises(AttributeError):
                    setattr(prescription, field, value)
                self.assertEqual(getattr(prescription, field), previous)

    def test_all_persisted_statuses_can_be_reconstructed(self):
        for status in PrescriptionStatus:
            for supplied in (status, status.value):
                with self.subTest(status=supplied):
                    self.assertIs(
                        self.make_prescription(status=supplied).status, status
                    )

    def test_invalid_status_strings_are_rejected(self):
        for status in ("", "PENDING", "pending ", "unknown"):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError, "status"):
                    self.make_prescription(status=status)

    def test_invalid_status_types_are_rejected(self):
        for status in (None, True, 1, [], b"pending"):
            with self.subTest(status=status):
                with self.assertRaisesRegex(TypeError, "status"):
                    self.make_prescription(status=status)

    def test_direct_status_assignment_is_rejected(self):
        prescription = self.make_prescription()
        for status in ("unknown", "dispensed", PrescriptionStatus.CANCELLED):
            with self.subTest(status=status):
                with self.assertRaises(AttributeError):
                    prescription.status = status
                self.assertIs(prescription.status, PrescriptionStatus.PENDING)


if __name__ == "__main__":
    unittest.main()
