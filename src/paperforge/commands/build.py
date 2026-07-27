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
from paperforge.core.project import Affiliation, PaperForgeProject, ProjectConfig
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


def _generate_figure_latex(fig_obj: Figure, project_root: Path | None = None) -> str:
    env = "figure*" if fig_obj.wide else "figure"
    escaped_caption = escape_latex(fig_obj.caption or "")

    file_exists = False
    if fig_obj.path:
        if project_root:
            image_file = project_root / fig_obj.path
        else:
            image_file = Path(fig_obj.path)
        file_exists = image_file.exists()

    if file_exists and fig_obj.path:
        if fig_obj.width_inches:
            width = f"{fig_obj.width_inches}in"
        elif fig_obj.wide:
            width = "\\textwidth"
        else:
            width = "\\columnwidth"
        path = fig_obj.path.replace("\\", "/")
        return (
            f"\\begin{{{env}}}[!t]\n"
            f"\\centering\n"
            f"\\includegraphics[width={width}]{{{path}}}\n"
            f"\\caption{{{escaped_caption}}}\n"
            f"\\label{{fig:{fig_obj.id}}}\n"
            f"\\end{{{env}}}"
        )

    # Missing figure placeholder box
    path_display = escape_latex(fig_obj.path or "not set")
    return (
        f"\\begin{{{env}}}[!t]\n"
        f"\\centering\n"
        f"\\fbox{{\\parbox{{0.9\\columnwidth}}{{\\centering\n"
        f"\\textbf{{Figure placeholder}}\\\\\n"
        f"{escaped_caption}\\\\\n"
        f"Path: {path_display}\n"
        f"}}}}\n"
        f"\\caption{{{escaped_caption}}}\n"
        f"\\label{{fig:{fig_obj.id}}}\n"
        f"\\end{{{env}}}"
    )


