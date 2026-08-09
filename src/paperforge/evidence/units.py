"""A small, bounded unit registry.

Not a symbolic algebra engine. Just enough to (a) group units into
compatibility categories so obviously-wrong operations like
``milliseconds + percent`` can be rejected, and (b) perform a handful of
deterministic, exact conversions (time, bytes) that are actually useful for
research evidence. Unknown unit strings are accepted (so authors are never
blocked from recording a value in a unit we haven't heard of) but are
treated as their own singleton category, incompatible with everything else
except an identical string and with themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

#: Canonical category name for each known unit string. Unknown unit
#: strings are not errors -- see :func:`category_of`.
_CATEGORY: dict[str, str] = {
    "": "dimensionless",
    "dimensionless": "dimensionless",
    "count": "count",
    "percent": "percent",
    "%": "percent",
    "ratio": "ratio",
    "seconds": "time",
    "s": "time",
    "milliseconds": "time",
    "ms": "time",
    "microseconds": "time",
    "us": "time",
    "μs": "time",
    "bytes": "data_size",
    "B": "data_size",
    "kilobytes": "data_size",
    "KB": "data_size",
    "megabytes": "data_size",
    "MB": "data_size",
    "messages/second": "rate",
    "msg/s": "rate",
    "operations/second": "rate",
    "ops/s": "rate",
}

#: Exact conversion factor to the category's base unit, as a Fraction so
#: repeated conversions stay exact (no float drift).
_TO_BASE: dict[str, Fraction] = {
    # time -> base unit: seconds
    "seconds": Fraction(1),
    "s": Fraction(1),
    "milliseconds": Fraction(1, 1_000),
    "ms": Fraction(1, 1_000),
    "microseconds": Fraction(1, 1_000_000),
    "us": Fraction(1, 1_000_000),
    "μs": Fraction(1, 1_000_000),
    # data_size -> base unit: bytes
    "bytes": Fraction(1),
    "B": Fraction(1),
    "kilobytes": Fraction(1000),
    "KB": Fraction(1000),
    "megabytes": Fraction(1_000_000),
    "MB": Fraction(1_000_000),
}


class UnitError(ValueError):
    """Raised for an incompatible or unrecognized unit operation."""


def category_of(unit: str) -> str:
    """Return the compatibility category for ``unit``.

    Known units map to a shared category (``time``, ``data_size``, ...).
    An unrecognized unit string maps to its own category
    (``"unknown:<unit>"``) so it is compatible with itself but with
    nothing else -- we never silently guess that two unfamiliar unit
    strings mean the same thing.
    """

    unit = (unit or "").strip()
    if unit in _CATEGORY:
        return _CATEGORY[unit]
    return f"unknown:{unit}"


def units_compatible(unit_a: str, unit_b: str) -> bool:
    """True if values in these two units may be added/subtracted directly."""

    return category_of(unit_a) == category_of(unit_b)


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert ``value`` from ``from_unit`` to ``to_unit``.

    Only defined within a known category that has base-unit factors
    (currently ``time`` and ``data_size``). Raises :class:`UnitError` for
    any other pair, including two categorically-compatible-but-unknown
    units, rather than guessing.
    """

    from_unit = (from_unit or "").strip()
    to_unit = (to_unit or "").strip()
    if from_unit == to_unit:
        return value
    if from_unit not in _TO_BASE or to_unit not in _TO_BASE:
        raise UnitError(
            f"No deterministic conversion is defined from '{from_unit}' to '{to_unit}'."
        )
    cat_a, cat_b = category_of(from_unit), category_of(to_unit)
    if cat_a != cat_b:
        raise UnitError(
            f"'{from_unit}' ({cat_a}) and '{to_unit}' ({cat_b}) are not the same "
            "kind of unit."
        )
    base = Fraction(value) * _TO_BASE[from_unit]
    result = base / _TO_BASE[to_unit]
    return float(result)


@dataclass(frozen=True)
class UnitCheckResult:
    ok: bool
    reason: str = ""


def check_addable(unit_a: str | None, unit_b: str | None) -> UnitCheckResult:
    """Check whether two units may be combined with ``+``/``-``.

    A bare numeric literal (represented by the caller passing ``unit=None``)
    is always compatible -- ``latency_ms + 5`` is not a unit error, it is
    an author decision about a raw offset.
    """

    if unit_a is None or unit_b is None:
        return UnitCheckResult(ok=True)
    if units_compatible(unit_a, unit_b):
        return UnitCheckResult(ok=True)
    return UnitCheckResult(
        ok=False,
        reason=(
            f"Cannot combine incompatible units '{unit_a}' "
            f"({category_of(unit_a)}) and '{unit_b}' ({category_of(unit_b)})."
        ),
    )


KNOWN_UNITS: frozenset[str] = frozenset(_CATEGORY)

__all__ = [
    "KNOWN_UNITS",
    "UnitCheckResult",
    "UnitError",
    "category_of",
    "check_addable",
    "convert",
    "units_compatible",
]
