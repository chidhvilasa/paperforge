"""paperforge build command."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from paperforge.commands.doctor import collect_issues
from paperforge.core.project import Affiliation, PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.models.figure import Figure
from paperforge.models.table import Table
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


def _claim_paragraph(claim: Claim, project: PaperForgeProject) -> str:
    paragraph = claim.text
    for citation in claim.citations:
        paragraph += f" \\cite{{{citation}}}"
    
    first_figure_yaml = None
    for figure_id in claim.figures:
        fig_obj = next((f for f in project.figures if f.id == figure_id), None)
        if fig_obj and not first_figure_yaml:
            first_figure_yaml = fig_obj
            
    if first_figure_yaml:
        paragraph += f" (see Fig.~\\ref{{fig:{first_figure_yaml.id}}})"
        
    for table in claim.tables:
        paragraph += f" \\ref{{tab:{table}}}"
    return paragraph


def _generate_abstract(claims: list[Claim]) -> str:
    abstract_claims = [c for c in claims if "abstract" in c.sections]
    if not abstract_claims:
        return "% TODO: Add claims to the abstract section."
    return " ".join(c.text for c in sorted(abstract_claims, key=lambda c: c.id))


def _generate_figure_latex(fig_obj: Figure) -> str:
    env = "figure*" if fig_obj.wide else "figure"
    if fig_obj.caption and fig_obj.path:
        width = f"{fig_obj.width_inches}in" if fig_obj.width_inches else "\\columnwidth"
        path = fig_obj.path if fig_obj.path else f"figures/{fig_obj.id}"
        return (
            f"\\begin{{{env}}}[!t]\n"
            f"\\centering\n"
            f"\\includegraphics[width={width}]{{{path}}}\n"
            f"\\caption{{{fig_obj.caption}}}\n"
            f"\\label{{fig:{fig_obj.id}}}\n"
            f"\\end{{{env}}}"
        )
    caption_text = (fig_obj.caption or "")[:60]
    return (
        f"% Figure: {fig_obj.id} — {caption_text} (path not set)\n"
        f"% \\label{{fig:{fig_obj.id}}}"
    )


def _generate_table_latex(table: Table) -> str:
    env = "table*" if table.wide else "table"

    if not table.columns:
        # No columns defined -- emit a comment placeholder
        return (
            f"% Table: {table.id} — {table.caption[:60]}\n"
            f"% (no column data — fill in .paperforge/tables/{table.id}.yaml)\n"
            f"% \\label{{tab:{table.id}}}"
        )

    col_spec = " ".join(["c"] * len(table.columns))
    header_row = " & ".join(table.columns) + " \\\\"

    data_rows = []
    for row in table.rows:
        # Pad or truncate to match column count
        padded = row[: len(table.columns)]
        while len(padded) < len(table.columns):
            padded.append("")
        data_rows.append(" & ".join(padded) + " \\\\")

    notes_block = ""
    if table.notes:
        notes_block = f"\n\\footnotesize{{\\textit{{Note: {table.notes}}}}}"

    lines = [
        f"\\begin{{{env}}}[!t]",
        "\\renewcommand{\\arraystretch}{1.3}",
        f"\\caption{{{table.caption}}}",
        f"\\label{{tab:{table.id}}}",
        "\\centering",
        f"\\begin{{tabular}}{{{col_spec}}}",
        "\\hline",
        header_row,
        "\\hline",
    ]
    lines.extend(data_rows)
    lines.append("\\hline")
    lines.append("\\end{tabular}")
    if notes_block:
        lines.append(notes_block)
    lines.append(f"\\end{{{env}}}")

    return "\n".join(lines)


def _generate_sections(sections: list[str], project: PaperForgeProject) -> str:
    blocks: list[str] = []
    emitted_figures: set[str] = set()
    emitted_tables: set[str] = set()

    for section in sections:
        if section == "abstract":
            continue
        title = SECTION_TITLES.get(section, section.replace("_", " ").title())
        section_claims = sorted(
            (c for c in project.claims if section in c.sections), key=lambda c: c.id
        )
        block = f"\\section{{{title}}}\n"
        if section_claims:
            claim_blocks = []
            for c in section_claims:
                text_par = _claim_paragraph(c, project)
                fig_envs = []
                for fig_id in c.figures:
                    fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                    if fig_obj and fig_id not in emitted_figures:
                        emitted_figures.add(fig_id)
                        fig_envs.append(_generate_figure_latex(fig_obj))
                    elif fig_obj and fig_id in emitted_figures:
                        fig_envs.append(f"% Figure~\\ref{{fig:{fig_id}}} already defined above.")
                    else:
                        fig_envs.append(f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)")
                if fig_envs:
                    text_par += "\n\n" + "\n\n".join(fig_envs)

                tbl_envs = []
                for tbl_id in c.tables:
                    tbl_obj = next((t for t in project.tables if t.id == tbl_id), None)
                    if tbl_obj and tbl_id not in emitted_tables:
                        emitted_tables.add(tbl_id)
                        if tbl_obj.caption:
                            tbl_envs.append(_generate_table_latex(tbl_obj))
                        else:
                            caption_text = (tbl_obj.caption or "")[:60]
                            tbl_envs.append(
                                f"% Table: {tbl_id} — {caption_text} (no caption set)\n"
                                f"% \\label{{tab:{tbl_id}}}"
                            )
                    elif tbl_obj and tbl_id in emitted_tables:
                        tbl_envs.append(f"% Table~\\ref{{tab:{tbl_id}}} already defined above.")
                    else:
                        tbl_envs.append(f"% Table reference: {tbl_id} (no YAML — run paperforge add-table)")
                if tbl_envs:
                    text_par += "\n\n" + "\n\n".join(tbl_envs)

                claim_blocks.append(text_par)
            block += "\n\n".join(claim_blocks)
        else:
            block += "% TODO: No claims linked to this section yet."
        blocks.append(block)
    return "\n\n".join(blocks)


def _ieee_parstart(text: str) -> str:
    if not text:
        return "\\IEEEPARstart{T}{his} section has no claims yet."
    first_word, _, rest_text = text.partition(" ")
    if len(first_word) < 2:
        drop_cap, rest_of_word = first_word, ""
    else:
        drop_cap, rest_of_word = first_word[0], first_word[1:]
    result = f"\\IEEEPARstart{{{drop_cap}}}{{{rest_of_word}}}"
    return f"{result} {rest_text}" if rest_text else result


def _generate_journal_sections(sections: list[str], project: PaperForgeProject) -> str:
    blocks: list[str] = []
    emitted_figures: set[str] = set()
    emitted_tables: set[str] = set()

    for section in sections:
        if section == "abstract":
            continue

        title = SECTION_TITLES.get(section, section.replace("_", " ").title())
        section_claims = sorted(
            (c for c in project.claims if section in c.sections), key=lambda c: c.id
        )

        if section == "introduction":
            heading = (
                f"\\IEEEraisesectionheading{{\\section{{{title}}}"
                f"\\label{{sec:introduction}}}}"
            )
            if section_claims:
                first, *rest = section_claims

                first_text = _ieee_parstart(_claim_paragraph(first, project))
                first_envs = []
                for fig_id in first.figures:
                    fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                    if fig_obj and fig_id not in emitted_figures:
                        emitted_figures.add(fig_id)
                        first_envs.append(_generate_figure_latex(fig_obj))
                    elif fig_obj and fig_id in emitted_figures:
                        first_envs.append(f"% Figure~\\ref{{fig:{fig_id}}} already defined above.")
                    else:
                        first_envs.append(f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)")
                if first_envs:
                    first_text += "\n\n" + "\n\n".join(first_envs)

                first_tbl_envs = []
                for tbl_id in first.tables:
                    tbl_obj = next((t for t in project.tables if t.id == tbl_id), None)
                    if tbl_obj and tbl_id not in emitted_tables:
                        emitted_tables.add(tbl_id)
                        if tbl_obj.caption:
                            first_tbl_envs.append(_generate_table_latex(tbl_obj))
                        else:
                            caption_text = (tbl_obj.caption or "")[:60]
                            first_tbl_envs.append(
                                f"% Table: {tbl_id} — {caption_text} (no caption set)\n"
                                f"% \\label{{tab:{tbl_id}}}"
                            )
                    elif tbl_obj and tbl_id in emitted_tables:
                        first_tbl_envs.append(f"% Table~\\ref{{tab:{tbl_id}}} already defined above.")
                    else:
                        first_tbl_envs.append(f"% Table reference: {tbl_id} (no YAML — run paperforge add-table)")
                if first_tbl_envs:
                    first_text += "\n\n" + "\n\n".join(first_tbl_envs)

                paragraphs = [first_text]

                for c in rest:
                    text_par = _claim_paragraph(c, project)
                    fig_envs = []
                    for fig_id in c.figures:
                        fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                        if fig_obj and fig_id not in emitted_figures:
                            emitted_figures.add(fig_id)
                            fig_envs.append(_generate_figure_latex(fig_obj))
                        elif fig_obj and fig_id in emitted_figures:
                            fig_envs.append(f"% Figure~\\ref{{fig:{fig_id}}} already defined above.")
                        else:
                            fig_envs.append(f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)")
                    if fig_envs:
                        text_par += "\n\n" + "\n\n".join(fig_envs)

                    tbl_envs = []
                    for tbl_id in c.tables:
                        tbl_obj = next((t for t in project.tables if t.id == tbl_id), None)
                        if tbl_obj and tbl_id not in emitted_tables:
                            emitted_tables.add(tbl_id)
                            if tbl_obj.caption:
                                tbl_envs.append(_generate_table_latex(tbl_obj))
                            else:
                                caption_text = (tbl_obj.caption or "")[:60]
                                tbl_envs.append(
                                    f"% Table: {tbl_id} — {caption_text} (no caption set)\n"
                                    f"% \\label{{tab:{tbl_id}}}"
                                )
                        elif tbl_obj and tbl_id in emitted_tables:
                            tbl_envs.append(f"% Table~\\ref{{tab:{tbl_id}}} already defined above.")
                        else:
                            tbl_envs.append(f"% Table reference: {tbl_id} (no YAML — run paperforge add-table)")
                    if tbl_envs:
                        text_par += "\n\n" + "\n\n".join(tbl_envs)

                    paragraphs.append(text_par)
                body = "\n\n".join(paragraphs)
            else:
                body = "% TODO: No claims linked to this section yet."
            blocks.append(f"{heading}\n{body}")
            continue

        block = f"\\section{{{title}}}\n"
        if section_claims:
            claim_blocks = []
            for c in section_claims:
                text_par = _claim_paragraph(c, project)
                fig_envs = []
                for fig_id in c.figures:
                    fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                    if fig_obj and fig_id not in emitted_figures:
                        emitted_figures.add(fig_id)
                        fig_envs.append(_generate_figure_latex(fig_obj))
                    elif fig_obj and fig_id in emitted_figures:
                        fig_envs.append(f"% Figure~\\ref{{fig:{fig_id}}} already defined above.")
                    else:
                        fig_envs.append(f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)")
                if fig_envs:
                    text_par += "\n\n" + "\n\n".join(fig_envs)

                tbl_envs = []
                for tbl_id in c.tables:
                    tbl_obj = next((t for t in project.tables if t.id == tbl_id), None)
                    if tbl_obj and tbl_id not in emitted_tables:
                        emitted_tables.add(tbl_id)
                        if tbl_obj.caption:
                            tbl_envs.append(_generate_table_latex(tbl_obj))
                        else:
                            caption_text = (tbl_obj.caption or "")[:60]
                            tbl_envs.append(
                                f"% Table: {tbl_id} — {caption_text} (no caption set)\n"
                                f"% \\label{{tab:{tbl_id}}}"
                            )
                    elif tbl_obj and tbl_id in emitted_tables:
                        tbl_envs.append(f"% Table~\\ref{{tab:{tbl_id}}} already defined above.")
                    else:
                        tbl_envs.append(f"% Table reference: {tbl_id} (no YAML — run paperforge add-table)")
                if tbl_envs:
                    text_par += "\n\n" + "\n\n".join(tbl_envs)

                claim_blocks.append(text_par)
            block += "\n\n".join(claim_blocks)
        else:
            block += "% TODO: No claims linked to this section yet."
        blocks.append(block)
    return "\n\n".join(blocks)


def _generate_author_block_journal(
    authors: list[str],
    affiliations: list[Affiliation],
    compsoc: bool = False,
) -> str:
    if not affiliations:
        return ", ".join(authors)

    if compsoc:
        lines = []
        for i, author in enumerate(authors):
            if i < len(affiliations):
                aff = affiliations[i]
                aff_str = ", ".join(filter(None, [
                    aff.department, aff.institution,
                    aff.city, aff.country
                ]))
                lines.append(
                    f"  {author},~\\IEEEmembership{{Member,~IEEE}}"
                )
                if aff_str:
                    lines.append(
                        f"  \\IEEEcompsocitemizethanks{{"
                        f"\\IEEEcompsocthanksitem {author} is with "
                        f"{aff_str}.}}"
                    )
            else:
                lines.append(f"  {author}")
        return "\n".join(lines)

    # Non-compsoc journal mode: standard \thanks{} footnote form.
    parts = []
    for i, author in enumerate(authors):
        if i < len(affiliations):
            aff = affiliations[i]
            aff_str = ", ".join(filter(None, [
                aff.department, aff.institution,
                aff.city, aff.country
            ]))
            if aff_str:
                parts.append(
                    f"{author},~\\IEEEmembership{{Member,~IEEE}}"
                    f"\\thanks{{{aff_str}}}"
                )
            else:
                parts.append(f"{author},~\\IEEEmembership{{Member,~IEEE}}")
        else:
            parts.append(author)
    return " \\and\n".join(parts)


def _generate_acknowledgment(project: PaperForgeProject) -> str:
    ack_text = project.config.acknowledgment
    if not ack_text:
        ack_text = "% TODO: Add acknowledgment text."
    return (
        "\\ifCLASSOPTIONcompsoc\n"
        "  \\section*{Acknowledgments}\n"
        "\\else\n"
        "  \\section*{Acknowledgment}\n"
        "\\fi\n\n"
        f"{ack_text}"
    )


def _generate_bibliography(project: PaperForgeProject) -> tuple[str, str | None]:
    """Return (bibliography LaTeX block, stub .bib file content or None)."""
    unique_citations = sorted(
        {citation for claim in project.claims for citation in claim.citations}
    )
    if unique_citations:
        entries = [
            f"@article{{{key},\n"
            f"  author = {{Author, A.}},\n"
            f"  title  = {{TODO: Title for {key}}},\n"
            f"  journal = {{TODO}},\n"
            f"  year   = {{2024}},\n"
            f"  note   = {{Auto-generated stub. Replace with real entry.}},\n"
            f"}}"
            for key in unique_citations
        ]
        bib_stub = "\n\n".join(entries) + "\n"
        return "\\bibliographystyle{IEEEtran}\n\\bibliography{references}", bib_stub

    stub_tex = (
        "\\begin{thebibliography}{99}\n"
        "\\bibitem{ref1} Placeholder reference. Replace with a real citation.\n"
        "\\end{thebibliography}"
    )
    return stub_tex, None


def _bib_has_real_entries(bib_path: Path) -> bool:
    """
    Returns True if the .bib file contains at least one
    real entry (an @-block that does not contain 'TODO').
    Returns False if file doesn't exist or only has stubs.
    """
    if not bib_path.exists():
        return False
    content = bib_path.read_text(encoding="utf-8")
    entries = re.findall(r"@\w+\{[^}]+\}", content, re.DOTALL)
    for entry in entries:
        if "TODO" not in entry:
            return True
    return False


def _generate_latex_conference(project: PaperForgeProject, plugin: VenuePlugin) -> str:
    """Generate LaTeX for a conference-style IEEE/ACM/NeurIPS paper."""
    title = project.config.title or "Untitled Paper"
    author_block = plugin.generate_author_block(project.config.authors)
    abstract_content = _generate_abstract(project.claims)
    sections = _generate_sections(project.config.sections, project)
    bibliography, _ = _generate_bibliography(project)

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


def _generate_latex_journal(project: PaperForgeProject, plugin: VenuePlugin) -> str:
    """Generate LaTeX for an IEEE Transactions / journal paper."""
    title = project.config.title or "Untitled Paper"
    compsoc = getattr(plugin, "mode", None) == "journal-compsoc"
    author_block = _generate_author_block_journal(
        project.config.authors, project.config.affiliations, compsoc=compsoc
    )
    abstract_content = _generate_abstract(project.claims)
    keywords_source = project.config.keywords or project.config.sections[:6]
    keywords = ", ".join(keywords_source)
    sections = _generate_journal_sections(project.config.sections, project)
    bibliography, _ = _generate_bibliography(project)
    acknowledgment = _generate_acknowledgment(project)

    return f"""{plugin.latex_documentclass}

