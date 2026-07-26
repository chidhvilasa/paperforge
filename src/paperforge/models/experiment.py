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
    seeds: list[int] | None = None
    ran_at: date | None = None

    @classmethod
    def from_yaml(cls, data: dict) -> Experiment:
        ran_at = None
        if data.get("ran_at"):
            ran_at = date.fromisoformat(str(data["ran_at"]))

        seeds_data = data.get("seeds")
        seeds: list[int] | None
        if isinstance(seeds_data, list):
            seeds = [int(s) for s in seeds_data]
        elif isinstance(seeds_data, str) and "-" in seeds_data:
            parts = seeds_data.split("-")
            try:
                seeds = list(range(int(parts[0]), int(parts[1]) + 1))
            except (ValueError, IndexError):
                seeds = None
        else:
            seeds = None

        return cls(
            id=data["id"],
            description=data.get("description", ""),
            results_file=data.get("results_file"),
            metrics=data.get("metrics", {}),
            hardware=data.get("hardware"),
            dataset=data.get("dataset"),
            seed=data.get("seed"),
            seeds=seeds,
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
            "seeds": self.seeds,
            "ran_at": self.ran_at.isoformat() if self.ran_at else None,
        }
