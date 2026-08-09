"""Tests for evidence dataclasses, correction families, and validators."""

from __future__ import annotations

import pytest

from paperforge.evidence.models import (
    DerivedEvidence,
    DirectEvidence,
    StatisticalEvidence,
    apply_precision,
    bonferroni_correction,
    holm_correction,
)
from paperforge.evidence.store import EvidenceStore
from paperforge.evidence.validators import (
    validate_derived_formula,
    validate_direct,
    validate_statistical,
)


def test_bonferroni_correction() -> None:
    adjusted = bonferroni_correction([0.01, 0.02, 0.20])
    assert adjusted == [pytest.approx(0.03), pytest.approx(0.06), pytest.approx(0.60)]


def test_bonferroni_caps_at_one() -> None:
    adjusted = bonferroni_correction([0.5, 0.5, 0.5])
    assert all(a == 1.0 for a in adjusted)


def test_holm_correction_is_monotonic_and_le_bonferroni() -> None:
    p = [0.01, 0.02, 0.03, 0.20]
    holm = holm_correction(p)
    bonf = bonferroni_correction(p)
    # Holm is uniformly at least as powerful (adjusted p <= Bonferroni's).
    for h, b in zip(sorted(holm), sorted(bonf), strict=True):
        assert h <= b + 1e-9
    order = sorted(range(len(p)), key=lambda i: p[i])
    sorted_holm = [holm[i] for i in order]
    assert sorted_holm == sorted(sorted_holm)


def test_apply_precision_half_up() -> None:
    assert apply_precision(2.345, 2, "half_up") == 2.35


def test_apply_precision_none_leaves_value_unchanged() -> None:
    assert apply_precision(2.34567, None, "half_up") == 2.34567


def test_direct_evidence_numeric_value() -> None:
    ev = DirectEvidence(id="x", value=3.5, value_type="number")
    assert ev.numeric_value() == 3.5


def test_direct_evidence_non_numeric_raises() -> None:
    ev = DirectEvidence(id="x", value="hello", value_type="number")
    with pytest.raises(ValueError, match="non-numeric"):
        ev.numeric_value()


def test_validate_direct_missing_source_path_for_csv() -> None:
    ev = DirectEvidence(id="x", type="csv", source_locator="row=0;col=a")
    issues = validate_direct(ev)
    assert any(i["code"] == "EVIDENCE_MISSING_SOURCE_PATH" for i in issues)


def test_validate_derived_formula_undeclared_operand() -> None:
    store = EvidenceStore(direct={"a": DirectEvidence(id="a", value=1)})
    d = DerivedEvidence(id="d", formula="a + b", operand_ids=["a"])
    issues = validate_derived_formula(d, store)
    assert any(i["code"] == "EVIDENCE_UNDECLARED_OPERAND" for i in issues)


def test_validate_derived_formula_missing_operand() -> None:
    store = EvidenceStore()
    d = DerivedEvidence(id="d", formula="a + 1", operand_ids=["a"])
    issues = validate_derived_formula(d, store)
    assert any(i["code"] == "EVIDENCE_MISSING_OPERAND" for i in issues)


def test_validate_derived_formula_rejects_incompatible_units() -> None:
    store = EvidenceStore(
        direct={
            "latency_ms": DirectEvidence(id="latency_ms", value=1, unit="milliseconds"),
            "pct": DirectEvidence(id="pct", value=1, unit="percent"),
        }
    )
    d = DerivedEvidence(
        id="d", formula="latency_ms + pct", operand_ids=["latency_ms", "pct"]
    )
    issues = validate_derived_formula(d, store)
    assert any(i["code"] == "EVIDENCE_INCOMPATIBLE_UNITS" for i in issues)


def test_validate_derived_formula_allows_compatible_units() -> None:
    store = EvidenceStore(
        direct={
            "a": DirectEvidence(id="a", value=1, unit="seconds"),
            "b": DirectEvidence(id="b", value=1, unit="milliseconds"),
        }
    )
    d = DerivedEvidence(id="d", formula="a + b", operand_ids=["a", "b"])
    issues = validate_derived_formula(d, store)
    assert not any(i["code"] == "EVIDENCE_INCOMPATIBLE_UNITS" for i in issues)


def test_validate_derived_formula_unsafe_formula() -> None:
    store = EvidenceStore()
    d = DerivedEvidence(id="d", formula="__import__('os')", operand_ids=[])
    issues = validate_derived_formula(d, store)
    assert any(i["code"] == "EVIDENCE_UNSAFE_FORMULA" for i in issues)


def test_validate_statistical_invalid_p_value() -> None:
    ev = StatisticalEvidence(id="s", test_name="paired_t_test", p_value=1.5)
    issues = validate_statistical(ev)
    assert any(i["code"] == "EVIDENCE_INVALID_P_VALUE" for i in issues)


def test_validate_statistical_invalid_sample_size() -> None:
    ev = StatisticalEvidence(id="s", test_name="paired_t_test", sample_size=0)
    issues = validate_statistical(ev)
    assert any(i["code"] == "EVIDENCE_INVALID_SAMPLE_SIZE" for i in issues)


def test_validate_statistical_paired_group_mismatch() -> None:
    ev = StatisticalEvidence(
        id="s", test_name="paired_t_test", paired=True, groups=["a", "b", "c"]
    )
    issues = validate_statistical(ev)
    assert any(i["code"] == "EVIDENCE_PAIRED_GROUP_COUNT" for i in issues)


def test_validate_statistical_interval_order() -> None:
    ev = StatisticalEvidence(id="s", test_name="t", confidence_interval=[5.0, -3.0])
    issues = validate_statistical(ev)
    assert any(i["code"] == "EVIDENCE_INTERVAL_ORDER" for i in issues)


def test_validate_statistical_effect_size_out_of_range() -> None:
    ev = StatisticalEvidence(
        id="s", test_name="t", effect_size_name="pearson_r", effect_size_value=1.5
    )
    issues = validate_statistical(ev)
    assert any(i["code"] == "EVIDENCE_EFFECT_SIZE_OUT_OF_RANGE" for i in issues)


def test_validate_statistical_effect_size_in_range_ok() -> None:
    ev = StatisticalEvidence(
        id="s", test_name="t", effect_size_name="pearson_r", effect_size_value=0.5
    )
    issues = validate_statistical(ev)
    assert not any(i["code"] == "EVIDENCE_EFFECT_SIZE_OUT_OF_RANGE" for i in issues)


def test_validate_statistical_alpha_range() -> None:
    ev = StatisticalEvidence(id="s", test_name="t", alpha=1.5)
    issues = validate_statistical(ev)
    assert any(i["code"] == "EVIDENCE_INVALID_ALPHA" for i in issues)
