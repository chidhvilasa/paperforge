from __future__ import annotations

from dataclasses import dataclass, field
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
    source_experiment: str | None = None  # experiment to plot
    chart_type: str = "auto"              # bar, line, scatter, grouped_bar, auto
    x_label: str = ""                     # x-axis label
    y_label: str = ""                     # y-axis label
    chart_title: str = ""                 # chart title (optional)
    metric_keys: list[str] = field(default_factory=list)  # specific metric keys to plot
    x_labels: list[str] = field(default_factory=list)     # custom tick labels for metrics
    is_math: bool = False                 # caption contains raw LaTeX math
    line_experiments: list[str] = field(default_factory=list)  # additional experiments for line chart series
    x_values: list[float] = field(default_factory=list)        # numeric X values for line chart
    error_bars: bool = False              # show uncertainty/error bars
    std_metric_keys: list[str] = field(default_factory=list)   # metric keys for standard deviation
    significance_markers: list[str] = field(default_factory=list) # significance markers e.g. ["*", "**", "n.s."]

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
            source_experiment=data.get("source_experiment"),
            chart_type=data.get("chart_type", "auto"),
            x_label=data.get("x_label", ""),
            y_label=data.get("y_label", ""),
            chart_title=data.get("chart_title", ""),
            metric_keys=data.get("metric_keys") or [],
            x_labels=data.get("x_labels") or [],
            is_math=bool(data.get("is_math", False)),
            line_experiments=data.get("line_experiments") or [],
            x_values=[float(v) for v in data.get("x_values") or []],
            error_bars=bool(data.get("error_bars", False)),
            std_metric_keys=data.get("std_metric_keys") or [],
            significance_markers=data.get("significance_markers") or [],
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
            "source_experiment": self.source_experiment,
            "chart_type": self.chart_type,
            "x_label": self.x_label,
            "y_label": self.y_label,
            "chart_title": self.chart_title,
            "metric_keys": self.metric_keys,
            "x_labels": self.x_labels,
            "is_math": self.is_math,
            "line_experiments": self.line_experiments,
            "x_values": self.x_values,
            "error_bars": self.error_bars,
            "std_metric_keys": self.std_metric_keys,
            "significance_markers": self.significance_markers,
        }
