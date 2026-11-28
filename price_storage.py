"""Validate price at the SQLite NUMERIC boundary."""
import sqlite3
from decimal import Decimal, InvalidOperation


def sqlite_price(value):
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float, str)):
        raise TypeError("Price must be numeric, not Boolean.")
    try:
        price = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Price must be numeric.") from exc
    if not price.is_finite() or price <= 0:
        raise ValueError("Price must be finite and positive.")
    connection = sqlite3.connect(":memory:")
    try:
        stored = connection.execute("SELECT CAST(? AS NUMERIC)", (str(price),)).fetchone()[0]
    finally:
        connection.close()
    restored = Decimal(str(stored))
    if not restored.is_finite() or restored <= 0 or restored != price:
        raise ValueError("Price cannot be stored and recovered without precision loss.")
    return stored
