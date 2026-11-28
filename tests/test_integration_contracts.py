"""Member 1 contract checks against reviewed, unmodified Git snapshots.

These tests use Git objects, never a checkout, network connection, or disk DB.
Missing snapshots cause explicit skips (for example in a single-branch clone).
Tests documenting known incompatibilities assert the observed failure; they
do not imply that the complete GUI or dispensing application is integrated.
"""

import ast
import math
import shutil
import sqlite3
import subprocess
import sys
import types
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from medicine import ControlledMedicine, Medicine, OrdinaryMedicine
from prescription import Prescription, PrescriptionLine, PrescriptionStatus


ROOT = Path(__file__).resolve().parents[1]
DATABASE_COMMIT = "08fda12c1c259f98832f48cf0d87df1b54298b77"
GUI_COMMIT = "10273185e21854f86abaa0f53e7075350fdc5354"


def snapshot_source(commit: str, filename: str) -> str:
    """Read an exact reviewed Git object, skipping only unavailable inputs."""
    if shutil.which("git") is None:
        raise unittest.SkipTest("Git is required for snapshot contract tests.")
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT, capture_output=True,
    )
    if exists.returncode:
        raise unittest.SkipTest(f"Reviewed Git snapshot unavailable: {commit}")
    return subprocess.check_output(
        ["git", "show", f"{commit}:{filename}"], cwd=ROOT, text=True,
        encoding="utf-8",
    )


def load_database_repositories():
    """Load the reviewed persistence modules in memory for contract tests."""
    database = types.ModuleType("database")
    database.__file__ = str(ROOT / "database.py")
    exec(compile(snapshot_source(DATABASE_COMMIT, "database.py"),
                 database.__file__, "exec"), database.__dict__)
    repositories = types.ModuleType("reviewed_repositories")
    with patch.dict(sys.modules, {"database": database}):
        exec(compile(snapshot_source(DATABASE_COMMIT, "repositories.py"),
                     "reviewed_repositories.py", "exec"),
             repositories.__dict__)
    return repositories


