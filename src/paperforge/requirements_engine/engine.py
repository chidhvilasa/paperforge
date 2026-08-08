"""Requirement evaluation rules.

Every rule function below states its applicability condition before
deciding whether it is satisfied, so nothing becomes universally mandatory
just because it exists as a rule. Rules read only the in-memory
:class:`~paperforge.project_manifest.models.ProjectManifest` and a small
amount of filesystem existence-checking (never file *content* execution).

The venue table here is intentionally tiny and explicitly marked as a
heuristic default, not an authoritative or currently-verified source of
venue policy -- see Milestone 15 / docs/VENUE_ADAPTERS.md for the caveat
this module inherits.
"""

from __future__ import annotations

from pathlib import Path

from paperforge.models.claim import RESULT_EVIDENCE_CLASSES
from paperforge.project_manifest.models import ProjectManifest
from paperforge.requirements_engine.models import Requirement

#: Venues this heuristic default believes conventionally expect author
#: biographies and/or ORCID identifiers. Not sourced/dated; see
#: docs/VENUE_ADAPTERS.md. Venue-specific `paperforge.venues` plugins (used
#: by `paperforge build`/`doctor`) are the authoritative source when they
#: exist for a given target; this table only fills gaps for the
#: requirements engine's own venue-awareness.
_VENUES_EXPECTING_BIOGRAPHY = frozenset({"ieee", "ieee-access", "ieee-journal"})
_VENUES_REQUIRING_ORCID: frozenset[str] = frozenset()

#: Study types that specifically imply human/animal-subject involvement.
#: Deliberately does NOT include generic "experimental"/"clinical" --
#: most computer-science/systems/ML "Experimental" studies (benchmarks,
#: simulations, ablations) involve no participants at all, so treating
#: every experimental study as ethics-applicable would be a false
#: positive. `methodology.participants` being set is the primary,
#: reliable signal; this set only widens applicability for study types
#: that are unambiguous even without that field being filled in yet.
_HUMAN_SUBJECT_STUDY_TYPES = frozenset(
    {
        "clinical trial",
        "randomized controlled trial",
        "human subjects",
        "human-subjects research",
        "survey",
        "user study",
        "interview study",
        "focus group",
    }
)

_NOT_APPLICABLE_MARKERS = frozenset(
    {"not applicable", "n/a", "na", "none", "not applicable.", "no external funding"}
)


def _is_marked_not_applicable(text: str) -> bool:
    return bool(text) and text.strip().lower() in _NOT_APPLICABLE_MARKERS


def _req_abstract(manifest: ProjectManifest) -> Requirement:
    provided = "abstract" in manifest.manuscript.required_sections
    return Requirement(
        id="REQ-ABSTRACT",
        category="manuscript",
        title="Abstract section planned",
        description="An abstract section must be part of the manuscript's required sections.",
        required=True,
        status="PROVIDED" if provided else "MISSING",
        severity="ERROR",
        source="manifest",
        source_locator="manuscript.required_sections",
        validation_rule="'abstract' in manuscript.required_sections",
        remediation="Add 'abstract' to manuscript.required_sections.",
        blocking_modes=["review", "submission"],
        related_fields=["manuscript.required_sections"],
    )


def _req_bibliography(manifest: ProjectManifest) -> Requirement:
    has_citations = bool(manifest.literature.bibliography) or any(
        c.citation_keys for c in manifest.claims
    )
    provided = bool(manifest.literature.bibliography)
    return Requirement(
        id="REQ-BIBLIOGRAPHY",
        category="literature",
        title="Bibliography present",
        description="A bibliography is required whenever claims cite sources.",
        required=has_citations,
        status="PROVIDED"
        if provided
        else ("NOT_APPLICABLE" if not has_citations else "MISSING"),
        severity="ERROR",
        source="manifest",
        source_locator="literature.bibliography",
        validation_rule="literature.bibliography is non-empty when any claim has citation_keys",
        remediation="Add a bibliography file under literature.bibliography.",
        blocking_modes=["submission"] if has_citations else [],
        related_fields=["literature.bibliography", "claims[*].citation_keys"],
    )


