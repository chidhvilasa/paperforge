"""paperforge add-table command."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from paperforge.core.project import PaperForgeProject
from paperforge.models.table import Table

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def run(project_root: Path) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    project = PaperForgeProject.load(project_root)

    tbl_ids = [tbl.id for tbl in project.tables]
    existing_tables = ", ".join(sorted(tbl_ids)) if tbl_ids else "none"
    exp_ids = [exp.id for exp in project.experiments]
    existing_exps = ", ".join(sorted(exp_ids)) if exp_ids else "none"

    console.print(
        Panel(
            f"Existing tables: {existing_tables}\n"
            f"Existing experiments: {existing_exps}\n"
            f"Fill in table details below.",
            title="Add Table",
            border_style="cyan",
        )
    )

    next_id = 1
    tables_dir = project.paperforge_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    if tables_dir.exists():
        for tbl_file in tables_dir.glob("tbl_*.yaml"):
            try:
                num = int(tbl_file.stem.split("_")[1])
                if num >= next_id:
                    next_id = num + 1
            except (IndexError, ValueError):
                continue
    tbl_id = f"tbl_{next_id:02d}"

    console.print("[bold]Caption[/bold] — table title (appears ABOVE table in IEEE)")
    caption = typer.prompt("Caption", default="")

    console.print("[bold]Source experiment[/bold] — which experiment generated this data")
    console.print(f"  Available: {existing_exps}")
    exp_val = typer.prompt("Experiment", default="")
    source_experiment = exp_val if exp_val else None

    console.print("[bold]Column headers[/bold] — comma-separated, e.g. Method,Accuracy,F1")
    cols_val = typer.prompt("Columns", default="")
    columns = [c.strip() for c in cols_val.split(",") if c.strip()] if cols_val else []

    console.print("[bold]Data rows[/bold] — one row per line, values comma-separated.")
    console.print("  Enter each row and press Enter. Type 'done' when finished.")
    rows: list[list[str]] = []
    while True:
        row_str = typer.prompt("Row (or 'done')", default="done")
        if row_str.strip().lower() == "done":
            break
        cells = [c.strip() for c in row_str.split(",")]
        if cells:
            rows.append(cells)

    console.print("[bold]First mentioned in[/bold] — section where table is first referenced")
    console.print(f"  Available: {', '.join(project.config.sections)}")
    section_val = typer.prompt("Section", default="")
    first_mentioned_in = section_val if section_val else None

    console.print("[bold]Notes[/bold] — footnotes or table notes (optional)")
    notes = typer.prompt("Notes", default="")

    table = Table(
        id=tbl_id,
        caption=caption,
        columns=columns,
        rows=rows,
        notes=notes,
        first_mentioned_in=first_mentioned_in,
        source_experiment=source_experiment,
    )

    out_file = tables_dir / f"{tbl_id}.yaml"
    with open(out_file, "w") as f:
        yaml.dump(table.to_yaml(), f, sort_keys=False, default_flow_style=False)

    short_caption = caption[:80] + ("..." if len(caption) > 80 else "")
    console.print(
        Panel(
            f"Created: .paperforge/tables/{tbl_id}.yaml\n\n"
            f"{tbl_id}: \"{short_caption}\"\n"
            f"Columns: {len(columns)} columns\n"
            f"Rows:    {len(rows)} data rows\n"
            f"Experiment: {source_experiment or '(not linked)'}\n\n"
            f"Next steps:\n"
            f"  1. Reference in claims: tables: [{tbl_id}]\n"
            f"  2. Run `paperforge doctor` to check table completeness.",
            title="Table Added",
            border_style="green",
        )
    )
