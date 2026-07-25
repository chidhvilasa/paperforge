"""paperforge doctor command."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from paperforge.core.project import PaperForgeProject
from paperforge.models.claim import Claim

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


@dataclass
class Issue:
    code: str
    severity: Literal["ERROR", "WARNING"]
    message: str


def collect_issues(project: PaperForgeProject) -> list[Issue]:
    issues: list[Issue] = []

    for claim in project.claims:
        if not claim.experiment:
            issues.append(
                Issue(
                    code="ORPHAN_CLAIM",
                    severity="ERROR",
                    message=f"{claim.id} has no linked experiment",
                )
            )

    experiment_ids = {experiment.id for experiment in project.experiments}
    for claim in project.claims:
        if claim.experiment and claim.experiment not in experiment_ids:
            issues.append(
                Issue(
                    code="MISSING_EXPERIMENT",
                    severity="ERROR",
                    message=(
                        f"{claim.id} references experiment "
                        f"'{claim.experiment}' which does not exist"
                    ),
                )
            )

    for claim in project.claims:
        if claim.status == "stale":
            issues.append(
                Issue(
                    code="STALE_CLAIM",
                    severity="ERROR",
                    message=f"{claim.id} is stale and requires re-verification",
                )
            )

    for claim in project.claims:
        if not claim.text:
            issues.append(
                Issue(
                    code="EMPTY_CLAIM_TEXT",
                    severity="ERROR",
                    message=f"{claim.id} has no text",
                )
            )

    for claim in project.claims:
        if claim.status == "unverified":
            issues.append(
                Issue(
                    code="UNVERIFIED_CLAIM",
                    severity="WARNING",
                    message=f"{claim.id} is unverified",
                )
            )

    for experiment in project.experiments:
        if experiment.metrics == {}:
            issues.append(
                Issue(
                    code="EMPTY_EXPERIMENT_METRICS",
                    severity="WARNING",
                    message=f"{experiment.id} has no metrics recorded",
                )
            )

    if len(project.claims) == 0:
        issues.append(
            Issue(
                code="NO_CLAIMS",
                severity="WARNING",
                message="No claims found in .paperforge/claims/",
            )
        )

    if len(project.experiments) == 0:
        issues.append(
            Issue(
                code="NO_EXPERIMENTS",
                severity="WARNING",
                message="No experiments found in .paperforge/experiments/",
            )
        )

    if not project.config.title:
        issues.append(
            Issue(
                code="MISSING_PAPER_TITLE",
                severity="WARNING",
                message="paper.yaml title is empty",
            )
        )

    if not project.config.authors:
        issues.append(
            Issue(
                code="MISSING_AUTHORS",
                severity="WARNING",
                message="paper.yaml authors list is empty",
            )
        )

    return issues


def _apply_fix(project_root: Path, unverified_claims: list[Claim]) -> None:
    claims_dir = project_root / ".paperforge" / "claims"
    for claim in unverified_claims:
        claim_path = claims_dir / f"{claim.id}.yaml"
        loaded = Claim.from_yaml(yaml.safe_load(claim_path.read_text(encoding="utf-8")))
        loaded.status = "stale"
        claim_path.write_text(
            yaml.dump(loaded.to_yaml(), default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        console.print(f"  Fixed: {loaded.id} status set to stale")


def run(project_root: Path, fix: bool = False, target: str | None = None) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    project = PaperForgeProject.load(project_root)

    issues = collect_issues(project)

    venue_issues: list[Issue] = []
    plugin = None
    if target is not None:
        from paperforge.venues.registry import get_plugin

        try:
            plugin = get_plugin(target)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            sys.exit(1)
        venue_issues = [
            Issue(
                code=vi.code,
                severity=cast(Literal["ERROR", "WARNING"], vi.severity),
                message=vi.message,
            )
            for vi in plugin.validate(project)
        ]

    console.print(Text("PaperForge Doctor", style="bold"))

    if not issues and not venue_issues:
        console.print(
            Panel("All checks passed. No issues found.", border_style="green")
        )
        return

    if fix:
        unverified_claims = [c for c in project.claims if c.status == "unverified"]
        _apply_fix(project_root, unverified_claims)

    errors = [issue for issue in issues if issue.severity == "ERROR"]
    warnings = [issue for issue in issues if issue.severity == "WARNING"]
    venue_errors = [issue for issue in venue_issues if issue.severity == "ERROR"]
    venue_warnings = [issue for issue in venue_issues if issue.severity == "WARNING"]

    if errors:
        console.print()
        console.print(Text("ERROR", style="bold red"))
        for issue in errors:
            console.print(Text(f"  [{issue.code}] {issue.message}"))

    if warnings:
        console.print()
        console.print(Text("WARNING", style="bold yellow"))
        for issue in warnings:
            console.print(Text(f"  [{issue.code}] {issue.message}"))

    if plugin is not None and venue_issues:
        console.print()
        console.print(Text(f"VENUE ({plugin.display_name})", style="bold cyan"))
        for issue in venue_issues:
            console.print(Text(f"  [{issue.code}] {issue.message}"))

    total_errors = errors + venue_errors
    total_warnings = warnings + venue_warnings

    console.print()
    console.print("─" * 40)
    console.print(
        f"Summary: {len(total_errors)} error(s), {len(total_warnings)} warning(s)"
    )

    if not fix and total_warnings:
        console.print(
            "Run `paperforge doctor --fix` to auto-resolve fixable warnings."
        )

    if total_errors:
        sys.exit(1)
