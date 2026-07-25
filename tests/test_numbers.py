"""Tests for paperforge.utils.numbers — number extraction and matching."""

from __future__ import annotations

from paperforge.utils.numbers import extract_numbers, numbers_match


def test_extract_percentage() -> None:
    result = extract_numbers("accuracy is 98.4%")
    assert len(result) == 1
    assert result[0].value == 98.4
    assert result[0].is_percentage is True


def test_extract_plain_number() -> None:
    result = extract_numbers("collected 12421 samples")
    assert len(result) == 1
    assert result[0].value == 12421.0
    assert result[0].is_percentage is False


def test_extract_comma_separated_number() -> None:
    result = extract_numbers("dataset has 12,421 records")
    assert len(result) == 1
    assert result[0].value == 12421.0


def test_extract_multiple_numbers() -> None:
    result = extract_numbers("98.4% accuracy and 97.1% precision")
    assert len(result) == 2
    values = {r.value for r in result}
    assert 98.4 in values
    assert 97.1 in values


def test_extract_empty_string() -> None:
    result = extract_numbers("")
    assert result == []


def test_extract_no_numbers() -> None:
    result = extract_numbers("no numbers here at all")
    assert result == []


def test_numbers_match_exact() -> None:
    assert numbers_match(98.4, 98.4) is True


def test_numbers_match_within_tolerance() -> None:
    assert numbers_match(98.4, 98.40) is True
    assert numbers_match(98.4, 98.41) is True


def test_numbers_match_outside_tolerance() -> None:
    assert numbers_match(98.4, 97.8) is False


def test_numbers_match_custom_tolerance() -> None:
    assert numbers_match(98.4, 98.0, tolerance=0.5) is True
    assert numbers_match(98.4, 97.8, tolerance=0.5) is False