def _generate_table_latex(
    table: Table, project: PaperForgeProject | None = None
) -> str:
    env = "table*" if table.wide else "table"
    escaped_caption = escape_latex(table.caption or "")

    columns = list(table.columns)
    rows = list(table.rows)

    if not rows and table.auto_rows_from_experiment and project:
        exp_obj = next(
            (e for e in project.experiments if e.id == table.auto_rows_from_experiment),
            None,
        )
        if exp_obj and exp_obj.metrics:
            if not columns:
                columns = ["Metric", "Value"]
            rows = [[m_name, str(m_val)] for m_name, m_val in exp_obj.metrics.items()]

    if not columns:
        # No columns defined -- emit a comment placeholder
        return (
            f"% Table: {table.id} — {escaped_caption[:60]}\n"
            f"% (no column data — fill in .paperforge/tables/{table.id}.yaml)\n"
            f"% \\label{{tab:{table.id}}}"
        )

    col_spec = " ".join(["c"] * len(columns))
    header_row = " & ".join(escape_latex(c) for c in columns) + " \\\\"

    data_rows = []
    for row in rows:
        padded = row[: len(columns)]
        while len(padded) < len(columns):
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
    emitted_algorithms: set[str] = set()
    emitted_claims: set[str] = set()

    for section in sections:
        if section == "abstract":
            continue
        title = SECTION_TITLES.get(section, section.replace("_", " ").title())
        section_claims = sorted(
            (c for c in project.claims if section in c.sections), key=lambda c: c.id
        )
        block = f"\\section{{{title}}}\n"
        current_subsection = ""

        if section_claims:
            claim_blocks = []
            non_contrib = [c for c in section_claims if not c.is_contribution]
            contrib = [c for c in section_claims if c.is_contribution]
            target_claims = non_contrib if (section == "introduction" and contrib) else section_claims

            for c in target_claims:
                if c.id in emitted_claims:
                    first_sec = c.sections[0] if c.sections else "above"
                    claim_blocks.append(
                        f"% Claim {c.id} content appears in {first_sec} above."
                    )
                    continue
                emitted_claims.add(c.id)

                prefix = ""
                if c.subsection and c.subsection != current_subsection:
                    prefix = f"\\subsection{{{escape_latex(c.subsection)}}}\n"
                    current_subsection = c.subsection

                if section == "related_work" and c.compared_work:
                    prefix += f"% --- {escape_latex(c.compared_work)} ---\n"

                text_par = prefix + _claim_paragraph(c, project)

                fig_envs = []
                for fig_id in c.figures:
                    fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                    if fig_obj and fig_id not in emitted_figures:
                        emitted_figures.add(fig_id)
                        fig_envs.append(_generate_figure_latex(fig_obj, project.root))
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
                        if tbl_obj.caption or tbl_obj.auto_rows_from_experiment:
                            tbl_envs.append(_generate_table_latex(tbl_obj, project))
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

                alg_envs = []
                for alg_id in c.algorithms:
                    alg_obj = project.algorithm_map.get(alg_id)
                    if alg_obj and alg_id not in emitted_algorithms:
                        emitted_algorithms.add(alg_id)
                        alg_envs.append(alg_obj.to_latex())
                    elif alg_obj and alg_id in emitted_algorithms:
                        alg_envs.append(
                            f"% Algorithm~\\ref{{alg:{alg_id}}} already defined above."
                        )
                    else:
                        alg_envs.append(
                            f"% Algorithm reference: {alg_id} (no algorithm YAML)"
                        )
                if alg_envs:
                    text_par += "\n\n" + "\n\n".join(alg_envs)

                claim_blocks.append(text_par)

            if section == "introduction":
                if contrib:
                    items = []
                    for c in contrib:
                        emitted_claims.add(c.id)
                        items.append(f"  \\item {_claim_paragraph(c, project)}")
                    item_block = (
                        "\\noindent The main contributions of this work are:\n"
                        "\\begin{itemize}\n"
                        + "\n".join(items)
                        + "\n\\end{itemize}"
                    )
                    claim_blocks.append(item_block)

                if project.config.sections_overview:
                    sec_overview = escape_latex(project.config.sections_overview)
                    claim_blocks.append(
                        f"The rest of this paper is organized as follows: Section II presents {sec_overview}."
                    )

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
    emitted_algorithms: set[str] = set()
    emitted_claims: set[str] = set()

    for section in sections:
        if section == "abstract":
            continue

        title = SECTION_TITLES.get(section, section.replace("_", " ").title())
        section_claims = sorted(
            (c for c in project.claims if section in c.sections), key=lambda c: c.id
        )
        current_subsection = ""

        if section == "introduction":
            heading = (
                f"\\IEEEraisesectionheading{{\\section{{{title}}}"
                f"\\label{{sec:introduction}}}}"
            )
            if section_claims:
                paragraphs: list[str] = []
                non_contrib = [c for c in section_claims if not c.is_contribution]
                contrib = [c for c in section_claims if c.is_contribution]
                target_claims = non_contrib if contrib else section_claims

                for idx, c in enumerate(target_claims):
                    if c.id in emitted_claims:
                        first_sec = c.sections[0] if c.sections else "above"
                        paragraphs.append(
                            f"% Claim {c.id} content appears in {first_sec} above."
                        )
                        continue
                    emitted_claims.add(c.id)

                    prefix = ""
                    if c.subsection and c.subsection != current_subsection:
                        prefix = f"\\subsection{{{escape_latex(c.subsection)}}}\n"
                        current_subsection = c.subsection

                    claim_text = _claim_paragraph(c, project)
                    if idx == 0 or not any(not p.startswith("%") for p in paragraphs):
                        first_text = prefix + _ieee_parstart(claim_text)
                    else:
                        first_text = prefix + claim_text

                    first_envs = []
                    for fig_id in c.figures:
                        fig_obj = next(
                            (f for f in project.figures if f.id == fig_id), None
                        )
                        if fig_obj and fig_id not in emitted_figures:
                            emitted_figures.add(fig_id)
                            first_envs.append(_generate_figure_latex(fig_obj, project.root))
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
                            if tbl_obj.caption or tbl_obj.auto_rows_from_experiment:
                                first_tbl_envs.append(_generate_table_latex(tbl_obj, project))
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

                    alg_envs = []
                    for alg_id in c.algorithms:
                        alg_obj = project.algorithm_map.get(alg_id)
                        if alg_obj and alg_id not in emitted_algorithms:
                            emitted_algorithms.add(alg_id)
                            alg_envs.append(alg_obj.to_latex())
                        elif alg_obj and alg_id in emitted_algorithms:
                            alg_envs.append(
                                f"% Algorithm~\\ref{{alg:{alg_id}}} already defined above."
                            )
                        else:
                            alg_envs.append(
                                f"% Algorithm reference: {alg_id} (no algorithm YAML)"
                            )
                    if alg_envs:
                        first_text += "\n\n" + "\n\n".join(alg_envs)

                    paragraphs.append(first_text)

                if contrib:
                    items = []
                    for c in contrib:
                        emitted_claims.add(c.id)
                        items.append(f"  \\item {_claim_paragraph(c, project)}")
                    item_block = (
                        "\\noindent The main contributions of this work are:\n"
                        "\\begin{itemize}\n"
                        + "\n".join(items)
                        + "\n\\end{itemize}"
                    )
                    paragraphs.append(item_block)

                if project.config.sections_overview:
                    sec_overview = escape_latex(project.config.sections_overview)
                    paragraphs.append(
                        f"The rest of this paper is organized as follows: Section II presents {sec_overview}."
                    )

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

                prefix = ""
                if c.subsection and c.subsection != current_subsection:
                    prefix = f"\\subsection{{{escape_latex(c.subsection)}}}\n"
                    current_subsection = c.subsection

                if section == "related_work" and c.compared_work:
                    prefix += f"% --- {escape_latex(c.compared_work)} ---\n"

                text_par = prefix + _claim_paragraph(c, project)

                fig_envs = []
                for fig_id in c.figures:
                    fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                    if fig_obj and fig_id not in emitted_figures:
                        emitted_figures.add(fig_id)
                        fig_envs.append(_generate_figure_latex(fig_obj, project.root))
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
                        if tbl_obj.caption or tbl_obj.auto_rows_from_experiment:
                            tbl_envs.append(_generate_table_latex(tbl_obj, project))
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

                alg_envs = []
                for alg_id in c.algorithms:
                    alg_obj = project.algorithm_map.get(alg_id)
                    if alg_obj and alg_id not in emitted_algorithms:
                        emitted_algorithms.add(alg_id)
                        alg_envs.append(alg_obj.to_latex())
                    elif alg_obj and alg_id in emitted_algorithms:
                        alg_envs.append(
                            f"% Algorithm~\\ref{{alg:{alg_id}}} already defined above."
                        )
                    else:
                        alg_envs.append(
                            f"% Algorithm reference: {alg_id} (no algorithm YAML)"
                        )
                if alg_envs:
                    text_par += "\n\n" + "\n\n".join(alg_envs)

                claim_blocks.append(text_par)
            block += "\n\n".join(claim_blocks)
        else:
            block += "% TODO: No claims linked to this section yet."
        blocks.append(block)
    return "\n\n".join(blocks)


