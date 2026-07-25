"""paperforge doctor command."""

from __future__ import annotations

import re
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
    severity: Literal["ERROR", "WARNING", "INFO"]
    message: str


COMMON_ACRONYMS = {
    "IEEE", "AI", "ML", "DL", "IoT", "API", "URL", "DOI",
    "CPU", "GPU", "RAM", "SSD", "PDF", "TCP", "UDP", "IP",
    "HTTP", "TLS", "SSL", "YAML", "JSON", "CLI",
}

ACRONYM_PATTERN = re.compile(r"\b([A-Z]{2,5})\b")


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

    # --- Checks 21-30: IEEE submission hardening ---

    # Check 21 — UNDEFINED_ACRONYM (WARNING)
    all_claim_text = [claim.text for claim in project.claims if claim.text]
    found_acronyms: set[str] = set()
    for text in all_claim_text:
        found_acronyms.update(ACRONYM_PATTERN.findall(text))
    for acronym in sorted(found_acronyms - COMMON_ACRONYMS):
        defined = any(
            f"({acronym})" in text or f"{acronym})" in text for text in all_claim_text
        )
        if not defined:
            issues.append(
                Issue(
                    code="UNDEFINED_ACRONYM",
                    severity="WARNING",
                    message=(
                        f"Acronym '{acronym}' used in claims but never "
                        f"defined. Define on first use: 'Term ({acronym})'"
                    ),
                )
            )

    # Checks 22-23 — ABSTRACT_TOO_LONG / ABSTRACT_TOO_SHORT (WARNING)
    abstract_claims = [c for c in project.claims if "abstract" in c.sections]
    abstract_word_count = len(
        " ".join(c.text for c in abstract_claims if c.text).split()
    )
    if abstract_word_count > 250:
        issues.append(
            Issue(
                code="ABSTRACT_TOO_LONG",
                severity="WARNING",
                message=(
                    f"Abstract content is {abstract_word_count} words. "
                    f"IEEE recommends under 250 words."
                ),
            )
        )
    if 0 < abstract_word_count < 50:
        issues.append(
            Issue(
                code="ABSTRACT_TOO_SHORT",
                severity="WARNING",
                message=(
                    f"Abstract is only {abstract_word_count} words. "
                    f"IEEE abstracts are typically 150-250 words."
                ),
            )
        )

    # Check 24 — NO_INTRODUCTION_CLAIMS (WARNING)
    if not any("introduction" in c.sections for c in project.claims):
        issues.append(
            Issue(
                code="NO_INTRODUCTION_CLAIMS",
                severity="WARNING",
                message="No claims are placed in the introduction section.",
            )
        )

    # Check 25 — NO_CONCLUSION_CLAIMS (WARNING)
    if not any("conclusion" in c.sections for c in project.claims):
        issues.append(
            Issue(
                code="NO_CONCLUSION_CLAIMS",
                severity="WARNING",
                message="No claims are placed in the conclusion section.",
            )
        )

    # Check 26 — EXPERIMENT_NO_RESULTS_FILE (WARNING)
    for experiment in project.experiments:
        if experiment.results_file is None:
            issues.append(
                Issue(
                    code="EXPERIMENT_NO_RESULTS_FILE",
                    severity="WARNING",
                    message=(
                        f"{experiment.id} has no results_file path recorded. "
                        f"Link to your metrics JSON for full traceability."
                    ),
                )
            )

    # Check 27 — CLAIM_EXCESSIVE_LENGTH (WARNING)
    for claim in project.claims:
        word_count = len(claim.text.split())
        if word_count > 80:
            issues.append(
                Issue(
                    code="CLAIM_EXCESSIVE_LENGTH",
                    severity="WARNING",
                    message=(
                        f"{claim.id} text is {word_count} words. "
                        f"Claims should be single sentences. "
                        f"Consider splitting into multiple claims."
                    ),
                )
            )

    # Check 28 — EXPERIMENT_OVERCROWDED (WARNING)
    exp_claim_counts: dict[str, int] = {}
    for claim in project.claims:
        if claim.experiment:
            exp_claim_counts[claim.experiment] = (
                exp_claim_counts.get(claim.experiment, 0) + 1
            )
    for experiment_id, claim_count in exp_claim_counts.items():
        if claim_count >= 5:
            issues.append(
                Issue(
                    code="EXPERIMENT_OVERCROWDED",
                    severity="WARNING",
                    message=(
                        f"{experiment_id} supports {claim_count} claims. "
                        f"Consider running additional experiments to "
                        f"diversify your evidence base."
                    ),
                )
            )

    # Check 29 — RESULTS_SECTION_EMPTY (ERROR)
    if project.claims and not any("results" in c.sections for c in project.claims):
        issues.append(
            Issue(
                code="RESULTS_SECTION_EMPTY",
                severity="ERROR",
                message=(
                    "No claims are placed in the results section. "
                    "A paper without results claims cannot be built."
                ),
            )
        )

    # Check 30 — EVIDENCE_COVERAGE (INFO)
    total_claims = len(project.claims)
    claims_with_experiment = sum(1 for c in project.claims if c.experiment)
    coverage_pct = (
        int(claims_with_experiment / total_claims * 100) if total_claims > 0 else 0
    )
    coverage_note = (
        "Full coverage."
        if coverage_pct == 100
        else "Link remaining claims to experiments."
    )
    issues.append(
        Issue(
            code="EVIDENCE_COVERAGE",
            severity="INFO",
            message=(
                f"Evidence coverage: {claims_with_experiment}/"
                f"{total_claims} claims linked to experiments "
                f"({coverage_pct}%). {coverage_note}"
            ),
        )
    )

    # --- Checks 31-35: Figure completeness ---

    claimed_figure_ids = {
        fig_id
        for claim in project.claims
        for fig_id in claim.figures
    }
    existing_figure_ids = {fig.id for fig in project.figures}

    # Check 31 — FIGURE_NO_CAPTION (WARNING)
    for figure in project.figures:
        if not figure.caption:
            issues.append(
                Issue(
                    code="FIGURE_NO_CAPTION",
                    severity="WARNING",
                    message=f"{figure.id} has no caption. IEEE requires all figures to have captions.",
                )
            )

    # Check 32 — FIGURE_NO_FIRST_MENTION (WARNING)
    for figure in project.figures:
        if not figure.first_mentioned_in:
            issues.append(
                Issue(
                    code="FIGURE_NO_FIRST_MENTION",
                    severity="WARNING",
                    message=f"{figure.id} has no first_mentioned_in section. IEEE requires figures to appear after first text reference.",
                )
            )

    # Check 33 — FIGURE_REFERENCED_BUT_NO_YAML (WARNING)
    for fig_id in claimed_figure_ids:
        if fig_id not in existing_figure_ids:
            issues.append(
                Issue(
                    code="FIGURE_REFERENCED_BUT_NO_YAML",
                    severity="WARNING",
                    message=f"Claim references '{fig_id}' but no .paperforge/figures/{fig_id}.yaml exists. Run `paperforge add-figure` to create it.",
                )
            )

    # Check 34 — FIGURE_YAML_BUT_NO_CLAIM (WARNING)
    for figure_id in existing_figure_ids:
        if figure_id not in claimed_figure_ids:
            issues.append(
                Issue(
                    code="FIGURE_YAML_BUT_NO_CLAIM",
                    severity="WARNING",
                    message=f"{figure_id} has a YAML file but is not referenced in any claim.",
                )
            )

    # Check 35 — LOW_RESOLUTION_FIGURE (WARNING)
    for figure in project.figures:
        if (
            figure.resolution_dpi is not None
            and figure.format is not None
            and figure.format.lower() in ("png", "jpg", "jpeg", "tiff", "tif")
            and figure.resolution_dpi < 300
        ):
            issues.append(
                Issue(
                    code="LOW_RESOLUTION_FIGURE",
                    severity="WARNING",
                    message=f"{figure.id} has {figure.resolution_dpi} DPI. IEEE requires minimum 300 DPI for raster images, 600 DPI for line art.",
                )
            )

    # Check 36 — MISSING_AFFILIATION (WARNING)
    if project.config.authors and not project.config.affiliations:
        issues.append(
            Issue(
                code="MISSING_AFFILIATION",
                severity="WARNING",
                message=(
                    "Authors are set but no affiliations are defined. "
                    "IEEE journal submissions require author affiliations. "
                    "Add affiliations to paper.yaml."
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
                severity=cast(Literal["ERROR", "WARNING", "INFO"], vi.severity),
                message=vi.message,
            )
            for vi in plugin.validate(project)
        ]

    console.print(Text("PaperForge Doctor", style="bold"))

    errors = [issue for issue in issues if issue.severity == "ERROR"]
    warnings = [issue for issue in issues if issue.severity == "WARNING"]
    info_issues = [issue for issue in issues if issue.severity == "INFO"]
    venue_errors = [issue for issue in venue_issues if issue.severity == "ERROR"]
    venue_warnings = [issue for issue in venue_issues if issue.severity == "WARNING"]

    if not errors and not warnings and not venue_issues:
        console.print(
            Panel("All checks passed. No issues found.", border_style="green")
        )
        if info_issues:
            console.print()
            console.print(Text("INFO", style="dim"))
            for issue in info_issues:
                console.print(Text(f"  [{issue.code}] {issue.message}", style="dim"))
        return

    if fix:
        unverified_claims = [c for c in project.claims if c.status == "unverified"]
        _apply_fix(project_root, unverified_claims)

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

    if info_issues:
        console.print()
        console.print(Text("INFO", style="dim"))
        for issue in info_issues:
            console.print(Text(f"  [{issue.code}] {issue.message}", style="dim"))

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
