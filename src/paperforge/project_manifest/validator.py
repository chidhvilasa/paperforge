"""Structural validation of a parsed manifest document.

Two things are checked, independently of each other:

1. **Structural requirements** — the small, mode-independent minimum
   described in :mod:`paperforge.project_manifest.models` (title, research
   domain/study type/language, at least one author with id+name, a primary
   research question, a generation policy and required-section list).
   Funding, ethics, consent, DOI, ORCID, statistics, datasets, figures, and
   code availability are deliberately never checked here — see
   :mod:`paperforge.requirements_engine` for conditional requirements.

2. **Unknown-field policy**, which depends on ``mode``:

   - ``draft`` / ``review``: fields that are not part of the schema *and*
     not under ``extensions`` are only a WARNING, unless they look like a
     likely misspelling of a real field name (edit-distance suggestion),
     in which case they are an ERROR because silently ignoring a
     near-miss field is worse than refusing it.
   - ``submission``: every unknown field outside ``extensions`` is an
     ERROR, misspelled or not.
"""

from __future__ import annotations

import dataclasses
import difflib
from dataclasses import dataclass, field
from typing import Any

from paperforge.project_manifest.errors import ManifestIssue, issue
from paperforge.project_manifest.models import (
    EVIDENCE_CLASSES,
    AuthorEntry,
    ClaimEntry,
    Declarations,
    EvidenceInventory,
    Literature,
    ManuscriptPlanConfig,
    Methodology,
    ProjectIdentity,
    ProjectManifest,
    ResearchBasis,
    SubmissionPackaging,
)

MODES = ("draft", "review", "submission")

_SECTION_MODELS: dict[str, type] = {
    "project": ProjectIdentity,
    "research": ResearchBasis,
    "methodology": Methodology,
    "evidence": EvidenceInventory,
    "literature": Literature,
    "manuscript": ManuscriptPlanConfig,
    "declarations": Declarations,
    "submission": SubmissionPackaging,
}

_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "project",
        "authors",
        "research",
        "methodology",
        "evidence",
        "literature",
        "claims",
        "manuscript",
        "declarations",
        "submission",
        "extensions",
    }
)

_MISSPELL_CUTOFF = 0.75


