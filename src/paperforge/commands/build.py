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
from paperforge.utils.latex import escape_latex
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
    paragraph = escape_latex(claim.text)
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
    return " ".join(
        escape_latex(c.text) for c in sorted(abstract_claims, key=lambda c: c.id)
    )


def _generate_figure_latex(fig_obj: Figure) -> str:
    env = "figure*" if fig_obj.wide else "figure"
    escaped_caption = escape_latex(fig_obj.caption or "")
    if fig_obj.caption and fig_obj.path:
        width = (
            f"{fig_obj.width_inches}in" if fig_obj.width_inches else "\\columnwidth"
        )
        path = fig_obj.path if fig_obj.path else f"figures/{fig_obj.id}"
        return (
            f"\\begin{{{env}}}[!t]\n"
            f"\\centering\n"
            f"\\includegraphics[width={width}]{{{path}}}\n"
            f"\\caption{{{escaped_caption}}}\n"
            f"\\label{{fig:{fig_obj.id}}}\n"
            f"\\end{{{env}}}"
        )
    caption_text = escaped_caption[:60]
    return (
        f"% Figure: {fig_obj.id} — {caption_text} (path not set)\n"
        f"% \\label{{fig:{fig_obj.id}}}"
    )


def _generate_table_latex(table: Table) -> str:
    env = "table*" if table.wide else "table"
    escaped_caption = escape_latex(table.caption or "")

    if not table.columns:
        # No columns defined -- emit a comment placeholder
        return (
            f"% Table: {table.id} — {escaped_caption[:60]}\n"
            f"% (no column data — fill in .paperforge/tables/{table.id}.yaml)\n"
            f"% \\label{{tab:{table.id}}}"
        )

    col_spec = " ".join(["c"] * len(table.columns))
    header_row = " & ".join(escape_latex(c) for c in table.columns) + " \\\\"

    data_rows = []
    for row in table.rows:
        # Pad or truncate to match column count
        padded = row[: len(table.columns)]
        while len(padded) < len(table.columns):
            padded.append("")
        escaped_row = [escape_latex(cell) for cell in padded]
        data_rows.append(" & ".join(escaped_row) + " \\\\")

    notes_block = ""
    if table.notes:
        notes_block = f"\n\\footnotesize{{\\textit{{Note: {escape_latex(table.notes)}}}}}"

    lines = [
        f"\\begin{{{env}}}[!t]",
        "\\renewcommand{\\arraystretch}{1.3}",
        f"\\caption{{{escaped_caption}}}",
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
    emitted_claims: set[str] = set()

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
                if c.id in emitted_claims:
                    first_sec = c.sections[0] if c.sections else "above"
                    claim_blocks.append(
                        f"% Claim {c.id} content appears in {first_sec} above."
                    )
                    continue
                emitted_claims.add(c.id)

                text_par = _claim_paragraph(c, project)
                fig_envs = []
                for fig_id in c.figures:
                    fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                    if fig_obj and fig_id not in emitted_figures:
                        emitted_figures.add(fig_id)
                        fig_envs.append(_generate_figure_latex(fig_obj))
                    elif fig_obj and fig_id in emitted_figures:
                        fig_envs.append(
                            f"% Figure~\\ref{{fig:{fig_id}}} already defined above."
                        )
                    else:
                        fig_envs.append(
                            f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)"
                        )
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
                            caption_text = escape_latex((tbl_obj.caption or "")[:60])
                            tbl_envs.append(
                                f"% Table: {tbl_id} — {caption_text} (no caption set)\n"
                                f"% \\label{{tab:{tbl_id}}}"
                            )
                    elif tbl_obj and tbl_id in emitted_tables:
                        tbl_envs.append(
                            f"% Table~\\ref{{tab:{tbl_id}}} already defined above."
                        )
                    else:
                        tbl_envs.append(
                            f"% Table reference: {tbl_id} (no YAML — run paperforge add-table)"
                        )
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


