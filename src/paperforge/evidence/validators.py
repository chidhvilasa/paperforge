"""Validators for evidence records and the graph as a whole.

Every function returns a list of issue dicts shaped like the rest of
PaperForge's validators (``code``/``severity``/``message``/``remediation``/
``evidence_id``) so callers can feed them straight into a
:class:`~paperforge.utils.envelope.ResultEnvelope`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge.evidence import formula as formula_mod
from paperforge.evidence.graph import (
    CycleReport,
    compute_staleness,
    detect_cycles,
    find_missing_references,
)
from paperforge.evidence.models import (
    CORRECTION_FAMILIES,
    REVIEW_STATUSES,
    ROUNDING_MODES,
    VALUE_TYPES,
    DerivedEvidence,
    DirectEvidence,
    StatisticalEvidence,
)
from paperforge.evidence.store import EvidenceStore
from paperforge.evidence.units import UnitError, check_addable

# Effect sizes with a known, checkable numeric range. Anything else is
# accepted without a range check (we do not maintain an exhaustive
# taxonomy of every effect size in existence).
_EFFECT_SIZE_RANGES: dict[str, tuple[float, float]] = {
    "pearson_r": (-1.0, 1.0),
    "spearman_rho": (-1.0, 1.0),
    "eta_squared": (0.0, 1.0),
    "partial_eta_squared": (0.0, 1.0),
    "r_squared": (0.0, 1.0),
}

_KNOWN_TEST_NAMES = frozenset(
    {
        "paired_t_test",
        "independent_t_test",
        "wilcoxon_signed_rank",
        "mann_whitney_u",
        "pearson_correlation",
        "spearman_correlation",
        "chi_square",
        "anova",
        "other",
    }
)


def _issue(
    code: str,
    message: str,
    *,
    evidence_id: str = "",
    severity: str = "ERROR",
    remediation: str = "",
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "evidence_id": evidence_id,
        "remediation": remediation,
    }


def validate_direct(ev: DirectEvidence) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not ev.id:
        issues.append(_issue("EVIDENCE_MISSING_ID", "Direct evidence has no id."))
    if ev.value_type not in VALUE_TYPES:
        issues.append(
            _issue(
                "EVIDENCE_INVALID_VALUE_TYPE",
                f"'{ev.value_type}' is not one of {sorted(VALUE_TYPES)}.",
                evidence_id=ev.id,
            )
        )
    if ev.type != "manual" and not ev.source_path:
        issues.append(
            _issue(
                "EVIDENCE_MISSING_SOURCE_PATH",
                f"Direct evidence '{ev.id}' has type='{ev.type}' but no source_path.",
                evidence_id=ev.id,
                remediation="Set source_path, or use type='manual' for an author-supplied value.",
            )
        )
    if ev.type != "manual" and not ev.source_locator:
        issues.append(
            _issue(
                "EVIDENCE_MISSING_SOURCE_LOCATOR",
                f"Direct evidence '{ev.id}' has no source_locator.",
                evidence_id=ev.id,
            )
        )
    if ev.value is None:
        issues.append(
            _issue(
                "EVIDENCE_MISSING_VALUE",
                f"Direct evidence '{ev.id}' has no value.",
                evidence_id=ev.id,
            )
        )
    if (
        ev.value_type == "number"
        and ev.value is not None
        and (isinstance(ev.value, bool) or not isinstance(ev.value, int | float))
    ):
        issues.append(
            _issue(
                "EVIDENCE_VALUE_TYPE_MISMATCH",
                f"'{ev.id}' declares value_type=number but value is {type(ev.value).__name__}.",
                evidence_id=ev.id,
            )
        )
    if ev.sample_size is not None and ev.sample_size < 0:
        issues.append(
            _issue(
                "EVIDENCE_INVALID_SAMPLE_SIZE",
                f"'{ev.id}' has a negative sample_size.",
                evidence_id=ev.id,
            )
        )
    if ev.author_review_status not in REVIEW_STATUSES:
        issues.append(
            _issue(
                "EVIDENCE_INVALID_REVIEW_STATUS",
                f"'{ev.author_review_status}' is not one of {sorted(REVIEW_STATUSES)}.",
                evidence_id=ev.id,
            )
        )
    return issues


def validate_derived_formula(
    ev: DerivedEvidence, store: EvidenceStore
) -> list[dict[str, Any]]:
    """Validate formula safety, operand existence, and obvious unit
    incompatibilities -- does NOT evaluate the formula (that happens when
    the evidence is recorded/recomputed)."""

    issues: list[dict[str, Any]] = []
    try:
        tree = formula_mod.parse_and_validate(ev.formula)
    except formula_mod.FormulaSecurityError as exc:
        issues.append(
            _issue(
                "EVIDENCE_UNSAFE_FORMULA",
                str(exc),
                evidence_id=ev.id,
                remediation="Use only +,-,*,/,** with a bounded literal exponent, parentheses, and numeric operand names.",
            )
        )
        return issues

    referenced = formula_mod.referenced_names(ev.formula)
    declared = set(ev.operand_ids)
    for name in referenced - declared:
        issues.append(
            _issue(
                "EVIDENCE_UNDECLARED_OPERAND",
                f"Formula references '{name}' but it is not listed in operand_ids.",
                evidence_id=ev.id,
            )
        )
    for op in ev.operand_ids:
        if op not in store.all_ids() and op != ev.id:
            issues.append(
                _issue(
                    "EVIDENCE_MISSING_OPERAND",
                    f"Operand '{op}' does not exist in the evidence store.",
                    evidence_id=ev.id,
                )
            )

    # Bounded unit check: reject top-level Add/Sub between two operands
    # whose declared units are known and incompatible.
    def unit_of(name: str) -> str | None:
        if name in store.direct:
            return store.direct[name].unit or ""
        if name in store.derived:
            return store.derived[name].unit or ""
        return None

    import ast

    def walk(node: ast.AST) -> str | None:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Name):
            return unit_of(node.id)
        if isinstance(node, ast.Constant):
            return None  # bare numeric literal: no declared unit
        if isinstance(node, ast.BinOp):
            left_unit = walk(node.left)
            right_unit = walk(node.right)
            if isinstance(node.op, ast.Add | ast.Sub):
                check = check_addable(left_unit, right_unit)
                if not check.ok:
                    issues.append(
                        _issue(
                            "EVIDENCE_INCOMPATIBLE_UNITS",
                            check.reason,
                            evidence_id=ev.id,
                        )
                    )
                return left_unit if left_unit is not None else right_unit
            return None  # Mult/Div/Pow: result unit is author-declared, not inferred
        if isinstance(node, ast.UnaryOp):
            return walk(node.operand)
        if isinstance(node, ast.Call):
            return None
        return None

    try:
        walk(tree)
    except UnitError:
        pass

    if ev.rounding not in ROUNDING_MODES:
        issues.append(
            _issue(
                "EVIDENCE_INVALID_ROUNDING",
                f"'{ev.rounding}' is not one of {sorted(ROUNDING_MODES)}.",
                evidence_id=ev.id,
            )
        )
    if ev.author_review_status not in REVIEW_STATUSES:
        issues.append(
            _issue(
                "EVIDENCE_INVALID_REVIEW_STATUS",
                f"'{ev.author_review_status}' is not one of {sorted(REVIEW_STATUSES)}.",
                evidence_id=ev.id,
            )
        )
    return issues


def validate_statistical(ev: StatisticalEvidence) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not ev.test_name:
        issues.append(
            _issue(
                "EVIDENCE_MISSING_TEST_NAME",
                f"'{ev.id}' has no test_name.",
                evidence_id=ev.id,
            )
        )

    if ev.p_value is not None and not (0.0 <= ev.p_value <= 1.0):
        issues.append(
            _issue(
                "EVIDENCE_INVALID_P_VALUE",
                f"p_value {ev.p_value} is not in [0, 1].",
                evidence_id=ev.id,
            )
        )
    if ev.adjusted_p_value is not None and not (0.0 <= ev.adjusted_p_value <= 1.0):
        issues.append(
            _issue(
                "EVIDENCE_INVALID_ADJUSTED_P_VALUE",
                f"adjusted_p_value {ev.adjusted_p_value} is not in [0, 1].",
                evidence_id=ev.id,
            )
        )
    if ev.sample_size is not None and ev.sample_size <= 0:
        issues.append(
            _issue(
                "EVIDENCE_INVALID_SAMPLE_SIZE",
                f"sample_size {ev.sample_size} must be positive.",
                evidence_id=ev.id,
            )
        )
    if not (0.0 < ev.alpha < 1.0):
        issues.append(
            _issue(
                "EVIDENCE_INVALID_ALPHA",
                f"alpha {ev.alpha} is not in (0, 1).",
                evidence_id=ev.id,
            )
        )
    if ev.correction_family not in CORRECTION_FAMILIES:
        issues.append(
            _issue(
                "EVIDENCE_INVALID_CORRECTION_FAMILY",
                f"'{ev.correction_family}' is not one of {sorted(CORRECTION_FAMILIES)}.",
                evidence_id=ev.id,
            )
        )
    if (
        ev.correction_family != "none"
        and ev.p_value is not None
        and ev.adjusted_p_value is None
    ):
        issues.append(
            _issue(
                "EVIDENCE_MISSING_ADJUSTED_P_VALUE",
                f"'{ev.id}' declares correction_family='{ev.correction_family}' but has no adjusted_p_value.",
                evidence_id=ev.id,
                severity="WARNING",
            )
        )
    if ev.paired and len(ev.groups) not in (0, 2):
        issues.append(
            _issue(
                "EVIDENCE_PAIRED_GROUP_COUNT",
                f"Paired test '{ev.id}' must have exactly 2 groups, got {len(ev.groups)}.",
                evidence_id=ev.id,
            )
        )
    if ev.confidence_interval:
        if len(ev.confidence_interval) != 2:
            issues.append(
                _issue(
                    "EVIDENCE_INVALID_INTERVAL",
                    f"confidence_interval must have exactly 2 values, got {len(ev.confidence_interval)}.",
                    evidence_id=ev.id,
                )
            )
        elif ev.confidence_interval[0] > ev.confidence_interval[1]:
            issues.append(
                _issue(
                    "EVIDENCE_INTERVAL_ORDER",
                    f"confidence_interval lower bound {ev.confidence_interval[0]} exceeds upper bound {ev.confidence_interval[1]}.",
                    evidence_id=ev.id,
                )
            )
    if ev.effect_size_name:
        if ev.effect_size_value is None:
            issues.append(
                _issue(
                    "EVIDENCE_MISSING_EFFECT_SIZE_VALUE",
                    f"'{ev.id}' names effect_size '{ev.effect_size_name}' but has no value.",
                    evidence_id=ev.id,
                )
            )
        else:
            bounds = _EFFECT_SIZE_RANGES.get(ev.effect_size_name)
            if bounds and not (bounds[0] <= ev.effect_size_value <= bounds[1]):
                issues.append(
                    _issue(
                        "EVIDENCE_EFFECT_SIZE_OUT_OF_RANGE",
                        f"{ev.effect_size_name}={ev.effect_size_value} is outside the valid range {bounds}.",
                        evidence_id=ev.id,
                    )
                )
    if ev.author_review_status not in REVIEW_STATUSES:
        issues.append(
            _issue(
                "EVIDENCE_INVALID_REVIEW_STATUS",
                f"'{ev.author_review_status}' is not one of {sorted(REVIEW_STATUSES)}.",
                evidence_id=ev.id,
            )
        )
    if ev.p_value is None and ev.statistic is None and ev.effect_size_value is None:
        issues.append(
            _issue(
                "EVIDENCE_STATISTICAL_RESULT_EMPTY",
                f"'{ev.id}' records no statistic, p_value, or effect size -- nothing to validate.",
                evidence_id=ev.id,
                severity="WARNING",
            )
        )
    return issues


def validate_store(project_root: Path, store: EvidenceStore) -> list[dict[str, Any]]:
    """Full-graph validation: per-record checks plus cycles, missing
    references, and staleness."""

    issues: list[dict[str, Any]] = []
    for direct_ev in store.direct.values():
        issues.extend(validate_direct(direct_ev))
    for derived_ev in store.derived.values():
        issues.extend(validate_derived_formula(derived_ev, store))
    for stat_ev in store.statistical.values():
        issues.extend(validate_statistical(stat_ev))

    cycles: CycleReport = detect_cycles(store)
    for cycle in cycles.cycles:
        issues.append(
            _issue(
                "EVIDENCE_DEPENDENCY_CYCLE",
                f"Cyclic derived-evidence dependency: {' -> '.join(cycle)}.",
                evidence_id=cycle[0] if cycle else "",
            )
        )

    for missing in find_missing_references(store):
        issues.append(
            _issue(
                "EVIDENCE_MISSING_REFERENCE",
                f"'{missing.referencing_id}' ({missing.referencing_kind}) references unknown evidence '{missing.missing_id}'.",
                evidence_id=missing.referencing_id,
            )
        )

    if not cycles.has_cycles:
        staleness = compute_staleness(project_root, store)
        for eid, reason in staleness.stale_direct.items():
            issues.append(
                _issue(
                    "EVIDENCE_STALE_DIRECT", reason, evidence_id=eid, severity="ERROR"
                )
            )
        for eid, reason in staleness.stale_derived.items():
            issues.append(
                _issue(
                    "EVIDENCE_STALE_DERIVED", reason, evidence_id=eid, severity="ERROR"
                )
            )
        for eid, reason in staleness.stale_statistical.items():
            issues.append(
                _issue(
                    "EVIDENCE_STALE_STATISTICAL",
                    reason,
                    evidence_id=eid,
                    severity="ERROR",
                )
            )
        for eid, reason in staleness.unreadable_sources.items():
            issues.append(
                _issue(
                    "EVIDENCE_SOURCE_UNREADABLE",
                    reason,
                    evidence_id=eid,
                    severity="ERROR",
                )
            )

    return issues


__all__ = [
    "validate_derived_formula",
    "validate_direct",
    "validate_statistical",
    "validate_store",
]
