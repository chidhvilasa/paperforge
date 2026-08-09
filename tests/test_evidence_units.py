"""Tests for the bounded unit registry (paperforge.evidence.units)."""

from __future__ import annotations

import pytest

from paperforge.evidence.units import (
    UnitError,
    category_of,
    check_addable,
    convert,
    units_compatible,
)


def test_same_category_compatible() -> None:
    assert units_compatible("seconds", "milliseconds")
    assert units_compatible("ms", "microseconds")


def test_incompatible_categories() -> None:
    assert not units_compatible("milliseconds", "percent")
    assert not units_compatible("bytes", "seconds")


def test_seconds_to_milliseconds_conversion() -> None:
    assert convert(1.0, "seconds", "milliseconds") == pytest.approx(1000.0)
    assert convert(1500.0, "milliseconds", "seconds") == pytest.approx(1.5)


def test_megabytes_to_bytes_conversion() -> None:
    assert convert(2.0, "megabytes", "bytes") == pytest.approx(2_000_000.0)


def test_conversion_between_incompatible_units_raises() -> None:
    with pytest.raises(UnitError):
        convert(1.0, "seconds", "bytes")


def test_conversion_with_unknown_unit_raises() -> None:
    with pytest.raises(UnitError):
        convert(1.0, "seconds", "furlongs")


def test_check_addable_rejects_ms_plus_percent() -> None:
    result = check_addable("milliseconds", "percent")
    assert not result.ok
    assert "incompatible" in result.reason.lower()


def test_check_addable_allows_same_category() -> None:
    assert check_addable("seconds", "milliseconds").ok


def test_check_addable_allows_bare_numeric_literal() -> None:
    assert check_addable(None, "milliseconds").ok


def test_unknown_unit_is_its_own_category() -> None:
    assert category_of("furlongs") != category_of("percent")
    assert category_of("furlongs") == category_of("furlongs")
