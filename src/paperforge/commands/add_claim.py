"""paperforge add-claim command — interactive guided claim creation."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from paperforge.core.project import PaperForgeProject
from paperforge.history import record_snapshot
from paperforge.models.claim import Claim

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _next_claim_id(claims_dir: Path) -> str:
    max_n = 0
    for claim_file in claims_dir.glob("claim_*.yaml"):
        suffix = claim_file.stem.removeprefix("claim_")
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return f"claim_{max_n + 1:02d}"


def run(project_root: Path) -> None:
    """Interactively create a new claim linked to an experiment."""
    # STEP 1 — Validate
    if not (project_root / ".paperforge").exists():
        console.print(
            "[red]Not a PaperForge project. Run `paperforge init` first.[/red]"
        )
        sys.exit(1)

    # STEP 2 — Load project and show context
    project = PaperForgeProject.load(project_root)

    experiment_ids = sorted(e.id for e in project.experiments)
    exp_display = ", ".join(experiment_ids) if experiment_ids else "none"
    sections_display = (
        ", ".join(project.config.sections) if project.config.sections else "none"
    )
    claim_count = len(project.claims)

    context_text = Text()
    context_text.append(f"Existing experiments: {exp_display}\n")
    context_text.append(f"Existing sections:    {sections_display}\n")
    context_text.append(f"Existing claims:      {claim_count}\n")
    context_text.append("\n")
    context_text.append("Fill in the claim details below.\n")
    context_text.append("Press Enter to leave a field empty.")

    console.print(Panel(context_text, title="Add Claim", border_style="cyan"))

    # STEP 3 — Prompt for each field in order

    # Claim text
    console.print(
        "[bold]Claim text[/bold] — the exact sentence as it will appear in your paper"
    )
    text = typer.prompt("Text", default="")

    # Experiment id
    console.print(
        "[bold]Experiment ID[/bold] — which experiment supports this claim"
    )
    console.print(f"  Available: {exp_display}")
    experiment = typer.prompt("Experiment", default="")

    # Sections
    console.print(
        "[bold]Sections[/bold] — comma-separated list where this claim appears"
    )
    console.print(f"  Available: {sections_display}")
    sections_raw = typer.prompt("Sections", default="")
    sections = [s.strip() for s in sections_raw.split(",") if s.strip()]

    # Figures
    console.print(
        "[bold]Figures[/bold] — comma-separated figure IDs, e.g. fig_01,fig_02"
    )
    figures_raw = typer.prompt("Figures", default="")
    figures = [f.strip() for f in figures_raw.split(",") if f.strip()]

    # Tables
    console.print(
        "[bold]Tables[/bold] — comma-separated table IDs, e.g. tbl_01"
    )
    tables_raw = typer.prompt("Tables", default="")
    tables = [t.strip() for t in tables_raw.split(",") if t.strip()]

    # Citations
    console.print(
        "[bold]Citations[/bold] — comma-separated BibTeX keys, e.g. smith2024,jones2023"
    )
    citations_raw = typer.prompt("Citations", default="")
    citations = [c.strip() for c in citations_raw.split(",") if c.strip()]

    # Status (with validation)
    console.print("[bold]Status[/bold] — verified, unverified, or stale")
    valid_statuses = {"verified", "unverified", "stale"}
    status_raw = typer.prompt("Status", default="unverified")
    if status_raw not in valid_statuses:
        console.print(
            f"[red]Invalid status '{status_raw}'. Must be: verified, unverified, stale.[/red]"
        )
        status_raw = typer.prompt("Status", default="unverified")
        if status_raw not in valid_statuses:
            console.print(
                "[yellow]Defaulting to 'unverified'.[/yellow]"
            )
            status_raw = "unverified"
    status = status_raw

    # STEP 4 — Auto-assign claim id
    claims_dir = project_root / ".paperforge" / "claims"
    claim_id = _next_claim_id(claims_dir)

    # STEP 5 — Write claim file
    claim_path = claims_dir / f"{claim_id}.yaml"
    if claim_path.exists():
        current_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
        record_snapshot(
            paperforge_dir=project_root / ".paperforge",
            claim_id=claim_id,
            claim_data=current_data,
            recorded_by="paperforge add-claim",
        )

    claim = Claim(
        id=claim_id,
        text=text,
        experiment=experiment,
        figures=figures,
        tables=tables,
        citations=citations,
        sections=sections,
        status=status,  # type: ignore[arg-type]
    )
    claim_path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    # STEP 6 — Print confirmation
    truncated_text = text[:80] + ("..." if len(text) > 80 else "")
    exp_display_result = experiment if experiment else "(none)"
    sections_display_result = ", ".join(sections) if sections else "(none)"

    impact_hint = (
        f"      Run `paperforge impact {experiment}` to see affected nodes."
        if experiment
        else ""
    )

    result_text = Text()
    result_text.append(f"Created: .paperforge/claims/{claim_id}.yaml\n\n")
    result_text.append(f'{claim_id}: "{truncated_text}"\n')
    result_text.append(f"Experiment: {exp_display_result}\n")
    result_text.append(f"Sections:   {sections_display_result}\n")
    result_text.append("\nNext steps:\n")
    result_text.append("      Run `paperforge doctor` to check consistency.\n")
    if impact_hint:
        result_text.append(impact_hint)

    console.print(Panel(result_text, title="Claim Added", border_style="green"))
