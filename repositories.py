"""Repository layer for the CSC2105 campus pharmacy project.

Member 2 owns this module. Repositories isolate SQL persistence from the rest
of the application. They do not implement Member 3's inventory business rules
or Member 4's dispensing workflow.

Connection and transaction ownership
------------------------------------
Most methods accept an optional ``conn`` parameter.

* If ``conn`` is ``None`` (default), the repository opens a connection using
  ``database.connect()``, executes the operation, commits on success, rolls
  back on error, and closes the connection.
* If ``conn`` is provided, the repository uses that connection and does **not**
  commit or close it. The caller owns the transaction. This allows Member 4 to
  perform multiple repository operations inside one atomic dispensing
  transaction.

All SQL uses parameterized queries.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

from database import DATABASE_PATH, connect

Row = sqlite3.Row


@contextmanager
def _managed_connection(
    database_path: str | Any = DATABASE_PATH,
    conn: sqlite3.Connection | None = None,
) -> Iterator[tuple[sqlite3.Connection, bool]]:
    """Yield a connection and whether this helper owns it.

    The helper owns the connection when ``conn`` is None. Owned connections are
    committed on success, rolled back on sqlite3.Error, and always closed.
    """
    owns_connection = conn is None
    connection = connect(database_path) if owns_connection else conn
    try:
        yield connection, owns_connection
        if owns_connection:
            connection.commit()
    except Exception:
        if owns_connection:
            connection.rollback()
        raise
    finally:
        if owns_connection:
            connection.close()


def _row_to_dict(row: Row | None) -> dict[str, Any] | None:
    """Convert a sqlite3.Row to a plain dict, or return None."""
    if row is None:
        return None
    return dict(row)


class MedicineRepository:
    """Persistence operations for medicine records."""

    def __init__(self, database_path: str | Any = DATABASE_PATH):
        self.database_path = database_path

    def add_medicine(
        self,
        medicine_code: str,
        name: str,
        unit_price: float | int,
        reorder_level: int,
        medicine_type: str,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Insert a new medicine. Raises sqlite3.IntegrityError on duplicates."""
        sql = """
            INSERT INTO Medicines (
                medicine_code, name, unit_price, reorder_level, medicine_type
            ) VALUES (?, ?, ?, ?, ?)
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            connection.execute(
                sql,
                (medicine_code, name, unit_price, reorder_level, medicine_type),
            )

    def save_medicine(
        self,
        medicine_code: str,
        name: str,
        unit_price: float | int,
        reorder_level: int,
        medicine_type: str,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Insert or update a medicine by primary key.

        This convenience method is useful for seed/setup workflows. Use
        ``add_medicine`` when duplicate codes must be rejected.
        """
        sql = """
            INSERT INTO Medicines (
                medicine_code, name, unit_price, reorder_level, medicine_type
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(medicine_code) DO UPDATE SET
                name = excluded.name,
                unit_price = excluded.unit_price,
                reorder_level = excluded.reorder_level,
                medicine_type = excluded.medicine_type
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            connection.execute(
                sql,
                (medicine_code, name, unit_price, reorder_level, medicine_type),
            )

    def get_medicine_by_code(
        self,
        medicine_code: str,
        conn: sqlite3.Connection | None = None,
    ) -> dict[str, Any] | None:
        """Return one medicine record by code, or None if not found."""
        sql = """
            SELECT medicine_code, name, unit_price, reorder_level, medicine_type
            FROM Medicines
            WHERE medicine_code = ?
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            row = connection.execute(sql, (medicine_code,)).fetchone()
        return _row_to_dict(row)

    def get_all_medicines(
        self,
        conn: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        """Return all medicine records ordered by medicine code."""
        sql = """
            SELECT medicine_code, name, unit_price, reorder_level, medicine_type
            FROM Medicines
            ORDER BY medicine_code
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            rows = connection.execute(sql).fetchall()
        return [dict(row) for row in rows]

    def update_medicine(
        self,
        medicine_code: str,
        name: str,
        unit_price: float | int,
        reorder_level: int,
        medicine_type: str,
        conn: sqlite3.Connection | None = None,
    ) -> bool:
        """Update an existing medicine. Returns True if a row was updated."""
        sql = """
            UPDATE Medicines
            SET name = ?, unit_price = ?, reorder_level = ?, medicine_type = ?
            WHERE medicine_code = ?
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            cursor = connection.execute(
                sql, (name, unit_price, reorder_level, medicine_type, medicine_code)
            )
        return cursor.rowcount > 0

    def delete_medicine(
        self,
        medicine_code: str,
        conn: sqlite3.Connection | None = None,
    ) -> bool:
        """Delete a medicine if no database relationship blocks it.

        Returns True if a row was deleted. Raises sqlite3.IntegrityError when
        related stock or prescription-line records prevent deletion.
        """
        sql = "DELETE FROM Medicines WHERE medicine_code = ?"
        with _managed_connection(self.database_path, conn) as (connection, _):
            cursor = connection.execute(sql, (medicine_code,))
        return cursor.rowcount > 0


class BranchRepository:
    """Persistence operations for pharmacy branches."""

    def __init__(self, database_path: str | Any = DATABASE_PATH):
        self.database_path = database_path

    def add_branch(
        self,
        branch_id: str,
        branch_name: str,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Insert a new branch."""
        sql = "INSERT INTO Branches (branch_id, branch_name) VALUES (?, ?)"
        with _managed_connection(self.database_path, conn) as (connection, _):
            connection.execute(sql, (branch_id, branch_name))

    def save_branch(
        self,
        branch_id: str,
        branch_name: str,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Insert or update a branch by primary key."""
        sql = """
            INSERT INTO Branches (branch_id, branch_name)
            VALUES (?, ?)
            ON CONFLICT(branch_id) DO UPDATE SET branch_name = excluded.branch_name
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            connection.execute(sql, (branch_id, branch_name))

    def get_branch_by_id(
        self,
        branch_id: str,
        conn: sqlite3.Connection | None = None,
    ) -> dict[str, Any] | None:
        """Return one branch record, or None if not found."""
        sql = "SELECT branch_id, branch_name FROM Branches WHERE branch_id = ?"
        with _managed_connection(self.database_path, conn) as (connection, _):
            row = connection.execute(sql, (branch_id,)).fetchone()
        return _row_to_dict(row)

    def get_all_branches(
        self,
        conn: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        """Return all branches ordered by branch ID."""
        sql = "SELECT branch_id, branch_name FROM Branches ORDER BY branch_id"
        with _managed_connection(self.database_path, conn) as (connection, _):
            rows = connection.execute(sql).fetchall()
        return [dict(row) for row in rows]


class StockRepository:
    """Persistence operations for branch-specific stock records.

    This repository provides data access only. Member 3 owns stock receipt and
    inventory business rules; Member 4 owns dispensing transaction logic.
    """

    def __init__(self, database_path: str | Any = DATABASE_PATH):
        self.database_path = database_path

    def create_stock_record(
        self,
        medicine_code: str,
        branch_id: str,
        quantity: int,
        conn: sqlite3.Connection | None = None,
    ) -> int:
        """Create an initial stock record and return its stock_id."""
        sql = """
            INSERT INTO Stock (medicine_code, branch_id, quantity)
            VALUES (?, ?, ?)
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            cursor = connection.execute(sql, (medicine_code, branch_id, quantity))
            return int(cursor.lastrowid)

    def set_stock_quantity(
        self,
        medicine_code: str,
        branch_id: str,
        quantity: int,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Create or update the stock quantity for a medicine/branch pair.

        This is a persistence helper. It does not apply Member 3's receipt
        workflow rules; callers are responsible for validating business intent.
        """
        sql = """
            INSERT INTO Stock (medicine_code, branch_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(medicine_code, branch_id) DO UPDATE SET
                quantity = excluded.quantity
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            connection.execute(sql, (medicine_code, branch_id, quantity))

    def get_stock_record(
        self,
        medicine_code: str,
        branch_id: str,
        conn: sqlite3.Connection | None = None,
    ) -> dict[str, Any] | None:
        """Return the stock record for a medicine at a branch."""
        sql = """
            SELECT stock_id, medicine_code, branch_id, quantity
            FROM Stock
            WHERE medicine_code = ? AND branch_id = ?
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            row = connection.execute(sql, (medicine_code, branch_id)).fetchone()
        return _row_to_dict(row)

    def get_stock_for_branch(
        self,
        branch_id: str,
        conn: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        """Return all stock records for a branch."""
        sql = """
            SELECT stock_id, medicine_code, branch_id, quantity
            FROM Stock
            WHERE branch_id = ?
            ORDER BY medicine_code
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            rows = connection.execute(sql, (branch_id,)).fetchall()
        return [dict(row) for row in rows]

    def get_all_stock_records(
        self,
        conn: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        """Return all stock records, ordered for stable inspection/tests."""
        sql = """
            SELECT stock_id, medicine_code, branch_id, quantity
            FROM Stock
            ORDER BY branch_id, medicine_code
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            rows = connection.execute(sql).fetchall()
        return [dict(row) for row in rows]

    def update_stock_quantity(
        self,
        medicine_code: str,
        branch_id: str,
        quantity: int,
        conn: sqlite3.Connection | None = None,
    ) -> bool:
        """Update an existing stock quantity. Returns True if updated."""
        sql = """
            UPDATE Stock
            SET quantity = ?
            WHERE medicine_code = ? AND branch_id = ?
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            cursor = connection.execute(sql, (quantity, medicine_code, branch_id))
        return cursor.rowcount > 0


class PrescriptionRepository:
    """Persistence operations for prescriptions and prescription lines."""

    def __init__(self, database_path: str | Any = DATABASE_PATH):
        self.database_path = database_path

    def save_prescription_header(
        self,
        prescription_id: str,
        patient_id: str,
        branch_id: str,
        prescriber_code: str | None,
        status: str,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Insert or update a prescription header record."""
        sql = """
            INSERT INTO Prescriptions (
                prescription_id, patient_id, branch_id, prescriber_code, status
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(prescription_id) DO UPDATE SET
                patient_id = excluded.patient_id,
                branch_id = excluded.branch_id,
                prescriber_code = excluded.prescriber_code,
                status = excluded.status
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            connection.execute(
                sql,
                (prescription_id, patient_id, branch_id, prescriber_code, status),
            )

    def add_prescription_line(
        self,
        prescription_id: str,
        medicine_code: str,
        quantity: int,
        conn: sqlite3.Connection | None = None,
    ) -> int:
        """Insert a prescription line and return its line_id."""
        sql = """
            INSERT INTO Prescription_Lines (prescription_id, medicine_code, quantity)
            VALUES (?, ?, ?)
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            cursor = connection.execute(sql, (prescription_id, medicine_code, quantity))
            return int(cursor.lastrowid)

    def save_prescription(
        self,
        prescription_id: str,
        patient_id: str,
        branch_id: str,
        prescriber_code: str | None,
        status: str,
        lines: Sequence[dict[str, Any] | tuple[Any, ...]],
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Save a prescription header and all its lines in one logical operation.

        ``lines`` items may be dicts with ``medicine_code`` and ``quantity``
        keys, or tuples/lists in the form ``(medicine_code, quantity)``.

        When this method owns the connection, it commits only after the header
        and all lines have been written. When ``conn`` is supplied, it writes to
        the caller's transaction without committing.
        """
        if not lines:
            raise ValueError("A prescription must contain at least one line.")

        normalized_lines: list[tuple[str, int]] = []
        for line in lines:
            if isinstance(line, dict):
                medicine_code = line["medicine_code"]
                quantity = line["quantity"]
            else:
                medicine_code, quantity = line[0], line[1]
            normalized_lines.append((medicine_code, quantity))

        with _managed_connection(self.database_path, conn) as (connection, _):
            connection.execute(
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
                (prescription_id, patient_id, branch_id, prescriber_code, status),
            )
            connection.execute(
                "DELETE FROM Prescription_Lines WHERE prescription_id = ?",
                (prescription_id,),
            )
            connection.executemany(
                """
                INSERT INTO Prescription_Lines (
                    prescription_id, medicine_code, quantity
                ) VALUES (?, ?, ?)
                """,
                [(prescription_id, code, qty) for code, qty in normalized_lines],
            )

    def get_prescription(
        self,
        prescription_id: str,
        conn: sqlite3.Connection | None = None,
    ) -> dict[str, Any] | None:
        """Return a prescription header, or None if not found."""
        sql = """
            SELECT prescription_id, patient_id, branch_id, prescriber_code, status
            FROM Prescriptions
            WHERE prescription_id = ?
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            row = connection.execute(sql, (prescription_id,)).fetchone()
        return _row_to_dict(row)

    def get_prescription_lines(
        self,
        prescription_id: str,
        conn: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        """Return all lines for a prescription ordered by line_id."""
        sql = """
            SELECT line_id, prescription_id, medicine_code, quantity
            FROM Prescription_Lines
            WHERE prescription_id = ?
            ORDER BY line_id
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            rows = connection.execute(sql, (prescription_id,)).fetchall()
        return [dict(row) for row in rows]

    def get_prescription_with_lines(
        self,
        prescription_id: str,
        conn: sqlite3.Connection | None = None,
    ) -> dict[str, Any] | None:
        """Return a prescription header with a nested ``lines`` list."""
        with _managed_connection(self.database_path, conn) as (connection, _):
            header = self.get_prescription(prescription_id, conn=connection)
            if header is None:
                return None
            header["lines"] = self.get_prescription_lines(
                prescription_id, conn=connection
            )
            return header

    def update_prescription_status(
        self,
        prescription_id: str,
        status: str,
        conn: sqlite3.Connection | None = None,
    ) -> bool:
        """Update only the prescription status. Returns True if updated.

        This helper is useful for Member 4's dispensing workflow when the
        header already exists and only the status changes inside a controlled
        transaction.
        """
        sql = "UPDATE Prescriptions SET status = ? WHERE prescription_id = ?"
        with _managed_connection(self.database_path, conn) as (connection, _):
            cursor = connection.execute(sql, (status, prescription_id))
        return cursor.rowcount > 0


class AuthorisedPrescriberRepository:
    """Persistence operations for the simulated prescriber allow-list."""

    def __init__(self, database_path: str | Any = DATABASE_PATH):
        self.database_path = database_path

    def add_prescriber(
        self,
        prescriber_code: str,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Add a fictional prescriber code to the allow-list."""
        sql = "INSERT INTO Authorised_Prescribers (prescriber_code) VALUES (?)"
        with _managed_connection(self.database_path, conn) as (connection, _):
            connection.execute(sql, (prescriber_code,))

    def save_prescriber(
        self,
        prescriber_code: str,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Insert a prescriber code idempotently."""
        sql = """
            INSERT INTO Authorised_Prescribers (prescriber_code)
            VALUES (?)
            ON CONFLICT(prescriber_code) DO NOTHING
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            connection.execute(sql, (prescriber_code,))

    def is_authorised(
        self,
        prescriber_code: str | None,
        conn: sqlite3.Connection | None = None,
    ) -> bool:
        """Return True when the prescriber code exists in the allow-list."""
        if prescriber_code is None:
            return False
        sql = """
            SELECT 1
            FROM Authorised_Prescribers
            WHERE prescriber_code = ?
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            row = connection.execute(sql, (prescriber_code,)).fetchone()
        return row is not None

    def get_all_prescribers(
        self,
        conn: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        """Return all authorised prescriber codes."""
        sql = """
            SELECT prescriber_code
            FROM Authorised_Prescribers
            ORDER BY prescriber_code
        """
        with _managed_connection(self.database_path, conn) as (connection, _):
            rows = connection.execute(sql).fetchall()
        return [dict(row) for row in rows]