def _generate_author_block_journal(
    authors: list[str],
    affiliations: list[Affiliation],
    config: ProjectConfig | None = None,
    compsoc: bool = False,
) -> str:
    escaped_authors = [escape_latex(a) for a in authors]
    if not authors:
        return "Author(s) TBD"

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

    # Non-compsoc journal mode
    if not affiliations and (
        not config
        or (
            not config.funding
            and not config.email
            and not config.manuscript_received
        )
    ):
        return ", ".join(escaped_authors)

    has_extra = config and (
        config.funding or config.email or config.manuscript_received
    )

    if has_extra:
        author_parts = []
        for author in escaped_authors:
            if config and config.orcid:
                author_parts.append(
                    f"{author}~\\orcidlink{{{escape_latex(config.orcid)}}}"
                )
            else:
                author_parts.append(author)

        if len(author_parts) == 1:
            author_str = f"{author_parts[0]},~\\IEEEmembership{{Member,~IEEE}}"
        elif len(author_parts) == 2:
            author_str = f"{author_parts[0]} and {author_parts[1]}"
        else:
            author_str = (
                ", ".join(author_parts[:-1]) + f", and {author_parts[-1]}"
            )

        thanks_parts = []
        if config and config.funding:
            fund_text = escape_latex(config.funding).strip()
            if not fund_text.endswith("."):
                fund_text += "."
            thanks_parts.append(fund_text)

        if affiliations:
            aff_lines = []
            for i, aff in enumerate(affiliations):
                aff_items = [
                    escape_latex(aff.department or ""),
                    escape_latex(aff.institution or ""),
                    escape_latex(aff.city or ""),
                    escape_latex(aff.country or ""),
                ]
                aff_str = ", ".join(filter(None, aff_items))
                if aff.email:
                    aff_str += f" (e-mail: {escape_latex(aff.email)})"
                if aff_str:
                    if len(escaped_authors) > i:
                        aff_lines.append(
                            f"{escaped_authors[i]} is with {aff_str}."
                        )
                    else:
                        aff_lines.append(f"{aff_str}.")
            if aff_lines:
                thanks_parts.append(" ".join(aff_lines))

        if config and config.email:
            thanks_parts.append(
                f"Corresponding author: {escaped_authors[0]} (e-mail: {escape_latex(config.email)})."
            )

        if config and config.manuscript_received:
            thanks_parts.append(
                f"Manuscript received {escape_latex(config.manuscript_received)}."
            )

        thanks_block = " ".join(thanks_parts)
        return f"{author_str}\\thanks{{{thanks_block}}}"
    else:
        parts = []
        for i, author in enumerate(escaped_authors):
            if config and config.orcid:
                author_fmt = f"{author}~\\orcidlink{{{escape_latex(config.orcid)}}}"
            else:
                author_fmt = author
            if i < len(affiliations):
                aff = affiliations[i]
                aff_items = [
                    escape_latex(aff.department or ""),
                    escape_latex(aff.institution or ""),
                    escape_latex(aff.city or ""),
                    escape_latex(aff.country or ""),
                ]
                aff_str = ", ".join(filter(None, aff_items))
                if aff.email:
                    aff_str += f" (e-mail: {escape_latex(aff.email)})"
                if aff_str:
                    parts.append(
                        f"{author_fmt},~\\IEEEmembership{{Member,~IEEE}}"
                        f"\\thanks{{{aff_str}}}"
                    )
                else:
                    parts.append(f"{author_fmt},~\\IEEEmembership{{Member,~IEEE}}")
            else:
                parts.append(author_fmt)
        return " \\and\n".join(parts)

    return author_str


