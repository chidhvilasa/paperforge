import sys
from pathlib import Path

build_path = Path(r"C:\Users\chidh\Downloads\PaperForge\paperforge\src\paperforge\commands\build.py")
content = build_path.read_text("utf-8")

# Fix imports
content = content.replace(
    "from paperforge.core.project import PaperForgeProject",
    "from paperforge.core.project import PaperForgeProject, Affiliation"
)

# _claim_paragraph changes
claim_para_old = """def _claim_paragraph(claim: Claim) -> str:
    paragraph = claim.text
    for citation in claim.citations:
        paragraph += f" \\cite{{{citation}}}"
    for figure in claim.figures:
        paragraph += f" \\ref{{fig:{figure}}}"
    for table in claim.tables:
        paragraph += f" \\ref{{tab:{table}}}"
    return paragraph"""

claim_para_new = """def _claim_paragraph(claim: Claim, project: PaperForgeProject) -> str:
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
    return paragraph"""
content = content.replace(claim_para_old, claim_para_new)

# _generate_sections
gen_sec_old = """def _generate_sections(sections: list[str], claims: list[Claim]) -> str:
    blocks: list[str] = []
    for section in sections:
        if section == "abstract":
            continue
        title = SECTION_TITLES.get(section, section.replace("_", " ").title())
        section_claims = sorted(
            (c for c in claims if section in c.sections), key=lambda c: c.id
        )
        block = f"\\section{{{title}}}\\n"
        if section_claims:
            block += "\\n\\n".join(_claim_paragraph(c) for c in section_claims)
        else:
            block += "% TODO: No claims linked to this section yet."
        blocks.append(block)
    return "\\n\\n".join(blocks)"""

gen_sec_new = """def _generate_sections(sections: list[str], project: PaperForgeProject) -> str:
    blocks: list[str] = []
    for section in sections:
        if section == "abstract":
            continue
        title = SECTION_TITLES.get(section, section.replace("_", " ").title())
        section_claims = sorted(
            (c for c in project.claims if section in c.sections), key=lambda c: c.id
        )
        block = f"\\section{{{title}}}\\n"
        if section_claims:
            claim_blocks = []
            for c in section_claims:
                text_par = _claim_paragraph(c, project)
                fig_envs = []
                for fig_id in c.figures:
                    fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                    if fig_obj:
                        if fig_obj.caption and fig_obj.path:
                            width = f"{fig_obj.width_inches}in" if fig_obj.width_inches else "\\columnwidth"
                            path = fig_obj.path if fig_obj.path else f"figures/{fig_id}"
                            fig_envs.append(
                                f"\\begin{{figure}}[!t]\\n"
                                f"\\centering\\n"
                                f"\\includegraphics[width={width}]{{{path}}}\\n"
                                f"\\caption{{{fig_obj.caption}}}\\n"
                                f"\\label{{fig:{fig_id}}}\\n"
                                f"\\end{{figure}}"
                            )
                        else:
                            caption_text = (fig_obj.caption or "")[:60]
                            fig_envs.append(
                                f"% Figure: {fig_id} — {caption_text} (path not set)\\n"
                                f"% \\label{{fig:{fig_id}}}"
                            )
                    else:
                        fig_envs.append(f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)")
                if fig_envs:
                    text_par += "\\n\\n" + "\\n\\n".join(fig_envs)
                claim_blocks.append(text_par)
            block += "\\n\\n".join(claim_blocks)
        else:
            block += "% TODO: No claims linked to this section yet."
        blocks.append(block)
    return "\\n\\n".join(blocks)"""
content = content.replace(gen_sec_old, gen_sec_new)

