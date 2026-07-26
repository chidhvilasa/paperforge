from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Table:
    id: str                     # e.g. "tbl_01" — matches filename stem
    caption: str = ""           # caption text (appears ABOVE table in IEEE)
    columns: list[str] = field(default_factory=list)
                                # column header names e.g. ["Method", "Accuracy", "F1"]
    rows: list[list[str]] = field(default_factory=list)
                                # data rows e.g. [["B2", "91.2%", "90.8%"], ...]
    notes: str = ""             # footnotes or table notes
    first_mentioned_in: str | None = None
                                # section where table is first referenced
    source_experiment: str | None = None
                                # experiment id that generated this table's data
    wide: bool = False         # spans both columns (table*) in IEEE two-column layout

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> Table:
        return cls(
            id=data["id"],
            caption=data.get("caption", ""),
            columns=data.get("columns") or [],
            rows=data.get("rows") or [],
            notes=data.get("notes", ""),
            first_mentioned_in=data.get("first_mentioned_in"),
            source_experiment=data.get("source_experiment"),
            wide=data.get("wide", False),
        )

    def to_yaml(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "caption": self.caption,
            "columns": self.columns,
            "rows": self.rows,
            "notes": self.notes,
            "first_mentioned_in": self.first_mentioned_in,
            "source_experiment": self.source_experiment,
            "wide": self.wide,
        }
