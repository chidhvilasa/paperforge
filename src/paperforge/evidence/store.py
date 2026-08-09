"""Persistence for the evidence store: ``.paperforge/evidence/*.yaml``.

Three flat files, one per evidence kind, each a YAML list of records sorted
by id for stable diffs. All writes are atomic (:mod:`paperforge.utils.atomic`)
so a crash mid-write never corrupts the store; a `.tmp` file is replaced into
place only after a full, successful write.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from paperforge.evidence.models import (
    DerivedEvidence,
    DirectEvidence,
    StatisticalEvidence,
)
from paperforge.utils.atomic import atomic_write_text

EVIDENCE_DIRNAME = "evidence"
DIRECT_FILENAME = "direct.yaml"
DERIVED_FILENAME = "derived.yaml"
STATISTICAL_FILENAME = "statistical.yaml"


@dataclass
class EvidenceStore:
    direct: dict[str, DirectEvidence] = field(default_factory=dict)
    derived: dict[str, DerivedEvidence] = field(default_factory=dict)
    statistical: dict[str, StatisticalEvidence] = field(default_factory=dict)

    def all_ids(self) -> set[str]:
        return set(self.direct) | set(self.derived) | set(self.statistical)

    def kind_of(self, evidence_id: str) -> str | None:
        if evidence_id in self.direct:
            return "direct"
        if evidence_id in self.derived:
            return "derived"
        if evidence_id in self.statistical:
            return "statistical"
        return None


def _evidence_dir(project_root: Path) -> Path:
    return project_root / ".paperforge" / EVIDENCE_DIRNAME


def _load_yaml_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


def load_store(project_root: Path) -> EvidenceStore:
    edir = _evidence_dir(project_root)
    direct = {
        d["id"]: DirectEvidence.from_dict(d)
        for d in _load_yaml_list(edir / DIRECT_FILENAME)
        if d.get("id")
    }
    derived = {
        d["id"]: DerivedEvidence.from_dict(d)
        for d in _load_yaml_list(edir / DERIVED_FILENAME)
        if d.get("id")
    }
    statistical = {
        d["id"]: StatisticalEvidence.from_dict(d)
        for d in _load_yaml_list(edir / STATISTICAL_FILENAME)
        if d.get("id")
    }
    return EvidenceStore(direct=direct, derived=derived, statistical=statistical)


def save_store(project_root: Path, store: EvidenceStore) -> None:
    edir = _evidence_dir(project_root)
    edir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        edir / DIRECT_FILENAME,
        yaml.safe_dump(
            [store.direct[k].to_dict() for k in sorted(store.direct)],
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    atomic_write_text(
        edir / DERIVED_FILENAME,
        yaml.safe_dump(
            [store.derived[k].to_dict() for k in sorted(store.derived)],
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    atomic_write_text(
        edir / STATISTICAL_FILENAME,
        yaml.safe_dump(
            [store.statistical[k].to_dict() for k in sorted(store.statistical)],
            sort_keys=False,
            allow_unicode=True,
        ),
    )


def store_fingerprint(project_root: Path) -> dict[str, str]:
    """A stable content fingerprint of the whole evidence store, used by
    :mod:`paperforge.planning.approval` to invalidate a plan approval when
    registered evidence changes underneath it."""

    store = load_store(project_root)
    payload = {
        "direct": [store.direct[k].to_dict() for k in sorted(store.direct)],
        "derived": [store.derived[k].to_dict() for k in sorted(store.derived)],
        "statistical": [
            store.statistical[k].to_dict() for k in sorted(store.statistical)
        ],
    }
    text = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return {"evidence_store_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()}


__all__ = [
    "DERIVED_FILENAME",
    "DIRECT_FILENAME",
    "EVIDENCE_DIRNAME",
    "STATISTICAL_FILENAME",
    "EvidenceStore",
    "load_store",
    "save_store",
    "store_fingerprint",
]