{plugin.generate_preamble()}

\\hyphenation{{op-tical net-works semi-conduc-tor}}

\\begin{{document}}

\\title{{{title}}}

\\author{{{author_block}}}

\\IEEEtitleabstractindextext{{%
\\begin{{abstract}}
{abstract_content}
\\end{{abstract}}

\\begin{{IEEEkeywords}}
{keywords}
\\end{{IEEEkeywords}}}}

\\maketitle

\\IEEEdisplaynontitleabstractindextext
\\IEEEpeerreviewmaketitle

{sections}

{acknowledgment}

{bibliography}

\\end{{document}}
"""


def _compile_pdf(tex_path: Path, output_dir: Path) -> tuple[bool, str]:

    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")

    if latexmk:
        result = subprocess.run(
            [latexmk, "-pdf", "-interaction=nonstopmode",
             f"-outdir={output_dir}", str(tex_path.name)],
            capture_output=True, text=True, cwd=output_dir, check=False
        )
        return result.returncode == 0, "latexmk"

    if pdflatex:
        for _ in range(2):
            result = subprocess.run(
                [pdflatex, "-interaction=nonstopmode",
                 f"-output-directory={output_dir}", str(tex_path)],
                capture_output=True, text=True, check=False
            )
        return result.returncode == 0, "pdflatex"

    return False, "none"

def _reveal_output(path: Path) -> None:
    """Open the containing folder of the output file."""
    try:
        system = platform.system()
        if system == "Windows":
            subprocess.run(
                ["explorer", "/select,", str(path)],
                check=False
            )
        elif system == "Darwin":
            subprocess.run(
                ["open", "-R", str(path)],
                check=False
            )
        elif system == "Linux":
            subprocess.run(
                ["xdg-open", str(path.parent)],
                check=False
            )
    except (OSError, subprocess.SubprocessError):
        pass  # Never crash the build over a reveal failure


def run(
    project_root: Path,
    target: str = "ieee",
    no_reveal: bool = False,
) -> None:
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

    rel_output = project.config.build_output_dir or "paper"
    output_dir = project_root / rel_output
    output_dir.mkdir(parents=True, exist_ok=True)

    if project.config.paper_type == "journal":
        latex = _generate_latex_journal(project, plugin)
    else:
        latex = _generate_latex_conference(project, plugin)
    tex_path = output_dir / "paper.tex"
    tex_path.write_text(latex, encoding="utf-8")

    _, bib_stub = _generate_bibliography(project)
    bib_path = output_dir / "references.bib"
    bib_status = ""
    if bib_stub is not None:
        if _bib_has_real_entries(bib_path):
            console.print(
                "[dim]references.bib already contains real entries "
                "— preserving existing file.[/dim]"
            )
            bib_status = "references.bib    (preserved — real entries detected)"
        else:
            bib_path.write_text(bib_stub, encoding="utf-8")
            console.print(
                "[dim]references.bib: generated stubs. "
                "Replace with real BibTeX entries.[/dim]"
            )
            bib_status = "references.bib    (stubs generated — fill in real entries)"

    pdf_ok, method = _compile_pdf(tex_path, output_dir)
    pdf_path = output_dir / "paper.pdf"
    if pdf_ok and not no_reveal:
        _reveal_output(pdf_path)

    unique_citations = {c for claim in project.claims for c in claim.citations}

    if method == "latexmk":
        compiler_msg = "Compiled with latexmk (auto cross-references)"
    elif method == "pdflatex":
        compiler_msg = "Compiled with pdflatex (2 passes)"
    else:
        compiler_msg = "pdflatex and latexmk not found — install TeX Live"

    if pdf_ok:
        pdf_line = "paper.pdf          \u2713"
    else:
        pdf_line = (
            f"paper.pdf          {compiler_msg}"
            if method == "none"
            else f"paper.pdf          compilation failed — see {rel_output}/paper.log"
        )

    body_lines = [
        Text(f"Output: {rel_output}/"),
        Text(""),
        Text("Files:"),
        Text("  paper.tex          \u2713"),
        Text(f"  {pdf_line}"),
        Text(f"  ({compiler_msg})"),
    ]
    if bib_status:
        body_lines.append(Text(f"  {bib_status}"))
    body_lines.append(Text(""))
    body = Group(
        *body_lines,
        Text(f"Claims compiled:    {len(project.claims)}"),
        Text(f"Sections:           {len(project.config.sections)}"),
        Text(f"Citations:          {len(unique_citations)}"),
        Text(""),
        Text("To compile PDF manually:"),
        Text(f"  cd {rel_output}"),
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
