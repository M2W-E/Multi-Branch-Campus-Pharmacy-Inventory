"""Prescription domain values, with no database, GUI, or stock operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


def _validate_identifier(value: str, field_name: str) -> str:
    """Require non-blank text while preserving exact database identifiers."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty or whitespace.")
    return value


class PrescriptionStatus(str, Enum):
    """The exact status values accepted by the Prescriptions table."""

    PENDING = "pending"
    DISPENSED = "dispensed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class PrescriptionLine:
    """An immutable medicine-code/quantity value within a prescription.

    Quantities are positive integers; Boolean values are explicitly rejected.
    Numeric form strings must be parsed at the GUI or application boundary.
    """

    medicine_code: str
    quantity: int

    def __post_init__(self) -> None:
        _validate_identifier(self.medicine_code, "medicine_code")
        if isinstance(self.quantity, bool) or not isinstance(
            self.quantity, int
        ):
            raise TypeError("quantity must be an integer, not a Boolean.")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero.")
