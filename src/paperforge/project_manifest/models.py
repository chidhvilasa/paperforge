"""Typed models for the canonical project manifest (``paperforge.project.yaml``).

These dataclasses mirror the ten evidence classes and other conventions
already shipped in PaperForge 1.6.0 (see :mod:`paperforge.models.claim`) so
that a manifest's ``claims`` section can be produced from, or reconciled
with, the existing per-claim data model without duplicating definitions.

Only ``project.title``, ``project.research_domain``, ``project.study_type``,
``project.language``, at least one author with ``id``/``name``,
``research.primary_question``, and ``manuscript.generation_policy`` +
``manuscript.required_sections`` are structurally required. Funding, ethics,
consent, DOI, ORCID, statistics, datasets, figures, and code-availability
requirements are *never* hardcoded as universally mandatory here — whether
they are required depends on study type, venue, mode, and declarations, and
is decided by :mod:`paperforge.requirements_engine`, not by this module.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, ClassVar

CURRENT_SCHEMA_VERSION = "1.0"

#: Evidence-class taxonomy, kept identical to paperforge.models.claim so the
#: two subsystems never drift apart.
EVIDENCE_CLASSES = frozenset(
    {
        "AUTHOR_ASSERTED",
        "SOURCE_SUPPORTED",
        "DIRECT_RESULT",
        "DERIVED_RESULT",
        "STATISTICAL_RESULT",
        "INTERPRETATION",
        "HYPOTHESIS",
        "LIMITATION",
        "FUTURE_WORK",
        "PLACEHOLDER",
    }
)


def _ordered_dict(dc: Any) -> dict[str, Any]:
    """Serialize a dataclass instance to a plain dict, preserving declared
    field order, recursing into nested dataclasses/lists/dicts."""

    if dataclasses.is_dataclass(dc) and not isinstance(dc, type):
        out: dict[str, Any] = {}
        for f in dataclasses.fields(dc):
            out[f.name] = _ordered_dict(getattr(dc, f.name))
        return out
    if isinstance(dc, list):
        return [_ordered_dict(item) for item in dc]  # type: ignore[return-value]
    if isinstance(dc, dict):
        return {k: _ordered_dict(v) for k, v in dc.items()}  # type: ignore[return-value]
    return dc


def _build(dc_cls: type, data: Any) -> Any:
    """Build a dataclass instance from a (possibly partial) mapping,
    ignoring unknown keys (unknown-field *policy* is enforced separately by
    the validator; the loader itself must never raise merely because a
    field is unrecognized, so drafts round-trip even with foreign content
    stashed for review).
    """

    if not isinstance(data, dict):
        data = {}
    field_names = {f.name for f in dataclasses.fields(dc_cls)}
    kwargs: dict[str, Any] = {}
    for k, v in data.items():
        if k not in field_names:
            continue
        kwargs[k] = v
    return dc_cls(**kwargs)


@dataclass
class ProjectIdentity:
    title: str = ""
    short_title: str = ""
    subtitle: str = ""
    research_domain: str = ""
    study_type: str = ""
    project_status: str = "draft"
    language: str = "English"
    target_venue: str = ""
    target_format: str = ""
    deadline: str = ""
    repository_url: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectIdentity:
        return _build(cls, data)  # type: ignore[return-value]


@dataclass
class AuthorEntry:
    id: str = ""
    name: str = ""
    email: str = ""
    orcid: str = ""
    affiliations: list[str] = field(default_factory=list)
    corresponding: bool = False
    biography: str = ""
    contribution_roles: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthorEntry:
        return _build(cls, data)  # type: ignore[return-value]


@dataclass
class ResearchBasis:
    problem_statement: str = ""
    motivation: str = ""
    primary_question: str = ""
    secondary_questions: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    objectives: list[str] = field(default_factory=list)
    claimed_contributions: list[str] = field(default_factory=list)
    scope: str = ""
    limitations: str = ""
    future_work: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchBasis:
        return _build(cls, data)  # type: ignore[return-value]


@dataclass
class Methodology:
    study_design: str = ""
    datasets: list[str] = field(default_factory=list)
    participants: str = ""
    systems: list[str] = field(default_factory=list)
    hardware: list[str] = field(default_factory=list)
    software: list[str] = field(default_factory=list)
    experimental_conditions: list[str] = field(default_factory=list)
    baselines: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    statistical_plan: str = ""
    assumptions: list[str] = field(default_factory=list)
    threat_model: str = ""
    ethics: str = ""
    consent: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Methodology:
        return _build(cls, data)  # type: ignore[return-value]


@dataclass
class EvidenceInventory:
    raw_data: list[str] = field(default_factory=list)
    processed_data: list[str] = field(default_factory=list)
    canonical_results: list[str] = field(default_factory=list)
    experiment_manifests: list[str] = field(default_factory=list)
    benchmark_results: list[str] = field(default_factory=list)
    notebooks: list[str] = field(default_factory=list)
    analysis_scripts: list[str] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    source_code: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceInventory:
        return _build(cls, data)  # type: ignore[return-value]


@dataclass
class Literature:
    bibliography: list[str] = field(default_factory=list)
    search_log: str = ""
    inclusion_criteria: str = ""
    exclusion_criteria: str = ""
    closest_work: list[str] = field(default_factory=list)
    novelty_statement: str = ""
    reference_verification_status: str = "unverified"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Literature:
        return _build(cls, data)  # type: ignore[return-value]


@dataclass
class ClaimEntry:
    id: str = ""
    text: str = ""
    evidence_class: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    citation_keys: list[str] = field(default_factory=list)
    author_review_status: str = "pending"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClaimEntry:
        return _build(cls, data)  # type: ignore[return-value]


@dataclass
class ManuscriptPlanConfig:
    generation_policy: str = "validation_only"
    required_sections: list[str] = field(default_factory=list)
    optional_sections: list[str] = field(default_factory=list)
    section_order: list[str] = field(default_factory=list)
    target_length: str = ""
    abstract_limit: int = 0
    keyword_limit: int = 0
    figure_limit: int = 0
    table_limit: int = 0
    anonymous_review: bool = False
    supplementary_material: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManuscriptPlanConfig:
        return _build(cls, data)  # type: ignore[return-value]


@dataclass
class Declarations:
    funding: str = ""
    conflicts_of_interest: str = ""
    ethics_approval: str = ""
    informed_consent: str = ""
    data_availability: str = ""
    code_availability: str = ""
    author_contributions: str = ""
    acknowledgments: str = ""
    ai_use: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Declarations:
        return _build(cls, data)  # type: ignore[return-value]


@dataclass
class SubmissionPackaging:
    cover_letter: str = ""
    highlights: list[str] = field(default_factory=list)
    graphical_abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    reviewer_suggestions: list[str] = field(default_factory=list)
    reviewer_exclusions: list[str] = field(default_factory=list)
    source_package: str = ""
    overleaf_package: str = ""
    checklist: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubmissionPackaging:
        return _build(cls, data)  # type: ignore[return-value]


@dataclass
class ProjectManifest:
    """The canonical, top-level PaperForge project manifest."""

    schema_version: str = CURRENT_SCHEMA_VERSION
    project: ProjectIdentity = field(default_factory=ProjectIdentity)
    authors: list[AuthorEntry] = field(default_factory=list)
    research: ResearchBasis = field(default_factory=ResearchBasis)
    methodology: Methodology = field(default_factory=Methodology)
    evidence: EvidenceInventory = field(default_factory=EvidenceInventory)
    literature: Literature = field(default_factory=Literature)
    claims: list[ClaimEntry] = field(default_factory=list)
    manuscript: ManuscriptPlanConfig = field(default_factory=ManuscriptPlanConfig)
    declarations: Declarations = field(default_factory=Declarations)
    submission: SubmissionPackaging = field(default_factory=SubmissionPackaging)
    extensions: dict[str, Any] = field(default_factory=dict)

    #: Top-level keys in canonical, stable serialization order.
    TOP_LEVEL_ORDER: ClassVar[tuple[str, ...]] = (
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
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectManifest:
        if not isinstance(data, dict):
            data = {}
        extensions = data.get("extensions", {})
        if not isinstance(extensions, dict):
            extensions = {}
        return cls(
            schema_version=str(
                data.get("schema_version", CURRENT_SCHEMA_VERSION)
                or CURRENT_SCHEMA_VERSION
            ),
            project=ProjectIdentity.from_dict(data.get("project") or {}),
            authors=[
                AuthorEntry.from_dict(a)
                for a in (data.get("authors") or [])
                if isinstance(a, dict)
            ],
            research=ResearchBasis.from_dict(data.get("research") or {}),
            methodology=Methodology.from_dict(data.get("methodology") or {}),
            evidence=EvidenceInventory.from_dict(data.get("evidence") or {}),
            literature=Literature.from_dict(data.get("literature") or {}),
            claims=[
                ClaimEntry.from_dict(c)
                for c in (data.get("claims") or [])
                if isinstance(c, dict)
            ],
            manuscript=ManuscriptPlanConfig.from_dict(data.get("manuscript") or {}),
            declarations=Declarations.from_dict(data.get("declarations") or {}),
            submission=SubmissionPackaging.from_dict(data.get("submission") or {}),
            extensions=extensions,
        )

    def to_dict(self) -> dict[str, Any]:
        full = _ordered_dict(self)
        return {k: full[k] for k in self.TOP_LEVEL_ORDER if k in full}

    def to_yaml_text(self) -> str:
        import yaml

        return yaml.safe_dump(
            self.to_dict(),
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )

    def to_json_text(self, *, indent: int = 2) -> str:
        import json

        return json.dumps(
            self.to_dict(), indent=indent, sort_keys=False, ensure_ascii=False
        )


__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "EVIDENCE_CLASSES",
    "AuthorEntry",
    "ClaimEntry",
    "Declarations",
    "EvidenceInventory",
    "Literature",
    "ManuscriptPlanConfig",
    "Methodology",
    "ProjectIdentity",
    "ProjectManifest",
    "ResearchBasis",
    "SubmissionPackaging",
]