# _generate_journal_sections
gen_j_sec_old = """def _generate_journal_sections(sections: list[str], claims: list[Claim]) -> str:
    blocks: list[str] = []
    for section in sections:
        if section == "abstract":
            continue

        title = SECTION_TITLES.get(section, section.replace("_", " ").title())
        section_claims = sorted(
            (c for c in claims if section in c.sections), key=lambda c: c.id
        )

        if section == "introduction":
            heading = (
                f"\\IEEEraisesectionheading{{\\section{{{title}}}"
                f"\\label{{sec:introduction}}}}"
            )
            if section_claims:
                first, *rest = section_claims
                paragraphs = [_ieee_parstart(_claim_paragraph(first))]
                paragraphs.extend(_claim_paragraph(c) for c in rest)
                body = "\\n\\n".join(paragraphs)
            else:
                body = "% TODO: No claims linked to this section yet."
            blocks.append(f"{heading}\\n{body}")
            continue

        block = f"\\section{{{title}}}\\n"
        if section_claims:
            block += "\\n\\n".join(_claim_paragraph(c) for c in section_claims)
        else:
            block += "% TODO: No claims linked to this section yet."
        blocks.append(block)
    return "\\n\\n".join(blocks)"""

gen_j_sec_new = """def _generate_journal_sections(sections: list[str], project: PaperForgeProject) -> str:
    blocks: list[str] = []
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
                    if fig_obj:
                        if fig_obj.caption and fig_obj.path:
                            width = f"{fig_obj.width_inches}in" if fig_obj.width_inches else "\\columnwidth"
                            path = fig_obj.path if fig_obj.path else f"figures/{fig_id}"
                            first_envs.append(
                                f"\\begin{{figure}}[!t]\\n"
                                f"\\centering\\n"
                                f"\\includegraphics[width={width}]{{{path}}}\\n"
                                f"\\caption{{{fig_obj.caption}}}\\n"
                                f"\\label{{fig:{fig_id}}}\\n"
                                f"\\end{{figure}}"
                            )
                        else:
                            caption_text = (fig_obj.caption or "")[:60]
                            first_envs.append(
                                f"% Figure: {fig_id} — {caption_text} (path not set)\\n"
                                f"% \\label{{fig:{fig_id}}}"
                            )
                    else:
                        first_envs.append(f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)")
                if first_envs:
                    first_text += "\\n\\n" + "\\n\\n".join(first_envs)
                    
                paragraphs = [first_text]
                
                for c in rest:
                    text_par = _claim_paragraph(c, project)
                    fig_envs = []
                    for fig_id in c.figures:
                        fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                        if fig_obj:
                            if fig_obj.caption and fig_obj.path:
                                width = f"{fig_obj.width_inches}in" if fig_obj.width_inches else "\\columnwidth"
                                path = fig_obj.path if fig_obj.path else f"figures/{fig_id}"
                                fig_envs.append(
                                    f"\\begin{{figure}}[!t]\\n"
                                    f"\\centering\\n"
                                    f"\\includegraphics[width={width}]{{{path}}}\\n"
                                    f"\\caption{{{fig_obj.caption}}}\\n"
                                    f"\\label{{fig:{fig_id}}}\\n"
                                    f"\\end{{figure}}"
                                )
                            else:
                                caption_text = (fig_obj.caption or "")[:60]
                                fig_envs.append(
                                    f"% Figure: {fig_id} — {caption_text} (path not set)\\n"
                                    f"% \\label{{fig:{fig_id}}}"
                                )
                        else:
                            fig_envs.append(f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)")
                    if fig_envs:
                        text_par += "\\n\\n" + "\\n\\n".join(fig_envs)
                    paragraphs.append(text_par)
                body = "\\n\\n".join(paragraphs)
            else:
                body = "% TODO: No claims linked to this section yet."
            blocks.append(f"{heading}\\n{body}")
            continue

        block = f"\\section{{{title}}}\\n"
        if section_claims:
            claim_blocks = []
            for c in section_claims:
                text_par = _claim_paragraph(c, project)
                fig_envs = []
                for fig_id in c.figures:
                    fig_obj = next((f for f in project.figures if f.id == fig_id), None)
                    if fig_obj:
                        if fig_obj.caption and fig_obj.path:
                            width = f"{fig_obj.width_inches}in" if fig_obj.width_inches else "\\columnwidth"
                            path = fig_obj.path if fig_obj.path else f"figures/{fig_id}"
                            fig_envs.append(
                                f"\\begin{{figure}}[!t]\\n"
                                f"\\centering\\n"
                                f"\\includegraphics[width={width}]{{{path}}}\\n"
                                f"\\caption{{{fig_obj.caption}}}\\n"
                                f"\\label{{fig:{fig_id}}}\\n"
                                f"\\end{{figure}}"
                            )
                        else:
                            caption_text = (fig_obj.caption or "")[:60]
                            fig_envs.append(
                                f"% Figure: {fig_id} — {caption_text} (path not set)\\n"
                                f"% \\label{{fig:{fig_id}}}"
                            )
                    else:
                        fig_envs.append(f"% Reference: {fig_id} (no figure YAML — run paperforge add-figure)")
                if fig_envs:
                    text_par += "\\n\\n" + "\\n\\n".join(fig_envs)
                claim_blocks.append(text_par)
            block += "\\n\\n".join(claim_blocks)
        else:
            block += "% TODO: No claims linked to this section yet."
        blocks.append(block)
    return "\\n\\n".join(blocks)"""
