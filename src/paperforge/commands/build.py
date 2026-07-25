"""paperforge build command."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.venues.base import VenuePlugin
from paperforge.venues.registry import get_plugin

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()

SECTION_TITLES = {
    "introduction": "Introduction",
    "related_work": "Related Work",
    "methodology": "Methodology",
    "experiments": "Experimental Setup",
    "results": "Results",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
}


def _claim_paragraph(claim: Claim) -> str:
    paragraph = claim.text
    for citation in claim.citations:
        paragraph += f" \\cite{{{citation}}}"
    for figure in claim.figures:
        paragraph += f" \\ref{{fig:{figure}}}"
    for table in claim.tables:
        paragraph += f" \\ref{{tab:{table}}}"
    return paragraph


def _generate_abstract(claims: list[Claim]) -> str:
    abstract_claims = [c for c in claims if "abstract" in c.sections]
    if not abstract_claims:
        return "% TODO: Add claims to the abstract section."
    return " ".join(c.text for c in sorted(abstract_claims, key=lambda c: c.id))


def _generate_sections(sections: list[str], claims: list[Claim]) -> str:
    blocks: list[str] = []
    for section in sections:
        if section == "abstract":
            continue
        title = SECTION_TITLES.get(section, section.replace("_", " ").title())
        section_claims = sorted(
            (c for c in claims if section in c.sections), key=lambda c: c.id
        )
        block = f"\\section{{{title}}}\n"
        if section_claims:
            block += "\n\n".join(_claim_paragraph(c) for c in section_claims)
        else:
            block += "% TODO: No claims linked to this section yet."
        blocks.append(block)
    return "\n\n".join(blocks)


def _generate_latex(project: PaperForgeProject, plugin: VenuePlugin) -> str:
    title = project.config.title or "Untitled Paper"
    author_block = plugin.generate_author_block(project.config.authors)
    abstract_content = _generate_abstract(project.claims)
    sections = _generate_sections(project.config.sections, project.claims)

    has_citations = any(claim.citations for claim in project.claims)
    bibliography = (
        "\\bibliographystyle{IEEEtran}\n\\bibliography{references}"
        if has_citations
        else ""
    )

    return f"""{plugin.latex_documentclass}

{plugin.generate_preamble()}

\\begin{{document}}

\\title{{{title}}}

{author_block}

\\maketitle

\\begin{{abstract}}
{abstract_content}
\\end{{abstract}}

{sections}

{bibliography}

\\end{{document}}
"""


def run(project_root: Path, target: str = "ieee") -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    project = PaperForgeProject.load(project_root)

    try:
        plugin = get_plugin(target)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    issues = collect_issues(project)
    venue_issues = plugin.validate(project)

    errors = [issue for issue in issues if issue.severity == "ERROR"]
    venue_errors = [issue for issue in venue_issues if issue.severity == "ERROR"]
    if errors or venue_errors:
        body = Group(
            Text("Build blocked. Fix all ERRORs before building."),
            *(Text(f"  [{issue.code}] {issue.message}") for issue in errors),
            *(Text(f"  [{issue.code}] {issue.message}") for issue in venue_errors),
            Text("Run `paperforge doctor` for full details."),
        )
        console.print(Panel(body, border_style="red"))
        sys.exit(1)

    venue_warnings = [issue for issue in venue_issues if issue.severity == "WARNING"]

    output_dir = project_root / ".paperforge" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    latex = _generate_latex(project, plugin)
    tex_path = output_dir / "paper.tex"
    tex_path.write_text(latex, encoding="utf-8")

    pdflatex = shutil.which("pdflatex")
    pdf_ok = False
    if pdflatex is not None:
        result = None
        for _ in range(2):
            result = subprocess.run(
                [
                    pdflatex,
                    "-interaction=nonstopmode",
                    "-output-directory",
                    str(output_dir),
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        pdf_ok = result is not None and result.returncode == 0

    unique_citations = {c for claim in project.claims for c in claim.citations}

    if pdflatex is None:
        pdf_line = "paper.pdf          pdflatex not found — install TeX Live"
    elif pdf_ok:
        pdf_line = "paper.pdf          \u2713"
    else:
        pdf_line = "paper.pdf          compilation failed — see .paperforge/output/paper.log"

    body = Group(
        Text("Output: .paperforge/output/"),
        Text(""),
        Text("Files:"),
        Text("  paper.tex          \u2713"),
        Text(f"  {pdf_line}"),
        Text(""),
        Text(f"Claims compiled:    {len(project.claims)}"),
        Text(f"Sections:           {len(project.config.sections)}"),
        Text(f"Citations:          {len(unique_citations)}"),
        Text(""),
        Text("To compile PDF manually:"),
        Text("  cd .paperforge/output"),
        Text("  pdflatex paper.tex"),
        Text(""),
        Text(
            "Next step: Review paper.tex and run `paperforge doctor`\n"
            "           before submission."
        ),
    )

    console.print(Panel(body, title="Build Complete", border_style="green"))

    if venue_warnings:
        console.print()
        console.print(Text(f"VENUE ({plugin.display_name})", style="bold yellow"))
        for issue in venue_warnings:
            console.print(Text(f"  [{issue.code}] {issue.message}"))
