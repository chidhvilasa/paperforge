"""paperforge export command — research graph export."""

from __future__ import annotations

import csv
import io
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

_VALID_FORMATS = ("bibtex", "json", "markdown", "traceability")

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


# --- Traceability Matrix ---

def _escape_latex(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\\", "\x00BACKSLASH\x00")
    text = text.replace("%", "\\%")
    text = text.replace("$", "\\$")
    text = text.replace("&", "\\&")
    text = text.replace("#", "\\#")
    text = text.replace("_", "\\_")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = text.replace("~", "\x00TILDE\x00")
    text = text.replace("^", "\x00CIRCUM\x00")

    text = text.replace("\x00BACKSLASH\x00", "\\textbackslash{}")
    text = text.replace("\x00TILDE\x00", "\\textasciitilde{}")
    text = text.replace("\x00CIRCUM\x00", "\\textasciicircum{}")
    return text


def _generate_traceability_md(project: PaperForgeProject) -> str:
    title = project.config.title or "Untitled Paper"
    now = datetime.now(tz=UTC).isoformat(timespec="seconds")
    claims_total = len(project.claims)
    claims_linked = sum(1 for c in project.claims if c.experiment)
    coverage_pct = int(claims_linked / claims_total * 100) if claims_total > 0 else 0

    lines: list[str] = []
    lines.append(f"# Claim Traceability Matrix — {title}")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append(
        f"**Evidence Coverage:** {coverage_pct}% ({claims_linked}/{claims_total} claims linked to experiments)"
    )
    lines.append("")
    lines.append(
        "| Claim ID | Text | Status | Experiment | Key Metric | Figures | Tables | Citations | Sections | Verified |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")

    exp_map = {exp.id: exp for exp in project.experiments}

    for claim in sorted(project.claims, key=lambda c: c.id):
        text_disp = claim.text[:60] + "..." if len(claim.text) > 60 else claim.text

        if claim.status == "verified":
            status_disp = "✅ verified"
        elif claim.status == "unverified":
            status_disp = "⚠️ unverified"
        elif claim.status == "stale":
            status_disp = "❌ stale"
        else:
            status_disp = claim.status

        exp_id = claim.experiment or "none"
        key_metric = "none"
        if claim.experiment and claim.experiment in exp_map:
            exp_obj = exp_map[claim.experiment]
            if exp_obj.metrics:
                first_k = next(iter(exp_obj.metrics))
                key_metric = f"{first_k}: {exp_obj.metrics[first_k]}"

        figs = ", ".join(claim.figures) if claim.figures else "none"
        tbls = ", ".join(claim.tables) if claim.tables else "none"
        cits = ", ".join(claim.citations) if claim.citations else "none"
        secs = ", ".join(claim.sections) if claim.sections else "none"
        verified_date = (
            claim.last_verified.strftime("%Y-%m-%d")
            if claim.last_verified
            else "never"
        )

        lines.append(
            f"| {claim.id} | {text_disp} | {status_disp} | {exp_id} | {key_metric} | {figs} | {tbls} | {cits} | {secs} | {verified_date} |"
        )

    lines.append("")
    return "\n".join(lines)


def _generate_traceability_csv(project: PaperForgeProject) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Claim ID",
        "Text",
        "Status",
        "Experiment",
        "Key Metric",
        "Figures",
        "Tables",
        "Citations",
        "Sections",
        "Verified",
    ])

    exp_map = {exp.id: exp for exp in project.experiments}

    for claim in sorted(project.claims, key=lambda c: c.id):
        exp_id = claim.experiment or ""
        key_metric = ""
        if claim.experiment and claim.experiment in exp_map:
            exp_obj = exp_map[claim.experiment]
            if exp_obj.metrics:
                first_k = next(iter(exp_obj.metrics))
                key_metric = f"{first_k}: {exp_obj.metrics[first_k]}"

        figs = "|".join(claim.figures) if claim.figures else ""
        tbls = "|".join(claim.tables) if claim.tables else ""
        cits = "|".join(claim.citations) if claim.citations else ""
        secs = "|".join(claim.sections) if claim.sections else ""
        verified_date = (
            claim.last_verified.strftime("%Y-%m-%d")
            if claim.last_verified
            else ""
        )

        writer.writerow([
            claim.id,
            claim.text,
            claim.status,
            exp_id,
            key_metric,
            figs,
            tbls,
            cits,
            secs,
            verified_date,
        ])

    return output.getvalue()


