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


def _next_fig_id(figures_dir: Path) -> str:
    next_id = 1
    if figures_dir.exists():
        for fig_file in figures_dir.glob("fig_*.yaml"):
            try:
                num = int(fig_file.stem.split("_")[1])
                if num >= next_id:
                    next_id = num + 1
            except (IndexError, ValueError):
                continue
    return f"fig_{next_id:02d}"


def run(
    project_root: Path,
    caption: str | None = None,
    path: str | None = None,
    format: str | None = None,
    width: float | None = None,
    dpi: int | None = None,
    section: str | None = None,
    notes: str | None = None,
    wide: bool = False,
    from_yaml: Path | None = None,
) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    figures_dir = project_root / ".paperforge" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Handle --from-yaml
    if from_yaml is not None:
        yaml_file = from_yaml if from_yaml.is_absolute() else project_root / from_yaml
        if not yaml_file.exists():
            console.print(f"[red]YAML file not found: {from_yaml}[/red]")
            sys.exit(1)
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
        fig_id = _next_fig_id(figures_dir)
        figure = Figure(
            id=fig_id,
            caption=data.get("caption", ""),
            path=data.get("path"),
            format=data.get("format"),
            width_inches=data.get("width_inches"),
            resolution_dpi=data.get("resolution_dpi"),
            first_mentioned_in=data.get("first_mentioned_in"),
            notes=data.get("notes", ""),
            wide=bool(data.get("wide", False)),
        )
        out_file = figures_dir / f"{fig_id}.yaml"
        with open(out_file, "w", encoding="utf-8") as f:
            yaml.dump(figure.to_yaml(), f, sort_keys=False, default_flow_style=False)
        console.print(f"Created {fig_id} from {from_yaml}")
        return

    # Handle Non-interactive flags
    non_interactive = (
        any(v is not None for v in [caption, path, format, width, dpi, section, notes])
        or wide
    )
    if non_interactive:
        fig_id = _next_fig_id(figures_dir)
        figure = Figure(
            id=fig_id,
            caption=caption or "",
            path=path,
            format=format,
            width_inches=width,
            resolution_dpi=dpi,
            first_mentioned_in=section,
            notes=notes or "",
            wide=wide,
        )
        out_file = figures_dir / f"{fig_id}.yaml"
        with open(out_file, "w", encoding="utf-8") as f:
            yaml.dump(figure.to_yaml(), f, sort_keys=False, default_flow_style=False)
        console.print(f"Created {fig_id}")
        return

    # Interactive mode
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

    fig_id = _next_fig_id(figures_dir)

    console.print("[bold]Caption[/bold] — full caption as it will appear in the paper")
    caption_inp = typer.prompt("Caption", default="")

    console.print("[bold]File path[/bold] — relative path to image file, e.g. figures/fig_01.png")
    path_val = typer.prompt("Path", default="")
    path_inp = path_val if path_val else None

    console.print("[bold]Format[/bold] — png, pdf, eps, svg")
    format_val = typer.prompt("Format", default="").strip().lower()
    fmt_inp = format_val if format_val else None

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
    notes_inp = typer.prompt("Notes", default="")

    console.print("[bold]Wide (spans both columns)[/bold] — for full-width figures")
    wide_val = typer.prompt("Wide? (y/n)", default="n")
    wide_inp = wide_val.strip().lower() in ("y", "yes")

    figure = Figure(
        id=fig_id,
        caption=caption_inp,
        path=path_inp,
        format=fmt_inp,
        width_inches=width_inches,
        resolution_dpi=resolution_dpi,
        first_mentioned_in=first_mentioned_in,
        notes=notes_inp,
        wide=wide_inp,
    )

    out_file = figures_dir / f"{fig_id}.yaml"
    with open(out_file, "w", encoding="utf-8") as f:
        yaml.dump(figure.to_yaml(), f, sort_keys=False, default_flow_style=False)

    short_caption = caption_inp[:80] + ("..." if len(caption_inp) > 80 else "")
    console.print(
        Panel(
            f"Created: .paperforge/figures/{fig_id}.yaml\n\n"
            f"{fig_id}: \"{short_caption}\"\n"
            f"Path:    {path_inp or '(not set)'}\n"
            f"Format:  {fmt_inp or '(not set)'}\n\n"
            f"Next steps:\n"
            f"  1. Reference this figure in your claims:\n"
            f"     figures: [{fig_id}]\n"
            f"  2. Run `paperforge doctor` to check figure completeness.\n"
            f"  3. Run `paperforge impact <experiment>` to see traceability.",
            title="Figure Added",
            border_style="green",
        )
    )
