"""The evidence dependency graph.

Connects ``DirectEvidence -> DerivedEvidence -> StatisticalEvidence ->
Claim`` (manifest claims reference evidence ids via ``evidence_refs``).
Detects cycles among derived-evidence operand chains, missing references,
and staleness -- a change to a direct-evidence source file (or a manual
value) propagates forward through every derived/statistical/claim node
that (transitively) depends on it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from paperforge.evidence.models import DerivedEvidence, sha256_text
from paperforge.evidence.sources import SourceExtractionError, current_source_hash
from paperforge.evidence.store import EvidenceStore
from paperforge.project_manifest.path_safety import check_project_path

MAX_GRAPH_NODES = 20_000


class GraphError(ValueError):
    pass


@dataclass
class CycleReport:
    cycles: list[list[str]] = field(default_factory=list)

    @property
    def has_cycles(self) -> bool:
        return bool(self.cycles)


def _derived_edges(store: EvidenceStore) -> dict[str, list[str]]:
    return {d.id: list(d.operand_ids) for d in store.derived.values()}


def _enforce_graph_size(store: EvidenceStore) -> None:
    total = len(store.direct) + len(store.derived) + len(store.statistical)
    if total > MAX_GRAPH_NODES:
        raise GraphError(
            f"Evidence graph has {total} nodes, exceeding the {MAX_GRAPH_NODES}-node "
            "bound. Refusing to traverse (possible resource-exhaustion input)."
        )


def detect_cycles(store: EvidenceStore) -> CycleReport:
    """Find cycles in the derived-evidence operand graph via DFS.

    Only ``DerivedEvidence -> DerivedEvidence`` edges can cycle (direct and
    statistical evidence are always leaves), but operand ids that happen to
    reference other derived nodes are followed regardless of kind mix.
    """

    _enforce_graph_size(store)
    edges = _derived_edges(store)
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(edges, WHITE)
    cycles: list[list[str]] = []
    path: list[str] = []

    def dfs(node: str) -> None:
        color[node] = GRAY
        path.append(node)
        for nxt in edges.get(node, []):
            if nxt not in edges:
                continue  # not a derived node; can't participate in a cycle
            if color.get(nxt, WHITE) == WHITE:
                dfs(nxt)
            elif color.get(nxt) == GRAY:
                start = path.index(nxt)
                cycles.append([*path[start:], nxt])
        path.pop()
        color[node] = BLACK

    for node in edges:
        if color.get(node) == WHITE:
            dfs(node)
    return CycleReport(cycles=cycles)


def topological_order(store: EvidenceStore) -> list[str]:
    """Kahn's algorithm over derived-evidence operand edges.

    Raises :class:`GraphError` if a cycle is present -- callers should run
    :func:`detect_cycles` first and refuse to compute dependency hashes
    over a cyclic graph.
    """

    _enforce_graph_size(store)
    edges = _derived_edges(store)
    in_degree = dict.fromkeys(edges, 0)
    for node, operands in edges.items():
        for op in operands:
            if op in edges:
                in_degree[node] += 1

    queue = [n for n, d in in_degree.items() if d == 0]
    order: list[str] = []
    # process dependencies before dependents: we need reverse edges
    dependents: dict[str, list[str]] = {n: [] for n in edges}
    for node, operands in edges.items():
        for op in operands:
            if op in edges:
                dependents[op].append(node)

    queue.sort()
    while queue:
        node = queue.pop(0)
        order.append(node)
        for dep in sorted(dependents.get(node, [])):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)
        queue.sort()

    if len(order) != len(edges):
        raise GraphError(
            "Cannot compute a topological order: the derived-evidence graph has a cycle."
        )
    return order


@dataclass
class MissingReference:
    referencing_id: str
    referencing_kind: str
    missing_id: str


def find_missing_references(store: EvidenceStore) -> list[MissingReference]:
    known = store.all_ids()
    missing: list[MissingReference] = []
    for d in store.derived.values():
        for op in d.operand_ids:
            if op not in known:
                missing.append(MissingReference(d.id, "derived", op))
    for s in store.statistical.values():
        for ref in s.observation_refs:
            if ref not in known:
                missing.append(MissingReference(s.id, "statistical", ref))
    return missing


@dataclass
class StalenessReport:
    stale_direct: dict[str, str] = field(default_factory=dict)  # id -> reason
    stale_derived: dict[str, str] = field(default_factory=dict)
    stale_statistical: dict[str, str] = field(default_factory=dict)
    unreadable_sources: dict[str, str] = field(default_factory=dict)

    @property
    def stale_ids(self) -> set[str]:
        return (
            set(self.stale_direct)
            | set(self.stale_derived)
            | set(self.stale_statistical)
        )

    @property
    def is_clean(self) -> bool:
        return not (self.stale_direct or self.stale_derived or self.stale_statistical)


def _direct_effective_hash(store: EvidenceStore, evidence_id: str) -> str:
    return store.direct[evidence_id].content_hash


def compute_dependency_hash(
    formula: str, operand_ids: list[str], operand_hashes: dict[str, str]
) -> str:
    payload = {
        "formula": formula,
        "operands": [[oid, operand_hashes.get(oid, "")] for oid in sorted(operand_ids)],
    }
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def recompute_derived_dependency_hashes(store: EvidenceStore) -> dict[str, str]:
    """Recompute the *expected* dependency hash for every derived-evidence
    node from its current formula/operands and its operands' current
    effective hashes, walked bottom-up. Raises :class:`GraphError` if the
    graph is cyclic (call :func:`detect_cycles` first)."""

    _enforce_graph_size(store)
    order = topological_order(store)
    effective: dict[str, str] = {}
    for eid in store.direct:
        effective[eid] = _direct_effective_hash(store, eid)
    for eid in store.statistical:
        effective[eid] = (
            store.statistical[eid].dependency_hash or store.statistical[eid].id
        )

    expected: dict[str, str] = {}
    for eid in order:
        d = store.derived[eid]
        operand_hashes = {op: effective.get(op, "") for op in d.operand_ids}
        h = compute_dependency_hash(d.formula, d.operand_ids, operand_hashes)
        expected[eid] = h
        effective[eid] = h
    return expected


def compute_staleness(project_root: Path, store: EvidenceStore) -> StalenessReport:
    _enforce_graph_size(store)
    report = StalenessReport()

    for d in store.direct.values():
        if d.type == "manual":
            continue
        check = check_project_path(
            project_root,
            d.source_path,
            field_path=f"evidence.direct.{d.id}.source_path",
        )
        if not check.ok or check.resolved is None:
            report.unreadable_sources[d.id] = check.reason or "invalid source path"
            continue
        try:
            current_hash = current_source_hash(d.type, check.resolved)
        except SourceExtractionError as exc:
            report.unreadable_sources[d.id] = str(exc)
            continue
        if current_hash != d.content_hash:
            report.stale_direct[d.id] = (
                f"Source file '{d.source_path}' has changed since this evidence was recorded."
            )

    cycles = detect_cycles(store)
    if not cycles.has_cycles:
        try:
            expected = recompute_derived_dependency_hashes(store)
        except GraphError:
            expected = {}
        for eid, derived_ev in store.derived.items():
            if eid in report.unreadable_sources:
                continue
            upstream_stale = [
                op for op in derived_ev.operand_ids if op in report.stale_ids
            ]
            if upstream_stale:
                report.stale_derived[eid] = (
                    f"Depends on stale evidence: {', '.join(sorted(upstream_stale))}."
                )
            elif expected.get(eid) and expected[eid] != derived_ev.dependency_hash:
                report.stale_derived[eid] = (
                    "Formula, operands, or an upstream value changed since this "
                    "result was last computed."
                )

    for s in store.statistical.values():
        upstream_stale = [ref for ref in s.observation_refs if ref in report.stale_ids]
        if upstream_stale:
            report.stale_statistical[s.id] = (
                f"Depends on stale evidence: {', '.join(sorted(upstream_stale))}."
            )

    return report


def stale_evidence_ids(
    project_root: Path, store: EvidenceStore | None = None
) -> set[str]:
    from paperforge.evidence.store import load_store

    store = store if store is not None else load_store(project_root)
    return compute_staleness(project_root, store).stale_ids


def affected_claim_ids(
    claims_evidence_refs: dict[str, list[str]], stale_or_missing_ids: set[str]
) -> set[str]:
    """Given ``{claim_id: [evidence_refs...]}`` and a set of stale/missing
    evidence ids, return the claim ids that reference at least one of
    them."""

    return {
        cid
        for cid, refs in claims_evidence_refs.items()
        if set(refs) & stale_or_missing_ids
    }


def recompute_dependency_hash_for(
    store: EvidenceStore, derived: DerivedEvidence
) -> str:
    """Compute the dependency hash a single derived-evidence record
    *should* have right now (used when recording a fresh computation)."""

    expected = recompute_derived_dependency_hashes(store)
    return expected.get(derived.id, "")


__all__ = [
    "MAX_GRAPH_NODES",
    "CycleReport",
    "GraphError",
    "MissingReference",
    "StalenessReport",
    "affected_claim_ids",
    "compute_dependency_hash",
    "compute_staleness",
    "detect_cycles",
    "find_missing_references",
    "recompute_dependency_hash_for",
    "recompute_derived_dependency_hashes",
    "stale_evidence_ids",
    "topological_order",
]