def _generate_journal_sections(
    sections: list[str], project: PaperForgeProject
) -> str:
    blocks: list[str] = []
    emitted_figures: set[str] = set()
    emitted_tables: set[str] = set()
    emitted_claims: set[str] = set()

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
                paragraphs: list[str] = []
                for idx, c in enumerate(section_claims):
                    if c.id in emitted_claims:
                        first_sec = c.sections[0] if c.sections else "above"
                        paragraphs.append(
                            f"% Claim {c.id} content appears in {first_sec} above."
                        )
                        continue
                    emitted_claims.add(c.id)

                    text_p = _claim_paragraph(c, project)
                    if idx == 0 or not any(not p.startswith("%") for p in paragraphs):
                        first_text = _ieee_parstart(text_p)
                    else:
                        first_text = text_p

                    first_envs = []
                    for fig_id in c.figures:
                        fig_obj = next(
                            (f for f in project.figures if f.id == fig_id), None
                        )
                        if fig_obj and fig_id not in emitted_figures:
                            emitted_figures.add(fig_id)
                            first_envs.append(_generate_figure_latex(fig_obj))
                        elif fig_obj and fig_id in emitted_figures:
                            first_envs.append(
                                f"% Figure~\\ref{{fig:{fig_id}}} already defined above."
                            )
                        else:
                            first_envs.append(
                                f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)"
                            )
                    if first_envs:
                        first_text += "\n\n" + "\n\n".join(first_envs)

                    first_tbl_envs = []
                    for tbl_id in c.tables:
                        tbl_obj = next(
                            (t for t in project.tables if t.id == tbl_id), None
                        )
                        if tbl_obj and tbl_id not in emitted_tables:
                            emitted_tables.add(tbl_id)
                            if tbl_obj.caption:
                                first_tbl_envs.append(_generate_table_latex(tbl_obj))
                            else:
                                caption_text = escape_latex((tbl_obj.caption or "")[:60])
                                first_tbl_envs.append(
                                    f"% Table: {tbl_id} — {caption_text} (no caption set)\n"
                                    f"% \\label{{tab:{tbl_id}}}"
                                )
                        elif tbl_obj and tbl_id in emitted_tables:
                            first_tbl_envs.append(
                                f"% Table~\\ref{{tab:{tbl_id}}} already defined above."
                            )
                        else:
                            first_tbl_envs.append(
                                f"% Table reference: {tbl_id} (no YAML — run paperforge add-table)"
                            )
                    if first_tbl_envs:
                        first_text += "\n\n" + "\n\n".join(first_tbl_envs)

                    paragraphs.append(first_text)
                body = "\n\n".join(paragraphs)
            else:
                body = "% TODO: No claims linked to this section yet."
            blocks.append(f"{heading}\n{body}")
            continue

        block = f"\\section{{{title}}}\n"
        if section_claims:
            claim_blocks = []
            for c in section_claims:
                if c.id in emitted_claims:
                    first_sec = c.sections[0] if c.sections else "above"
                    claim_blocks.append(
                        f"% Claim {c.id} content appears in {first_sec} above."
                    )
                    continue
                emitted_claims.add(c.id)

                text_par = _claim_paragraph(c, project)
                fig_envs = []
                for fig_id in c.figures:
                    fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                    if fig_obj and fig_id not in emitted_figures:
                        emitted_figures.add(fig_id)
                        fig_envs.append(_generate_figure_latex(fig_obj))
                    elif fig_obj and fig_id in emitted_figures:
                        fig_envs.append(
                            f"% Figure~\\ref{{fig:{fig_id}}} already defined above."
                        )
                    else:
                        fig_envs.append(
                            f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)"
                        )
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
                            caption_text = escape_latex((tbl_obj.caption or "")[:60])
                            tbl_envs.append(
                                f"% Table: {tbl_id} — {caption_text} (no caption set)\n"
                                f"% \\label{{tab:{tbl_id}}}"
                            )
                    elif tbl_obj and tbl_id in emitted_tables:
                        tbl_envs.append(
                            f"% Table~\\ref{{tab:{tbl_id}}} already defined above."
                        )
                    else:
                        tbl_envs.append(
                            f"% Table reference: {tbl_id} (no YAML — run paperforge add-table)"
                        )
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
    escaped_authors = [escape_latex(a) for a in authors]
    if not affiliations:
        return ", ".join(escaped_authors)

    if compsoc:
        lines = []
        for i, author in enumerate(escaped_authors):
            if i < len(affiliations):
                aff = affiliations[i]
                aff_str = ", ".join(
                    filter(
                        None,
                        [
                            escape_latex(aff.department or ""),
                            escape_latex(aff.institution or ""),
                            escape_latex(aff.city or ""),
                            escape_latex(aff.country or ""),
                        ],
                    )
                )
                lines.append(f"  {author},~\\IEEEmembership{{Member,~IEEE}}")
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
    for i, author in enumerate(escaped_authors):
        if i < len(affiliations):
            aff = affiliations[i]
            aff_str = ", ".join(
                filter(
                    None,
                    [
                        escape_latex(aff.department or ""),
                        escape_latex(aff.institution or ""),
                        escape_latex(aff.city or ""),
                        escape_latex(aff.country or ""),
                    ],
                )
            )
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
    else:
        ack_text = escape_latex(ack_text)
    return (
        "\\ifCLASSOPTIONcompsoc\n"
        "  \\section*{Acknowledgments}\n"
        "\\else\n"
        "  \\section*{Acknowledgment}\n"
        "\\fi\n\n"
        f"{ack_text}"
    )


