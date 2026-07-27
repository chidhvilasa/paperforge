"""paperforge generate-figures command."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from rich.console import Console

from paperforge.core.project import PaperForgeProject
from paperforge.models.experiment import Experiment
from paperforge.models.figure import Figure

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _generate_bar_chart(
    figure: Figure,
    experiment: Experiment,
    output_path: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt

    # Use IEEE-compatible style
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.05,
        }
    )

    metrics = experiment.metrics
    if not metrics:
        return

    # Filter to specified keys if set
    if figure.metric_keys:
        metrics = {k: v for k, v in metrics.items() if k in figure.metric_keys}
        if not metrics:
            console.print(
                f"[yellow]Warning: none of {figure.metric_keys} "
                f"found in {experiment.id} metrics. "
                f"Available: {list(experiment.metrics.keys())}[/yellow]"
            )
            return

    keys = list(metrics.keys())
    values = list(metrics.values())
    tick_labels = figure.x_labels if figure.x_labels else keys

    fig_width = figure.width_inches if figure.width_inches else 3.5
    _fig, ax = plt.subplots(figsize=(fig_width, fig_width * 0.75))

    bars = ax.bar(
        tick_labels, values, color="#2196F3", edgecolor="black", linewidth=0.5
    )

    ax.set_xlabel(figure.x_label or "Metric")
    ax.set_ylabel(figure.y_label or "Value")
    if figure.chart_title:
        ax.set_title(figure.chart_title, fontsize=9)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{val:.2f}",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=300)
    plt.close()


def _generate_line_chart(
    figure: Figure,
    experiments: list[tuple[str, dict]],
    output_path: Path,
) -> None:
    """experiments: list of (label, metrics_dict) tuples.

    Plots each experiment as a separate line series.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.05,
        }
    )

    markers = ["o", "s", "^", "D", "v", "x", "+"]
    linestyles = ["-", "--", "-.", ":", "-", "--", "-."]
    colors = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
    ]

    fig_width = figure.width_inches if figure.width_inches else 3.5
    _fig, ax = plt.subplots(figsize=(fig_width, fig_width * 0.75))

    for i, (label, metrics) in enumerate(experiments):
        if figure.metric_keys:
            values = [metrics.get(k, 0) for k in figure.metric_keys]
        else:
            values = list(metrics.values())

        if figure.x_values and len(figure.x_values) == len(values):
            x = figure.x_values
        else:
            x = list(range(len(values)))

        ax.plot(
            x,
            values,
            marker=markers[i % len(markers)],
            linestyle=linestyles[i % len(linestyles)],
            color=colors[i % len(colors)],
            label=label,
            linewidth=1.0,
            markersize=4,
        )

    ax.set_xlabel(figure.x_label or "X")
    ax.set_ylabel(figure.y_label or "Y")
    if figure.chart_title:
        ax.set_title(figure.chart_title, fontsize=9)
    ax.legend(fontsize=7, framealpha=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if figure.x_labels and figure.x_values:
        ax.set_xticks(figure.x_values)
        ax.set_xticklabels(figure.x_labels, fontsize=8)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=300)
    plt.close()


def run(project_root: Path, figure_id: str | None = None) -> None:
    if not (project_root / ".paperforge").exists():
        console.print(
            "[red]Not a PaperForge project. Run `paperforge init` first.[/red]"
        )
        sys.exit(1)

    project = PaperForgeProject.load(project_root)
    figures_to_process = (
        [f for f in project.figures if f.id == figure_id]
        if figure_id
        else project.figures
    )

    if not figures_to_process:
        if figure_id:
            console.print(f"[red]Figure '{figure_id}' not found.[/red]")
        else:
            console.print("[dim]No figures found to generate.[/dim]")
        return

    exp_map = {e.id: e for e in project.experiments}

    for fig in figures_to_process:
        if not fig.source_experiment and not fig.line_experiments:
            continue

        rel_path = fig.path or f"figures/{fig.id}.png"
        output_path = project_root / rel_path
        chart_type = fig.chart_type.lower()

        if chart_type == "line":
            series: list[tuple[str, dict]] = []
            if fig.source_experiment:
                exp = exp_map.get(fig.source_experiment)
                if exp and exp.metrics:
                    series.append((exp.id, exp.metrics))
            for exp_id in fig.line_experiments:
                exp = exp_map.get(exp_id)
                if exp and exp.metrics:
                    series.append((exp_id, exp.metrics))
            if series:
                _generate_line_chart(fig, series, output_path)
        else:
            exp = exp_map.get(fig.source_experiment or "")
            if exp and exp.metrics:
                _generate_bar_chart(fig, exp, output_path)

        fig.path = rel_path
        fig_yaml_path = (
            project_root / ".paperforge" / "figures" / f"{fig.id}.yaml"
        )
        if fig_yaml_path.exists():
            data = yaml.safe_load(fig_yaml_path.read_text(encoding="utf-8"))
            data["path"] = rel_path
            fig_yaml_path.write_text(
                yaml.dump(data, default_flow_style=False), encoding="utf-8"
            )

        console.print(f"[green]Generated figure '{fig.id}' -> {rel_path}[/green]")
