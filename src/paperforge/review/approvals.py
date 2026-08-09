"""The approval ledger and the objects it can review.

Reviewable object kinds:

- ``provenance_sentence`` -- one :class:`~paperforge.generation.provenance.ProvenanceRecord`,
  identified by its ``sentence_id`` (``"<section>:<claim_id>"``).
- ``claim`` -- one manifest claim, identified by its id. Approving/rejecting
  writes ``author_review_status`` back onto that claim in
  ``paperforge.project.yaml``.
- ``direct_evidence`` / ``derived_evidence`` / ``statistical_evidence`` --
  one evidence record, identified by its id.

Every decision appends an :class:`ApprovalRecord` to
``.paperforge/approvals.json`` (atomic write) recording the reviewer,
timestamp, decision, and a content hash of the object *at decision time*.
:func:`reconcile` re-hashes every previously-approved object and downgrades
any whose current hash no longer matches the ledger entry back to
``pending`` -- editing an approved sentence, claim, or evidence record
un-approves it automatically rather than silently keeping a stale approval.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paperforge.evidence.models import sha256_text
from paperforge.evidence.store import EvidenceStore, load_store, save_store
from paperforge.generation.provenance import ProvenanceRecord, load_provenance
from paperforge.project_manifest.errors import ManifestError
from paperforge.project_manifest.loader import load_manifest_file
from paperforge.project_manifest.models import ProjectManifest
from paperforge.utils.atomic import atomic_write_text

DEFAULT_MANIFEST_FILENAME = "paperforge.project.yaml"
LEDGER_FILENAME = "approvals.json"

OBJECT_KINDS = frozenset(
    {
        "provenance_sentence",
        "claim",
        "direct_evidence",
        "derived_evidence",
        "statistical_evidence",
    }
)
DECISIONS = frozenset({"approved", "rejected", "pending"})


class ApprovalError(ValueError):
    pass


@dataclass
class ApprovalRecord:
    object_id: str
    object_kind: str
    object_hash: str
    decision: str
    reviewer: str
    timestamp: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "object_kind": self.object_kind,
            "object_hash": self.object_hash,
            "decision": self.decision,
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalRecord:
        return cls(
            object_id=str(data.get("object_id", "")),
            object_kind=str(data.get("object_kind", "")),
            object_hash=str(data.get("object_hash", "")),
            decision=str(data.get("decision", "pending")),
            reviewer=str(data.get("reviewer", "")),
            timestamp=str(data.get("timestamp", "")),
            note=str(data.get("note", "")),
        )


def _ledger_path(project_root: Path) -> Path:
    return project_root / ".paperforge" / LEDGER_FILENAME


def load_ledger(project_root: Path) -> list[ApprovalRecord]:
    path = _ledger_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [ApprovalRecord.from_dict(d) for d in data if isinstance(d, dict)]


def save_ledger(project_root: Path, records: list[ApprovalRecord]) -> None:
    path = _ledger_path(project_root)
    atomic_write_text(
        path, json.dumps([r.to_dict() for r in records], indent=2, ensure_ascii=False)
    )


def _latest_by_object(records: list[ApprovalRecord]) -> dict[str, ApprovalRecord]:
    latest: dict[str, ApprovalRecord] = {}
    for r in records:
        latest[r.object_id] = r  # ledger is append-only in chronological order
    return latest


def _manifest_path(project_root: Path, manifest_path: Path | None) -> Path:
    return manifest_path or (project_root / DEFAULT_MANIFEST_FILENAME)


def _load_manifest(project_root: Path, manifest_path: Path | None) -> ProjectManifest:
    mpath = _manifest_path(project_root, manifest_path)
    if not mpath.exists():
        return ProjectManifest()
    try:
        raw = load_manifest_file(mpath)
    except ManifestError:
        return ProjectManifest()
    return ProjectManifest.from_dict(raw)


def _save_manifest(
    project_root: Path, manifest_path: Path | None, manifest: ProjectManifest
) -> None:
    mpath = _manifest_path(project_root, manifest_path)
    atomic_write_text(mpath, manifest.to_yaml_text())


def _claim_hash(claim_data: dict[str, Any]) -> str:
    payload = {k: v for k, v in claim_data.items() if k != "author_review_status"}
    return sha256_text(json.dumps(payload, sort_keys=True, default=str))


def _evidence_hash(record_dict: dict[str, Any]) -> str:
    payload = {
        k: v
        for k, v in record_dict.items()
        if k not in ("author_review_status", "recorded_at")
    }
    return sha256_text(json.dumps(payload, sort_keys=True, default=str))


def _provenance_hash(rec: ProvenanceRecord) -> str:
    return rec.text_hash


@dataclass
class ReviewableObject:
    object_id: str
    object_kind: str
    current_hash: str
    label: str = ""


def _find_provenance_sentence(
    project_root: Path, object_id: str
) -> ProvenanceRecord | None:
    _index, records_by_section = load_provenance(project_root)
    for records in records_by_section.values():
        for rec in records:
            if rec.sentence_id == object_id:
                return rec
    return None


def find_object(
    project_root: Path,
    object_id: str,
    *,
    manifest_path: Path | None = None,
    store: EvidenceStore | None = None,
) -> ReviewableObject:
    store = store if store is not None else load_store(project_root)

    if object_id in store.direct:
        return ReviewableObject(
            object_id,
            "direct_evidence",
            _evidence_hash(store.direct[object_id].to_dict()),
        )
    if object_id in store.derived:
        return ReviewableObject(
            object_id,
            "derived_evidence",
            _evidence_hash(store.derived[object_id].to_dict()),
        )
    if object_id in store.statistical:
        return ReviewableObject(
            object_id,
            "statistical_evidence",
            _evidence_hash(store.statistical[object_id].to_dict()),
        )

    rec = _find_provenance_sentence(project_root, object_id)
    if rec is not None:
        return ReviewableObject(
            object_id, "provenance_sentence", _provenance_hash(rec), label=rec.text_hash
        )

    manifest = _load_manifest(project_root, manifest_path)
    for claim in manifest.claims:
        if claim.id == object_id:
            claim_data = {
                "id": claim.id,
                "text": claim.text,
                "evidence_class": claim.evidence_class,
                "evidence_refs": list(claim.evidence_refs),
                "citation_keys": list(claim.citation_keys),
            }
            return ReviewableObject(object_id, "claim", _claim_hash(claim_data))

    raise ApprovalError(
        f"No reviewable object with id '{object_id}' found (checked evidence store, "
        "provenance sentences, and manifest claims)."
    )


def _apply_status(
    project_root: Path,
    obj: ReviewableObject,
    status: str,
    *,
    manifest_path: Path | None,
    store: EvidenceStore,
) -> None:
    """Write ``status`` (one of "pending"/"reviewed"/"approved"/"rejected")
    onto the underlying object's own status field."""

    if obj.object_kind == "direct_evidence":
        store.direct[obj.object_id].author_review_status = status
        save_store(project_root, store)
    elif obj.object_kind == "derived_evidence":
        store.derived[obj.object_id].author_review_status = status
        save_store(project_root, store)
    elif obj.object_kind == "statistical_evidence":
        store.statistical[obj.object_id].author_review_status = status
        save_store(project_root, store)
    elif obj.object_kind == "provenance_sentence":
        _set_provenance_status(project_root, obj.object_id, status)
    elif obj.object_kind == "claim":
        manifest = _load_manifest(project_root, manifest_path)
        for claim in manifest.claims:
            if claim.id == obj.object_id:
                claim.author_review_status = status
        _save_manifest(project_root, manifest_path, manifest)


