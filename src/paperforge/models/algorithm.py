"""Algorithm model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from paperforge.utils.latex import escape_latex


@dataclass
class Algorithm:
    id: str  # e.g. "alg_01"
    caption: str = ""  # algorithm title
    steps: list[str] = field(default_factory=list)  # list of algorithm steps
    notes: str = ""

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> Algorithm:
        return cls(
            id=data["id"],
            caption=data.get("caption", ""),
            steps=data.get("steps") or [],
            notes=data.get("notes", ""),
        )

    def to_yaml(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "caption": self.caption,
            "steps": self.steps,
            "notes": self.notes,
        }

    def to_latex(self) -> str:
        """Generate IEEE-compatible algorithm environment."""
        lines = [
            "\\begin{algorithm}[!t]",
            f"\\caption{{{escape_latex(self.caption)}}}",
            f"\\label{{alg:{self.id}}}",
            "\\begin{algorithmic}[1]",
        ]
        for step in self.steps:
            lines.append(f"  {escape_latex(step)}")
        lines.extend(
            [
                "\\end{algorithmic}",
                "\\end{algorithm}",
            ]
        )
        return "\n".join(lines)
