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
    claim_id: str = ""


COMMON_ACRONYMS = {
    "IEEE", "AI", "ML", "DL", "IoT", "API", "URL", "DOI",
    "CPU", "GPU", "RAM", "SSD", "PDF", "TCP", "UDP", "IP",
    "HTTP", "TLS", "SSL", "YAML", "JSON", "CLI",
}

ACRONYM_PATTERN = re.compile(r"\b([A-Z]{2,5})\b")


def _is_acronym_defined(acronym: str, all_texts: list[str]) -> bool:
    """
    Returns True if the acronym (or its plural form) is defined
    in any claim text via the pattern 'Expansion (ACRONYM)'
    or 'Expansion (ACRONYMs)'.
    """
    singular = acronym
    plural = acronym + "s"
    for text in all_texts:
        if f"({singular})" in text or f"({plural})" in text:
            return True
    return False


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
        if not claim.text:
            continue
        linked_exp_ids: list[str] = []
        if claim.experiment:
            linked_exp_ids.append(claim.experiment)
        for eid in claim.experiments:
            if eid not in linked_exp_ids:
                linked_exp_ids.append(eid)
        if not linked_exp_ids:
            continue

        combined_metrics: dict[str, float] = {}
        for eid in linked_exp_ids:
            exp_obj = experiment_map.get(eid)
            if exp_obj and exp_obj.metrics:
                combined_metrics.update(exp_obj.metrics)

        if not combined_metrics:
            continue

        percentage_numbers = [
            n for n in extract_numbers(claim.text) if n.is_percentage
        ]
        if not percentage_numbers:
            continue
        # Only consider metrics whose values are in the 0-100 range
        range_metrics = {
            k: v for k, v in combined_metrics.items() if 0 <= v <= 100
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
                            f"but no metric in {linked_exp_ids} matches "
                            f"(metrics: {combined_metrics})"
                        ),
                    )
                )
                break  # at most one METRIC_CLAIM_MISMATCH per claim

    # Check 12 — DUPLICATE_CLAIM_TEXT (ERROR)
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
                    severity="ERROR",
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
        if experiment.seed is None and experiment.seeds is None:
            issues.append(
                Issue(
                    code="EXPERIMENT_NO_SEED",
                    severity="WARNING",
                    message=(
                        f"{experiment.id} has no seed(s) recorded. "
                        f"Set either 'seed: 42' (single) or "
                        f"'seeds: [0,1,2,3,4]' (multi-seed experiment)."
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
        for match in ACRONYM_PATTERN.findall(text):
            base_acronym = (
                match[:-1] if match.endswith("S") and len(match) > 2 else match
            )
            found_acronyms.add(base_acronym)
    for acronym in sorted(found_acronyms - COMMON_ACRONYMS):
        if not _is_acronym_defined(acronym, all_claim_text):
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
    if 0 < abstract_word_count < 100:
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
            and 150 <= figure.resolution_dpi < 300
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

    # --- Checks 37-41: Table completeness ---

    claimed_table_ids = {
        tbl_id
        for claim in project.claims
        for tbl_id in claim.tables
    }
    existing_table_ids = {tbl.id for tbl in project.tables}

    # Check 37 — TABLE_NO_CAPTION (ERROR)
    for table in project.tables:
        if not table.caption:
            issues.append(
                Issue(
                    code="TABLE_NO_CAPTION",
                    severity="ERROR",
                    message=(
                        f"{table.id} has no caption. "
                        f"IEEE requires all tables to have captions "
                        f"(placed ABOVE the table)."
                    ),
                )
            )

    # Check 38 — TABLE_NO_COLUMNS (WARNING)
    for table in project.tables:
        if not table.columns:
            issues.append(
                Issue(
                    code="TABLE_NO_COLUMNS",
                    severity="WARNING",
                    message=f"{table.id} has no column headers defined.",
                )
            )

    # Check 39 — TABLE_REFERENCED_BUT_NO_YAML (WARNING)
    for tbl_id in claimed_table_ids:
        if tbl_id not in existing_table_ids:
            issues.append(
                Issue(
                    code="TABLE_REFERENCED_BUT_NO_YAML",
                    severity="WARNING",
                    message=(
                        f"Claim references '{tbl_id}' but no "
                        f".paperforge/tables/{tbl_id}.yaml exists. "
                        f"Run `paperforge add-table` to create it."
                    ),
                )
            )

    # Check 40 — TABLE_YAML_BUT_NO_CLAIM (WARNING)
    for table_id in existing_table_ids:
        if table_id not in claimed_table_ids:
            issues.append(
                Issue(
                    code="TABLE_YAML_BUT_NO_CLAIM",
                    severity="WARNING",
                    message=(
                        f"{table_id} has a YAML file but is not "
                        f"referenced in any claim."
                    ),
                )
            )

    # Check 41 — TABLE_ROW_COLUMN_MISMATCH (WARNING)
    for table in project.tables:
        if table.columns and table.rows:
            expected_cols = len(table.columns)
            for row in table.rows:
                if len(row) != expected_cols:
                    issues.append(
                        Issue(
                            code="TABLE_ROW_COLUMN_MISMATCH",
                            severity="WARNING",
                            message=(
                                f"{table.id} has {expected_cols} columns but "
                                f"row {table.rows.index(row)+1} has {len(row)} "
                                f"cells."
                            ),
                        )
                    )
                    break

    # Check 42 — MISSING_ACKNOWLEDGMENT (WARNING)
    if not project.config.acknowledgment:
        issues.append(
            Issue(
                code="MISSING_ACKNOWLEDGMENT",
                severity="WARNING",
                message=(
                    "paper.yaml acknowledgment field is empty. "
                    "IEEE submissions typically require an acknowledgment "
                    "section crediting funding sources."
                ),
            )
        )

    # Check 43 — WIDE_TABLE_RECOMMENDED (WARNING)
    for table in project.tables:
        if len(table.columns) >= 6 and not table.wide:
            issues.append(
                Issue(
                    code="WIDE_TABLE_RECOMMENDED",
                    severity="WARNING",
                    message=(
                        f"{table.id} has {len(table.columns)} columns. "
                        f"Consider setting wide: true for two-column "
                        f"IEEE layout to prevent overflow."
                    ),
                )
            )

    # Citation Checks 44-48
    citation_map = {c.key: c for c in project.citations}
    all_claimed_keys = {
        key for claim in project.claims for key in claim.citations
    }
    all_defined_keys = set(citation_map.keys())

    # Check 44 — CITED_KEY_NO_YAML (WARNING)
    for key in sorted(all_claimed_keys):
        if key not in all_defined_keys:
            issues.append(
                Issue(
                    code="CITED_KEY_NO_YAML",
                    severity="WARNING",
                    message=(
                        f"Citation key '{key}' used in claims but has no "
                        f".paperforge/citations/{key}.yaml. "
                        f"Run `paperforge add-citation {key}`."
                    ),
                )
            )

    # Check 45 — CITATION_YAML_NO_CLAIM (WARNING)
    for key in sorted(all_defined_keys):
        if key not in all_claimed_keys:
            issues.append(
                Issue(
                    code="CITATION_YAML_NO_CLAIM",
                    severity="WARNING",
                    message=(
                        f"Citation '{key}' has a YAML file but is not "
                        f"used in any claim."
                    ),
                )
            )

    # Check 46 — CITATION_NO_TITLE (ERROR)
    for citation in project.citations:
        if not citation.title:
            issues.append(
                Issue(
                    code="CITATION_NO_TITLE",
                    severity="ERROR",
                    message=(
                        f"Citation '{citation.key}' has no title. "
                        f"A reference without a title cannot appear in "
                        f"an IEEE bibliography."
                    ),
                )
            )

    # Check 47 — CITATION_NO_YEAR (WARNING)
    for citation in project.citations:
        if citation.year is None:
            issues.append(
                Issue(
                    code="CITATION_NO_YEAR",
                    severity="WARNING",
                    message=f"Citation '{citation.key}' has no year.",
                )
            )

    # Check 48 — CITATION_NO_AUTHORS (WARNING)
    for citation in project.citations:
        if not citation.authors:
            issues.append(
                Issue(
                    code="CITATION_NO_AUTHORS",
                    severity="WARNING",
                    message=f"Citation '{citation.key}' has no authors.",
                )
            )

    # Check 49 — MULTI_EXPERIMENT_CLAIM (INFO)
    for claim in project.claims:
        if claim.experiments:
            issues.append(
                Issue(
                    code="MULTI_EXPERIMENT_CLAIM",
                    severity="INFO",
                    message=(
                        f"{claim.id} draws from {1 + len(claim.experiments)} "
                        f"experiments: [{claim.experiment}] + "
                        f"{claim.experiments}. Verify all are cited."
                    ),
                )
            )

    # Check 50 — FUNDING_IN_ACKNOWLEDGMENT (WARNING)
    if project.config.acknowledgment:
        ack_lower = project.config.acknowledgment.lower()
        funding_keywords = ["supported by", "grant", "funded by", "nsf", "nih"]
        if any(kw in ack_lower for kw in funding_keywords):
            issues.append(
                Issue(
                    code="FUNDING_IN_ACKNOWLEDGMENT",
                    severity="WARNING",
                    message=(
                        "Acknowledgment section appears to contain funding info. "
                        "Per IEEE convention, funding goes in the \\thanks{} "
                        "footnote (use the 'funding:' field in paper.yaml), "
                        "not in the acknowledgment section."
                    ),
                )
            )

    # Check 51 — MISSING_COI (WARNING)
    if not project.config.conflict_of_interest:
        issues.append(
            Issue(
                code="MISSING_COI",
                severity="WARNING",
                message=(
                    "IEEE Access requires a conflict of interest statement. "
                    "Set 'conflict_of_interest:' in paper.yaml. If none: "
                    "'The authors declare no conflicts of interest.'"
                ),
            )
        )

    # Check 52 — MISSING_DATA_AVAILABILITY (WARNING)
    if not project.config.data_availability:
        issues.append(
            Issue(
                code="MISSING_DATA_AVAILABILITY",
                severity="WARNING",
                message=(
                    "IEEE Access expects a data availability statement. "
                    "Set 'data_availability:' in paper.yaml."
                ),
            )
        )

    # Check 53 — ABSTRACT_HAS_CITATION (ERROR)
    abstract_claims_list = [c for c in project.claims if "abstract" in c.sections]
    if any(c.citations for c in abstract_claims_list):
        issues.append(
            Issue(
                code="ABSTRACT_HAS_CITATION",
                severity="ERROR",
                message=(
                    "Abstract claims have linked citations. IEEE Access "
                    "abstracts must not contain citation references. "
                    "Move citations to Introduction or body sections."
                ),
            )
        )

    # Check 54 — ABSTRACT_MULTIPARAGRAPH (WARNING)
    joined_abstract_text = " ".join(c.text for c in abstract_claims_list if c.text)
    if "\n\n" in joined_abstract_text:
        issues.append(
            Issue(
                code="ABSTRACT_MULTIPARAGRAPH",
                severity="WARNING",
                message=(
                    "Abstract appears to contain multiple paragraphs. "
                    "IEEE Access requires a single-paragraph abstract."
                ),
            )
        )

    # Check 55 — KEYWORDS_NOT_ALPHABETICAL (WARNING)
    if project.config.keywords and len(project.config.keywords) > 1:
        sorted_kw = sorted(project.config.keywords, key=str.lower)
        if sorted_kw != project.config.keywords:
            issues.append(
                Issue(
                    code="KEYWORDS_NOT_ALPHABETICAL",
                    severity="WARNING",
                    message=(
                        "IEEE style recommends alphabetical keyword order. "
                        f"Suggested order: {', '.join(sorted_kw)}"
                    ),
                )
            )

    # Check 56 — TOO_FEW_KEYWORDS (WARNING)
    if len(project.config.keywords) < 4:
        issues.append(
            Issue(
                code="TOO_FEW_KEYWORDS",
                severity="WARNING",
                message=(
                    f"Only {len(project.config.keywords)} keyword(s). "
                    "IEEE Access expects 4-8 keywords."
                ),
            )
        )

    # Check 57 — TOO_MANY_KEYWORDS (WARNING)
    if len(project.config.keywords) > 8:
        issues.append(
            Issue(
                code="TOO_MANY_KEYWORDS",
                severity="WARNING",
                message=(
                    f"{len(project.config.keywords)} keywords. "
                    "IEEE Access recommends 4-8 keywords."
                ),
            )
        )

    # Check 58 — TABLE_NOTES_INTERNAL_REF (WARNING)
    table_internal_patterns = [
        r"\.\w{2,4}$",
        r"exp_\w+",
        r"D-\d{3}",
        r"TECH_DEBT",
        r"results[/\\]",
        r"\.json",
        r"\.txt",
        r"\w+_results",
    ]
    for table in project.tables:
        if table.notes:
            matched_pat = None
            for pat in table_internal_patterns:
                if re.search(pat, table.notes, re.IGNORECASE):
                    matched_pat = pat
                    break
            if matched_pat:
                issues.append(
                    Issue(
                        code="TABLE_NOTES_INTERNAL_REF",
                        severity="WARNING",
                        message=(
                            f"{table.id} notes contain internal references "
                            f"(matched '{matched_pat}'). Table notes should be "
                            f"reader-facing prose, not lab notes."
                        ),
                    )
                )

    # Check 59 — ABSTRACT_INTRO_OVERLAP (ERROR)
    claims_in_abstract_set = {
        c.id for c in project.claims if "abstract" in c.sections
    }
    claims_in_intro_set = {
        c.id for c in project.claims if "introduction" in c.sections
    }
    overlap_set = claims_in_abstract_set & claims_in_intro_set
    if overlap_set:
        issues.append(
            Issue(
                code="ABSTRACT_INTRO_OVERLAP",
                severity="ERROR",
                message=(
                    f"Claims {sorted(overlap_set)} appear in both abstract "
                    f"and introduction. The introduction must not repeat "
                    f"the abstract. Use separate claims for each section."
                ),
            )
        )

    # Check 60 — INTRO_MISSING_MOTIVATION (WARNING)
    claims_in_results_set = {
        c.id for c in project.claims if "results" in c.sections
    }
    if claims_in_intro_set and claims_in_intro_set.issubset(
        claims_in_abstract_set | claims_in_results_set
    ):
        issues.append(
            Issue(
                code="INTRO_MISSING_MOTIVATION",
                severity="WARNING",
                message=(
                    "Introduction only contains result statements. "
                    "Introduction should also contain: problem motivation, "
                    "gap in existing work, and explicit contributions list."
                ),
            )
        )

    # Check 61 — DUPLICATE_CITATION_KEY (WARNING)
    for claim in project.claims:
        if claim.citations and len(claim.citations) != len(set(claim.citations)):
            issues.append(
                Issue(
                    code="DUPLICATE_CITATION_KEY",
                    severity="WARNING",
                    message=(
                        "Claim has duplicate citation key. "
                        "Each key should appear once per claim."
                    ),
                )
            )

    # Check 62 — CITATION_YEAR_FUTURE (WARNING)
    for citation in project.citations:
        if citation.year is not None and citation.year > 2026:
            issues.append(
                Issue(
                    code="CITATION_YEAR_FUTURE",
                    severity="WARNING",
                    message=(
                        f"Citation '{citation.key}' has year {citation.year} "
                        f"which is in the future. Verify the year is correct."
                    ),
                )
            )

    # Check 63 — FIGURE_CRITICALLY_LOW_RESOLUTION (ERROR)
    for figure in project.figures:
        if (
            figure.resolution_dpi is not None
            and figure.format is not None
            and figure.format.lower() in ("png", "jpg", "jpeg", "tiff", "tif")
            and figure.resolution_dpi < 150
        ):
            issues.append(
                Issue(
                    code="FIGURE_CRITICALLY_LOW_RESOLUTION",
                    severity="ERROR",
                    message=(
                        f"{figure.id} has {figure.resolution_dpi} DPI. "
                        f"Minimum for IEEE production: 300 DPI (photos/color), "
                        f"600 DPI (line art). This will fail production check."
                    ),
                )
            )

    # Check 64 — FIGURE_FORMAT_NOT_IEEE (WARNING)
    for figure in project.figures:
        if (
            figure.format
            and figure.format.lower()
            not in (
                "pdf",
                "eps",
                "ps",
                "png",
                "jpg",
                "jpeg",
                "tiff",
                "tif",
            )
        ):
                issues.append(
                    Issue(
                        code="FIGURE_FORMAT_NOT_IEEE",
                        severity="WARNING",
                        message=(
                            f"{figure.id} format '{figure.format}' may not be "
                            f"accepted by IEEE production. Preferred: PDF, EPS, "
                            f"PNG (300+ DPI), TIFF (300+ DPI)."
                        ),
                    )
                )

    # Check 65 — UNUSUAL_SECTION_ORDER (WARNING)
    expected_section_order = [
        "abstract",
        "introduction",
        "related_work",
        "methodology",
        "experiments",
        "results",
        "discussion",
        "conclusion",
    ]
    configured_sections = [
        s for s in project.config.sections if s in expected_section_order
    ]
    indices = [expected_section_order.index(s) for s in configured_sections]
    if indices != sorted(indices):
        issues.append(
            Issue(
                code="UNUSUAL_SECTION_ORDER",
                severity="WARNING",
                message=(
                    f"Section order {configured_sections} deviates from "
                    f"standard IEEE structure. Verify this is intentional."
                ),
            )
        )

    # Check 66 — REPRODUCIBILITY_INCOMPLETE (WARNING)
    for experiment in project.experiments:
        missing_repro = []
        if not experiment.seed and not experiment.seeds:
            missing_repro.append("seed")
        if not experiment.hardware:
            missing_repro.append("hardware")
        if not experiment.dataset:
            missing_repro.append("dataset")
        if not experiment.description:
            missing_repro.append("description")
        if missing_repro:
            issues.append(
                Issue(
                    code="REPRODUCIBILITY_INCOMPLETE",
                    severity="WARNING",
                    message=(
                        f"{experiment.id} missing reproducibility fields: "
                        f"{', '.join(missing_repro)}. IEEE reviewers routinely "
                        f"request these for replication."
                    ),
                )
            )

    # Check 67 — PVALUE_WITHOUT_TEST_NAME (WARNING)
    p_val_regex = re.compile(r"p\s*[=<>]\s*0\.\d+", re.IGNORECASE)
    test_keywords = ["wilcoxon", "t-test", "anova", "mann-whitney", "chi-square"]
    for claim in project.claims:
        if claim.text and p_val_regex.search(claim.text):
            exp = experiment_map.get(claim.experiment or "")
            exp_desc = (exp.description or "").lower() if exp else ""
            if not any(tk in exp_desc for tk in test_keywords):
                issues.append(
                    Issue(
                        code="PVALUE_WITHOUT_TEST_NAME",
                        severity="WARNING",
                        message=(
                            f"{claim.id} reports a p-value but the linked "
                            f"experiment description does not name the statistical "
                            f"test used. IEEE reviewers require the test name, "
                            f"degrees of freedom, and effect size."
                        ),
                    )
                )

    # Check 68 — MISSING_CORRESPONDING_EMAIL (WARNING)
    if not project.config.email:
        issues.append(
            Issue(
                code="MISSING_CORRESPONDING_EMAIL",
                severity="WARNING",
                message=(
                    "No corresponding author email set. Add 'email:' "
                    "to paper.yaml. IEEE Access requires a corresponding "
                    "author email in the author block."
                ),
            )
        )

    # Check 69 — MISSING_ORCID (INFO)
    if not project.config.orcid:
        issues.append(
            Issue(
                code="MISSING_ORCID",
                severity="INFO",
                message=(
                    "No ORCID iD set. IEEE Access supports ORCID "
                    "in the author block. Add 'orcid:' to paper.yaml."
                ),
            )
        )

    # Check 70 — TITLE_ENDS_WITH_PERIOD (WARNING)
    if project.config.title and project.config.title.strip().endswith("."):
        issues.append(
            Issue(
                code="TITLE_ENDS_WITH_PERIOD",
                severity="WARNING",
                message="IEEE title should not end with a period.",
            )
        )

    # Check 71 — TITLE_TOO_LONG (WARNING)
    if project.config.title:
        word_cnt = len(project.config.title.split())
        if word_cnt > 15:
            issues.append(
                Issue(
                    code="TITLE_TOO_LONG",
                    severity="WARNING",
                    message=(
                        f"Title is {word_cnt} words. IEEE titles are "
                        f"typically under 15 words."
                    ),
                )
            )

    # Check 72 — NO_CONTRIBUTION_CLAIMS (WARNING)
    intro_claims = [c for c in project.claims if "introduction" in c.sections]
    if intro_claims and not any(c.is_contribution for c in intro_claims):
        issues.append(
            Issue(
                code="NO_CONTRIBUTION_CLAIMS",
                severity="WARNING",
                message=(
                    "Introduction has no contribution claims. "
                    "IEEE papers list explicit contributions. "
                    "Set is_contribution: true on contribution claims."
                ),
            )
        )

    # Check 73 — MISSING_SECTIONS_OVERVIEW (WARNING)
    if not project.config.sections_overview:
        issues.append(
            Issue(
                code="MISSING_SECTIONS_OVERVIEW",
                severity="WARNING",
                message=(
                    "No sections_overview set. IEEE introductions "
                    "typically end with paper organization. "
                    "Set 'sections_overview:' in paper.yaml."
                ),
            )
        )

    # Check 74 — FIGURE_MIXED_METRIC_UNITS (WARNING)
    for figure in project.figures:
        if figure.source_experiment and not figure.metric_keys:
            exp = experiment_map.get(figure.source_experiment)
            if exp and exp.metrics:
                m_keys = [k.lower() for k in exp.metrics]
                has_latency = any("ms" in k or "latency" in k for k in m_keys)
                has_ratio = any("ratio" in k or "pdr" in k or "rate" in k for k in m_keys)
                if has_latency and has_ratio:
                    issues.append(
                        Issue(
                            code="FIGURE_MIXED_METRIC_UNITS",
                            severity="WARNING",
                            message=(
                                f"{figure.id} will plot metrics with mixed units "
                                f"(latency in ms + ratios). Set 'metric_keys:' "
                                f"to specify which metrics to plot."
                            ),
                        )
                    )

    # Check 75 — MATH_CLAIM_MISSING_FLAG (WARNING)
    math_tokens = [
        r"\\", r"\alpha", r"\beta", r"\gamma", r"\theta", r"\sum", r"\prod",
        r"\frac", r"\begin{equation", r"\mathbf", r"\mathcal", r"\[", "$$", "$"
    ]
    for claim in project.claims:
        if (
            not claim.is_math
            and not claim.raw_latex
            and any(token in claim.text for token in math_tokens)
        ):
            issues.append(
                Issue(
                    code="MATH_CLAIM_MISSING_FLAG",
                    severity="WARNING",
                    message=(
                        f"{claim.id} text appears to contain LaTeX math "
                        f"but is_math: false. Set 'is_math: true' to prevent "
                        f"escape_latex() from corrupting math content."
                    ),
                )
            )

    # Check 76 — PROOF_WITHOUT_THEOREM (WARNING)
    for claim in project.claims:
        if claim.claim_type == "proof":
            has_thm = any(
                c.claim_type in ("theorem", "lemma") for c in project.claims
            )
            if not has_thm:
                issues.append(
                    Issue(
                        code="PROOF_WITHOUT_THEOREM",
                        severity="WARNING",
                        message=(
                            f"{claim.id} is a proof but no theorem/lemma "
                            f"precedes it in the project."
                        ),
                        claim_id=claim.id,
                    )
                )

    # Check 78 — CLAIM_MISSING_IMPORT_HASH (INFO)
    for claim in project.claims:
        # Heuristic: imported claim = no experiment, status=unverified,
        # no figures/tables, non-empty text
        if (
            not claim.import_hash
            and not claim.experiment
            and claim.status == "unverified"
            and not claim.figures
            and not claim.tables
            and claim.text
        ):
            issues.append(
                Issue(
                    code="CLAIM_MISSING_IMPORT_HASH",
                    severity="INFO",
                    message=(
                        f"{claim.id} appears imported but has no hash. "
                        "Run `paperforge import` to add tracking hash."
                    ),
                    claim_id=claim.id,
                )
            )

    # Check 79 — MISSING_BIOGRAPHY (WARNING)
    if project.config.authors and not project.config.biographies:
        issues.append(
            Issue(
                code="MISSING_BIOGRAPHY",
                severity="WARNING",
                message=(
                    "No author biographies set. IEEE Access strongly "
                    "encourages author biographies. Add 'biographies:' "
                    "to paper.yaml."
                ),
            )
        )

    # Check 80 — MISSING_AI_DISCLOSURE (INFO)
    issues.append(
        Issue(
            code="MISSING_AI_DISCLOSURE",
            severity="INFO",
            message=(
                "IEEE requires disclosure if AI tools were used. "
                "Set 'ai_disclosure:' in paper.yaml, or set to "
                "'No AI tools were used in this work.' if applicable."
            ),
        )
    )

    return issues


def _print_fix_hint(issue: "Issue", project: "PaperForgeProject") -> None:
    """Print a concrete fix hint for an issue when --fix-hints is active."""
    hints: dict[str, str] = {
        "ORPHAN_CLAIM": "Edit the claim YAML and set 'experiment: exp_XX'.",
        "MISSING_EXPERIMENT": "Run `paperforge capture --experiment EXP_ID results.json` to create the experiment.",
        "STALE_CLAIM": "Re-run your experiment and update the claim text/metrics.",
        "EMPTY_CLAIM_TEXT": "Edit the claim YAML and add text: 'Your claim here.'",
        "UNVERIFIED_CLAIM": "After verifying, set 'status: verified' in the claim YAML.",
        "METRIC_CLAIM_MISMATCH": (
            "Check experiment metrics. Run `paperforge diff CLAIM_ID --against experiment` "
            "to see available metric values."
        ),
        "DUPLICATE_CLAIM_TEXT": "Delete one of the duplicate claim YAML files in .paperforge/claims/.",
        "CLAIM_IN_NO_SECTION": "Add 'sections: [results]' (or appropriate section) to the claim YAML.",
        "MISSING_PAPER_TITLE": "Set 'title: Your Paper Title' in .paperforge/paper.yaml.",
        "MISSING_AUTHORS": "Set 'authors: [Author Name]' in .paperforge/paper.yaml.",
        "MISSING_AFFILIATION": "Add 'affiliations:' list to .paperforge/paper.yaml.",
        "MISSING_ACKNOWLEDGMENT": "Set 'acknowledgment: Your acknowledgment text' in paper.yaml.",
        "MISSING_COI": "Set 'conflict_of_interest: The authors declare no conflicts of interest.' in paper.yaml.",
        "MISSING_DATA_AVAILABILITY": "Set 'data_availability:' in paper.yaml.",
        "MISSING_BIOGRAPHY": "Add 'biographies: [{author: Name, text: Bio text.}]' to paper.yaml.",
        "MISSING_AI_DISCLOSURE": "Set 'ai_disclosure: No AI tools were used.' or describe your AI tool use in paper.yaml.",
        "MISSING_CORRESPONDING_EMAIL": "Set 'email: your@email.com' in paper.yaml.",
        "CLAIM_MISSING_IMPORT_HASH": "Run `paperforge import` to add tracking hashes to legacy claims.",
        "RESULTS_SECTION_EMPTY": "Add claims with 'sections: [results]' to your results section.",
        "NO_INTRODUCTION_CLAIMS": "Add claims with 'sections: [introduction]' to introduce your paper.",
        "NO_CONCLUSION_CLAIMS": "Add claims with 'sections: [conclusion]' to your conclusion section.",
        "ABSTRACT_TOO_LONG": "Shorten abstract claims. IEEE recommends under 250 words.",
        "ABSTRACT_TOO_SHORT": "Expand abstract claims to at least 150 words.",
        "ABSTRACT_HAS_CITATION": "Remove citations from abstract claims — move them to introduction.",
        "DUPLICATE_CLAIM_TEXT": "Delete one of the duplicate claim YAML files from .paperforge/claims/.",
    }
    hint = hints.get(issue.code)

    # For METRIC_CLAIM_MISMATCH, try to show available metrics
    if issue.code == "METRIC_CLAIM_MISMATCH" and issue.claim_id:
        claim = next((c for c in project.claims if c.id == issue.claim_id), None)
        if claim:
            exp_ids = [claim.experiment] + list(claim.experiments)
            exp_map = {e.id: e for e in project.experiments}
            for eid in exp_ids:
                exp = exp_map.get(eid)
                if exp and exp.metrics:
                    metrics_str = ", ".join(
                        f"{k}: {v}" for k, v in list(exp.metrics.items())[:5]
                    )
                    hint = f"Available metrics in {eid}: {metrics_str}"
                    break

    if hint:
        console.print(Text(f"    Fix hint: {hint}", style="dim cyan"))




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


def run_self_check(project_root: Path) -> None:
    import importlib.metadata
    import shutil

    from paperforge import __version__

    console.print(f"[bold]PaperForge Environment Diagnostics (v{__version__})[/bold]\n")

    # 1. Version & dependencies
    console.print("[cyan]1. Dependencies & Libraries[/cyan]")
    for pkg in ["python-docx", "matplotlib", "pyyaml", "rich", "typer"]:
        try:
            ver = importlib.metadata.version(pkg)
            console.print(f"  ✅ {pkg}: installed ({ver})")
        except importlib.metadata.PackageNotFoundError:
            console.print(f"  ❌ {pkg}: NOT installed")

    # 2. System tools
    console.print("\n[cyan]2. System Tools & Toolchains[/cyan]")
    pdflatex = shutil.which("pdflatex")
    latexmk = shutil.which("latexmk")
    llm = shutil.which("llm")
    git = shutil.which("git")

    console.print(f"  {'✅' if pdflatex else '⚠️'} pdflatex: {pdflatex or 'not found (DOCX fallback)'}")
    console.print(f"  {'✅' if latexmk else '⚠️'} latexmk: {latexmk or 'not found'}")
    console.print(f"  {'✅' if llm else 'ℹ️'} llm CLI: {llm or 'not found (optional)'}")
    console.print(f"  {'✅' if git else '⚠️'} git: {git or 'not found'}")

    # 3. Directories
    console.print("\n[cyan]3. Project Directory Structure[/cyan]")
    if (project_root / ".paperforge").exists():
        project = PaperForgeProject.load(project_root)
        out_dir = project_root / project.config.build_output_dir
        info_dir = project_root / project.config.paper_information_dir
        console.print("  ✅ .paperforge/ present")
        console.print(f"  {'✅' if out_dir.exists() else '⚠️'} Output dir ({project.config.build_output_dir}): {'exists' if out_dir.exists() else 'missing'}")
        console.print(f"  {'✅' if info_dir.exists() else '⚠️'} Info dir ({project.config.paper_information_dir}): {'exists' if info_dir.exists() else 'missing'}")
    else:
        console.print("  ℹ️ Not inside a PaperForge project directory")

    console.print("\n[bold green]Self-check completed.[/bold green]")


def run_pre_submission_check(project: PaperForgeProject) -> bool:
    """Print a SUBMISSION READINESS REPORT with pass/fail for 10 submission requirements."""
    abstract_claims = [c for c in project.claims if "abstract" in c.sections]
    abstract_words = sum(len(c.text.split()) for c in abstract_claims)
    abstract_pass = 150 <= abstract_words <= 250

    unique_citations = {k for c in project.claims for k in c.citations}
    num_citations = max(len(unique_citations), len(project.citations))
    citations_pass = num_citations >= 15

    figs_with_captions = sum(
        1 for f in project.figures if f.caption and f.caption.strip()
    )
    total_figs = len(project.figures)
    figs_pass = total_figs == 0 or figs_with_captions == total_figs

    tbls_with_captions = sum(
        1 for t in project.tables if t.caption and t.caption.strip()
    )
    total_tbls = len(project.tables)
    tbls_pass = total_tbls == 0 or tbls_with_captions == total_tbls

    contrib_claims = [c for c in project.claims if c.is_contribution]
    contrib_pass = len(contrib_claims) >= 1

    verified_claims = [c for c in project.claims if c.status == "verified"]
    total_claims = len(project.claims)
    verified_pass = total_claims > 0 and len(verified_claims) == total_claims

    email_set = bool(
        project.config.email
        or any(a.email for a in project.config.affiliations)
    )
    coi_set = bool(project.config.conflict_of_interest)
    data_avail_set = bool(project.config.data_availability)

    all_pass = (
        abstract_pass
        and citations_pass
        and figs_pass
        and tbls_pass
        and contrib_pass
        and verified_pass
        and email_set
        and coi_set
        and data_avail_set
    )

    def mark(ok: bool) -> str:
        return "[bold green]✓[/bold green]" if ok else "[bold red]✗[/bold red]"

    report_lines = [
        f"Abstract word count:     {abstract_words} / 150-250  [{mark(abstract_pass)}]",
        f"Citations:               {num_citations} / 15+      [{mark(citations_pass)}]",
        f"Figures with captions:   {figs_with_captions}/{total_figs}          [{mark(figs_pass)}]",
        f"Tables with captions:    {tbls_with_captions}/{total_tbls}          [{mark(tbls_pass)}]",
        f"Contribution claims:     {len(contrib_claims)}            [{mark(contrib_pass)}]",
        f"Verified claims:         {len(verified_claims)}/{total_claims}          [{mark(verified_pass)}]",
        f"Email set:               [{mark(email_set)}]",
        f"COI set:                 [{mark(coi_set)}]",
        f"Data availability set:   [{mark(data_avail_set)}]",
        "",
        f"Overall: [{'READY FOR SUBMISSION' if all_pass else 'NOT READY FOR SUBMISSION'}]",
    ]

    style = "green" if all_pass else "yellow"
    console.print(
        Panel(
            "\n".join(report_lines),
            title="SUBMISSION READINESS REPORT",
            border_style=style,
        )
    )
    return all_pass


def run(
    project_root: Path,
    fix: bool = False,
    target: str | None = None,
    self_check: bool = False,
    pre_submission: bool = False,
    fix_hints: bool = False,
    json_output: bool = False,
) -> None:
    if self_check:
        run_self_check(project_root)
        return

    if not (project_root / ".paperforge").exists():
        console.print(
            "[red]Not a PaperForge project. Run `paperforge init` first.[/red]"
        )
        sys.exit(1)

    project = PaperForgeProject.load(project_root)

    if pre_submission:
        run_pre_submission_check(project)


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

    all_issues = issues + venue_issues

    # JSON output mode
    if json_output:
        import json
        data = [
            {"code": i.code, "severity": i.severity, "message": i.message, "claim_id": i.claim_id}
            for i in all_issues
        ]
        console.print(json.dumps({"issues": data}, indent=2, ensure_ascii=False))
        if any(i.severity == "ERROR" for i in all_issues):
            sys.exit(1)
        return

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
            if fix_hints:
                _print_fix_hint(issue, project)

    if warnings:
        console.print()
        console.print(Text("WARNING", style="bold yellow"))
        for issue in warnings:
            console.print(Text(f"  [{issue.code}] {issue.message}"))
            if fix_hints:
                _print_fix_hint(issue, project)

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

    # Issues by section
    section_issue_counts: dict[str, dict[str, int]] = {}
    claim_map = {c.id: c for c in project.claims}
    for issue in all_issues:
        if issue.severity == "INFO":
            continue
        # Map to section via claim_id
        secs: list[str] = []
        if issue.claim_id and issue.claim_id in claim_map:
            secs = claim_map[issue.claim_id].sections or ["(global)"]
        elif not issue.claim_id:
            secs = ["(global)"]
        for sec in secs:
            section_issue_counts.setdefault(sec, {"errors": 0, "warnings": 0})
            if issue.severity == "ERROR":
                section_issue_counts[sec]["errors"] += 1
            else:
                section_issue_counts[sec]["warnings"] += 1

    console.print()
    console.print("─" * 40)
    console.print(
        f"Summary: {len(total_errors)} error(s), {len(total_warnings)} warning(s)"
    )

    if section_issue_counts:
        console.print()
        console.print(Text("Issues by section:", style="bold"))
        for sec, counts in sorted(section_issue_counts.items()):
            parts = []
            if counts["errors"]:
                parts.append(f"{counts['errors']} error(s)")
            if counts["warnings"]:
                parts.append(f"{counts['warnings']} warning(s)")
            if parts:
                console.print(f"  {sec}: {', '.join(parts)}")
            else:
                console.print(f"  {sec}: 0 issues ✓")

    if not fix and total_warnings:
        console.print(
            "Run `paperforge doctor --fix` to auto-resolve fixable warnings."
        )

    if total_errors:
        sys.exit(1)
