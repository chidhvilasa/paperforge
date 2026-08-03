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
    Examples: "98.4%", "12,421", "0.953", "14.2%", "500 samples"
    Strips commas from numbers like "12,421" -> 12421.0
    Returns list of ExtractedNumber, empty list if none found.
    """
    # Two alternatives in order of preference:
    # 1. Comma-grouped numbers like 12,421 or 1,234,567 (requires at least one comma group)
    # 2. Plain numbers: integers or decimals without commas
    # Followed by an optional % character.
    pattern = (
        r"\b"
        r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?"  # comma-grouped: 12,421 or 1,234.56
        r"|\d+(?:\.\d+)?)"  # plain: 12421 or 98.4
        r"(%?)"
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


# --- Structural references and identifier labels (domain-independent) ---
#
# These describe generic *kinds* of non-scientific numeric mentions that
# show up in research prose regardless of research domain: pointers to
# document structure ("Figure 1", "Section 3", "{{table:id}}") and generic
# experiment-configuration identifiers ("batch-50", "model-7", "version 2").
# None of the words below are specific to any one research field.

_STRUCTURAL_REFERENCE_RE = re.compile(
    r"(?i)\b(?:Figure|Fig\.|Section|Sec\.|Table|Eq\.|Equation|Algorithm)\s+\d+"
)
_SYMBOLIC_REFERENCE_RE = re.compile(r"\{\{[^}]+\}\}")
_IDENTIFIER_LABEL_RE = re.compile(
    r"(?i)\b(?:batch|model|protocol|version|sample|experiment|config(?:uration)?|"
    r"dataset|run|seed|trial|round|epoch|fold|split|node|worker|client|user|group|"
    r"cluster|shard|replica|instance|build|release)[\s-]*v?\d+(?:\.\d+)?\b"
)


def strip_reference_and_identifier_mentions(text: str) -> str:
    """Remove structural references and generic labeled identifiers from
    text, leaving only content that could plausibly be a measured
    scientific quantity.

    Removes things like "Figure 1", "Section 3", "{{table:id}}",
    "batch-50", "model-7", "protocol-v2", "version 2", "sample 10" -- none
    of which are scientific measurements even though they contain digits.
    """
    text = _STRUCTURAL_REFERENCE_RE.sub("", text)
    text = _SYMBOLIC_REFERENCE_RE.sub("", text)
    text = _IDENTIFIER_LABEL_RE.sub("", text)
    return text


# --- P-value syntax classification ---
#
# Recognizes explicit p-value syntax ("p = .05", "p<.01", "p-value of .03",
# "p value was 0.04") without relying on any domain-specific keyword list.

_PVALUE_SYNTAX_RE = re.compile(r"\bp\s*[=<>≤≥]\s*\.?\d+(?:\.\d+)?", re.IGNORECASE)
_PVALUE_PHRASE_RE = re.compile(
    r"\bp[\s-]?value\b\s*(?:of|was|is|:)?\s*[=<>≤≥]?\s*\.?\d+(?:\.\d+)?",
    re.IGNORECASE,
)


def find_pvalue_mentions(text: str) -> list[tuple[int, int]]:
    """Return merged (start, end) character spans of explicit p-value
    mentions in text, e.g. "p = .05", "p < 0.01", "p-value of .03",
    "p value was 0.04". Case-insensitive; accepts both '=' '<' '>' and the
    Unicode '≤' '≥' comparators, with or without a leading zero.
    """
    spans = [m.span() for m in _PVALUE_PHRASE_RE.finditer(text)]
    spans += [m.span() for m in _PVALUE_SYNTAX_RE.finditer(text)]
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
