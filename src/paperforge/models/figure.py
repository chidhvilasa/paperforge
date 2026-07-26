from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Figure:
    id: str                     # e.g. "fig_01" — matches filename stem
    caption: str = ""           # full caption text
    path: str | None = None     # relative path to image file, e.g. "figures/fig_01.png"
    format: str | None = None   # "png", "pdf", "eps", "svg", etc.
    width_inches: float | None = None   # intended width for LaTeX
    resolution_dpi: int | None = None   # DPI for raster images
    first_mentioned_in: str | None = None  # section where fig is first referenced
                                            # e.g. "results"
    notes: str = ""             # any free-form notes about the figure
    wide: bool = False           # spans both columns (figure*) in IEEE two-column layout

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> Figure:
        return cls(
            id=data["id"],
            caption=data.get("caption", ""),
            path=data.get("path"),
            format=data.get("format"),
            width_inches=data.get("width_inches"),
            resolution_dpi=data.get("resolution_dpi"),
            first_mentioned_in=data.get("first_mentioned_in"),
            notes=data.get("notes", ""),
            wide=data.get("wide", False),
        )

    def to_yaml(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "caption": self.caption,
            "path": self.path,
            "format": self.format,
            "width_inches": self.width_inches,
            "resolution_dpi": self.resolution_dpi,
            "first_mentioned_in": self.first_mentioned_in,
            "notes": self.notes,
            "wide": self.wide,
        }