class DatabaseContractTests(unittest.TestCase):
    """Round trips plus explicit evidence of persistence integration gaps."""

    @classmethod
    def setUpClass(cls):
        cls.repositories = load_database_repositories()
        cls.schema = snapshot_source(DATABASE_COMMIT, "schema.sql")

    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.addCleanup(self.connection.close)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(self.schema)
        self.medicines = self.repositories.MedicineRepository()
        self.prescriptions = self.repositories.PrescriptionRepository()
        self.prescribers = self.repositories.AuthorisedPrescriberRepository()
        branches = self.repositories.BranchRepository()
        branches.add_branch("BR-MAIN", "Demo branch", conn=self.connection)
        for code, kind in (("M1", "ordinary"), ("M2", "controlled")):
            self.medicines.add_medicine(
                code, "Demo medicine", 10, 0, kind, conn=self.connection
            )
        self.connection.commit()

    def save_prescription(self, prescription):
        self.prescriptions.save_prescription(
            prescription.prescription_id, prescription.patient_id,
            prescription.branch_id, prescription.prescriber_code,
            prescription.status.value,
            [(line.medicine_code, line.quantity)
             for line in prescription.lines],
            conn=self.connection,
        )

    def test_medicine_field_and_type_round_trip_with_boundary_conversion(self):
        for medicine_class in (OrdinaryMedicine, ControlledMedicine):
            medicine = medicine_class(
                medicine_class.__name__, "Demo medicine", "12.50", 0
            )
            self.medicines.add_medicine(
                medicine.medicine_code, medicine.name,
                str(medicine.unit_price),
                medicine.reorder_level, medicine.medicine_type,
                conn=self.connection,
            )
            record = self.medicines.get_medicine_by_code(
                medicine.medicine_code, conn=self.connection
            )
            self.assertEqual(record["medicine_type"], medicine.medicine_type)
            restored = medicine_class(
                record["medicine_code"], record["name"],
                record["unit_price"], record["reorder_level"],
            )
            self.assertEqual(restored.unit_price, medicine.unit_price)

    def test_known_gap_repository_rejects_unadapted_decimal(self):
        with self.assertRaisesRegex(sqlite3.ProgrammingError, "Decimal"):
            self.medicines.add_medicine(
                "M3", "Demo", Decimal("1.25"), 0, "ordinary",
                conn=self.connection,
            )

    def test_known_gap_numeric_storage_loses_decimal_precision(self):
        price = Decimal("0.12345678901234567890123456789")
        self.medicines.add_medicine(
            "M3", "Demo", str(price), 0, "ordinary", conn=self.connection
        )
        record = self.medicines.get_medicine_by_code(
            "M3", conn=self.connection
        )
        self.assertNotEqual(Decimal(str(record["unit_price"])), price)

    def test_known_gap_tiny_positive_decimal_underflows_at_database(self):
        medicine = OrdinaryMedicine("M3", "Demo", "1E-1000", 0)
        with self.assertRaises(sqlite3.IntegrityError):
            self.medicines.add_medicine(
                medicine.medicine_code, medicine.name,
                str(medicine.unit_price),
                medicine.reorder_level, medicine.medicine_type,
                conn=self.connection,
            )

    def test_known_gap_domain_integers_can_exceed_sqlite_range(self):
        medicine = OrdinaryMedicine("M3", "Demo", 1, 2**63)
        with self.assertRaises(OverflowError):
            self.medicines.add_medicine(
                medicine.medicine_code, medicine.name, 1,
                medicine.reorder_level, medicine.medicine_type,
                conn=self.connection,
            )

    def test_known_gap_huge_finite_decimal_becomes_infinite_in_storage(self):
        medicine = OrdinaryMedicine("M3", "Demo", "1E+1000", 0)
        self.medicines.add_medicine(
            medicine.medicine_code, medicine.name, str(medicine.unit_price),
            medicine.reorder_level, medicine.medicine_type,
            conn=self.connection,
        )
        record = self.medicines.get_medicine_by_code(
            "M3", conn=self.connection
        )
        self.assertTrue(math.isinf(record["unit_price"]))
        with self.assertRaisesRegex(ValueError, "unit_price"):
            OrdinaryMedicine("M3", "Demo", record["unit_price"], 0)

    def test_prescription_round_trip_statuses_and_optional_prescribers(self):
        for status in PrescriptionStatus:
            for code in (None, "PRESC-DEMO-OK"):
                with self.subTest(status=status, code=code):
                    prescription = Prescription(
                        "RX-DEMO-001", "PAT-DEMO-001", "BR-MAIN",
                        lines=[PrescriptionLine("M1", 1),
                               PrescriptionLine("M2", 2)],
                        prescriber_code=code, status=status,
                    )
                    self.save_prescription(prescription)
                    record = self.prescriptions.get_prescription_with_lines(
                        prescription.prescription_id, conn=self.connection
                    )
                    restored = Prescription(
                        record["prescription_id"], record["patient_id"],
                        record["branch_id"], prescriber_code=record[
                            "prescriber_code"
                        ], status=record["status"],
                        lines=[PrescriptionLine(
                            line["medicine_code"], line["quantity"]
                        ) for line in record["lines"]],
                    )
                    self.assertEqual(restored.lines, prescription.lines)
                    self.assertEqual(restored.prescriber_code, code)
                    self.assertIs(restored.status, status)

    def test_duplicate_rows_are_consolidated_on_reconstruction(self):
        self.prescriptions.save_prescription(
            "RX-DEMO-001", "PAT-DEMO-001", "BR-MAIN", None, "pending",
            [("M1", 3), ("M1", 3)], conn=self.connection,
        )
        record = self.prescriptions.get_prescription_with_lines(
            "RX-DEMO-001", conn=self.connection
        )
        self.assertEqual(len(record["lines"]), 2)
        prescription = Prescription(
            record["prescription_id"], record["patient_id"],
            record["branch_id"],
            lines=[PrescriptionLine(line["medicine_code"], line["quantity"])
                   for line in record["lines"]],
        )
        self.assertEqual(prescription.lines, (PrescriptionLine("M1", 6),))
        self.save_prescription(prescription)
        self.assertEqual(len(self.prescriptions.get_prescription_lines(
            prescription.prescription_id, conn=self.connection
        )), 1)

    def test_repository_allow_list_matches_domain_exactly(self):
        self.prescribers.add_prescriber("PRESC-DEMO-OK", conn=self.connection)
        allowed = {row["prescriber_code"] for row in
                   self.prescribers.get_all_prescribers(conn=self.connection)}
        medicine = ControlledMedicine("M2", "Demo", 1, 0)
        for code in (None, "UNKNOWN", "presc-demo-ok", "PRESC-DEMO-OK"):
            with self.subTest(code=code):
                self.assertEqual(
                    medicine.can_dispense(code, allowed),
                    self.prescribers.is_authorised(code, conn=self.connection),
                )

    def test_known_gap_repository_does_not_guard_terminal_transitions(self):
        prescription = Prescription(
            "RX-DEMO-001", "PAT-DEMO-001", "BR-MAIN",
            lines=[PrescriptionLine("M1", 1)], status="cancelled",
        )
        self.save_prescription(prescription)
        with self.assertRaises(ValueError):
            prescription.mark_dispensed()
        self.assertTrue(self.prescriptions.update_prescription_status(
            prescription.prescription_id, "dispensed", conn=self.connection
        ))
        # The repository checks vocabulary; Member 4 owns atomic guards.
        record = self.prescriptions.get_prescription(
            prescription.prescription_id, conn=self.connection
        )
        self.assertEqual(record["status"], "dispensed")

    def test_repository_respects_caller_rollback(self):
        prescription = Prescription(
            "RX-DEMO-001", "PAT-DEMO-001", "BR-MAIN",
            lines=[PrescriptionLine("M1", 1)],
        )
        self.save_prescription(prescription)
        self.connection.rollback()
        self.assertIsNone(self.prescriptions.get_prescription(
            prescription.prescription_id, conn=self.connection
        ))