content = content.replace(gen_j_sec_old, gen_j_sec_new)

# _generate_journal_author_block
auth_old = """def _generate_journal_author_block(authors: list[str]) -> str:
    if not authors:
        return "Author(s)~TBD,~\\IEEEmembership{Member,~IEEE}"
    return "\\\\\\n".join(
        f"{author},~\\IEEEmembership{{Member,~IEEE}}" for author in authors
    )"""

auth_new = """def _generate_author_block_journal(
    authors: list[str],
    affiliations: list[Affiliation],
) -> str:
    if not affiliations:
        return f"\\author{{{', '.join(authors)}}}"
    lines = ["\\author{"]
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
        if i < len(authors) - 1:
            lines.append("")
    lines.append("}")
    return "\\n".join(lines)"""
content = content.replace(auth_old, auth_new)


# updating callers
content = content.replace("_generate_sections(project.config.sections, project.claims)", "_generate_sections(project.config.sections, project)")
content = content.replace("_generate_journal_sections(project.config.sections, project.claims)", "_generate_journal_sections(project.config.sections, project)")
content = content.replace("author_block = _generate_journal_author_block(project.config.authors)", "author_block = _generate_author_block_journal(project.config.authors, project.config.affiliations)")


# latexmk task 3 inside `build.py`
latexmk_old = """    pdflatex = shutil.which("pdflatex")
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
"""

# Let's insert the _compile_pdf function just above `def run`
compile_func = """def _compile_pdf(tex_path: Path, output_dir: Path) -> tuple[bool, str]:
    import shutil
    import subprocess

    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")

    if latexmk:
        result = subprocess.run(
            [latexmk, "-pdf", "-interaction=nonstopmode",
             f"-outdir={output_dir}", str(tex_path.name)],
            capture_output=True, text=True, cwd=output_dir
        )
        return result.returncode == 0, "latexmk"

    if pdflatex:
        for _ in range(2):
            result = subprocess.run(
                [pdflatex, "-interaction=nonstopmode",
                 f"-output-directory={output_dir}", str(tex_path)],
                capture_output=True, text=True
            )
        return result.returncode == 0, "pdflatex"

    return False, "none"
"""

content = content.replace("def run(project_root: Path, target: str = \"ieee\") -> None:", compile_func + "\ndef run(project_root: Path, target: str = \"ieee\") -> None:")

latexmk_new = """    pdf_ok, method = _compile_pdf(tex_path, output_dir)
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
        pdf_line = f"paper.pdf          {compiler_msg}" if method == "none" else "paper.pdf          compilation failed — see .paperforge/output/paper.log"
"""
content = content.replace(latexmk_old, latexmk_new)

# panel changes
panel_old = """    body = Group(
        Text("Output: .paperforge/output/"),
        Text(""),
        Text("Files:"),
        Text("  paper.tex          \u2713"),
        Text(f"  {pdf_line}"),
        Text(""),
        Text(f"Claims compiled:    {len(project.claims)}"),"""

panel_new = """    body = Group(
        Text("Output: .paperforge/output/"),
        Text(""),
        Text("Files:"),
        Text("  paper.tex          \u2713"),
        Text(f"  {pdf_line}"),
        Text(f"  ({compiler_msg})"),
        Text(""),
        Text(f"Claims compiled:    {len(project.claims)}"),"""
content = content.replace(panel_old, panel_new)

build_path.write_text(content, "utf-8")
print("Done build.py")