def _req_funding(manifest: ProjectManifest) -> Requirement:
    text = manifest.declarations.funding
    return Requirement(
        id="REQ-FUNDING-STATEMENT",
        category="declarations",
        title="Funding statement present",
        description=(
            "A funding statement is always required, but 'no external funding' "
            "is itself a valid, complete statement."
        ),
        required=True,
        status="PROVIDED" if text else "MISSING",
        severity="ERROR",
        source="manifest",
        source_locator="declarations.funding",
        validation_rule="declarations.funding is non-empty",
        remediation="State funding sources, or explicitly state that no external funding was received.",
        blocking_modes=["submission"],
        related_fields=["declarations.funding"],
    )


def _req_data_availability(manifest: ProjectManifest) -> Requirement:
    text = manifest.declarations.data_availability
    return Requirement(
        id="REQ-DATA-AVAILABILITY",
        category="declarations",
        title="Data availability statement present",
        description=(
            "A data availability statement is required even when the data cannot "
            "be shared -- stating that is itself a valid, complete statement."
        ),
        required=True,
        status="PROVIDED" if text else "MISSING",
        severity="ERROR",
        source="manifest",
        source_locator="declarations.data_availability",
        validation_rule="declarations.data_availability is non-empty",
        remediation="State how data can be accessed, or explicitly state that it cannot be shared and why.",
        blocking_modes=["submission"],
        related_fields=["declarations.data_availability"],
    )


def _req_ethics(manifest: ProjectManifest) -> Requirement:
    study_type = (manifest.project.study_type or "").strip().lower()
    involves_participants = bool(manifest.methodology.participants.strip())
    applicable = involves_participants or study_type in _HUMAN_SUBJECT_STUDY_TYPES
    text = manifest.declarations.ethics_approval
    if not applicable:
        status = "NOT_APPLICABLE"
    elif _is_marked_not_applicable(text):
        status = "NOT_APPLICABLE"
    elif text:
        status = "PROVIDED"
    else:
        status = "MISSING"
    return Requirement(
        id="REQ-ETHICS-APPROVAL",
        category="declarations",
        title="Ethics approval statement",
        description="Ethics approval is only required when the study involves participants/human or animal subjects.",
        required=applicable,
        status=status,
        severity="ERROR",
        source="manifest",
        source_locator="declarations.ethics_approval",
        validation_rule="applicable iff methodology.participants set or study_type suggests human/animal subjects",
        remediation="State the ethics approval / IRB reference, or explicitly mark not applicable.",
        blocking_modes=["submission"] if applicable else [],
        related_fields=[
            "declarations.ethics_approval",
            "methodology.participants",
            "project.study_type",
        ],
    )


def _req_consent(manifest: ProjectManifest) -> Requirement:
    involves_participants = bool(manifest.methodology.participants.strip())
    text = manifest.declarations.informed_consent
    if not involves_participants:
        status = "NOT_APPLICABLE"
    elif _is_marked_not_applicable(text):
        status = "NOT_APPLICABLE"
    elif text:
        status = "PROVIDED"
    else:
        status = "MISSING"
    return Requirement(
        id="REQ-INFORMED-CONSENT",
        category="declarations",
        title="Informed consent statement",
        description="Informed consent is only required when the study involves participants.",
        required=involves_participants,
        status=status,
        severity="ERROR",
        source="manifest",
        source_locator="declarations.informed_consent",
        validation_rule="applicable iff methodology.participants is set",
        remediation="State the informed consent procedure, or explicitly mark not applicable.",
        blocking_modes=["submission"] if involves_participants else [],
        related_fields=["declarations.informed_consent", "methodology.participants"],
    )