def _generate_acknowledgment(project: PaperForgeProject) -> str:
    ack_text = project.config.acknowledgment
    comment_line = ""
    if project.config.funding:
        comment_line = (
            "% Note: Funding acknowledgment is in the \\thanks{} footnote per IEEE convention. "
            "Add only people/institution thanks here.\n"
        )
    if not ack_text:
        ack_text = "% TODO: Add acknowledgment text."
    else:
        ack_text = escape_latex(ack_text)
    return (
        f"{comment_line}"
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

    preamble = plugin.generate_preamble()
    if "\\usepackage{algorithmic}" not in preamble:
        preamble += "\n\\usepackage{algorithm}\n\\usepackage{algorithmic}"
    if project.config.orcid and "\\usepackage{orcidlink}" not in preamble:
        preamble += "\n\\usepackage{orcidlink}"

    statements = []
    if project.config.data_availability:
        statements.append(
            f"\\section*{{Data Availability}}\n{escape_latex(project.config.data_availability)}"
        )
    if project.config.code_availability:
        statements.append(
            f"\\section*{{Code Availability}}\n{escape_latex(project.config.code_availability)}"
        )
    if project.config.conflict_of_interest:
        statements.append(
            f"\\section*{{Conflict of Interest}}\n{escape_latex(project.config.conflict_of_interest)}"
        )
    statements_block = "\n\n".join(statements)
    if statements_block:
        statements_block = "\n\n" + statements_block

    return f"""{plugin.latex_documentclass}

{preamble}

\\begin{{document}}

\\title{{{title}}}

{author_block}

\\maketitle

\\begin{{abstract}}
{abstract_content}
\\end{{abstract}}

{sections}{statements_block}

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
        project.config.authors,
        project.config.affiliations,
        project.config,
        compsoc=compsoc,
    )
    abstract_content = _generate_abstract(project.claims)
    keywords_source = project.config.keywords or project.config.sections[:6]
    keywords = ", ".join(escape_latex(k) for k in keywords_source)
    sections = _generate_journal_sections(project.config.sections, project)
    bibliography = _generate_bibliography(project)
    acknowledgment = _generate_acknowledgment(project)

    preamble = plugin.generate_preamble()
    if "\\usepackage{algorithmic}" not in preamble:
        preamble += "\n\\usepackage{algorithm}\n\\usepackage{algorithmic}"
    if project.config.orcid and "\\usepackage{orcidlink}" not in preamble:
        preamble += "\n\\usepackage{orcidlink}"

    publisher_id_block = ""
    if project.config.publisher_id:
        publisher_id_block = f"\n\\IEEEpubid{{{escape_latex(project.config.publisher_id)}}}\n"

    statements = []
    if project.config.data_availability:
        statements.append(
            f"\\section*{{Data Availability}}\n{escape_latex(project.config.data_availability)}"
        )
    if project.config.code_availability:
        statements.append(
            f"\\section*{{Code Availability}}\n{escape_latex(project.config.code_availability)}"
        )
    if project.config.conflict_of_interest:
        statements.append(
            f"\\section*{{Conflict of Interest}}\n{escape_latex(project.config.conflict_of_interest)}"
        )
    statements_block = "\n\n".join(statements)
    if statements_block:
        statements_block = "\n\n" + statements_block

    return f"""{plugin.latex_documentclass}

{preamble}

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
{publisher_id_block}
\\IEEEdisplaynontitleabstractindextext
\\IEEEpeerreviewmaketitle

{sections}

{acknowledgment}{statements_block}

{bibliography}

\\end{{document}}
"""


def _is_pdf_stale(project_root: Path, output_dir: Path | None = None) -> bool:
    """
    Returns True if paper.pdf does not exist or is older
    than any source file in .paperforge/.
    Returns False if PDF is newer than all sources.
    """
    if output_dir is None:
        output_dir = project_root / "paper_generated" / "current"
        if not (output_dir / "paper.pdf").exists() and (project_root / "paper" / "paper.pdf").exists():
            output_dir = project_root / "paper"
    pdf_path = output_dir / "paper.pdf"
    if not pdf_path.exists():
        return True

    pdf_mtime = pdf_path.stat().st_mtime
    pf_dir = project_root / ".paperforge"

    # Check all YAML source files
    for yaml_file in pf_dir.rglob("*.yaml"):
        if yaml_file.stat().st_mtime > pdf_mtime:
            return True

    return False


def _compile_pdf_full(
    tex_path: Path,
    output_dir: Path,
) -> tuple[bool, str]:
    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")

    if latexmk:
        # latexmk handles the full BibTeX pipeline automatically
        result = subprocess.run(
            [
                latexmk,
                "-pdf",
                "-bibtex",
                "-interaction=nonstopmode",
                f"-outdir={output_dir}",
                str(tex_path),
            ],
            capture_output=True,
            text=True,
            cwd=output_dir,
            check=False,
        )
        return result.returncode == 0, "latexmk"

    if pdflatex:
        tex_name = tex_path.stem  # "paper" without extension

        def run_pdflatex() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    pdflatex,
                    "-interaction=nonstopmode",
                    f"-output-directory={output_dir}",
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                cwd=output_dir,
                check=False,
            )

        def run_bibtex() -> subprocess.CompletedProcess[str] | None:
            if bibtex:
                return subprocess.run(
                    [bibtex, tex_name],
                    capture_output=True,
                    text=True,
                    cwd=output_dir,
                    check=False,
                )
            return None

        # Full BibTeX pipeline: pdflatex -> bibtex -> pdflatex -> pdflatex
        run_pdflatex()          # pass 1: generate .aux
        run_bibtex()            # bibtex: process references
        run_pdflatex()          # pass 2: resolve citations
        result = run_pdflatex() # pass 3: resolve cross-references
        return result.returncode == 0, "pdflatex+bibtex"

    return False, "none"


_compile_pdf = _compile_pdf_full


def _generate_docx(
    project: PaperForgeProject,
    output_dir: Path,
) -> Path:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt

    doc = Document()

    # Page margins (IEEE-like: narrow)
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Title
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = title_para.add_run(project.config.title or "Untitled")
    run_t.bold = True
    run_t.font.size = Pt(14)

    # Authors
    authors_para = doc.add_paragraph()
    authors_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    authors_para.add_run(", ".join(project.config.authors) or "Author TBD")

    # Affiliations
    for aff in project.config.affiliations:
        aff_parts = list(
            filter(
                None,
                [aff.department, aff.institution, aff.city, aff.country],
            )
        )
        aff_str = ", ".join(aff_parts)
        if aff_str:
            aff_para = doc.add_paragraph()
            aff_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_a = aff_para.add_run(aff_str)
            run_a.italic = True
            run_a.font.size = Pt(9)

    doc.add_paragraph()  # spacing

    # Abstract
    abs_claims = [c for c in project.claims if "abstract" in c.sections]
    if abs_claims:
        abs_para = doc.add_paragraph()
        abs_run = abs_para.add_run("Abstract\u2014")
        abs_run.bold = True
        abs_para.add_run(" ".join(c.text for c in abs_claims if c.text))

    # Keywords
    if project.config.keywords:
        kw_para = doc.add_paragraph()
        kw_run = kw_para.add_run("Index Terms\u2014")
        kw_run.bold = True
        kw_para.add_run(", ".join(project.config.keywords))

    doc.add_paragraph()

    # Sections
    section_titles = {
        "introduction": "Introduction",
        "related_work": "Related Work",
        "methodology": "Methodology",
        "experiments": "Experimental Setup",
        "results": "Results",
        "discussion": "Discussion",
        "conclusion": "Conclusion",
    }

    emitted_claims: set[str] = set()
    emitted_tables: set[str] = set()

    for section_name in project.config.sections:
        if section_name == "abstract":
            continue

        title = section_titles.get(
            section_name, section_name.replace("_", " ").title()
        )
        doc.add_heading(title, level=1)

        section_claims = [
            c for c in project.claims if section_name in c.sections
        ]

        for claim in section_claims:
            if claim.id in emitted_claims:
                continue
            if claim.text:
                doc.add_paragraph(claim.text)
                emitted_claims.add(claim.id)

            # Tables
            for tbl_id in claim.tables:
                if tbl_id in emitted_tables:
                    continue
                tbl_obj = next(
                    (t for t in project.tables if t.id == tbl_id), None
                )
                if tbl_obj and tbl_obj.columns and tbl_obj.rows:
                    # Caption above table (IEEE style)
                    cap = doc.add_paragraph()
                    cap.add_run(f"TABLE: {tbl_obj.caption}").bold = True
                    # Table
                    word_table = doc.add_table(
                        rows=1 + len(tbl_obj.rows), cols=len(tbl_obj.columns)
                    )
                    word_table.style = "Table Grid"
                    # Header row
                    hdr = word_table.rows[0].cells
                    for i, col in enumerate(tbl_obj.columns):
                        hdr[i].text = col
                        hdr[i].paragraphs[0].runs[0].bold = True
                    # Data rows
                    for r_idx, row in enumerate(tbl_obj.rows):
                        cells = word_table.rows[r_idx + 1].cells
                        for c_idx, cell in enumerate(row):
                            if c_idx < len(cells):
                                cells[c_idx].text = cell
                    if tbl_obj.notes:
                        note_para = doc.add_paragraph()
                        run_n = note_para.add_run(tbl_obj.notes)
                        run_n.italic = True
                        run_n.font.size = Pt(8)
                    emitted_tables.add(tbl_id)

    # Acknowledgment
    ack = project.config.acknowledgment
    if ack and ack.strip():
        doc.add_heading("Acknowledgment", level=1)
        doc.add_paragraph(ack)

    # COI
    coi = project.config.conflict_of_interest
    if coi and coi.strip():
        doc.add_heading("Conflict of Interest", level=1)
        doc.add_paragraph(coi)

    # References
    doc.add_heading("References", level=1)
    cit_map = project.citation_map
    all_keys = sorted(
        {key for claim in project.claims for key in claim.citations}
    )
    for i, key in enumerate(all_keys, 1):
        cit = cit_map.get(key)
        if cit and cit.title:
            authors_str = (
                " and ".join(cit.authors) if cit.authors else "Author"
            )
            ref_text = (
                f"[{i}] {authors_str}, \"{cit.title},\" "
                f"{cit.venue}, {cit.year or 'n.d.'}"
            )
            if cit.doi:
                ref_text += f", doi: {cit.doi}"
        else:
            ref_text = f"[{i}] {key} — add citation YAML for real reference"
        doc.add_paragraph(ref_text)

    docx_path = output_dir / "paper.docx"
    doc.save(str(docx_path))
    return docx_path


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


def _rotate_output(project_root: Path) -> None:
    """
    Before each build, copy current/ to previous/.
    This preserves the last successful build for comparison.
    """
    current = project_root / "paper_generated" / "current"
    previous = project_root / "paper_generated" / "previous"

    current.mkdir(parents=True, exist_ok=True)
    previous.mkdir(parents=True, exist_ok=True)

    rotatable = [
        "paper.tex",
        "paper.pdf",
        "paper.docx",
        "references.bib",
        "traceability.tex",
    ]

    for filename in rotatable:
        src = current / filename
        dst = previous / filename
        if src.exists():
            import shutil

            shutil.copy2(str(src), str(dst))


def run(
    project_root: Path,
    target: str = "ieee",
    no_reveal: bool = False,
    force: bool = False,
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

    _rotate_output(project_root)

    rel_output = project.config.build_output_dir or "paper_generated/current"
    output_dir = project_root / rel_output
    pdf_path = output_dir / "paper.pdf"

    stale = _is_pdf_stale(project_root, output_dir)

    if not stale and pdf_path.exists() and not force:
        body = Group(
            Text(f"{rel_output}/paper.pdf is newer than all source files."),
            Text("No rebuild needed."),
            Text(""),
            Text("To force a rebuild: paperforge build --force"),
        )
        console.print(Panel(body, title="PDF Up To Date", border_style="dim"))
        return

    if stale and pdf_path.exists():
        console.print("[dim]Source changed — deleting stale PDF...[/dim]")
        pdf_path.unlink()

    venue_warnings = [issue for issue in venue_issues if issue.severity == "WARNING"]
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

    _pdf_ok, compiler = _compile_pdf_full(tex_path, output_dir)

    if compiler == "none":
        console.print(
            "[yellow]No LaTeX toolchain found. Generating DOCX instead...[/yellow]"
        )
        docx_path = _generate_docx(project, output_dir)
        console.print(
            f"[green]DOCX generated: {docx_path.relative_to(project_root)}[/green]"
        )
    else:
        pdf_ok_actual = pdf_path.exists()
        if pdf_ok_actual:
            console.print(f"[green]PDF generated: {rel_output}/paper.pdf[/green]")
            if not no_reveal:
                _reveal_output(pdf_path)
        else:
            console.print(
                f"[red]LaTeX compilation failed. Check {rel_output}/paper.log[/red]"
            )
            if not no_reveal:
                _reveal_output(tex_path)

    unique_citations = {c for claim in project.claims for c in claim.citations}

    if compiler == "none":
        body_lines = [
            Text(f"Output:    {rel_output}/paper.docx  \u2713  (LaTeX not installed)"),
            Text(f"Source:    {rel_output}/paper.tex"),
            Text("Install TeX Live for PDF: https://tug.org/texlive/"),
            Text("Or upload paper_overleaf.zip to Overleaf for free PDF"),
        ]
    elif pdf_path.exists():
        body_lines = [
            Text(f"Output:    {rel_output}/paper.pdf  \u2713"),
            Text(f"Compiled:  {compiler}"),
            Text(f"Source:    {rel_output}/paper.tex"),
        ]
    else:
        body_lines = [
            Text(f"Output:    {rel_output}/paper.tex  (compilation failed)"),
            Text(f"Log:       {rel_output}/paper.log"),
            Text("Check the log for LaTeX errors."),
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
