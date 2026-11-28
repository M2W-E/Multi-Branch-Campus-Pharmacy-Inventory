"""Medicine domain models, independent of database and GUI operations.

Attribute names and medicine types match Member 2's Medicines table. Prices
remain Decimal values here. The persistence layer must explicitly convert or
adapt them before SQLite binding. NUMERIC storage may lose decimal precision.
Text identifiers are preserved exactly so database lookups remain consistent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection
from decimal import Decimal, InvalidOperation

PriceInput = Decimal | int | float | str


def _validate_text(value: str, field_name: str) -> str:
    """Require non-blank text without changing the supplied identifier."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty or whitespace.")
    return value


class Medicine(ABC):
    """Abstract parent containing validated medicine attributes.

    Invalid types raise TypeError; invalid values raise ValueError. Failed
    property updates preserve the previous value. medicine_type is read-only
    so changing a label cannot change a subclass's authorization rules.
    """

    def __init__(
        self,
        medicine_code: str,
        name: str,
        unit_price: PriceInput,
        reorder_level: int,
        medicine_type: str,
    ) -> None:
        if not isinstance(medicine_type, str):
            raise TypeError("medicine_type must be a string.")
        if medicine_type not in ("ordinary", "controlled"):
            raise ValueError(
                "medicine_type must be 'ordinary' or 'controlled'."
            )
        self._medicine_type = medicine_type
        self.medicine_code = medicine_code
        self.name = name
        self.unit_price = unit_price
        self.reorder_level = reorder_level

    @property
    def medicine_code(self) -> str:
        """Return the medicine's database identifier."""
        return self._medicine_code

    @medicine_code.setter
    def medicine_code(self, value: str) -> None:
        self._medicine_code = _validate_text(value, "medicine_code")

    @property
    def name(self) -> str:
        """Return the medicine name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = _validate_text(value, "name")

    @property
    def unit_price(self) -> Decimal:
        """Return a finite, strictly positive Decimal price."""
        return self._unit_price

    @unit_price.setter
    def unit_price(self, value: PriceInput) -> None:
        if isinstance(value, bool) or not isinstance(
            value, (Decimal, int, float, str)
        ):
            raise TypeError(
                "unit_price must be a Decimal, integer, float, "
                "or numeric string."
            )
        try:
            price = (
                value if isinstance(value, Decimal) else Decimal(str(value))
            )
        except InvalidOperation as exc:
            raise ValueError("unit_price must be numeric.") from exc
        if not price.is_finite() or price <= 0:
            raise ValueError(
                "unit_price must be finite and greater than zero."
            )
        self._unit_price = price

    @property
    def reorder_level(self) -> int:
        """Return the non-negative integer reorder threshold."""
        return self._reorder_level

    @reorder_level.setter
    def reorder_level(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("reorder_level must be an integer, not a Boolean.")
        if value < 0:
            raise ValueError("reorder_level must be non-negative.")
        self._reorder_level = value

    @property
    def medicine_type(self) -> str:
        """Return the fixed database label for this medicine."""
        return self._medicine_type

    @abstractmethod
    def can_dispense(
        self,
        prescriber_code: str | None = None,
        authorised_prescribers: Collection[str] | None = None,
    ) -> bool:
        """Check prescriber authorization only, without dispensing stock."""


class OrdinaryMedicine(Medicine):
    """An ordinary medicine that needs no prescriber authorization."""

    def __init__(
        self,
        medicine_code: str,
        name: str,
        unit_price: PriceInput,
        reorder_level: int,
    ) -> None:
        super().__init__(
            medicine_code, name, unit_price, reorder_level, "ordinary"
        )

    def can_dispense(
        self,
        prescriber_code: str | None = None,
        authorised_prescribers: Collection[str] | None = None,
    ) -> bool:
        """Return True regardless of prescriber authorization inputs."""
        return True


class ControlledMedicine(Medicine):
    """A controlled medicine requiring an explicitly authorised prescriber."""

    def __init__(
        self,
        medicine_code: str,
        name: str,
        unit_price: PriceInput,
        reorder_level: int,
    ) -> None:
        super().__init__(
            medicine_code, name, unit_price, reorder_level, "controlled"
        )

    def can_dispense(
        self,
        prescriber_code: str | None = None,
        authorised_prescribers: Collection[str] | None = None,
    ) -> bool:
        """Match a non-blank code exactly against a supplied collection.

        Missing/invalid codes or a missing allow-list return False. Codes are
        case-sensitive and are not stripped, matching SQLite's default lookup.
        A malformed allow-list raises TypeError or ValueError rather than
        allowing accidental substring matching against a single string.
        """
        if not isinstance(prescriber_code, str) or not prescriber_code.strip():
            return False
        if authorised_prescribers is None:
            return False
        if isinstance(authorised_prescribers, (str, bytes)) or not isinstance(
            authorised_prescribers, Collection
        ):
            raise TypeError(
                "authorised_prescribers must be a collection of codes."
            )
        for code in authorised_prescribers:
            _validate_text(code, "authorised prescriber code")
        return prescriber_code in authorised_prescribers
