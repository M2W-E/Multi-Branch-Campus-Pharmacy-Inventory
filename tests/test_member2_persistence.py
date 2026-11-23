import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from database import connect
from init_db import initialize_database, seed_database
from repositories import (
    AuthorisedPrescriberRepository,
    BranchRepository,
    MedicineRepository,
    PrescriptionRepository,
    StockRepository,
)


class TempDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_pharmacy.sqlite3"
        initialize_database(self.db_path)
        self.medicines = MedicineRepository(self.db_path)
        self.branches = BranchRepository(self.db_path)
        self.stock = StockRepository(self.db_path)
        self.prescriptions = PrescriptionRepository(self.db_path)
        self.prescribers = AuthorisedPrescriberRepository(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def seed_reference_data(self):
        self.medicines.add_medicine("MED-001", "Paracetamol 500mg", 500, 10, "ordinary")
        self.medicines.add_medicine("MED-002", "Codeine Syrup", 8000, 5, "controlled")
        self.branches.add_branch("BR-MAIN", "Main Campus Pharmacy")
        self.branches.add_branch("BR-SAT", "Satellite Clinic Pharmacy")
        self.prescribers.add_prescriber("PRESC-DEMO-OK")


class DatabaseInitializationTests(TempDatabaseTestCase):
    def test_initialize_database_creates_required_tables(self):
        with closing(connect(self.db_path)) as conn:
            rows = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        table_names = {row["name"] for row in rows}
        self.assertEqual(
            table_names,
            {
                "Authorised_Prescribers",
                "Branches",
                "Medicines",
                "Prescription_Lines",
                "Prescriptions",
                "Stock",
            },
        )

    def test_initialize_database_is_idempotent_and_preserves_data(self):
        self.seed_reference_data()
        initialize_database(self.db_path)
        initialize_database(self.db_path)
        medicine = self.medicines.get_medicine_by_code("MED-001")
        self.assertIsNotNone(medicine)
        self.assertEqual(medicine["name"], "Paracetamol 500mg")

    def test_foreign_keys_enabled_for_each_connection(self):
        with closing(connect(self.db_path)) as conn:
            enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(enabled, 1)
        with closing(connect(self.db_path)) as conn2:
            enabled2 = conn2.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(enabled2, 1)


class MedicineRepositoryTests(TempDatabaseTestCase):
    def test_save_and_retrieve_medicine(self):
        self.medicines.add_medicine("MED-010", "Ibuprofen 200mg", 750, 12, "ordinary")
        record = self.medicines.get_medicine_by_code("MED-010")
        self.assertIsNotNone(record)
        self.assertEqual(record["medicine_code"], "MED-010")
        self.assertEqual(record["name"], "Ibuprofen 200mg")
        self.assertEqual(float(record["unit_price"]), 750.0)
        self.assertEqual(record["reorder_level"], 12)
        self.assertEqual(record["medicine_type"], "ordinary")

    def test_duplicate_medicine_code_rejected(self):
        self.medicines.add_medicine("MED-011", "Aspirin", 300, 5, "ordinary")
        with self.assertRaises(sqlite3.IntegrityError):
            self.medicines.add_medicine("MED-011", "Aspirin Duplicate", 300, 5, "ordinary")

    def test_invalid_unit_price_rejected_at_database_boundary(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.medicines.add_medicine("MED-BAD-PRICE", "Bad Price", 0, 5, "ordinary")
        with self.assertRaises(sqlite3.IntegrityError):
            self.medicines.add_medicine("MED-BAD-PRICE2", "Bad Price", -10, 5, "ordinary")

    def test_invalid_reorder_level_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.medicines.add_medicine("MED-BAD-RL", "Bad RL", 100, -1, "ordinary")
        with self.assertRaises(sqlite3.IntegrityError):
            self.medicines.add_medicine("MED-BAD-RL2", "Bad RL", 100, 1.5, "ordinary")

    def test_retrieve_all_medicines(self):
        self.seed_reference_data()
        medicines = self.medicines.get_all_medicines()
        codes = [m["medicine_code"] for m in medicines]
        self.assertEqual(codes, ["MED-001", "MED-002"])

    def test_update_and_delete_medicine(self):
        self.medicines.add_medicine("MED-UPD", "Old Name", 100, 1, "ordinary")
        updated = self.medicines.update_medicine("MED-UPD", "New Name", 150, 2, "ordinary")
        self.assertTrue(updated)
        record = self.medicines.get_medicine_by_code("MED-UPD")
        self.assertEqual(record["name"], "New Name")
        deleted = self.medicines.delete_medicine("MED-UPD")
        self.assertTrue(deleted)
        self.assertIsNone(self.medicines.get_medicine_by_code("MED-UPD"))


class BranchRepositoryTests(TempDatabaseTestCase):
    def test_register_and_retrieve_branch(self):
        self.branches.add_branch("BR-001", "Main Campus")
        branch = self.branches.get_branch_by_id("BR-001")
        self.assertIsNotNone(branch)
        self.assertEqual(branch["branch_name"], "Main Campus")

    def test_retrieve_all_branches(self):
        self.seed_reference_data()
        branches = self.branches.get_all_branches()
        self.assertEqual([b["branch_id"] for b in branches], ["BR-MAIN", "BR-SAT"])


class StockRepositoryTests(TempDatabaseTestCase):
    def test_branch_specific_stock_records(self):
        self.seed_reference_data()
        self.stock.create_stock_record("MED-001", "BR-MAIN", 10)
        self.stock.create_stock_record("MED-001", "BR-SAT", 3)
        main = self.stock.get_stock_record("MED-001", "BR-MAIN")
        sat = self.stock.get_stock_record("MED-001", "BR-SAT")
        self.assertEqual(main["quantity"], 10)
        self.assertEqual(sat["quantity"], 3)

    def test_duplicate_medicine_branch_stock_rejected(self):
        self.seed_reference_data()
        self.stock.create_stock_record("MED-001", "BR-MAIN", 10)
        with self.assertRaises(sqlite3.IntegrityError):
            self.stock.create_stock_record("MED-001", "BR-MAIN", 5)

    def test_negative_stock_rejected(self):
        self.seed_reference_data()
        with self.assertRaises(sqlite3.IntegrityError):
            self.stock.create_stock_record("MED-001", "BR-MAIN", -1)

    def test_invalid_foreign_key_rejected(self):
        self.seed_reference_data()
        with self.assertRaises(sqlite3.IntegrityError):
            self.stock.create_stock_record("MED-NOPE", "BR-MAIN", 1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.stock.create_stock_record("MED-001", "BR-NOPE", 1)

    def test_get_stock_for_branch(self):
        self.seed_reference_data()
        self.stock.create_stock_record("MED-001", "BR-MAIN", 10)
        self.stock.create_stock_record("MED-002", "BR-MAIN", 4)
        records = self.stock.get_stock_for_branch("BR-MAIN")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["medicine_code"], "MED-001")


class PrescriptionRepositoryTests(TempDatabaseTestCase):
    def test_prescription_header_and_lines_persistence(self):
        self.seed_reference_data()
        self.prescriptions.save_prescription(
            prescription_id="RX-001",
            patient_id="PAT-DEMO-001",
            branch_id="BR-MAIN",
            prescriber_code="PRESC-DEMO-OK",
            status="pending",
            lines=[
                {"medicine_code": "MED-001", "quantity": 2},
                ("MED-002", 1),
            ],
        )
        header = self.prescriptions.get_prescription("RX-001")
        lines = self.prescriptions.get_prescription_lines("RX-001")
        self.assertIsNotNone(header)
        self.assertEqual(header["status"], "pending")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["medicine_code"], "MED-001")
        self.assertEqual(lines[1]["quantity"], 1)

    def test_invalid_prescription_status_rejected(self):
        self.seed_reference_data()
        with self.assertRaises(sqlite3.IntegrityError):
            self.prescriptions.save_prescription_header(
                "RX-BAD", "PAT-DEMO-001", "BR-MAIN", None, "unknown"
            )

    def test_invalid_prescription_line_quantity_rejected(self):
        self.seed_reference_data()
        self.prescriptions.save_prescription_header(
            "RX-QTY", "PAT-DEMO-001", "BR-MAIN", None, "pending"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.prescriptions.add_prescription_line("RX-QTY", "MED-001", 0)
        with self.assertRaises(sqlite3.IntegrityError):
            self.prescriptions.add_prescription_line("RX-QTY", "MED-001", -2)

    def test_save_prescription_is_atomic_when_it_owns_connection(self):
        self.seed_reference_data()
        # Second line has invalid FK; whole save should fail and leave no header.
        with self.assertRaises(sqlite3.IntegrityError):
            self.prescriptions.save_prescription(
                prescription_id="RX-ATOMIC",
                patient_id="PAT-DEMO-001",
                branch_id="BR-MAIN",
                prescriber_code=None,
                status="pending",
                lines=[
                    {"medicine_code": "MED-001", "quantity": 1},
                    {"medicine_code": "MED-MISSING", "quantity": 1},
                ],
            )
        self.assertIsNone(self.prescriptions.get_prescription("RX-ATOMIC"))
        self.assertEqual(self.prescriptions.get_prescription_lines("RX-ATOMIC"), [])


class AuthorisedPrescriberTests(TempDatabaseTestCase):
    def test_prescriber_persistence_and_lookup(self):
        self.prescribers.add_prescriber("PRESC-DEMO-OK")
        self.assertTrue(self.prescribers.is_authorised("PRESC-DEMO-OK"))
        self.assertFalse(self.prescribers.is_authorised("PRESC-NOPE"))
        self.assertFalse(self.prescribers.is_authorised(None))
        all_codes = [r["prescriber_code"] for r in self.prescribers.get_all_prescribers()]
        self.assertEqual(all_codes, ["PRESC-DEMO-OK"])


class PersistenceAndIsolationTests(TempDatabaseTestCase):
    def test_persistence_after_close_and_reopen(self):
        self.seed_reference_data()
        self.stock.create_stock_record("MED-001", "BR-MAIN", 10)
        self.prescriptions.save_prescription(
            "RX-PERSIST", "PAT-DEMO-001", "BR-MAIN", "PRESC-DEMO-OK", "pending",
            [("MED-001", 1)],
        )

        # Reopen repositories against same file path.
        medicines = MedicineRepository(self.db_path)
        stock = StockRepository(self.db_path)
        prescriptions = PrescriptionRepository(self.db_path)
        self.assertIsNotNone(medicines.get_medicine_by_code("MED-001"))
        self.assertEqual(stock.get_stock_record("MED-001", "BR-MAIN")["quantity"], 10)
        self.assertEqual(prescriptions.get_prescription("RX-PERSIST")["status"], "pending")

    def test_branch_isolation_after_reopen(self):
        self.seed_reference_data()
        self.stock.create_stock_record("MED-001", "BR-MAIN", 10)
        self.stock.create_stock_record("MED-001", "BR-SAT", 3)

        # New repository instances simulate reopening the application.
        reopened = StockRepository(self.db_path)
        main = reopened.get_stock_record("MED-001", "BR-MAIN")
        sat = reopened.get_stock_record("MED-001", "BR-SAT")
        self.assertEqual(main["quantity"], 10)
        self.assertEqual(sat["quantity"], 3)


class SeedTests(TempDatabaseTestCase):
    def test_seed_is_idempotent_and_does_not_multiply_stock(self):
        seed_database(self.db_path)
        with closing(connect(self.db_path)) as conn:
            before = conn.execute(
                "SELECT medicine_code, branch_id, quantity FROM Stock ORDER BY medicine_code, branch_id"
            ).fetchall()
        seed_database(self.db_path)
        with closing(connect(self.db_path)) as conn:
            after = conn.execute(
                "SELECT medicine_code, branch_id, quantity FROM Stock ORDER BY medicine_code, branch_id"
            ).fetchall()
        self.assertEqual([tuple(r) for r in before], [tuple(r) for r in after])
        with closing(connect(self.db_path)) as conn:
            med_count = conn.execute("SELECT COUNT(*) FROM Medicines").fetchone()[0]
            branch_count = conn.execute("SELECT COUNT(*) FROM Branches").fetchone()[0]
        self.assertEqual(med_count, 3)
        self.assertEqual(branch_count, 2)

    def test_seed_includes_required_demo_codes(self):
        seed_database(self.db_path)
        prescribers = AuthorisedPrescriberRepository(self.db_path)
        prescriptions = PrescriptionRepository(self.db_path)
        self.assertTrue(prescribers.is_authorised("PRESC-DEMO-OK"))
        rx = prescriptions.get_prescription("RX-DEMO-001")
        self.assertIsNotNone(rx)
        self.assertEqual(rx["patient_id"], "PAT-DEMO-001")


if __name__ == "__main__":
    unittest.main()
