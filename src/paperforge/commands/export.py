"""paperforge export command — research graph export."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from paperforge import __version__
from paperforge.core.project import PaperForgeProject

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()

_VALID_FORMATS = ("bibtex", "json", "markdown")

_DEFAULT_OUTPUTS = {
    "bibtex": "references.bib",
    "json": "research_graph.json",
    "markdown": "summary.md",
}


def _default_output_path(project_root: Path, fmt: str) -> Path:
    return project_root / ".paperforge" / "output" / _DEFAULT_OUTPUTS[fmt]


# --- BibTeX ---

def _generate_bibtex(project: PaperForgeProject) -> str:
    all_keys = sorted({key for claim in project.claims for key in claim.citations})
    if not all_keys:
        return (
            "% PaperForge references export\n"
            "% No citations found in any claim.\n"
            "% Add citation keys to your claims, then re-run:\n"
            "%   paperforge export --format bibtex\n"
        )
    lines: list[str] = []
    for key in all_keys:
        lines.append(f"@article{{{key},")
        lines.append("  author    = {Author, A.},")
        lines.append(f"  title     = {{TODO: fill in title for {key}}},")
        lines.append("  journal   = {TODO},")
        lines.append("  year      = {2024},")
        lines.append(
            "  note      = {Auto-generated stub by PaperForge. Replace with real entry.},"
        )
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


# --- JSON ---

def _generate_json(project: PaperForgeProject) -> str:
    edges = [
        {"claim": c.id, "experiment": c.experiment}
        for c in project.claims
        if c.experiment
    ]
    data = {
        "paperforge_version": __version__,
        "exported_at": datetime.now(tz=UTC).isoformat(),
        "project": {
            "title": project.config.title,
            "authors": project.config.authors,
            "venue": project.config.venue,
            "status": project.config.status,
            "sections": project.config.sections,
        },
        "claims": [
            {
                "id": c.id,
                "text": c.text,
                "experiment": c.experiment,
                "figures": c.figures,
                "tables": c.tables,
                "citations": c.citations,
                "sections": c.sections,
                "status": c.status,
                "last_verified": (
                    c.last_verified.isoformat() if c.last_verified else None
                ),
            }
            for c in project.claims
        ],
        "experiments": [
            {
                "id": e.id,
                "description": e.description,
                "results_file": e.results_file,
                "metrics": e.metrics,
                "hardware": e.hardware,
                "dataset": e.dataset,
                "seed": e.seed,
                "ran_at": e.ran_at.isoformat() if e.ran_at else None,
            }
            for e in project.experiments
        ],
        "graph": {
            "claim_count": len(project.claims),
            "experiment_count": len(project.experiments),
            "edges": edges,
        },
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# --- Markdown ---

def _generate_markdown(project: PaperForgeProject) -> str:
    now = datetime.now(tz=UTC).isoformat(timespec="seconds")
    title = project.config.title or "Untitled Paper"
    authors = ", ".join(project.config.authors) if project.config.authors else "TBD"
    venue = project.config.venue or "Not specified"
    status = project.config.status

    claims_total = len(project.claims)
    experiments_total = len(project.experiments)
    claims_verified = sum(1 for c in project.claims if c.status == "verified")
    claims_unverified = sum(1 for c in project.claims if c.status == "unverified")
    claims_stale = sum(1 for c in project.claims if c.status == "stale")

    lines: list[str] = []

    # Header
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Authors:** {authors}")
    lines.append(f"**Venue:** {venue}")
    lines.append(f"**Status:** {status}")
    lines.append(f"**Exported:** {now}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary table
    lines.append("## Project Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Claims | {claims_total} |")
    lines.append(f"| Experiments | {experiments_total} |")
    lines.append(f"| Verified claims | {claims_verified} |")
    lines.append(f"| Unverified claims | {claims_unverified} |")
    lines.append(f"| Stale claims | {claims_stale} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Claims by section
    lines.append("## Claims by Section")
    lines.append("")
    for section in project.config.sections:
        lines.append(f"### {section.replace('_', ' ').title()}")
        section_claims = [c for c in project.claims if section in c.sections]
        if section_claims:
            for claim in section_claims:
                figs = ", ".join(claim.figures) if claim.figures else "none"
                tbls = ", ".join(claim.tables) if claim.tables else "none"
                lines.append(
                    f"- **{claim.id}** ({claim.status}): {claim.text}"
                )
                lines.append(
                    f"  *Evidence:* {claim.experiment or 'none'} | "
                    f"*Figures:* {figs} | "
                    f"*Tables:* {tbls}"
                )
        else:
            lines.append("*(No claims in this section)*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Experiments
    lines.append("## Experiments")
    lines.append("")
    for exp in project.experiments:
        lines.append(f"### {exp.id}")
        lines.append(f"- **Description:** {exp.description or 'none'}")
        lines.append(f"- **Dataset:** {exp.dataset or 'not specified'}")
        lines.append(f"- **Hardware:** {exp.hardware or 'not specified'}")
        lines.append(f"- **Seed:** {exp.seed if exp.seed is not None else 'not specified'}")
        if exp.metrics:
            metrics_str = ", ".join(f"{k}: {v}" for k, v in exp.metrics.items())
        else:
            metrics_str = "none recorded"
        lines.append(f"- **Metrics:** {metrics_str}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Citation keys
    lines.append("## Citation Keys")
    lines.append("")
    all_keys = sorted({key for claim in project.claims for key in claim.citations})
    if all_keys:
        lines.extend(all_keys)
    else:
        lines.append("No citations found.")
    lines.append("")

    return "\n".join(lines)


# --- Main run ---

def run(project_root: Path, fmt: str, output: Path | None) -> None:
    """Export research graph as BibTeX, JSON, or Markdown."""
    if fmt not in _VALID_FORMATS:
        console.print(
            f"[red]Unknown format '{fmt}'. Choose: bibtex, json, markdown[/red]"
        )
        sys.exit(1)

    # STEP 1 — Validate
    if not (project_root / ".paperforge").exists():
        console.print(
            "[red]Not a PaperForge project. Run `paperforge init` first.[/red]"
        )
        sys.exit(1)

    project = PaperForgeProject.load(project_root)

    # STEP 2 — Determine output path
    output_path = output if output is not None else _default_output_path(project_root, fmt)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # STEP 3 — Generate and write
    if fmt == "bibtex":
        content = _generate_bibtex(project)
    elif fmt == "json":
        content = _generate_json(project)
    else:
        content = _generate_markdown(project)

    output_path.write_text(content, encoding="utf-8")

    # STEP 4 — Confirmation
    body = Text()
    body.append(f"Format:      {fmt}\n")
    body.append(f"Output:      {output_path}\n")
    body.append(f"Claims:      {len(project.claims)}\n")
    body.append(f"Experiments: {len(project.experiments)}")
    console.print(Panel(body, title="Export Complete", border_style="green"))
