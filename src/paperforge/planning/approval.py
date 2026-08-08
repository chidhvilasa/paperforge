"""Plan approval: content-hash recording and invalidation checking.

An approval records four independent SHA-256 hashes (manifest, evidence
inventory, claim set, plan). Any change to the manifest, its evidence
inventory, its claim set, the venue, the section structure, or required
declarations changes at least one of these hashes, which is exactly how
:func:`check_approval_validity` detects that a stored approval is stale.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from paperforge.planning.models import GenerationPlan, PlanApproval
from paperforge.project_manifest.models import ProjectManifest


def _hash_obj(obj: object) -> str:
    text = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def manifest_hash(manifest: ProjectManifest) -> str:
    return _hash_obj(manifest.to_dict())


def evidence_hash(manifest: ProjectManifest) -> str:
    return _hash_obj(
        {
            "evidence": manifest.evidence.__dict__,
            "literature_bibliography": sorted(manifest.literature.bibliography),
        }
    )


def claim_set_hash(manifest: ProjectManifest) -> str:
    return _hash_obj(
        sorted(
            (c.id, c.text, c.evidence_class, tuple(sorted(c.evidence_refs)))
            for c in manifest.claims
        )
    )


def plan_hash(plan: GenerationPlan) -> str:
    data = plan.to_dict()
    data.pop("generated_at", None)  # timestamp must not affect content identity
    return _hash_obj(data)


def approve_plan(
    manifest: ProjectManifest,
    plan: GenerationPlan,
    *,
    approver: str,
    mode: str = "submission",
) -> PlanApproval:
    return PlanApproval(
        manifest_hash=manifest_hash(manifest),
        evidence_hash=evidence_hash(manifest),
        claim_set_hash=claim_set_hash(manifest),
        plan_hash=plan_hash(plan),
        venue=manifest.project.target_venue,
        timestamp=datetime.now(UTC).isoformat(),
        approver=approver,
        mode=mode,
    )


def check_approval_validity(
    manifest: ProjectManifest,
    plan: GenerationPlan,
    approval: PlanApproval,
) -> list[str]:
    """Return a list of human-readable reasons the approval is stale.

    An empty list means the approval is still valid for the current
    manifest/plan state.
    """

    reasons = []
    if approval.manifest_hash != manifest_hash(manifest):
        reasons.append("The project manifest has changed since this plan was approved.")
    if approval.evidence_hash != evidence_hash(manifest):
        reasons.append(
            "The evidence inventory has changed since this plan was approved."
        )
    if approval.claim_set_hash != claim_set_hash(manifest):
        reasons.append("The claim set has changed since this plan was approved.")
    if approval.plan_hash != plan_hash(plan):
        reasons.append(
            "The generation plan (sections, venue constraints, etc.) has changed since approval."
        )
    if approval.venue != manifest.project.target_venue:
        reasons.append(
            f"The target venue changed ('{approval.venue}' -> '{manifest.project.target_venue}') since approval."
        )
    return reasons


__all__ = [
    "approve_plan",
    "check_approval_validity",
    "claim_set_hash",
    "evidence_hash",
    "manifest_hash",
    "plan_hash",
]
