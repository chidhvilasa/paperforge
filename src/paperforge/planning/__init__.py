"""Approval-gated manuscript generation planning.

A :class:`~paperforge.planning.models.GenerationPlan` is a structural plan
(section order, purpose, which claims/evidence/citations/figures/tables are
in scope per section, unresolved questions, prohibited claims, venue
constraints, expected outputs, validation gates) built deterministically
from the canonical manifest. It never contains final prose.

A :class:`~paperforge.planning.models.PlanApproval` records that a human (or
an agent acting on a human's behalf) has reviewed a specific plan for a
specific manifest/evidence/claim-set state, via four content hashes.
Generation (:mod:`paperforge.generation`) refuses to run in its default,
fully-validated mode unless a currently-valid approval exists for the
current plan and manifest state.
"""

from __future__ import annotations

from paperforge.planning.approval import approve_plan, check_approval_validity
from paperforge.planning.builder import build_plan
from paperforge.planning.models import GenerationPlan, PlanApproval, SectionPlan

__all__ = [
    "GenerationPlan",
    "PlanApproval",
    "SectionPlan",
    "approve_plan",
    "build_plan",
    "check_approval_validity",
]
