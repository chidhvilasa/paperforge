"""Mode-aware requirements engine.

Combines the canonical project manifest, detected repository content,
venue conventions, evidence classes, and the requested mode
(``outline``/``draft``/``review``/``submission``) into a single, ordered
list of :class:`~paperforge.requirements_engine.models.Requirement` objects.

Nothing here hardcodes funding/ethics/consent/DOI/ORCID/statistics/
datasets/figures/code-availability as universally mandatory: every rule
states *when* it applies before deciding whether it is satisfied.
"""

from __future__ import annotations

from paperforge.requirements_engine.engine import evaluate_requirements
from paperforge.requirements_engine.models import (
    MODES,
    SEVERITIES,
    STATUSES,
    Requirement,
)

__all__ = [
    "MODES",
    "SEVERITIES",
    "STATUSES",
    "Requirement",
    "evaluate_requirements",
]
