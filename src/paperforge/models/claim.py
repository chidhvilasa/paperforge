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
    experiments: list[str] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    status: ClaimStatus = "unverified"
    last_verified: date | None = None
    subsection: str = ""
    algorithms: list[str] = field(default_factory=list)
    is_contribution: bool = False
    compared_work: str = ""
    is_math: bool = False
    raw_latex: bool = False
    claim_type: str = "claim"  # claim, theorem, lemma, definition, proof, corollary, remark
    import_hash: str = ""

    @classmethod
    def from_yaml(cls, data: dict) -> Claim:
        last_verified = None
        if data.get("last_verified"):
            last_verified = date.fromisoformat(str(data["last_verified"]))
        return cls(
            id=data["id"],
            text=data.get("text", ""),
            experiment=data.get("experiment", ""),
            experiments=data.get("experiments", []),
            figures=data.get("figures", []),
            tables=data.get("tables", []),
            citations=data.get("citations", []),
            sections=data.get("sections", []),
            status=data.get("status", "unverified"),
            last_verified=last_verified,
            subsection=data.get("subsection", ""),
            algorithms=data.get("algorithms", []),
            is_contribution=bool(data.get("is_contribution", False)),
            compared_work=data.get("compared_work", ""),
            is_math=bool(data.get("is_math", False)),
            raw_latex=bool(data.get("raw_latex", False)),
            claim_type=str(data.get("claim_type", "claim")),
            import_hash=str(data.get("import_hash", "")),
        )

    def to_yaml(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "experiment": self.experiment,
            "experiments": self.experiments,
            "figures": self.figures,
            "tables": self.tables,
            "citations": self.citations,
            "sections": self.sections,
            "status": self.status,
            "last_verified": (
                self.last_verified.isoformat() if self.last_verified else None
            ),
            "subsection": self.subsection,
            "algorithms": self.algorithms,
            "is_contribution": self.is_contribution,
            "compared_work": self.compared_work,
            "is_math": self.is_math,
            "raw_latex": self.raw_latex,
            "claim_type": self.claim_type,
            "import_hash": self.import_hash,
        }
