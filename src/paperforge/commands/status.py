"""paperforge status command — project health dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def run(project_root: Path) -> None:
    """Show project health dashboard. Read-only — never modifies files."""
    # STEP 1 — Validate
    if not (project_root / ".paperforge").exists():
        console.print(
            "[red]Not a PaperForge project. Run `paperforge init` first.[/red]"
        )
        sys.exit(1)

    project = PaperForgeProject.load(project_root)
    issues = collect_issues(project)

    # STEP 2 — Compute metrics
    claims_total = len(project.claims)
    claims_verified = sum(1 for c in project.claims if c.status == "verified")
    claims_unverified = sum(1 for c in project.claims if c.status == "unverified")
    claims_stale = sum(1 for c in project.claims if c.status == "stale")
    experiments_total = len(project.experiments)
    errors = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARNING"]

    experiment_with_metrics = sum(1 for e in project.experiments if e.metrics)

    submission_ready = len(errors) == 0 and claims_total > 0

    title = project.config.title or "Untitled"
    border = "green" if submission_ready else "yellow"

    # STEP 3 — Print dashboard
    console.print(Panel(
        _build_dashboard(
            project=project,
            claims_total=claims_total,
            claims_verified=claims_verified,
            claims_unverified=claims_unverified,
            claims_stale=claims_stale,
            experiments_total=experiments_total,
            experiment_with_metrics=experiment_with_metrics,
            errors=errors,
            warnings=warnings,
            submission_ready=submission_ready,
        ),
        title=f"PaperForge Status — {title}",
        border_style=border,
    ))


def _build_dashboard(
    *,
    project: PaperForgeProject,
    claims_total: int,
    claims_verified: int,
    claims_unverified: int,
    claims_stale: int,
    experiments_total: int,
    experiment_with_metrics: int,
    errors: list,
    warnings: list,
    submission_ready: bool,
) -> Text:
    """Assemble the full status dashboard as a single rich Text object."""
    from rich.console import Group

    sections: list = []

    # --- SECTION 1: Project ---
    proj_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    proj_table.add_column("key", style="bold")
    proj_table.add_column("value")
    proj_table.add_row("Title:", project.config.title or "(not set)")
    proj_table.add_row(
        "Authors:",
        ", ".join(str(a) for a in project.config.authors) if project.config.authors else "(not set)",
    )
    proj_table.add_row("Venue:", project.config.venue or "(not set)")
    proj_table.add_row("Status:", project.config.status)
    sections.append(Text("Project", style="bold underline"))
    sections.append(proj_table)
    sections.append(Text(""))

    # --- SECTION 2: Research Graph ---
    graph_table = Table(show_header=True, box=None, padding=(0, 2, 0, 0))
    graph_table.add_column("Metric", style="bold")
    graph_table.add_column("Count", justify="right")
    graph_table.add_column("Health")

    graph_table.add_row("Claims (total)", str(claims_total), "")
    graph_table.add_row(
        "  Verified",
        str(claims_verified),
        Text("✓", style="green") if claims_verified > 0 else Text("—", style="yellow"),
    )
    graph_table.add_row(
        "  Unverified",
        str(claims_unverified),
        Text("✓", style="green") if claims_unverified == 0 else Text("!", style="yellow"),
    )
    graph_table.add_row(
        "  Stale",
        str(claims_stale),
        Text("✓", style="green") if claims_stale == 0 else Text("✗", style="red"),
    )
    graph_table.add_row("Experiments", str(experiments_total), "")
    graph_table.add_row(
        "  With metrics",
        str(experiment_with_metrics),
        (
            Text("✓", style="green")
            if experiment_with_metrics >= experiments_total > 0
            else Text("!", style="yellow")
        ),
    )

    sections.append(Text("Research Graph", style="bold underline"))
    sections.append(graph_table)
    sections.append(Text(""))

    # --- SECTION 3: Section Coverage ---
    cov_table = Table(show_header=True, box=None, padding=(0, 2, 0, 0))
    cov_table.add_column("Section", style="bold")
    cov_table.add_column("Claims", justify="right")
    cov_table.add_column("Status")
    for section in project.config.sections:
        count = sum(1 for c in project.claims if section in c.sections)
        status_cell = (
            Text("✓", style="green") if count > 0 else Text("empty", style="yellow")
        )
        cov_table.add_row(section, str(count), status_cell)

    sections.append(Text("Section Coverage", style="bold underline"))
    sections.append(cov_table)
    sections.append(Text(""))

    # --- SECTION 4: Doctor Summary ---
    doc_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    doc_table.add_column("label", style="bold")
    doc_table.add_column("count", justify="right")
    doc_table.add_row(
        "Errors:",
        Text(str(len(errors)), style="red" if errors else "green"),
    )
    doc_table.add_row(
        "Warnings:",
        Text(str(len(warnings)), style="yellow" if warnings else "green"),
    )
    sections.append(Text("Doctor Summary", style="bold underline"))
    sections.append(doc_table)

    if errors:
        sections.append(Text(""))
        for issue in errors:
            sections.append(Text(f"  • [{issue.code}] {issue.message}", style="red"))

    sections.append(Text(""))

    # --- SECTION 5: Submission Readiness ---
    if submission_ready:
        sections.append(Text("✓ Ready for paperforge build", style="bold green"))
    else:
        sections.append(
            Text(
                f"✗ Not ready — fix {len(errors)} error(s) first",
                style="bold red",
            )
        )
        sections.append(Text("  Run `paperforge doctor` for full details."))

    return Group(*sections)  # type: ignore[return-value]