def _set_provenance_status(project_root: Path, sentence_id: str, status: str) -> None:
    from paperforge.generation.provenance import (
        INDEX_FILENAME,
        PROVENANCE_DIRNAME,
    )

    prov_dir = project_root / ".paperforge" / PROVENANCE_DIRNAME
    index_path = prov_dir / INDEX_FILENAME
    if not index_path.exists():
        return
    section_name = sentence_id.split(":", 1)[0]
    section_file = prov_dir / f"{section_name}.json"
    if not section_file.exists():
        return
    try:
        raw = json.loads(section_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    changed = False
    for entry in raw:
        if entry.get("sentence_id") == sentence_id:
            entry["author_review_status"] = status
            changed = True
    if changed:
        atomic_write_text(section_file, json.dumps(raw, indent=2, ensure_ascii=False))


_DECISION_TO_STATUS = {
    "approved": "approved",
    "rejected": "rejected",
    "pending": "pending",
}


def record_decision(
    project_root: Path,
    object_id: str,
    decision: str,
    *,
    reviewer: str,
    note: str = "",
    manifest_path: Path | None = None,
) -> ApprovalRecord:
    if decision not in DECISIONS:
        raise ApprovalError(
            f"decision must be one of {sorted(DECISIONS)}, got '{decision}'."
        )

    store = load_store(project_root)
    obj = find_object(project_root, object_id, manifest_path=manifest_path, store=store)

    record = ApprovalRecord(
        object_id=object_id,
        object_kind=obj.object_kind,
        object_hash=obj.current_hash,
        decision=decision,
        reviewer=reviewer,
        timestamp=datetime.now(UTC).isoformat(),
        note=note,
    )
    ledger = load_ledger(project_root)
    ledger.append(record)
    save_ledger(project_root, ledger)

    _apply_status(
        project_root,
        obj,
        _DECISION_TO_STATUS[decision],
        manifest_path=manifest_path,
        store=store,
    )
    return record


def record_decision_for_section(
    project_root: Path,
    section: str,
    decision: str,
    *,
    reviewer: str,
    note: str = "",
) -> list[ApprovalRecord]:
    _index, records_by_section = load_provenance(project_root)
    recs = records_by_section.get(section, [])
    results = []
    for rec in recs:
        results.append(
            record_decision(
                project_root, rec.sentence_id, decision, reviewer=reviewer, note=note
            )
        )
    return results


@dataclass
class ReviewStatusEntry:
    object_id: str
    object_kind: str
    effective_status: str
    ledger_decision: str = ""
    reviewer: str = ""
    timestamp: str = ""
    stale: bool = False


@dataclass
class ReconcileResult:
    entries: list[ReviewStatusEntry] = field(default_factory=list)
    downgraded: list[str] = field(default_factory=list)


def reconcile(
    project_root: Path, *, manifest_path: Path | None = None
) -> ReconcileResult:
    """Re-hash every object with a ledger decision; any whose current hash
    no longer matches its last ledger entry is downgraded back to
    "pending" (on the object itself) and reported as stale."""

    ledger = load_ledger(project_root)
    latest = _latest_by_object(ledger)
    store = load_store(project_root)
    result = ReconcileResult()

    for object_id, rec in latest.items():
        try:
            obj = find_object(
                project_root, object_id, manifest_path=manifest_path, store=store
            )
        except ApprovalError:
            result.entries.append(
                ReviewStatusEntry(
                    object_id,
                    rec.object_kind,
                    "missing",
                    rec.decision,
                    rec.reviewer,
                    rec.timestamp,
                    stale=True,
                )
            )
            continue
        stale = obj.current_hash != rec.object_hash
        if stale and rec.decision == "approved":
            _apply_status(
                project_root, obj, "pending", manifest_path=manifest_path, store=store
            )
            result.downgraded.append(object_id)
            effective = "pending"
        else:
            effective = rec.decision
        result.entries.append(
            ReviewStatusEntry(
                object_id,
                obj.object_kind,
                effective,
                rec.decision,
                rec.reviewer,
                rec.timestamp,
                stale=stale,
            )
        )
    return result


__all__ = [
    "DECISIONS",
    "OBJECT_KINDS",
    "ApprovalError",
    "ApprovalRecord",
    "ReconcileResult",
    "ReviewStatusEntry",
    "ReviewableObject",
    "find_object",
    "load_ledger",
    "reconcile",
    "record_decision",
    "record_decision_for_section",
    "save_ledger",
]
