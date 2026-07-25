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
from paperforge.history import record_snapshot
from paperforge.models.claim import Claim
from paperforge.utils.numbers import extract_numbers, numbers_match

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

    # --- Checks 11-20: Number consistency ---

    # Check 11 — METRIC_CLAIM_MISMATCH (ERROR)
    experiment_map = {exp.id: exp for exp in project.experiments}
    for claim in project.claims:
        if not claim.text or not claim.experiment:
            continue
        exp = experiment_map.get(claim.experiment)
        if exp is None:
            continue
        if not exp.metrics:
            continue
        percentage_numbers = [
            n for n in extract_numbers(claim.text) if n.is_percentage
        ]
        if not percentage_numbers:
            continue
        # Only consider metrics whose values are in the 0-100 range
        range_metrics = {
            k: v for k, v in exp.metrics.items() if 0 <= v <= 100
        }
        if not range_metrics:
            continue
        for extracted in percentage_numbers:
            matched = any(
                numbers_match(extracted.value, mv)
                for mv in range_metrics.values()
            )
            if not matched:
                issues.append(
                    Issue(
                        code="METRIC_CLAIM_MISMATCH",
                        severity="ERROR",
                        message=(
                            f"{claim.id} contains '{extracted.raw}' "
                            f"but no metric in {exp.id} matches "
                            f"(metrics: {exp.metrics})"
                        ),
                    )
                )
                break  # at most one METRIC_CLAIM_MISMATCH per claim

    # Check 12 — DUPLICATE_CLAIM_TEXT (WARNING)
    text_to_ids: dict[str, list[str]] = {}
    for claim in project.claims:
        if not claim.text:
            continue
        key = claim.text.strip().lower()
        text_to_ids.setdefault(key, []).append(claim.id)
    for text_key, claim_ids in text_to_ids.items():
        if len(claim_ids) >= 2:
            issues.append(
                Issue(
                    code="DUPLICATE_CLAIM_TEXT",
                    severity="WARNING",
                    message=(
                        f"Identical text in {claim_ids}: '{text_key[:60]}...'"
                    ),
                )
            )

    # Check 13 — CLAIM_IN_NO_SECTION (WARNING)
    for claim in project.claims:
        if not claim.sections:
            issues.append(
                Issue(
                    code="CLAIM_IN_NO_SECTION",
                    severity="WARNING",
                    message=f"{claim.id} is not placed in any section",
                )
            )

    # Check 14 — EXPERIMENT_NO_DESCRIPTION (WARNING)
    for experiment in project.experiments:
        if not experiment.description:
            issues.append(
                Issue(
                    code="EXPERIMENT_NO_DESCRIPTION",
                    severity="WARNING",
                    message=f"{experiment.id} has no description",
                )
            )

    # Check 15 — EXPERIMENT_NO_HARDWARE (WARNING)
    for experiment in project.experiments:
        if experiment.hardware is None:
            issues.append(
                Issue(
                    code="EXPERIMENT_NO_HARDWARE",
                    severity="WARNING",
                    message=(
                        f"{experiment.id} has no hardware recorded "
                        f"— reviewers expect reproducibility details"
                    ),
                )
            )

    # Check 16 — EXPERIMENT_NO_DATASET (WARNING)
    for experiment in project.experiments:
        if experiment.dataset is None:
            issues.append(
                Issue(
                    code="EXPERIMENT_NO_DATASET",
                    severity="WARNING",
                    message=f"{experiment.id} has no dataset recorded",
                )
            )

    # Check 17 — EXPERIMENT_NO_SEED (WARNING)
    for experiment in project.experiments:
        if experiment.seed is None:
            issues.append(
                Issue(
                    code="EXPERIMENT_NO_SEED",
                    severity="WARNING",
                    message=(
                        f"{experiment.id} has no random seed recorded "
                        f"— required for reproducibility"
                    ),
                )
            )

    # Check 18 — UNCLAIMED_EXPERIMENT (WARNING)
    claimed_exp_ids = {c.experiment for c in project.claims if c.experiment}
    for experiment in project.experiments:
        if experiment.id not in claimed_exp_ids:
            issues.append(
                Issue(
                    code="UNCLAIMED_EXPERIMENT",
                    severity="WARNING",
                    message=f"{experiment.id} exists but no claim references it",
                )
            )

    # Check 19 — INVALID_FIGURE_ID (WARNING)
    for claim in project.claims:
        for fig_id in claim.figures:
            if not fig_id.startswith("fig_"):
                issues.append(
                    Issue(
                        code="INVALID_FIGURE_ID",
                        severity="WARNING",
                        message=(
                            f"{claim.id} references figure '{fig_id}' — "
                            f"convention is fig_NN (e.g. fig_01)"
                        ),
                    )
                )

    # Check 20 — INVALID_TABLE_ID (WARNING)
    for claim in project.claims:
        for tbl_id in claim.tables:
            if not tbl_id.startswith("tbl_"):
                issues.append(
                    Issue(
                        code="INVALID_TABLE_ID",
                        severity="WARNING",
                        message=(
                            f"{claim.id} references table '{tbl_id}' — "
                            f"convention is tbl_NN (e.g. tbl_01)"
                        ),
                    )
                )

    return issues


def _apply_fix(project_root: Path, unverified_claims: list[Claim]) -> None:
    claims_dir = project_root / ".paperforge" / "claims"
    for claim in unverified_claims:
        claim_path = claims_dir / f"{claim.id}.yaml"
        current_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
        record_snapshot(
            paperforge_dir=project_root / ".paperforge",
            claim_id=claim.id,
            claim_data=current_data,
            recorded_by="paperforge doctor --fix",
        )
        loaded = Claim.from_yaml(current_data)
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
