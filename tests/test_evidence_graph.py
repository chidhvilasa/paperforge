"""Tests for the evidence dependency graph: cycles, missing refs, staleness."""

from __future__ import annotations

from pathlib import Path

import pytest

from paperforge.evidence.graph import (
    MAX_GRAPH_NODES,
    GraphError,
    compute_staleness,
    detect_cycles,
    find_missing_references,
    recompute_derived_dependency_hashes,
    topological_order,
)
from paperforge.evidence.models import DerivedEvidence, DirectEvidence
from paperforge.evidence.store import EvidenceStore


def test_no_cycle_in_simple_chain() -> None:
    store = EvidenceStore(
        direct={"a": DirectEvidence(id="a", value=1)},
        derived={"d": DerivedEvidence(id="d", formula="a + 1", operand_ids=["a"])},
    )
    assert not detect_cycles(store).has_cycles


def test_direct_cycle_detected() -> None:
    store = EvidenceStore(
        derived={
            "x": DerivedEvidence(id="x", formula="y + 1", operand_ids=["y"]),
            "y": DerivedEvidence(id="y", formula="x + 1", operand_ids=["x"]),
        }
    )
    report = detect_cycles(store)
    assert report.has_cycles
    assert {"x", "y"}.issubset(set(report.cycles[0]))


def test_self_cycle_detected() -> None:
    store = EvidenceStore(
        derived={"x": DerivedEvidence(id="x", formula="x + 1", operand_ids=["x"])}
    )
    assert detect_cycles(store).has_cycles


def test_longer_cycle_detected() -> None:
    store = EvidenceStore(
        derived={
            "a": DerivedEvidence(id="a", formula="b + 1", operand_ids=["b"]),
            "b": DerivedEvidence(id="b", formula="c + 1", operand_ids=["c"]),
            "c": DerivedEvidence(id="c", formula="a + 1", operand_ids=["a"]),
        }
    )
    assert detect_cycles(store).has_cycles


def test_topological_order_raises_on_cycle() -> None:
    store = EvidenceStore(
        derived={"x": DerivedEvidence(id="x", formula="x + 1", operand_ids=["x"])}
    )
    with pytest.raises(GraphError):
        topological_order(store)


def test_missing_reference_detected() -> None:
    store = EvidenceStore(
        derived={"d": DerivedEvidence(id="d", formula="a + 1", operand_ids=["a"])}
    )
    missing = find_missing_references(store)
    assert len(missing) == 1
    assert missing[0].missing_id == "a"


def test_recompute_dependency_hashes_deterministic() -> None:
    store = EvidenceStore(
        direct={"a": DirectEvidence(id="a", value=1, content_hash="h1")},
        derived={"d": DerivedEvidence(id="d", formula="a + 1", operand_ids=["a"])},
    )
    h1 = recompute_derived_dependency_hashes(store)
    h2 = recompute_derived_dependency_hashes(store)
    assert h1 == h2
    assert h1["d"]


def test_dependency_hash_changes_when_operand_source_hash_changes() -> None:
    store1 = EvidenceStore(
        direct={"a": DirectEvidence(id="a", value=1, content_hash="h1")},
        derived={"d": DerivedEvidence(id="d", formula="a + 1", operand_ids=["a"])},
    )
    store2 = EvidenceStore(
        direct={"a": DirectEvidence(id="a", value=1, content_hash="h2-different")},
        derived={"d": DerivedEvidence(id="d", formula="a + 1", operand_ids=["a"])},
    )
    h1 = recompute_derived_dependency_hashes(store1)["d"]
    h2 = recompute_derived_dependency_hashes(store2)["d"]
    assert h1 != h2


def test_compute_staleness_manual_evidence_never_stale(tmp_path: Path) -> None:
    store = EvidenceStore(
        direct={
            "a": DirectEvidence(id="a", type="manual", value=1, content_hash="anything")
        }
    )
    report = compute_staleness(tmp_path, store)
    assert report.is_clean


def test_compute_staleness_detects_edited_source_file(tmp_path: Path) -> None:
    from paperforge.evidence.sources import extract

    csv_path = tmp_path / "data.csv"
    csv_path.write_text("run,val\n0,10\n", encoding="utf-8")
    value, content_hash = extract("csv", csv_path, "row=0;col=val")
    assert value == 10

    store = EvidenceStore(
        direct={
            "a": DirectEvidence(
                id="a",
                type="csv",
                source_path="data.csv",
                source_locator="row=0;col=val",
                value=value,
                content_hash=content_hash,
            )
        }
    )
    report = compute_staleness(tmp_path, store)
    assert report.is_clean

    csv_path.write_text("run,val\n0,999\n", encoding="utf-8")
    report2 = compute_staleness(tmp_path, store)
    assert "a" in report2.stale_direct


def test_huge_graph_is_rejected(tmp_path: Path) -> None:
    store = EvidenceStore(
        direct={
            f"d{i}": DirectEvidence(id=f"d{i}", type="manual", value=i)
            for i in range(MAX_GRAPH_NODES + 1)
        }
    )
    with pytest.raises(GraphError):
        detect_cycles(store)
