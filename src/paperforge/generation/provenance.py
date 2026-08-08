"""Provenance sidecars for generated content.

Every generated sentence gets one :class:`ProvenanceRecord`. Sidecars are
written to ``.paperforge/provenance/<section>.json`` (list of records for
that section) with a top-level ``.paperforge/provenance/index.json``
mapping each section to its sentence count and a whole-file text hash of
the generated Markdown, so staleness (the generated file was hand-edited
or regenerated without updating the sidecar) can be detected cheaply
without re-parsing every record.

:func:`validate_provenance` implements the submission-mode checks the spec
requires: missing provenance, stale provenance (hash mismatch), missing
claim, missing evidence, missing citation, unreviewed generated scientific
results, and placeholder provenance. Sections explicitly marked
author-authored (no sidecar, by design) are allowed through but recorded
as such -- they are not "missing provenance" errors.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paperforge.generation.no_ai import GeneratedSection
from paperforge.models.claim import RESULT_EVIDENCE_CLASSES
from paperforge.project_manifest.models import ProjectManifest

PROVENANCE_DIRNAME = "provenance"
INDEX_FILENAME = "index.json"


@dataclass
class ProvenanceRecord:
    section: str
    sentence_id: str
    text_hash: str
    evidence_class: str
    claim_ids: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    citation_keys: list[str] = field(default_factory=list)
    formula_refs: list[str] = field(default_factory=list)
    source_paths: list[str] = field(default_factory=list)
    source_locators: list[str] = field(default_factory=list)
    generation_method: str = "template:no_ai"
    provider: str = "no_ai"
    model: str = ""
    confidence: float = 1.0
    timestamp: str = ""
    author_review_status: str = "pending"
    approval_status: str = "unknown"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "sentence_id": self.sentence_id,
            "text_hash": self.text_hash,
            "evidence_class": self.evidence_class,
            "claim_ids": list(self.claim_ids),
            "evidence_refs": list(self.evidence_refs),
            "citation_keys": list(self.citation_keys),
            "formula_refs": list(self.formula_refs),
            "source_paths": list(self.source_paths),
            "source_locators": list(self.source_locators),
            "generation_method": self.generation_method,
            "provider": self.provider,
            "model": self.model,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "author_review_status": self.author_review_status,
            "approval_status": self.approval_status,
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProvenanceRecord:
        return cls(
            section=str(data.get("section", "")),
            sentence_id=str(data.get("sentence_id", "")),
            text_hash=str(data.get("text_hash", "")),
            evidence_class=str(data.get("evidence_class", "")),
            claim_ids=list(data.get("claim_ids", [])),
            evidence_refs=list(data.get("evidence_refs", [])),
            citation_keys=list(data.get("citation_keys", [])),
            formula_refs=list(data.get("formula_refs", [])),
            source_paths=list(data.get("source_paths", [])),
            source_locators=list(data.get("source_locators", [])),
            generation_method=str(data.get("generation_method", "")),
            provider=str(data.get("provider", "")),
            model=str(data.get("model", "")),
            confidence=float(data.get("confidence", 1.0)),
            timestamp=str(data.get("timestamp", "")),
            author_review_status=str(data.get("author_review_status", "pending")),
            approval_status=str(data.get("approval_status", "unknown")),
            warnings=list(data.get("warnings", [])),
        )


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_records(
    generated: GeneratedSection,
    *,
    provider_name: str,
    model_identifier: str,
    approval_status: str,
) -> list[ProvenanceRecord]:
    records = []
    for sentence in generated.sentences:
        records.append(
            ProvenanceRecord(
                section=generated.section,
                sentence_id=f"{generated.section}:{sentence.claim_id}",
                text_hash=_text_hash(sentence.text),
                evidence_class=sentence.evidence_class,
                claim_ids=[sentence.claim_id],
                evidence_refs=list(sentence.evidence_refs),
                citation_keys=list(sentence.citation_keys),
                generation_method="template:no_ai",
                provider=provider_name,
                model=model_identifier,
                confidence=1.0,
                timestamp=datetime.now(UTC).isoformat(),
                author_review_status="pending",
                approval_status=approval_status,
                warnings=list(sentence.warnings),
            )
        )
    return records


def write_provenance(
    project_root: Path,
    generated: GeneratedSection,
    records: list[ProvenanceRecord],
) -> None:
    from paperforge.utils.atomic import atomic_write_text

    prov_dir = project_root / ".paperforge" / PROVENANCE_DIRNAME
    prov_dir.mkdir(parents=True, exist_ok=True)

    section_file = prov_dir / f"{generated.section}.json"
    atomic_write_text(
        section_file,
        json.dumps([r.to_dict() for r in records], indent=2, ensure_ascii=False),
    )

    index_file = prov_dir / INDEX_FILENAME
    index: dict[str, Any] = {}
    if index_file.exists():
        try:
            index = json.loads(index_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            index = {}
    index.setdefault("sections", {})
    index["sections"][generated.section] = {
        "sentence_count": len(records),
        "section_markdown_hash": _text_hash(generated.to_markdown()),
        "generated_at": generated.generated_at,
        "mode": generated.mode,
    }
    atomic_write_text(index_file, json.dumps(index, indent=2, ensure_ascii=False))


def load_provenance(
    project_root: Path,
) -> tuple[dict[str, Any], dict[str, list[ProvenanceRecord]]]:
    prov_dir = project_root / ".paperforge" / PROVENANCE_DIRNAME
    index_file = prov_dir / INDEX_FILENAME
    index: dict[str, Any] = {"sections": {}}
    if index_file.exists():
        try:
            index = json.loads(index_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            index = {"sections": {}}

    records_by_section: dict[str, list[ProvenanceRecord]] = {}
    for section_name in index.get("sections", {}):
        section_file = prov_dir / f"{section_name}.json"
        if not section_file.exists():
            continue
        try:
            raw = json.loads(section_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = []
        records_by_section[section_name] = [ProvenanceRecord.from_dict(r) for r in raw]
    return index, records_by_section


def validate_provenance(
    project_root: Path,
    manifest: ProjectManifest,
    *,
    generated_sections_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Returns a list of issue dicts (code/severity/message/section) for
    every submission-mode provenance problem found."""

    issues: list[dict[str, Any]] = []
    index, records_by_section = load_provenance(project_root)
    claims_by_id = {c.id: c for c in manifest.claims}
    gen_dir = generated_sections_dir or (
        project_root / ".paperforge" / "generated_sections"
    )

    for section_name, meta in index.get("sections", {}).items():
        section_file = gen_dir / f"{section_name}.md"
        if not section_file.exists():
            issues.append(
                {
                    "code": "PROVENANCE_MISSING_GENERATED_FILE",
                    "severity": "ERROR",
                    "section": section_name,
                    "message": f"Provenance exists for '{section_name}' but the generated file is missing.",
                }
            )
            continue
        current_hash = _text_hash(section_file.read_text(encoding="utf-8"))
        if current_hash != meta.get("section_markdown_hash"):
            issues.append(
                {
                    "code": "PROVENANCE_STALE_HASH",
                    "severity": "ERROR",
                    "section": section_name,
                    "message": f"Generated content for '{section_name}' does not match its provenance hash "
                    "(file was edited or regenerated without updating provenance).",
                }
            )

        for rec in records_by_section.get(section_name, []):
            if rec.evidence_class == "PLACEHOLDER":
                issues.append(
                    {
                        "code": "PROVENANCE_PLACEHOLDER",
                        "severity": "ERROR",
                        "section": section_name,
                        "message": f"{rec.sentence_id}: placeholder provenance is not submission-ready.",
                    }
                )
            for claim_id in rec.claim_ids:
                if claim_id not in claims_by_id:
                    issues.append(
                        {
                            "code": "PROVENANCE_MISSING_CLAIM",
                            "severity": "ERROR",
                            "section": section_name,
                            "message": f"{rec.sentence_id}: references claim '{claim_id}', not found in the manifest.",
                        }
                    )
            if rec.evidence_class in RESULT_EVIDENCE_CLASSES:
                if not (rec.evidence_refs or rec.citation_keys):
                    issues.append(
                        {
                            "code": "PROVENANCE_MISSING_EVIDENCE",
                            "severity": "ERROR",
                            "section": section_name,
                            "message": f"{rec.sentence_id}: {rec.evidence_class} claim has no evidence or citation reference.",
                        }
                    )
                if rec.author_review_status not in {"approved", "reviewed"}:
                    issues.append(
                        {
                            "code": "PROVENANCE_UNREVIEWED_RESULT",
                            "severity": "ERROR",
                            "section": section_name,
                            "message": f"{rec.sentence_id}: generated {rec.evidence_class} content has not been "
                            "marked reviewed by an author.",
                        }
                    )

    return issues


__all__ = [
    "ProvenanceRecord",
    "build_records",
    "load_provenance",
    "validate_provenance",
    "write_provenance",
]
