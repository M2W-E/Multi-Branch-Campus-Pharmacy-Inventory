"""Prescription domain values, with no database, GUI, or stock operations."""

from __future__ import annotations

from collections.abc import Iterable
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


class Prescription:
    """A non-empty collection of immutable lines and validated identifiers.

    Duplicate medicine codes are consolidated in first-seen order. Member 4
    must check these total quantities against branch stock in one transaction.
    This object neither reserves stock nor guarantees concurrent safety.

    Identity, lines, prescriber and status are read-only public properties.
    Valid persisted statuses can be supplied when reconstructing a record.
    Blank optional prescriber input becomes None; other codes stay exact.
    """

    def __init__(
        self,
        prescription_id: str,
        patient_id: str,
        branch_id: str,
        lines: Iterable[PrescriptionLine],
        prescriber_code: str | None = None,
        status: PrescriptionStatus | str = PrescriptionStatus.PENDING,
    ) -> None:
        self._prescription_id = _validate_identifier(
            prescription_id, "prescription_id"
        )
        self._patient_id = _validate_identifier(patient_id, "patient_id")
        self._branch_id = _validate_identifier(branch_id, "branch_id")
        if prescriber_code is not None:
            if not isinstance(prescriber_code, str):
                raise TypeError("prescriber_code must be a string or None.")
            if not prescriber_code.strip():
                prescriber_code = None
        self._prescriber_code = prescriber_code
        if not isinstance(status, (str, PrescriptionStatus)):
            raise TypeError("status must be a PrescriptionStatus or string.")
        try:
            self._status = PrescriptionStatus(status)
        except ValueError as exc:
            raise ValueError(
                "status must be 'pending', 'dispensed', or 'cancelled'."
            ) from exc

        if not isinstance(lines, Iterable):
            raise TypeError(
                "lines must be an iterable of PrescriptionLine values."
            )
        quantities: dict[str, int] = {}
        for line in lines:
            if not isinstance(line, PrescriptionLine):
                raise TypeError("Every line must be a PrescriptionLine.")
            quantities[line.medicine_code] = (
                quantities.get(line.medicine_code, 0) + line.quantity
            )
        if not quantities:
            raise ValueError("A prescription must contain at least one line.")
        self._lines = tuple(
            PrescriptionLine(code, quantity)
            for code, quantity in quantities.items()
        )

    @property
    def prescription_id(self) -> str:
        """Return the explicit application-supplied prescription identifier."""
        return self._prescription_id

    @property
    def patient_id(self) -> str:
        """Return the patient identifier, without exposing patient details."""
        return self._patient_id

    @property
    def branch_id(self) -> str:
        """Return the branch at which the prescription will be processed."""
        return self._branch_id

    @property
    def prescriber_code(self) -> str | None:
        """Return the optional code, without implying authorization."""
        return self._prescriber_code

    @property
    def lines(self) -> tuple[PrescriptionLine, ...]:
        """Return consolidated lines as a tuple that callers cannot edit."""
        return self._lines

    @property
    def status(self) -> PrescriptionStatus:
        """Return the lifecycle status; serialize using status.value."""
        return self._status
