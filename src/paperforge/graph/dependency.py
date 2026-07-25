"""Dependency graph."""

from __future__ import annotations

from dataclasses import dataclass, field

from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


@dataclass
class AffectedNodes:
    claims: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)


class ResearchGraph:
    def __init__(self) -> None:
        self._claims: dict[str, Claim] = {}
        self._experiments: dict[str, Experiment] = {}

    def add_claim(self, claim: Claim) -> None:
        self._claims[claim.id] = claim

    def add_experiment(self, experiment: Experiment) -> None:
        self._experiments[experiment.id] = experiment

    def get_affected(self, experiment_id: str) -> AffectedNodes:
        affected = AffectedNodes()
        for claim in self._claims.values():
            if claim.experiment != experiment_id:
                continue
            affected.claims.append(claim.id)
            for section in claim.sections:
                if section not in affected.sections:
                    affected.sections.append(section)
            for figure in claim.figures:
                if figure not in affected.figures:
                    affected.figures.append(figure)
            for table in claim.tables:
                if table not in affected.tables:
                    affected.tables.append(table)
        return affected

    @property
    def claim_count(self) -> int:
        return len(self._claims)

    @property
    def experiment_count(self) -> int:
        return len(self._experiments)
