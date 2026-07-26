"""paperforge add-claim command — guided claim creation."""

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
    if claims_dir.exists():
        for claim_file in claims_dir.glob("claim_*.yaml"):
            suffix = claim_file.stem.removeprefix("claim_")
            if suffix.isdigit():
                max_n = max(max_n, int(suffix))
    return f"claim_{max_n + 1:02d}"


def run(
    project_root: Path,
    text: str | None = None,
    experiment: str | None = None,
    sections: str | None = None,
    figures: str | None = None,
    tables: str | None = None,
    citations: str | None = None,
    status: str | None = None,
    from_yaml: Path | None = None,
) -> None:
    """Create a new claim linked to an experiment."""
    # STEP 1 — Validate
    if not (project_root / ".paperforge").exists():
        console.print(
            "[red]Not a PaperForge project. Run `paperforge init` first.[/red]"
        )
        sys.exit(1)

    claims_dir = project_root / ".paperforge" / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)

    # STEP 2 — Handle --from-yaml
    if from_yaml is not None:
        yaml_file = from_yaml if from_yaml.is_absolute() else project_root / from_yaml
        if not yaml_file.exists():
            console.print(f"[red]YAML file not found: {from_yaml}[/red]")
            sys.exit(1)
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
        claim_id = _next_claim_id(claims_dir)
        claim = Claim(
            id=claim_id,
            text=str(data.get("text", "")),
            experiment=str(data.get("experiment", "")),
            experiments=list(data.get("experiments", [])),
            figures=list(data.get("figures", [])),
            tables=list(data.get("tables", [])),
            citations=list(data.get("citations", [])),
            sections=list(data.get("sections", [])),
            status=data.get("status", "unverified"),
        )
        claim_path = claims_dir / f"{claim_id}.yaml"
        claim_path.write_text(
            yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        console.print(f"Created {claim_id} from {from_yaml}")
        return

    # STEP 3 — Handle Non-interactive flags
    non_interactive = any(
        v is not None
        for v in [text, experiment, sections, figures, tables, citations, status]
    )
    if non_interactive:
        claim_id = _next_claim_id(claims_dir)
        sections_list = (
            [s.strip() for s in sections.split(",") if s.strip()]
            if sections
            else []
        )
        figures_list = (
            [f.strip() for f in figures.split(",") if f.strip()]
            if figures
            else []
        )
        tables_list = (
            [t.strip() for t in tables.split(",") if t.strip()]
            if tables
            else []
        )
        citations_list = (
            [c.strip() for c in citations.split(",") if c.strip()]
            if citations
            else []
        )
        valid_status = status if status in {"verified", "unverified", "stale"} else "unverified"

        claim = Claim(
            id=claim_id,
            text=text or "",
            experiment=experiment or "",
            figures=figures_list,
            tables=tables_list,
            citations=citations_list,
            sections=sections_list,
            status=valid_status,  # type: ignore[arg-type]
        )
        claim_path = claims_dir / f"{claim_id}.yaml"
        claim_path.write_text(
            yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        console.print(f"Created {claim_id}")
        return

    # STEP 4 — Interactive Mode
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

    console.print(
        "[bold]Claim text[/bold] — the exact sentence as it will appear in your paper"
    )
    text_inp = typer.prompt("Text", default="")

    console.print(
        "[bold]Experiment ID[/bold] — which experiment supports this claim"
    )
    console.print(f"  Available: {exp_display}")
    exp_inp = typer.prompt("Experiment", default="")

    console.print(
        "[bold]Sections[/bold] — comma-separated list where this claim appears"
    )
    console.print(f"  Available: {sections_display}")
    sections_raw = typer.prompt("Sections", default="")
    sections_inp = [s.strip() for s in sections_raw.split(",") if s.strip()]

    console.print(
        "[bold]Figures[/bold] — comma-separated figure IDs, e.g. fig_01,fig_02"
    )
    figures_raw = typer.prompt("Figures", default="")
    figures_inp = [f.strip() for f in figures_raw.split(",") if f.strip()]

    console.print(
        "[bold]Tables[/bold] — comma-separated table IDs, e.g. tbl_01"
    )
    tables_raw = typer.prompt("Tables", default="")
    tables_inp = [t.strip() for t in tables_raw.split(",") if t.strip()]

    console.print(
        "[bold]Citations[/bold] — comma-separated BibTeX keys, e.g. smith2024,jones2023"
    )
    citations_raw = typer.prompt("Citations", default="")
    citations_inp = [c.strip() for c in citations_raw.split(",") if c.strip()]

    console.print("[bold]Status[/bold] — verified, unverified, or stale")
    valid_statuses = {"verified", "unverified", "stale"}
    status_raw = typer.prompt("Status", default="unverified")
    if status_raw not in valid_statuses:
        console.print(
            f"[red]Invalid status '{status_raw}'. Must be: verified, unverified, stale.[/red]"
        )
        status_raw = typer.prompt("Status", default="unverified")
        if status_raw not in valid_statuses:
            console.print("[yellow]Defaulting to 'unverified'.[/yellow]")
            status_raw = "unverified"
    status_inp = status_raw

    claim_id = _next_claim_id(claims_dir)
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
        text=text_inp,
        experiment=exp_inp,
        figures=figures_inp,
        tables=tables_inp,
        citations=citations_inp,
        sections=sections_inp,
        status=status_inp,  # type: ignore[arg-type]
    )
    claim_path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    truncated_text = text_inp[:80] + ("..." if len(text_inp) > 80 else "")
    exp_display_result = exp_inp if exp_inp else "(none)"
    sections_display_result = ", ".join(sections_inp) if sections_inp else "(none)"

    impact_hint = (
        f"      Run `paperforge impact {exp_inp}` to see affected nodes."
        if exp_inp
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
