"""Data model for a generation plan and its approval record."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SectionPlan:
    name: str
    purpose: str = ""
    claim_ids: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    citation_keys: list[str] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "claim_ids": list(self.claim_ids),
            "evidence_refs": list(self.evidence_refs),
            "citation_keys": list(self.citation_keys),
            "figures": list(self.figures),
            "tables": list(self.tables),
        }


@dataclass
class GenerationPlan:
    sections: list[SectionPlan] = field(default_factory=list)
    declarations_in_scope: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    prohibited_claims: list[str] = field(default_factory=list)
    venue_constraints: dict[str, Any] = field(default_factory=dict)
    expected_outputs: list[str] = field(default_factory=list)
    validation_gates: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "sections": [s.to_dict() for s in self.sections],
            "declarations_in_scope": list(self.declarations_in_scope),
            "unresolved_questions": list(self.unresolved_questions),
            "prohibited_claims": list(self.prohibited_claims),
            "venue_constraints": dict(self.venue_constraints),
            "expected_outputs": list(self.expected_outputs),
            "validation_gates": list(self.validation_gates),
        }

    def to_markdown(self) -> str:
        lines = ["# Generation plan", "", f"Generated at: {self.generated_at}", ""]
        lines.append("This plan is structural only. It contains no manuscript prose.")
        lines.append("")
        lines.append("## Section order")
        lines.append("")
        for s in self.sections:
            lines.append(f"### {s.name}")
            lines.append("")
            lines.append(f"- purpose: {s.purpose}")
            lines.append(f"- claims: {', '.join(s.claim_ids) or '(none)'}")
            lines.append(f"- evidence: {', '.join(s.evidence_refs) or '(none)'}")
            lines.append(f"- citations: {', '.join(s.citation_keys) or '(none)'}")
            lines.append(f"- figures: {', '.join(s.figures) or '(none)'}")
            lines.append(f"- tables: {', '.join(s.tables) or '(none)'}")
            lines.append("")
        if self.declarations_in_scope:
            lines.append("## Declarations in scope")
            lines.append("")
            for d in self.declarations_in_scope:
                lines.append(f"- {d}")
            lines.append("")
        if self.unresolved_questions:
            lines.append("## Unresolved questions")
            lines.append("")
            for q in self.unresolved_questions:
                lines.append(f"- {q}")
            lines.append("")
        if self.prohibited_claims:
            lines.append("## Prohibited claims (cannot be used in generation)")
            lines.append("")
            for c in self.prohibited_claims:
                lines.append(f"- {c}")
            lines.append("")
        if self.venue_constraints:
            lines.append("## Venue constraints")
            lines.append("")
            for k, v in self.venue_constraints.items():
                lines.append(f"- {k}: {v}")
            lines.append("")
        lines.append("## Expected outputs")
        lines.append("")
        for o in self.expected_outputs:
            lines.append(f"- {o}")
        lines.append("")
        lines.append("## Validation gates")
        lines.append("")
        for g in self.validation_gates:
            lines.append(f"- {g}")
        lines.append("")
        return "\n".join(lines)


@dataclass
class PlanApproval:
    manifest_hash: str
    evidence_hash: str
    claim_set_hash: str
    plan_hash: str
    venue: str
    timestamp: str
    approver: str
    mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_hash": self.manifest_hash,
            "evidence_hash": self.evidence_hash,
            "claim_set_hash": self.claim_set_hash,
            "plan_hash": self.plan_hash,
            "venue": self.venue,
            "timestamp": self.timestamp,
            "approver": self.approver,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanApproval:
        return cls(
            manifest_hash=str(data.get("manifest_hash", "")),
            evidence_hash=str(data.get("evidence_hash", "")),
            claim_set_hash=str(data.get("claim_set_hash", "")),
            plan_hash=str(data.get("plan_hash", "")),
            venue=str(data.get("venue", "")),
            timestamp=str(data.get("timestamp", "")),
            approver=str(data.get("approver", "")),
            mode=str(data.get("mode", "")),
        )


__all__ = ["GenerationPlan", "PlanApproval", "SectionPlan"]
