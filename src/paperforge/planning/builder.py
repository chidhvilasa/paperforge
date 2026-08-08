"""Builds a :class:`~paperforge.planning.models.GenerationPlan` deterministically
from a :class:`~paperforge.project_manifest.models.ProjectManifest`.

The plan never contains manuscript prose -- only structure: which claims,
evidence, citations, figures, and tables are in scope for each section, plus
unresolved questions, prohibited claims, venue constraints, expected
outputs, and validation gates.
"""

from __future__ import annotations

from datetime import UTC, datetime

from paperforge.planning.models import GenerationPlan, SectionPlan
from paperforge.project_manifest.models import ClaimEntry, ProjectManifest

#: Human-readable purpose text for common section names. Sections outside
#: this table get a generic purpose statement -- this is a convenience
#: default, not a claim about any particular venue's requirements.
_SECTION_PURPOSES = {
    "abstract": "Summarize the research question, method, and key findings in brief.",
    "introduction": "State the problem, motivation, and contributions.",
    "related_work": "Situate the work relative to the closest prior research.",
    "related work": "Situate the work relative to the closest prior research.",
    "background": "Provide context and definitions needed to follow the rest of the paper.",
    "methodology": "Describe the study design, data, systems, and procedures used.",
    "methods": "Describe the study design, data, systems, and procedures used.",
    "results": "Report the direct, derived, and statistical findings, with evidence.",
    "discussion": "Interpret the results, note limitations, and compare to expectations.",
    "conclusion": "Summarize contributions, limitations, and future work.",
    "limitations": "State the known limitations of the study.",
    "future_work": "Describe planned or suggested follow-up work.",
}

#: Deterministic heuristic mapping evidence class -> preferred section name,
#: used only when the manifest doesn't otherwise indicate where a claim
#: belongs. Falls back to "introduction" for assertions/support and
#: "results" for anything result-shaped.
_EVIDENCE_CLASS_SECTION_HINT = {
    "AUTHOR_ASSERTED": "introduction",
    "SOURCE_SUPPORTED": "related_work",
    "DIRECT_RESULT": "results",
    "DERIVED_RESULT": "results",
    "STATISTICAL_RESULT": "results",
    "INTERPRETATION": "discussion",
    "HYPOTHESIS": "introduction",
    "LIMITATION": "discussion",
    "FUTURE_WORK": "conclusion",
    "PLACEHOLDER": "",
}

_VALIDATION_GATES = [
    "doctor",
    "build",
    "preflight",
    "references",
    "provenance.validate",
]


def _section_purpose(name: str) -> str:
    return _SECTION_PURPOSES.get(
        name.strip().lower(), f"Content for the '{name}' section."
    )


def _preferred_section_for_claim(
    claim: ClaimEntry, available_sections: list[str]
) -> str | None:
    hint = _EVIDENCE_CLASS_SECTION_HINT.get(claim.evidence_class, "")
    if hint and hint in [s.lower() for s in available_sections]:
        for s in available_sections:
            if s.lower() == hint:
                return s
    # fall back to the first available section as a catch-all so no claim
    # is silently dropped from the plan.
    return available_sections[0] if available_sections else None


def build_plan(manifest: ProjectManifest) -> GenerationPlan:
    section_names = list(manifest.manuscript.section_order) or list(
        manifest.manuscript.required_sections
    )
    sections = [
        SectionPlan(name=name, purpose=_section_purpose(name)) for name in section_names
    ]
    section_by_name = {s.name: s for s in sections}

    prohibited: list[str] = []
    for claim in manifest.claims:
        if claim.evidence_class == "PLACEHOLDER":
            prohibited.append(claim.id)
            continue
        target = _preferred_section_for_claim(claim, section_names)
        if target is None:
            continue
        sp = section_by_name[target]
        sp.claim_ids.append(claim.id)
        sp.evidence_refs.extend(
            r for r in claim.evidence_refs if r not in sp.evidence_refs
        )
        sp.citation_keys.extend(
            k for k in claim.citation_keys if k not in sp.citation_keys
        )

    results_section = next((s for s in sections if s.name.lower() == "results"), None)
    if results_section is not None:
        for fig in manifest.evidence.figures:
            if fig not in results_section.figures:
                results_section.figures.append(fig)
        for tbl in manifest.evidence.tables:
            if tbl not in results_section.tables:
                results_section.tables.append(tbl)

    declarations_in_scope = [
        field_name
        for field_name, value in (
            ("funding", manifest.declarations.funding),
            ("conflicts_of_interest", manifest.declarations.conflicts_of_interest),
            ("ethics_approval", manifest.declarations.ethics_approval),
            ("informed_consent", manifest.declarations.informed_consent),
            ("data_availability", manifest.declarations.data_availability),
            ("code_availability", manifest.declarations.code_availability),
            ("author_contributions", manifest.declarations.author_contributions),
            ("acknowledgments", manifest.declarations.acknowledgments),
        )
        if value
    ]

    unresolved_questions = list(manifest.research.secondary_questions)
    pending_review = [
        c.id
        for c in manifest.claims
        if c.author_review_status not in {"approved", "reviewed"}
    ]
    if pending_review:
        unresolved_questions.append(
            f"{len(pending_review)} claim(s) pending author review: {', '.join(pending_review)}"
        )

    venue_constraints = {
        "target_venue": manifest.project.target_venue,
        "abstract_limit": manifest.manuscript.abstract_limit,
        "keyword_limit": manifest.manuscript.keyword_limit,
        "figure_limit": manifest.manuscript.figure_limit,
        "table_limit": manifest.manuscript.table_limit,
        "anonymous_review": manifest.manuscript.anonymous_review,
    }

    expected_outputs = [f"sections/{name}.md" for name in section_names]
    expected_outputs.append("provenance/index.json")

    return GenerationPlan(
        sections=sections,
        declarations_in_scope=declarations_in_scope,
        unresolved_questions=unresolved_questions,
        prohibited_claims=prohibited,
        venue_constraints=venue_constraints,
        expected_outputs=expected_outputs,
        validation_gates=list(_VALIDATION_GATES),
        generated_at=datetime.now(UTC).isoformat(),
    )


__all__ = ["build_plan"]
