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
    auto_rows_from_experiment: str | None = None
    is_math: bool = False      # caption contains raw LaTeX math
    raw_latex_rows: bool = False  # skip escaping table row cells

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
            auto_rows_from_experiment=data.get("auto_rows_from_experiment"),
            is_math=bool(data.get("is_math", False)),
            raw_latex_rows=bool(data.get("raw_latex_rows", False)),
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
            "auto_rows_from_experiment": self.auto_rows_from_experiment,
            "is_math": self.is_math,
            "raw_latex_rows": self.raw_latex_rows,
        }
