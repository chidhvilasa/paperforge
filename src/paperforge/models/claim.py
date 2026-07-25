"""Claim model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

ClaimStatus = Literal["verified", "unverified", "stale"]


@dataclass
class Claim:
    id: str
    text: str
    experiment: str
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    status: ClaimStatus = "unverified"
    last_verified: date | None = None

    @classmethod
    def from_yaml(cls, data: dict) -> Claim:
        last_verified = None
        if data.get("last_verified"):
            last_verified = date.fromisoformat(str(data["last_verified"]))
        return cls(
            id=data["id"],
            text=data.get("text", ""),
            experiment=data.get("experiment", ""),
            figures=data.get("figures", []),
            tables=data.get("tables", []),
            citations=data.get("citations", []),
            sections=data.get("sections", []),
            status=data.get("status", "unverified"),
            last_verified=last_verified,
        )

    def to_yaml(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "experiment": self.experiment,
            "figures": self.figures,
            "tables": self.tables,
            "citations": self.citations,
            "sections": self.sections,
            "status": self.status,
            "last_verified": (
                self.last_verified.isoformat() if self.last_verified else None
            ),
        }
