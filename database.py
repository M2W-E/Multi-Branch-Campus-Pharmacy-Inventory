"""SQLite connection helper for the CSC2105 campus pharmacy project.

Member 2 owns this module. It provides a reusable connection factory that
other modules can use for persistence. Every connection enables foreign-key
enforcement and uses ``sqlite3.Row`` for name-based column access.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).with_name("pharmacy.sqlite3")


def connect(database_path: str | Path = DATABASE_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with project-standard settings.

    Args:
        database_path: Path to the SQLite database file, or ``":memory:"``
            for a temporary in-memory database used during tests.

    Returns:
        A configured ``sqlite3.Connection`` with ``sqlite3.Row`` as the row
        factory and ``PRAGMA foreign_keys = ON``.

    Raises:
        sqlite3.Error: If the connection cannot be opened or configured.
    """
    try:
        connection = sqlite3.connect(str(database_path))
    except sqlite3.Error as exc:
        raise sqlite3.Error(
            f"Could not open database '{database_path}': {exc}"
        ) from exc

    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
    except sqlite3.Error:
        connection.close()
        raise
    return connection
