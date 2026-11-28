"""Database initialization script for the CSC2105 campus pharmacy project.

Member 2 owns this module. It creates the SQLite schema and optionally loads
fictional demonstration data.

Usage:
    python init_db.py
    python init_db.py --seed
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from database import DATABASE_PATH, connect

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def initialize_database(database_path: str | Path = DATABASE_PATH) -> Path:
    """Create database tables from ``schema.sql`` without destroying data.

    The schema uses ``CREATE TABLE IF NOT EXISTS`` so repeated initialization
    preserves existing records.

    Args:
        database_path: Target SQLite database path.

    Returns:
        The resolved database path.

    Raises:
        FileNotFoundError: If ``schema.sql`` cannot be found.
        sqlite3.Error: If schema execution fails.
    """
    db_path = Path(database_path)
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(db_path) as connection:
        connection.executescript(schema_sql)
    return db_path


def seed_database(database_path: str | Path = DATABASE_PATH) -> None:
    """Insert fictional demonstration records idempotently.

    Re-running this function does not duplicate reference records and does not
    multiply stock quantities. Stock seed rows are written with a deterministic
    quantity using an upsert on ``(medicine_code, branch_id)``.

    Args:
        database_path: Target SQLite database path.

    Raises:
        sqlite3.Error: If seeding fails.
    """
    medicines = [
        ("MED-DEMO-001", "Paracetamol 500mg", 500, 20, "ordinary"),
        ("MED-DEMO-002", "Amoxicillin 250mg", 1500, 15, "ordinary"),
        ("MED-DEMO-003", "Codeine Syrup 100ml", 8000, 10, "controlled"),
    ]
    branches = [
        ("BR-MAIN", "Main Campus Pharmacy"),
        ("BR-SAT", "Satellite Clinic Pharmacy"),
    ]
    stock_rows = [
        ("MED-DEMO-001", "BR-MAIN", 50),
        ("MED-DEMO-001", "BR-SAT", 20),
        ("MED-DEMO-002", "BR-MAIN", 30),
        ("MED-DEMO-003", "BR-MAIN", 12),
    ]
    prescribers = [("PRESC-DEMO-OK",)]
    prescriptions = [
        ("RX-DEMO-001", "PAT-DEMO-001", "BR-MAIN", "PRESC-DEMO-OK", "pending"),
    ]
    prescription_lines = [
        ("RX-DEMO-001", "MED-DEMO-001", 2),
        ("RX-DEMO-001", "MED-DEMO-002", 1),
    ]

    connection = connect(database_path)
    try:
        connection.execute("BEGIN")
        connection.executemany(
            """
            INSERT INTO Medicines (
                medicine_code, name, unit_price, reorder_level, medicine_type
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(medicine_code) DO UPDATE SET
                name = excluded.name,
                unit_price = excluded.unit_price,
                reorder_level = excluded.reorder_level,
                medicine_type = excluded.medicine_type
            """,
            medicines,
        )
        connection.executemany(
            """
            INSERT INTO Branches (branch_id, branch_name)
            VALUES (?, ?)
            ON CONFLICT(branch_id) DO UPDATE SET
                branch_name = excluded.branch_name
            """,
            branches,
        )
        connection.executemany(
            """
            INSERT INTO Stock (medicine_code, branch_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(medicine_code, branch_id) DO UPDATE SET
                quantity = excluded.quantity
            """,
            stock_rows,
        )
        connection.executemany(
            """
            INSERT INTO Authorised_Prescribers (prescriber_code)
            VALUES (?)
            ON CONFLICT(prescriber_code) DO NOTHING
            """,
            prescribers,
        )
        connection.executemany(
            """
            INSERT INTO Prescriptions (
                prescription_id, patient_id, branch_id, prescriber_code, status
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(prescription_id) DO UPDATE SET
                patient_id = excluded.patient_id,
                branch_id = excluded.branch_id,
                prescriber_code = excluded.prescriber_code,
                status = excluded.status
            """,
            prescriptions,
        )

        # Keep demo prescription lines deterministic: replace lines for the
        # seeded prescription only, then insert the known demo lines.
        seeded_rx_ids = [(rx[0],) for rx in prescriptions]
        connection.executemany(
            "DELETE FROM Prescription_Lines WHERE prescription_id = ?",
            seeded_rx_ids,
        )
        connection.executemany(
            """
            INSERT INTO Prescription_Lines (
                prescription_id, medicine_code, quantity
            ) VALUES (?, ?, ?)
            """,
            prescription_lines,
        )
        connection.commit()
    except sqlite3.Error:
        connection.rollback()
        raise
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Initialize the CSC2105 pharmacy SQLite database."
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Load fictional demonstration data after initialization.",
    )
    parser.add_argument(
        "--database",
        default=str(DATABASE_PATH),
        help="Path to the SQLite database file (default: pharmacy.sqlite3).",
    )
    return parser


def main() -> int:
    """Run database initialization from the command line."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        db_path = initialize_database(args.database)
        print(f"Database initialized: {db_path}")
        if args.seed:
            seed_database(args.database)
            print("Fictional seed data loaded.")
            print("Demo prescriber: PRESC-DEMO-OK")
            print("Demo patient: PAT-DEMO-001")
    except (FileNotFoundError, sqlite3.Error, OSError) as exc:
        print(f"Database initialization failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