def _generate_bibliography_from_citations(
    project: PaperForgeProject,
    all_keys: set[str],
) -> str:
    lines = [
        "% references.bib — generated by PaperForge",
        "% Source: .paperforge/citations/*.yaml",
        "% Re-generated on every build when citation YAMLs exist.",
        "",
    ]
    cit_map = project.citation_map
    for key in sorted(all_keys):
        if key in cit_map:
            lines.append(cit_map[key].to_bibtex())
        else:
            # Stub for keys without a YAML file
            lines.append(
                f"@article{{{key},\n"
                f"  author  = {{Author, A.}},\n"
                f"  title   = {{TODO: fill in title for {key}}},\n"
                f"  journal = {{TODO}},\n"
                f"  year    = {{2024}},\n"
                f"  note    = {{Add .paperforge/citations/{key}.yaml for real metadata}},\n"
                f"}}"
            )
        lines.append("")
    return "\n".join(lines)


def _generate_bibliography_stubs(all_keys: set[str]) -> str:
    entries = [
        f"@article{{{key},\n"
        f"  author = {{Author, A.}},\n"
        f"  title  = {{TODO: Title for {key}}},\n"
        f"  journal = {{TODO}},\n"
        f"  year   = {{2024}},\n"
        f"  note   = {{Auto-generated stub. Replace with real entry.}},\n"
        f"}}"
        for key in sorted(all_keys)
    ]
    return "\n\n".join(entries) + "\n"


def _generate_bibliography(project: PaperForgeProject) -> str:
    """Return bibliography LaTeX block."""
    unique_citations = sorted(
        {citation for claim in project.claims for citation in claim.citations}
    )
    if unique_citations or project.citations:
        return "\\bibliographystyle{IEEEtran}\n\\bibliography{references}"

    return (
        "\\begin{thebibliography}{99}\n"
        "\\bibitem{ref1} Placeholder reference. Replace with a real citation.\n"
        "\\end{thebibliography}"
    )


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


def _generate_latex_conference(
    project: PaperForgeProject, plugin: VenuePlugin
) -> str:
    """Generate LaTeX for a conference-style IEEE/ACM/NeurIPS paper."""
    title = escape_latex(project.config.title or "Untitled Paper")
    escaped_authors = [escape_latex(a) for a in project.config.authors]
    author_block = plugin.generate_author_block(escaped_authors)
    abstract_content = _generate_abstract(project.claims)
    sections = _generate_sections(project.config.sections, project)
    bibliography = _generate_bibliography(project)

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


def _generate_latex_journal(
    project: PaperForgeProject, plugin: VenuePlugin
) -> str:
    """Generate LaTeX for an IEEE Transactions / journal paper."""
    title = escape_latex(project.config.title or "Untitled Paper")
    compsoc = getattr(plugin, "mode", None) == "journal-compsoc"
    author_block = _generate_author_block_journal(
        project.config.authors, project.config.affiliations, compsoc=compsoc
    )
    abstract_content = _generate_abstract(project.claims)
    keywords_source = project.config.keywords or project.config.sections[:6]
    keywords = ", ".join(escape_latex(k) for k in keywords_source)
    sections = _generate_journal_sections(project.config.sections, project)
    bibliography = _generate_bibliography(project)
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
            [
                latexmk,
                "-pdf",
                "-interaction=nonstopmode",
                f"-outdir={output_dir}",
                str(tex_path.name),
            ],
            capture_output=True,
            text=True,
            cwd=output_dir,
            check=False,
        )
        return result.returncode == 0, "latexmk"

    if pdflatex:
        for _ in range(2):
            result = subprocess.run(
                [
                    pdflatex,
                    "-interaction=nonstopmode",
                    f"-output-directory={output_dir}",
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        return result.returncode == 0, "pdflatex"

    return False, "none"


def _reveal_output(path: Path) -> None:
    """Open the containing folder of the output file."""
    try:
        system = platform.system()
        if system == "Windows":
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        elif system == "Darwin":
            subprocess.run(["open", "-R", str(path)], check=False)
        elif system == "Linux":
            subprocess.run(["xdg-open", str(path.parent)], check=False)
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

    all_claim_citation_keys = {
        key for claim in project.claims for key in claim.citations
    }
    has_citation_yamls = len(project.citations) > 0
    bib_path = output_dir / "references.bib"
    bib_status = ""

    if has_citation_yamls:
        # Always regenerate from YAML source of truth
        bib_content = _generate_bibliography_from_citations(
            project, all_claim_citation_keys
        )
        bib_path.write_text(bib_content, encoding="utf-8")
        bib_status = f"references.bib    (generated from {len(project.citations)} citation YAML(s))"
    elif all_claim_citation_keys:
        # Fall back to preserve-or-stub behavior
        if _bib_has_real_entries(bib_path):
            console.print(
                "[dim]references.bib already contains real entries "
                "— preserving existing file.[/dim]"
            )
            bib_status = "references.bib    (preserved — real entries detected)"
        else:
            bib_path.write_text(
                _generate_bibliography_stubs(all_claim_citation_keys),
                encoding="utf-8",
            )
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
