"""Typed models for the three evidence kinds.

None of these dataclasses ever fabricate a value: every field is either
supplied verbatim by an author/agent, extracted deterministically from a
named location in a named source file (see
:mod:`paperforge.evidence.sources`), or computed from other evidence by the
sandboxed evaluator in :mod:`paperforge.evidence.formula`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Any

#: Author-review lifecycle shared by every evidence kind and by provenance
#: records. Mirrors the states already used for provenance
#: ``author_review_status`` in 1.7.0 (`pending`, `reviewed`, `approved`) but
#: adds `rejected` for the explicit reject workflow in Phase 9.
REVIEW_STATUSES = frozenset({"pending", "reviewed", "approved", "rejected"})

VALUE_TYPES = frozenset({"number", "string", "bool"})

ROUNDING_MODES = frozenset({"half_up", "half_even", "floor", "ceil", "none"})

CORRECTION_FAMILIES = frozenset({"none", "bonferroni", "holm"})


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_DECIMAL_ROUNDING = {
    "half_up": ROUND_HALF_UP,
    "half_even": ROUND_HALF_EVEN,
    "floor": ROUND_FLOOR,
    "ceil": ROUND_CEILING,
}


def apply_precision(value: float, precision: int | None, rounding: str) -> float:
    """Round ``value`` to ``precision`` decimal digits using exact Decimal
    arithmetic (never float rounding, which can surprise for values like
    ``2.675``). ``rounding='none'`` or ``precision=None`` returns ``value``
    unchanged -- intermediate results are never silently rounded."""

    if precision is None or rounding == "none":
        return value
    if rounding not in _DECIMAL_ROUNDING:
        raise ValueError(f"Unknown rounding mode '{rounding}'.")
    quant = Decimal(1).scaleb(-precision)
    result = Decimal(str(value)).quantize(quant, rounding=_DECIMAL_ROUNDING[rounding])
    return float(result)


@dataclass
class DirectEvidence:
    id: str
    type: str = "manual"  # csv | json | yaml | manual
    source_path: str = ""
    source_locator: str = ""
    content_hash: str = ""
    value: Any = None
    value_type: str = "number"
    unit: str = ""
    sample_size: int | None = None
    observations_count: int | None = None
    collection_metadata: dict[str, Any] = field(default_factory=dict)
    source_timestamp: str = ""
    author_review_status: str = "pending"
    notes: str = ""
    recorded_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "source_path": self.source_path,
            "source_locator": self.source_locator,
            "content_hash": self.content_hash,
            "value": self.value,
            "value_type": self.value_type,
            "unit": self.unit,
            "sample_size": self.sample_size,
            "observations_count": self.observations_count,
            "collection_metadata": dict(self.collection_metadata),
            "source_timestamp": self.source_timestamp,
            "author_review_status": self.author_review_status,
            "notes": self.notes,
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DirectEvidence:
        return cls(
            id=str(data.get("id", "")),
            type=str(data.get("type", "manual")),
            source_path=str(data.get("source_path", "")),
            source_locator=str(data.get("source_locator", "")),
            content_hash=str(data.get("content_hash", "")),
            value=data.get("value"),
            value_type=str(data.get("value_type", "number")),
            unit=str(data.get("unit", "")),
            sample_size=data.get("sample_size"),
            observations_count=data.get("observations_count"),
            collection_metadata=dict(data.get("collection_metadata") or {}),
            source_timestamp=str(data.get("source_timestamp", "")),
            author_review_status=str(data.get("author_review_status", "pending")),
            notes=str(data.get("notes", "")),
            recorded_at=str(data.get("recorded_at", "")) or _now_iso(),
        )

    def numeric_value(self) -> float:
        if self.value_type != "number":
            raise ValueError(
                f"Direct evidence '{self.id}' is not numeric (value_type={self.value_type})."
            )
        if isinstance(self.value, bool) or not isinstance(self.value, int | float):
            # Deliberately ValueError, not TypeError: this is a domain-data
            # validation error (a recorded evidence value doesn't match its
            # own declared value_type), not a Python calling-convention error.
            raise ValueError(f"Direct evidence '{self.id}' has a non-numeric value.")  # noqa: TRY004
        return float(self.value)


@dataclass
class DerivedEvidence:
    id: str
    formula: str = ""
    operand_ids: list[str] = field(default_factory=list)
    result: float | None = None
    unit: str = ""
    precision: int | None = None
    rounding: str = "half_up"
    dependency_hash: str = ""
    author_review_status: str = "pending"
    notes: str = ""
    recorded_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "formula": self.formula,
            "operand_ids": list(self.operand_ids),
            "result": self.result,
            "unit": self.unit,
            "precision": self.precision,
            "rounding": self.rounding,
            "dependency_hash": self.dependency_hash,
            "author_review_status": self.author_review_status,
            "notes": self.notes,
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DerivedEvidence:
        return cls(
            id=str(data.get("id", "")),
            formula=str(data.get("formula", "")),
            operand_ids=list(data.get("operand_ids") or []),
            result=data.get("result"),
            unit=str(data.get("unit", "")),
            precision=data.get("precision"),
            rounding=str(data.get("rounding", "half_up")),
            dependency_hash=str(data.get("dependency_hash", "")),
            author_review_status=str(data.get("author_review_status", "pending")),
            notes=str(data.get("notes", "")),
            recorded_at=str(data.get("recorded_at", "")) or _now_iso(),
        )


@dataclass
class StatisticalEvidence:
    id: str
    test_name: str = ""
    hypothesis_null: str = ""
    hypothesis_alternative: str = ""
    paired: bool = False
    sample_size: int | None = None
    groups: list[str] = field(default_factory=list)
    observation_refs: list[str] = field(default_factory=list)
    statistic: float | None = None
    p_value: float | None = None
    adjusted_p_value: float | None = None
    correction_family: str = "none"
    correction_method: str = ""
    effect_size_name: str = ""
    effect_size_value: float | None = None
    confidence_interval: list[float] = field(default_factory=list)
    alpha: float = 0.05
    assumptions: list[str] = field(default_factory=list)
    software: str = ""
    software_version: str = ""
    author_review_status: str = "pending"
    dependency_hash: str = ""
    notes: str = ""
    recorded_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "test_name": self.test_name,
            "hypothesis_null": self.hypothesis_null,
            "hypothesis_alternative": self.hypothesis_alternative,
            "paired": self.paired,
            "sample_size": self.sample_size,
            "groups": list(self.groups),
            "observation_refs": list(self.observation_refs),
            "statistic": self.statistic,
            "p_value": self.p_value,
            "adjusted_p_value": self.adjusted_p_value,
            "correction_family": self.correction_family,
            "correction_method": self.correction_method,
            "effect_size_name": self.effect_size_name,
            "effect_size_value": self.effect_size_value,
            "confidence_interval": list(self.confidence_interval),
            "alpha": self.alpha,
            "assumptions": list(self.assumptions),
            "software": self.software,
            "software_version": self.software_version,
            "author_review_status": self.author_review_status,
            "dependency_hash": self.dependency_hash,
            "notes": self.notes,
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatisticalEvidence:
        return cls(
            id=str(data.get("id", "")),
            test_name=str(data.get("test_name", "")),
            hypothesis_null=str(data.get("hypothesis_null", "")),
            hypothesis_alternative=str(data.get("hypothesis_alternative", "")),
            paired=bool(data.get("paired", False)),
            sample_size=data.get("sample_size"),
            groups=list(data.get("groups") or []),
            observation_refs=list(data.get("observation_refs") or []),
            statistic=data.get("statistic"),
            p_value=data.get("p_value"),
            adjusted_p_value=data.get("adjusted_p_value"),
            correction_family=str(data.get("correction_family", "none")),
            correction_method=str(data.get("correction_method", "")),
            effect_size_name=str(data.get("effect_size_name", "")),
            effect_size_value=data.get("effect_size_value"),
            confidence_interval=list(data.get("confidence_interval") or []),
            alpha=float(data.get("alpha", 0.05)),
            assumptions=list(data.get("assumptions") or []),
            software=str(data.get("software", "")),
            software_version=str(data.get("software_version", "")),
            author_review_status=str(data.get("author_review_status", "pending")),
            dependency_hash=str(data.get("dependency_hash", "")),
            notes=str(data.get("notes", "")),
            recorded_at=str(data.get("recorded_at", "")) or _now_iso(),
        )


# --- Multiple-comparison correction families -------------------------------
#
# Both operate on an ordered list of raw p-values and return adjusted
# p-values in the *same order* (pure functions, no hidden state, no test
# selection -- the caller supplies the p-values and the family; nothing here
# ever runs a statistical test itself).


def bonferroni_correction(p_values: list[float]) -> list[float]:
    n = len(p_values)
    return [min(1.0, p * n) for p in p_values]


def holm_correction(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni step-down correction.

    Returns adjusted p-values in the *original* input order (monotonically
    enforced, as is standard for Holm: each adjusted p-value is at least as
    large as the previous one in sorted-rank order).
    """

    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted_sorted = []
    running_max = 0.0
    for rank, idx in enumerate(order):
        candidate = (n - rank) * p_values[idx]
        running_max = max(running_max, candidate)
        adjusted_sorted.append(min(1.0, running_max))
    result = [0.0] * n
    for rank, idx in enumerate(order):
        result[idx] = adjusted_sorted[rank]
    return result


def apply_correction(family: str, p_values: list[float]) -> list[float]:
    if family == "bonferroni":
        return bonferroni_correction(p_values)
    if family == "holm":
        return holm_correction(p_values)
    if family == "none":
        return list(p_values)
    raise ValueError(f"Unknown correction family '{family}'.")


__all__ = [
    "CORRECTION_FAMILIES",
    "REVIEW_STATUSES",
    "ROUNDING_MODES",
    "VALUE_TYPES",
    "DerivedEvidence",
    "DirectEvidence",
    "StatisticalEvidence",
    "apply_correction",
    "apply_precision",
    "bonferroni_correction",
    "holm_correction",
    "sha256_bytes",
    "sha256_text",
]
