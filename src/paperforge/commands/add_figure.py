"""paperforge add-figure command."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from paperforge.core.project import PaperForgeProject
from paperforge.models.figure import Figure

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def run(project_root: Path) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    project = PaperForgeProject.load(project_root)

    fig_ids = [fig.id for fig in project.figures]
    existing_figs = ", ".join(sorted(fig_ids)) if fig_ids else "none"

    console.print(
        Panel(
            f"Existing figures: {existing_figs}\n"
            f"Existing claims: {len(project.claims)}\n"
            f"Fill in figure details below.",
            title="Add Figure",
            border_style="cyan",
        )
    )

    next_id = 1
    figures_dir = project.paperforge_dir / "figures"
    if figures_dir.exists():
        for fig_file in figures_dir.glob("fig_*.yaml"):
            try:
                num = int(fig_file.stem.split("_")[1])
                if num >= next_id:
                    next_id = num + 1
            except (IndexError, ValueError):
                continue
    fig_id = f"fig_{next_id:02d}"

    console.print("[bold]Caption[/bold] — full caption as it will appear in the paper")
    caption = typer.prompt("Caption", default="")

    console.print("[bold]File path[/bold] — relative path to image file, e.g. figures/fig_01.png")
    path_val = typer.prompt("Path", default="")
    path = path_val if path_val else None

    console.print("[bold]Format[/bold] — png, pdf, eps, svg")
    format_val = typer.prompt("Format", default="").strip().lower()
    fmt = format_val if format_val else None

    console.print("[bold]Width (inches)[/bold] — intended LaTeX width, e.g. 3.5 for single column")
    width_val = typer.prompt("Width inches", default="")
    width_inches = None
    if width_val:
        try:
            width_inches = float(width_val)
        except ValueError:
            console.print("[red]Must be a number.[/red]")

    console.print("[bold]Resolution (DPI)[/bold] — e.g. 300 for photos, 600 for line art")
    dpi_val = typer.prompt("DPI", default="")
    resolution_dpi = None
    if dpi_val:
        try:
            resolution_dpi = int(dpi_val)
        except ValueError:
            console.print("[red]Must be an integer.[/red]")

    console.print("[bold]First mentioned in[/bold] — section where figure is first referenced")
    console.print(f"  Available: {', '.join(project.config.sections)}")
    section_val = typer.prompt("Section", default="")
    first_mentioned_in = section_val if section_val else None

    console.print("[bold]Notes[/bold] — any additional notes (optional)")
    notes = typer.prompt("Notes", default="")

    figure = Figure(
        id=fig_id,
        caption=caption,
        path=path,
        format=fmt,
        width_inches=width_inches,
        resolution_dpi=resolution_dpi,
        first_mentioned_in=first_mentioned_in,
        notes=notes,
    )

    out_file = figures_dir / f"{fig_id}.yaml"
    with open(out_file, "w") as f:
        yaml.dump(figure.to_yaml(), f, sort_keys=False, default_flow_style=False)

    short_caption = caption[:80] + ("..." if len(caption) > 80 else "")
    console.print(
        Panel(
            f"Created: .paperforge/figures/{fig_id}.yaml\n\n"
            f"{fig_id}: \"{short_caption}\"\n"
            f"Path:    {path or '(not set)'}\n"
            f"Format:  {fmt or '(not set)'}\n\n"
            f"Next steps:\n"
            f"  1. Reference this figure in your claims:\n"
            f"     figures: [{fig_id}]\n"
            f"  2. Run `paperforge doctor` to check figure completeness.\n"
            f"  3. Run `paperforge impact <experiment>` to see traceability.",
            title="Figure Added",
            border_style="green",
        )
    )
