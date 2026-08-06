"""The generic :class:`Requirement` model shared by every rule in the
requirements engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STATUSES = frozenset(
    {
        "PROVIDED",
        "DISCOVERED",
        "VERIFIED",
        "MISSING",
        "PLACEHOLDER",
        "NOT_APPLICABLE",
        "CONFLICTING",
        "NEEDS_AUTHOR_REVIEW",
        "INACCESSIBLE",
        "UNSUPPORTED",
    }
)

SEVERITIES = frozenset({"ERROR", "WARNING", "INFO"})

MODES = ("outline", "draft", "review", "submission")

#: Statuses that count as "satisfied" for the purpose of deciding whether a
#: requirement blocks a mode.
_SATISFIED_STATUSES = frozenset(
    {"PROVIDED", "DISCOVERED", "VERIFIED", "NOT_APPLICABLE"}
)


@dataclass
class Requirement:
    id: str
    category: str
    title: str
    description: str = ""
    required: bool = True
    status: str = "MISSING"
    severity: str = "ERROR"
    source: str = ""
    source_locator: str = ""
    validation_rule: str = ""
    remediation: str = ""
    blocking_modes: list[str] = field(default_factory=list)
    venue_origin: str = ""
    author_review_required: bool = False
    related_fields: list[str] = field(default_factory=list)

    @property
    def satisfied(self) -> bool:
        return self.status in _SATISFIED_STATUSES

    def blocks(self, mode: str) -> bool:
        """Whether this (unsatisfied) requirement blocks the given mode."""

        if self.satisfied:
            return False
        if not self.required:
            return False
        return mode in self.blocking_modes

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "required": self.required,
            "status": self.status,
            "severity": self.severity,
            "source": self.source,
            "source_locator": self.source_locator,
            "validation_rule": self.validation_rule,
            "remediation": self.remediation,
            "blocking_modes": list(self.blocking_modes),
            "venue_origin": self.venue_origin,
            "author_review_required": self.author_review_required,
            "related_fields": list(self.related_fields),
            "satisfied": self.satisfied,
        }


__all__ = ["MODES", "SEVERITIES", "STATUSES", "Requirement"]