def _req_corresponding_author(manifest: ProjectManifest) -> Requirement:
    provided = any(a.corresponding for a in manifest.authors)
    return Requirement(
        id="REQ-CORRESPONDING-AUTHOR",
        category="authors",
        title="Corresponding author designated",
        description="Exactly one (or more) author should be marked as corresponding for submission.",
        required=bool(manifest.authors),
        status="PROVIDED" if provided else "MISSING",
        severity="ERROR",
        source="manifest",
        source_locator="authors[*].corresponding",
        validation_rule="any(author.corresponding for author in authors)",
        remediation="Set corresponding: true on at least one author.",
        blocking_modes=["submission"],
        related_fields=["authors[*].corresponding"],
    )


def _req_orcid(manifest: ProjectManifest) -> list[Requirement]:
    venue = (manifest.project.target_venue or "").strip().lower()
    venue_requires = venue in _VENUES_REQUIRING_ORCID
    reqs = []
    for author in manifest.authors:
        status = "PROVIDED" if author.orcid else "MISSING"
        reqs.append(
            Requirement(
                id=f"REQ-ORCID-{author.id or author.name}",
                category="authors",
                title=f"ORCID for {author.name or author.id}",
                description="ORCID is optional unless the target venue requires it.",
                required=venue_requires,
                status=status
                if venue_requires
                else ("PROVIDED" if author.orcid else "NOT_APPLICABLE"),
                severity="WARNING" if not venue_requires else "ERROR",
                source="manifest",
                source_locator=f"authors[id={author.id}].orcid",
                validation_rule="author.orcid is non-empty when venue requires it",
                remediation="Add the author's ORCID identifier.",
                blocking_modes=["submission"] if venue_requires else [],
                venue_origin=venue if venue_requires else "",
                related_fields=["authors[*].orcid"],
            )
        )
    return reqs


def _req_biography(manifest: ProjectManifest) -> list[Requirement]:
    venue = (manifest.project.target_venue or "").strip().lower()
    venue_requires = venue in _VENUES_EXPECTING_BIOGRAPHY
    if not venue_requires:
        return []
    reqs = []
    for author in manifest.authors:
        status = "PROVIDED" if author.biography else "MISSING"
        reqs.append(
            Requirement(
                id=f"REQ-BIOGRAPHY-{author.id or author.name}",
                category="authors",
                title=f"Biography for {author.name or author.id}",
                description=f"Target venue '{venue}' conventionally expects author biographies.",
                required=True,
                status=status,
                severity="WARNING",
                source="venue",
                source_locator=f"authors[id={author.id}].biography",
                validation_rule="author.biography is non-empty",
                remediation="Add a short author biography.",
                blocking_modes=[],
                venue_origin=venue,
                related_fields=["authors[*].biography"],
            )
        )
    return reqs


def _req_result_claims_have_evidence(manifest: ProjectManifest) -> list[Requirement]:
    reqs = []
    for claim in manifest.claims:
        if claim.evidence_class not in RESULT_EVIDENCE_CLASSES:
            continue
        has_support = bool(claim.evidence_refs) or bool(claim.citation_keys)
        reqs.append(
            Requirement(
                id=f"REQ-EVIDENCE-{claim.id}",
                category="evidence",
                title=f"Evidence for claim {claim.id}",
                description=(
                    f"Claims classified as {claim.evidence_class} must reference at "
                    "least one evidence source or citation."
                ),
                required=True,
                status="PROVIDED" if has_support else "UNSUPPORTED",
                severity="ERROR",
                source="evidence",
                source_locator=f"claims[id={claim.id}]",
                validation_rule="evidence_refs or citation_keys is non-empty",
                remediation="Link the claim to at least one evidence file or citation key.",
                blocking_modes=["submission"],
                author_review_required=not has_support,
                related_fields=[
                    f"claims[id={claim.id}].evidence_refs",
                    f"claims[id={claim.id}].citation_keys",
                ],
            )
        )
    return reqs


