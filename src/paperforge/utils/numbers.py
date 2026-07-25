"""Number extraction and matching utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ExtractedNumber:
    raw: str  # original string as it appeared, e.g. "98.4%"
    value: float  # parsed float, e.g. 98.4
    is_percentage: bool


def extract_numbers(text: str) -> list[ExtractedNumber]:
    """Extract all numeric values from a string.

    Handles: integers, decimals, percentages.
    Examples: "98.4%", "12,421", "0.953", "14.2%", "500 vehicles"
    Strips commas from numbers like "12,421" -> 12421.0
    Returns list of ExtractedNumber, empty list if none found.
    """
    # Two alternatives in order of preference:
    # 1. Comma-grouped numbers like 12,421 or 1,234,567 (requires at least one comma group)
    # 2. Plain numbers: integers or decimals without commas
    # Followed by an optional % character.
    pattern = (
        r'\b'
        r'(\d{1,3}(?:,\d{3})+(?:\.\d+)?'  # comma-grouped: 12,421 or 1,234.56
        r'|\d+(?:\.\d+)?)'                  # plain: 12421 or 98.4
        r'(%?)'
    )
    results = []
    for match in re.finditer(pattern, text):
        raw_num = match.group(1).replace(",", "")
        is_pct = match.group(2) == "%"
        try:
            value = float(raw_num)
            raw = match.group(0)
            results.append(ExtractedNumber(raw=raw, value=value, is_percentage=is_pct))
        except ValueError:
            continue
    return results




def numbers_match(a: float, b: float, tolerance: float = 0.01) -> bool:
    """Return True if two floats are within tolerance of each other.

    Default tolerance: 0.01 (handles rounding like 98.4 vs 98.40).
    """
    return abs(a - b) <= tolerance