def gui_method(filename: str, class_name: str, method_name: str):
    """Compile an actual GUI callback in isolation, without widgets."""
    tree = ast.parse(snapshot_source(GUI_COMMIT, filename))
    view = next(node for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in view.body
                  if isinstance(node, ast.FunctionDef)
                  and node.name == method_name)
    module = ast.Module(body=[method], type_ignores=[])
    namespace = {
        "Medicine": Medicine, "ControlledMedicine": ControlledMedicine,
        "Prescription": Prescription, "PrescriptionLine": PrescriptionLine,
        "run_action": lambda action: (action(), True)[1],
        "messagebox": Mock(), "fill_table": Mock(),
    }
    exec(compile(module, filename, "exec"), namespace)
    return namespace[method_name]


class GuiContractTests(unittest.TestCase):
    """Reproduce legacy GUI mismatches and verify an explicit new mapping."""

    def test_known_gap_gui_imports_absent_pharmacy_facade(self):
        source = snapshot_source(GUI_COMMIT, "gui/common.py")
        imports = [node.module for node in ast.walk(ast.parse(source))
                   if isinstance(node, ast.ImportFrom)]
        self.assertIn("pharmacy", imports)
        tree = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", GUI_COMMIT],
            cwd=ROOT, text=True,
        ).splitlines()
        self.assertNotIn("pharmacy.py", tree)
        self.assertFalse((ROOT / "pharmacy.py").exists())

    def test_known_gap_gui_constructs_abstract_ordinary_medicine(self):
        save = gui_method("gui/medicine_view.py", "MedicineView", "save")
        view = types.SimpleNamespace(
            controlled=Mock(get=lambda: False), code=Mock(get=lambda: "M3"),
            name=Mock(get=lambda: "Demo"), price=Mock(get=lambda: "10"),
            reorder=Mock(get=lambda: "0"), pharmacy=Mock(), on_change=Mock(),
        )
        with self.assertRaises(TypeError):
            save(view)
        view.pharmacy.add_medicine.assert_not_called()

    def test_known_gap_gui_passes_string_reorder_level(self):
        save = gui_method("gui/medicine_view.py", "MedicineView", "save")
        view = types.SimpleNamespace(
            controlled=Mock(get=lambda: True), code=Mock(get=lambda: "M3"),
            name=Mock(get=lambda: "Demo"), price=Mock(get=lambda: "10"),
            reorder=Mock(get=lambda: "0"), pharmacy=Mock(), on_change=Mock(),
        )
        with self.assertRaisesRegex(TypeError, "reorder_level"):
            save(view)

    def test_known_gap_gui_reads_legacy_medicine_aliases(self):
        refresh = gui_method("gui/medicine_view.py", "MedicineView", "refresh")
        view = types.SimpleNamespace(table=Mock(), pharmacy=Mock())
        view.pharmacy.list_medicines.return_value = [
            OrdinaryMedicine("M1", "Demo", 1, 0)
        ]
        with self.assertRaisesRegex(AttributeError, "code"):
            refresh(view)

    def test_known_gap_gui_passes_string_line_quantity(self):
        add_line = gui_method(
            "gui/prescription_view.py", "PrescriptionView", "add_line"
        )
        view = types.SimpleNamespace(
            code=Mock(get=lambda: "M1"), qty=Mock(get=lambda: "1"),
            lines=[], lines_box=Mock(),
        )
        with self.assertRaisesRegex(TypeError, "quantity"):
            add_line(view)
        self.assertEqual(view.lines, [])

    def test_known_gap_gui_uses_legacy_prescription_constructor(self):
        save = gui_method(
            "gui/prescription_view.py", "PrescriptionView", "save"
        )
        view = types.SimpleNamespace(
            patient=Mock(get=lambda: "PAT-DEMO-001"),
            branch_box=Mock(get=lambda: "BR-MAIN"),
            prescriber=Mock(get=lambda: "PRESC-DEMO-OK"),
            lines=[PrescriptionLine("M1", 1)], pharmacy=Mock(),
        )
        with self.assertRaises(TypeError):
            save(view)
        view.pharmacy.create_prescription.assert_not_called()

    def test_known_gap_gui_casts_text_prescription_ids_to_int(self):
        selected_id = gui_method(
            "gui/prescription_view.py", "PrescriptionView", "selected_id"
        )
        table = Mock()
        table.selection.return_value = ("row1",)
        table.item.return_value = {"values": ["RX-DEMO-001"]}
        with self.assertRaises(ValueError):
            selected_id(types.SimpleNamespace(table=table))

    def test_explicit_form_mapping_constructs_valid_domain_objects(self):
        # Test-only mapping example, not an implementation of Member 5's GUI.
        line = PrescriptionLine("M1", int("2"))
        medicine = OrdinaryMedicine("M1", "Demo", "10.50", int("0"))
        prescription = Prescription(
            prescription_id="RX-DEMO-001", patient_id="PAT-DEMO-001",
            branch_id="BR-MAIN", lines=[line], prescriber_code="",
        )
        self.assertEqual(prescription.lines[0].medicine_code,
                         medicine.medicine_code)
        self.assertIsNone(prescription.prescriber_code)
        self.assertEqual(medicine.unit_price, Decimal("10.50"))


if __name__ == "__main__":
    unittest.main()