def _req_placeholder_claims(manifest: ProjectManifest) -> list[Requirement]:
    reqs = []
    for claim in manifest.claims:
        if claim.evidence_class != "PLACEHOLDER":
            continue
        reqs.append(
            Requirement(
                id=f"REQ-PLACEHOLDER-{claim.id}",
                category="evidence",
                title=f"Unresolved placeholder claim {claim.id}",
                description="Placeholder claims may appear in draft/outline output but must be resolved before submission.",
                required=True,
                status="PLACEHOLDER",
                severity="ERROR",
                source="evidence",
                source_locator=f"claims[id={claim.id}]",
                validation_rule="claim.evidence_class != 'PLACEHOLDER'",
                remediation="Replace the placeholder with real evidence, a citation, or reclassify the claim.",
                blocking_modes=["submission"],
                author_review_required=True,
                related_fields=[f"claims[id={claim.id}].evidence_class"],
            )
        )
    return reqs


def _req_statistical_plan(manifest: ProjectManifest) -> Requirement | None:
    has_statistical_claims = any(
        c.evidence_class == "STATISTICAL_RESULT" for c in manifest.claims
    )
    if not has_statistical_claims:
        return None
    provided = bool(manifest.methodology.statistical_plan.strip())
    return Requirement(
        id="REQ-STATISTICAL-PLAN",
        category="methodology",
        title="Statistical analysis plan documented",
        description="A statistical plan is required whenever any claim is classified STATISTICAL_RESULT.",
        required=True,
        status="PROVIDED" if provided else "MISSING",
        severity="ERROR",
        source="manifest",
        source_locator="methodology.statistical_plan",
        validation_rule="methodology.statistical_plan is non-empty when any claim.evidence_class == STATISTICAL_RESULT",
        remediation="Describe the statistical tests, corrections, and assumptions used.",
        blocking_modes=["submission"],
        related_fields=["methodology.statistical_plan"],
    )


def _req_repository_bibliography_file(
    manifest: ProjectManifest, project_root: Path
) -> list[Requirement]:
    """Cross-checks declared bibliography paths against the filesystem
    (existence only -- never reads/executes their content here)."""

    reqs = []
    for rel in manifest.literature.bibliography:
        path = project_root / rel
        exists = path.is_file()
        reqs.append(
            Requirement(
                id=f"REQ-BIBLIOGRAPHY-FILE-{rel}",
                category="literature",
                title=f"Bibliography file exists: {rel}",
                description="Every declared bibliography path must exist in the project.",
                required=True,
                status="VERIFIED" if exists else "INACCESSIBLE",
                severity="ERROR",
                source="repository",
                source_locator=rel,
                validation_rule="path exists on disk",
                remediation=f"Ensure '{rel}' exists relative to the project root.",
                blocking_modes=["submission"],
                related_fields=["literature.bibliography"],
            )
        )
    return reqs


def evaluate_requirements(
    manifest: ProjectManifest,
    *,
    project_root: Path | None = None,
    mode: str = "draft",
) -> list[Requirement]:
    """Evaluate every requirement rule against ``manifest`` for ``mode``.

    Returns a deterministically ordered list (sorted by requirement id).
    ``mode`` only affects each :class:`Requirement`'s ``blocks(mode)``
    outcome, not which requirements are computed -- callers who only care
    about a specific mode's blockers should filter with
    ``[r for r in reqs if r.blocks(mode)]``.
    """

    reqs: list[Requirement] = [
        _req_abstract(manifest),
        _req_bibliography(manifest),
        _req_funding(manifest),
        _req_data_availability(manifest),
        _req_ethics(manifest),
        _req_consent(manifest),
        _req_corresponding_author(manifest),
    ]
    reqs.extend(_req_orcid(manifest))
    reqs.extend(_req_biography(manifest))
    reqs.extend(_req_result_claims_have_evidence(manifest))
    reqs.extend(_req_placeholder_claims(manifest))
    stats_req = _req_statistical_plan(manifest)
    if stats_req:
        reqs.append(stats_req)
    if project_root is not None:
        reqs.extend(_req_repository_bibliography_file(manifest, project_root))

    reqs.sort(key=lambda r: r.id)
    return reqs


__all__ = ["evaluate_requirements"]