def _generate_traceability_tex(project: PaperForgeProject) -> str:
    lines: list[str] = [
        "\\begin{longtable}{|l|p{4.5cm}|c|c|p{2.5cm}|}",
        "\\caption{Claim Traceability Matrix} \\label{tab:traceability} \\\\",
        "\\hline",
        "\\textbf{ID} & \\textbf{Claim Text} & \\textbf{Status} & \\textbf{Exp} & \\textbf{Evidence} \\\\",
        "\\hline",
        "\\endfirsthead",
        "\\hline",
        "\\textbf{ID} & \\textbf{Claim Text} & \\textbf{Status} & \\textbf{Exp} & \\textbf{Evidence} \\\\",
        "\\hline",
        "\\endhead",
        "\\hline",
        "\\endfoot",
    ]

    for claim in sorted(project.claims, key=lambda c: c.id):
        cid = _escape_latex(claim.id)
        ctext = _escape_latex(claim.text)
        cstatus = _escape_latex(claim.status)
        cexp = _escape_latex(claim.experiment or "none")

        evidence_items = []
        if claim.figures:
            evidence_items.append("Figs: " + ", ".join(claim.figures))
        if claim.tables:
            evidence_items.append("Tabs: " + ", ".join(claim.tables))
        if claim.citations:
            evidence_items.append("Cits: " + ", ".join(claim.citations))

        evidence_str = _escape_latex(
            "; ".join(evidence_items) if evidence_items else "none"
        )

        lines.append(
            f"{cid} & {ctext} & {cstatus} & {cexp} & {evidence_str} \\\\ \\hline"
        )

    lines.append("\\end{longtable}")
    lines.append("")
    return "\n".join(lines)


# --- Main run ---

def run(project_root: Path, fmt: str, output: Path | None) -> None:
    """Export research graph as BibTeX, JSON, Markdown, or Traceability Matrix."""
    if fmt not in _VALID_FORMATS:
        console.print(
            f"[red]Unknown format '{fmt}'. Choose: bibtex, json, markdown, traceability[/red]"
        )
        sys.exit(1)

    # STEP 1 — Validate
    if not (project_root / ".paperforge").exists():
        console.print(
            "[red]Not a PaperForge project. Run `paperforge init` first.[/red]"
        )
        sys.exit(1)

    project = PaperForgeProject.load(project_root)

    if fmt == "traceability":
        output_dir = output if output is not None else project_root / ".paperforge" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        md_content = _generate_traceability_md(project)
        csv_content = _generate_traceability_csv(project)
        tex_content = _generate_traceability_tex(project)

        (output_dir / "traceability.md").write_text(md_content, encoding="utf-8")
        (output_dir / "traceability.csv").write_text(csv_content, encoding="utf-8")
        (output_dir / "traceability.tex").write_text(tex_content, encoding="utf-8")

        body = Text()
        body.append(f"Format:      {fmt}\n")
        body.append(f"Output:      {output_dir}\n")
        body.append("Files:       traceability.md, traceability.csv, traceability.tex\n")
        body.append(f"Claims:      {len(project.claims)}\n")
        body.append(f"Experiments: {len(project.experiments)}")
        console.print(Panel(body, title="Export Complete", border_style="green"))
        return

    # STEP 2 — Determine output path for single-file exports
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

