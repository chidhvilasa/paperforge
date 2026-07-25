"""Experiment model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Experiment:
    id: str
    description: str = ""
    results_file: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    hardware: str | None = None
    dataset: str | None = None
    seed: int | None = None
    ran_at: date | None = None

    @classmethod
    def from_yaml(cls, data: dict) -> Experiment:
        ran_at = None
        if data.get("ran_at"):
            ran_at = date.fromisoformat(str(data["ran_at"]))
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            results_file=data.get("results_file"),
            metrics=data.get("metrics", {}),
            hardware=data.get("hardware"),
            dataset=data.get("dataset"),
            seed=data.get("seed"),
            ran_at=ran_at,
        )

    def to_yaml(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "results_file": self.results_file,
            "metrics": self.metrics,
            "hardware": self.hardware,
            "dataset": self.dataset,
            "seed": self.seed,
            "ran_at": self.ran_at.isoformat() if self.ran_at else None,
        }