@dataclass
class ValidationResult:
    errors: list[ManifestIssue] = field(default_factory=list)
    warnings: list[ManifestIssue] = field(default_factory=list)
    info: list[ManifestIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def all_issues(self) -> list[ManifestIssue]:
        return [*self.errors, *self.warnings, *self.info]

    def add(self, iss: ManifestIssue) -> None:
        if iss.severity == "ERROR":
            self.errors.append(iss)
        elif iss.severity == "WARNING":
            self.warnings.append(iss)
        else:
            self.info.append(iss)


def _suggest(unknown_key: str, known_keys: frozenset[str] | set[str]) -> str | None:
    matches = difflib.get_close_matches(
        unknown_key, list(known_keys), n=1, cutoff=_MISSPELL_CUTOFF
    )
    return matches[0] if matches else None


def _check_unknown_fields(
    data: dict[str, Any],
    known_keys: frozenset[str] | set[str],
    *,
    field_path: str,
    mode: str,
    result: ValidationResult,
    allow_extensions_sibling: bool = False,
) -> None:
    for key in data:
        if key in known_keys:
            continue
        if allow_extensions_sibling and key == "extensions":
            continue
        suggestion = _suggest(key, known_keys)
        path = f"{field_path}.{key}" if field_path else key
        if suggestion:
            result.add(
                issue(
                    "LIKELY_MISSPELLED_FIELD",
                    f"Unknown field '{key}' looks like a misspelling of '{suggestion}'.",
                    remediation=f"Rename '{key}' to '{suggestion}', or move it under 'extensions'.",
                    field_path=path,
                    severity="ERROR",
                )
            )
        elif mode == "submission":
            result.add(
                issue(
                    "UNKNOWN_FIELD_SUBMISSION",
                    f"Unknown field '{key}' is not part of the manifest schema.",
                    remediation="Remove the field or move it under 'extensions'.",
                    field_path=path,
                    severity="ERROR",
                )
            )
        else:
            result.add(
                issue(
                    "UNKNOWN_FIELD",
                    f"Unknown field '{key}' is not part of the manifest schema.",
                    remediation="Move project-specific data under 'extensions', or remove it.",
                    field_path=path,
                    severity="WARNING",
                )
            )


def _dataclass_field_names(dc_cls: type) -> set[str]:
    return {f.name for f in dataclasses.fields(dc_cls)}


def validate_manifest_dict(
    raw: dict[str, Any], *, mode: str = "draft"
) -> ValidationResult:
    """Validate a raw (already safely-parsed) manifest mapping.

    This does not require the caller to have built a :class:`ProjectManifest`
    first, so misspelled/unknown top-level sections can still be reported
    (building the typed model silently drops unrecognized keys).
    """

    if mode not in MODES:
        raise ValueError(f"Unknown validation mode: {mode!r}. Expected one of {MODES}.")

    result = ValidationResult()

    _check_unknown_fields(
        raw, _TOP_LEVEL_FIELDS, field_path="", mode=mode, result=result
    )

    for section_name, dc_cls in _SECTION_MODELS.items():
        section = raw.get(section_name)
        if isinstance(section, dict):
            _check_unknown_fields(
                section,
                _dataclass_field_names(dc_cls),
                field_path=section_name,
                mode=mode,
                result=result,
            )

    authors_raw = raw.get("authors")
    if isinstance(authors_raw, list):
        author_fields = _dataclass_field_names(AuthorEntry)
        for idx, a in enumerate(authors_raw):
            if isinstance(a, dict):
                _check_unknown_fields(
                    a,
                    author_fields,
                    field_path=f"authors[{idx}]",
                    mode=mode,
                    result=result,
                )

    claims_raw = raw.get("claims")
    if isinstance(claims_raw, list):
        claim_fields = _dataclass_field_names(ClaimEntry)
        for idx, c in enumerate(claims_raw):
            if isinstance(c, dict):
                _check_unknown_fields(
                    c,
                    claim_fields,
                    field_path=f"claims[{idx}]",
                    mode=mode,
                    result=result,
                )
                ec = c.get("evidence_class", "")
                if ec and ec not in EVIDENCE_CLASSES:
                    result.add(
                        issue(
                            "INVALID_EVIDENCE_CLASS",
                            f"claims[{idx}].evidence_class '{ec}' is not a recognized evidence class.",
                            remediation=f"Use one of: {', '.join(sorted(EVIDENCE_CLASSES))}.",
                            field_path=f"claims[{idx}].evidence_class",
                            severity="WARNING",
                        )
                    )

    schema_version = raw.get("schema_version")
    if not schema_version:
        result.add(
            issue(
                "MISSING_SCHEMA_VERSION",
                "Manifest is missing 'schema_version'.",
                remediation='Add `schema_version: "1.0"` at the top of the manifest.',
                field_path="schema_version",
                severity="ERROR",
            )
        )

    project_raw = raw.get("project")
    project: dict[str, Any] = project_raw if isinstance(project_raw, dict) else {}
    if not project.get("title"):
        result.add(
            issue(
                "MISSING_TITLE",
                "Manifest is missing 'project.title'.",
                remediation="Add a working title under 'project.title'.",
                field_path="project.title",
                severity="ERROR",
            )
        )
    if not project.get("research_domain"):
        result.add(
            issue(
                "MISSING_RESEARCH_DOMAIN",
                "Manifest is missing 'project.research_domain'.",
                remediation="Add the research field/domain under 'project.research_domain'.",
                field_path="project.research_domain",
                severity="ERROR",
            )
        )
    if not project.get("study_type"):
        result.add(
            issue(
                "MISSING_STUDY_TYPE",
                "Manifest is missing 'project.study_type'.",
                remediation="Add the study type (e.g. Experimental, Observational, Survey) under 'project.study_type'.",
                field_path="project.study_type",
                severity="ERROR",
            )
        )
    if not project.get("language"):
        result.add(
            issue(
                "MISSING_LANGUAGE",
                "Manifest is missing 'project.language'.",
                remediation="Add the manuscript language under 'project.language'.",
                field_path="project.language",
                severity="ERROR",
            )
        )

    authors_for_structural_check = raw.get("authors")
    authors: list[Any] = (
        authors_for_structural_check if isinstance(authors_for_structural_check, list) else []
    )
    if not authors:
        result.add(
            issue(
                "MISSING_AUTHORS",
                "Manifest has no authors.",
                remediation="Add at least one author with 'id' and 'name' under 'authors'.",
                field_path="authors",
                severity="ERROR",
            )
        )
    else:
        for idx, a in enumerate(authors):
            if not isinstance(a, dict) or not a.get("id"):
                result.add(
                    issue(
                        "MISSING_AUTHOR_ID",
                        f"authors[{idx}] is missing 'id'.",
                        remediation="Give every author a stable, unique 'id'.",
                        field_path=f"authors[{idx}].id",
                        severity="ERROR",
                    )
                )
            if not isinstance(a, dict) or not a.get("name"):
                result.add(
                    issue(
                        "MISSING_AUTHOR_NAME",
                        f"authors[{idx}] is missing 'name'.",
                        remediation="Give every author a 'name'.",
                        field_path=f"authors[{idx}].name",
                        severity="ERROR",
                    )
                )

    research_raw = raw.get("research")
    research: dict[str, Any] = research_raw if isinstance(research_raw, dict) else {}
    if not research.get("primary_question"):
        result.add(
            issue(
                "MISSING_PRIMARY_QUESTION",
                "Manifest is missing 'research.primary_question'.",
                remediation="State the primary research question under 'research.primary_question'.",
                field_path="research.primary_question",
                severity="ERROR",
            )
        )

    manuscript_raw = raw.get("manuscript")
    manuscript: dict[str, Any] = manuscript_raw if isinstance(manuscript_raw, dict) else {}
    if not manuscript.get("generation_policy"):
        result.add(
            issue(
                "MISSING_GENERATION_POLICY",
                "Manifest is missing 'manuscript.generation_policy'.",
                remediation="Set 'manuscript.generation_policy' (e.g. 'validation_only', 'outline_only', 'draft_with_placeholders').",
                field_path="manuscript.generation_policy",
                severity="ERROR",
            )
        )
    if not manuscript.get("required_sections"):
        result.add(
            issue(
                "MISSING_REQUIRED_SECTIONS",
                "Manifest is missing 'manuscript.required_sections'.",
                remediation="List the manuscript's required sections under 'manuscript.required_sections'.",
                field_path="manuscript.required_sections",
                severity="ERROR",
            )
        )

    return result


def validate_manifest(
    manifest: ProjectManifest, *, mode: str = "draft"
) -> ValidationResult:
    """Validate an already-built :class:`ProjectManifest`.

    Prefer :func:`validate_manifest_dict` when you still have the raw
    mapping available (e.g. straight out of the loader) since it can report
    unknown/misspelled fields that ``ProjectManifest.from_dict`` silently
    drops.
    """

    return validate_manifest_dict(manifest.to_dict(), mode=mode)


__all__ = [
    "MODES",
    "ValidationResult",
    "validate_manifest",
    "validate_manifest_dict",
]
