"""paperforge impact command."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from paperforge.core.project import PaperForgeProject

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _display_text(text: str) -> str:
    if not text:
        return "(no text yet)"
    truncated = text[:60]
    suffix = "..." if len(text) > 60 else ""
    return f'"{truncated}{suffix}"'


def run(experiment_id: str, project_root: Path) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    project = PaperForgeProject.load(project_root)
    graph = project.get_graph()

    experiment_ids = {e.id for e in project.experiments}
    if experiment_id not in experiment_ids:
        console.print(f"[red]Experiment '{experiment_id}' not found.[/red]")
        console.print(f"[red]Available experiments: {sorted(experiment_ids)}[/red]")
        console.print("[red]Check .paperforge/experiments/[/red]")
        sys.exit(1)

    affected = graph.get_affected(experiment_id)

    claims_by_id = {claim.id: claim for claim in project.claims}

    if not affected.claims:
        console.print(
            Panel(
                f"No claims are linked to experiment '{experiment_id}'.\n"
                "Add claims using `paperforge capture`.",
                border_style="yellow",
            )
        )
        return

    console.print(f"Source: Experiment {experiment_id}")
    console.print()

    console.print("Affected Claims:")
    for claim_id in affected.claims:
        claim = claims_by_id.get(claim_id)
        text = claim.text if claim else ""
        console.print(f"  {claim_id}    {_display_text(text)}")
    console.print()

    console.print("Affected Sections:")
    for section in sorted(affected.sections):
        console.print(f"  {section}")
    console.print()

    console.print("Affected Figures:")
    for fig_id in sorted(affected.figures):
        fig = graph.get_figure(fig_id)
        if fig:
            caption = fig.caption or ""
            truncated = caption[:60]
            suffix = "..." if len(caption) > 60 else ""
            display_caption = f"{truncated}{suffix}"
            path_str = fig.path if fig.path else "(no path)"
            console.print(f"  {fig_id}    \"{display_caption}\"")
            console.print(f"               Path: {path_str}")
        else:
            console.print(f"  {fig_id}    (no figure YAML — run `paperforge add-figure`)")
    console.print()

    console.print("Affected Tables:")
    for table in sorted(affected.tables):
        console.print(f"  {table}")
    console.print()

    console.print("─" * 55)
    console.print("Verification Status:")
    unverified_count = sum(
        1
        for claim_id in affected.claims
        if claims_by_id.get(claim_id) and claims_by_id[claim_id].status != "verified"
    )
    console.print(f"  {unverified_count} claim(s) require verification")
    console.print(f"  {len(affected.figures)} figure(s) should be reviewed")
    console.print(f"  {len(affected.tables)} table(s) should be reviewed")
    console.print()
    console.print("Run `paperforge doctor` to check full consistency.")
