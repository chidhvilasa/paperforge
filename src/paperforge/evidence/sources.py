"""Deterministic, non-executing extraction of a single value from a data file.

Only three source kinds are supported, all via safe stdlib parsers -- never
``exec``, never importing the target project, never running notebooks or
scripts:

- ``csv``   -- locator ``row=<0-based data row>;col=<header name>``
- ``json``  -- locator is a dotted path with optional ``[index]`` segments,
               e.g. ``results.latency.mean`` or ``results[0].latency``
- ``yaml``  -- same dotted-path locator, parsed with ``yaml.safe_load``
- ``manual``-- no source file; the value is supplied directly by the author

Every extractor returns the raw value plus the exact bytes that were hashed
for :attr:`DirectEvidence.content_hash`, so later staleness checks compare
against the identical byte sequence.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from paperforge.evidence.models import sha256_bytes

_PATH_SEGMENT_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


class SourceExtractionError(ValueError):
    pass


def _read_bytes(path: Path, *, max_size: int = 50_000_000) -> bytes:
    if not path.exists():
        raise SourceExtractionError(f"Source file not found: {path}")
    if not path.is_file():
        raise SourceExtractionError(f"Source path is not a regular file: {path}")
    size = path.stat().st_size
    if size > max_size:
        raise SourceExtractionError(
            f"Source file '{path}' is {size} bytes, exceeding the {max_size}-byte "
            "limit for direct-evidence extraction."
        )
    return path.read_bytes()


def _parse_dotted_path(locator: str) -> list[str | int]:
    segments: list[str | int] = []
    for m in _PATH_SEGMENT_RE.finditer(locator):
        name, idx = m.group(1), m.group(2)
        if idx is not None:
            segments.append(int(idx))
        elif name:
            segments.append(name)
    if not segments:
        raise SourceExtractionError(f"Could not parse path locator '{locator}'.")
    return segments


def _walk_path(data: Any, segments: list[str | int], locator: str) -> Any:
    current = data
    for seg in segments:
        if isinstance(seg, int):
            if not isinstance(current, list) or seg >= len(current):
                raise SourceExtractionError(
                    f"Locator '{locator}': index [{seg}] not found."
                )
            current = current[seg]
        else:
            if not isinstance(current, dict) or seg not in current:
                raise SourceExtractionError(
                    f"Locator '{locator}': key '{seg}' not found."
                )
            current = current[seg]
    return current


def extract_csv(path: Path, locator: str) -> tuple[Any, bytes]:
    """locator: ``row=<n>;col=<header>`` (row is 0-based over data rows,
    excluding the header row)."""

    raw = _read_bytes(path)
    parts = dict(p.split("=", 1) for p in locator.split(";") if "=" in p)
    if "row" not in parts or "col" not in parts:
        raise SourceExtractionError(
            f"CSV locator must look like 'row=0;col=latency_ms', got '{locator}'."
        )
    row_idx = int(parts["row"])
    col_name = parts["col"]
    text = raw.decode("utf-8", errors="strict")
    reader = csv.DictReader(text.splitlines())
    if col_name not in (reader.fieldnames or []):
        raise SourceExtractionError(
            f"CSV column '{col_name}' not found in {path} (columns: {reader.fieldnames})."
        )
    rows = list(reader)
    if row_idx < 0 or row_idx >= len(rows):
        raise SourceExtractionError(
            f"CSV row {row_idx} out of range for {path} ({len(rows)} data rows)."
        )
    raw_value = rows[row_idx][col_name]
    try:
        value: Any = int(raw_value)
    except ValueError:
        try:
            value = float(raw_value)
        except ValueError:
            value = raw_value
    return value, raw


def extract_json(path: Path, locator: str) -> tuple[Any, bytes]:
    raw = _read_bytes(path)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceExtractionError(f"Could not parse JSON from {path}: {exc}") from exc
    segments = _parse_dotted_path(locator)
    return _walk_path(data, segments, locator), raw


def extract_yaml(path: Path, locator: str) -> tuple[Any, bytes]:
    import yaml

    raw = _read_bytes(path)
    try:
        data = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise SourceExtractionError(f"Could not parse YAML from {path}: {exc}") from exc
    segments = _parse_dotted_path(locator)
    return _walk_path(data, segments, locator), raw


def extract(source_type: str, path: Path, locator: str) -> tuple[Any, str]:
    """Extract a value and return ``(value, content_hash)``.

    ``content_hash`` is the sha256 of the *entire source file's raw bytes*
    at extraction time -- deliberately coarse (not just the extracted
    cell/path) so any edit to the source file, not only the exact cell
    read, is detected as staleness.
    """

    if source_type == "csv":
        value, raw = extract_csv(path, locator)
    elif source_type == "json":
        value, raw = extract_json(path, locator)
    elif source_type == "yaml":
        value, raw = extract_yaml(path, locator)
    else:
        raise SourceExtractionError(f"Unknown source type '{source_type}'.")
    return value, sha256_bytes(raw)


def current_source_hash(source_type: str, path: Path) -> str:
    """Recompute the hash of a source file as it exists right now, for
    staleness comparison against a recorded ``content_hash``."""

    if source_type == "manual":
        raise SourceExtractionError("Manual evidence has no source file to hash.")
    raw = _read_bytes(path)
    return sha256_bytes(raw)


__all__ = [
    "SourceExtractionError",
    "current_source_hash",
    "extract",
    "extract_csv",
    "extract_json",
    "extract_yaml",
]
