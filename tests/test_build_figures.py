from pathlib import Path
from unittest.mock import patch

from paperforge.commands.build import _claim_paragraph, _compile_pdf, _generate_sections
from paperforge.core.project import PaperForgeProject, ProjectConfig
from paperforge.models.claim import Claim
from paperforge.models.figure import Figure


def mock_project(figures=None, claims=None):
    config = ProjectConfig(version="0.1", title="T", authors=["A"], venue="acm", status="draft", sections=[], build_output_dir=".", latex_template="ieee")
    project = PaperForgeProject(root=Path("."), config=config, claims=claims or [], experiments=[], figures=figures or [])
    return project

def test_figure_with_path_and_caption_emits_environment():
    fig = Figure(id="fig_01", caption="A map", path="figures/map.png")
    claim = Claim(id="claim_01", text="Text", sections=["introduction"], figures=["fig_01"], experiment="")
    project = mock_project(figures=[fig], claims=[claim])
    latex = _generate_sections(["introduction"], project)
    assert "\\begin{figure}[!t]" in latex
    assert "\\includegraphics[width=\\columnwidth]{figures/map.png}" in latex
    assert "\\caption{A map}" in latex
    assert "\\label{fig:fig_01}" in latex
    assert "\\end{figure}" in latex

def test_figure_missing_path_emits_comment_only():
    fig = Figure(id="fig_01", caption="A map", path=None)
    claim = Claim(id="claim_01", text="Text", sections=["introduction"], figures=["fig_01"], experiment="")
    project = mock_project(figures=[fig], claims=[claim])
    latex = _generate_sections(["introduction"], project)
    assert "\\begin{figure}" not in latex
    assert "% Figure: fig_01 — A map (path not set)" in latex
    assert "% \\label{fig:fig_01}" in latex

def test_bare_string_figure_emits_run_add_figure_comment():
    claim = Claim(id="claim_01", text="Text", sections=["introduction"], figures=["fig_99"], experiment="")
    project = mock_project(figures=[], claims=[claim])
    latex = _generate_sections(["introduction"], project)
    assert "% Reference: fig_99 (no figure YAML — run paperforge add-figure)" in latex

def test_inline_ref_added_to_claim_paragraph():
    fig = Figure(id="fig_01", caption="Cap")
    claim = Claim(id="claim_01", text="This is it.", figures=["fig_01"], experiment="")
    project = mock_project(figures=[fig])
    para = _claim_paragraph(claim, project)
    assert "This is it. (see Fig.~\\ref{fig:fig_01})" in para

def test_width_inches_converted_correctly():
    fig = Figure(id="fig_01", caption="Cap", path="figures/x.png", width_inches=3.5)
    claim = Claim(id="claim_01", text="Text", sections=["introduction"], figures=["fig_01"], experiment="")
    project = mock_project(figures=[fig], claims=[claim])
    latex = _generate_sections(["introduction"], project)
    assert "\\includegraphics[width=3.5in]{figures/x.png}" in latex

def test_fallback_to_columnwidth_if_no_width_inches():
    fig = Figure(id="fig_01", caption="Cap", path="figures/x.png", width_inches=None)
    claim = Claim(id="claim_01", text="Text", sections=["introduction"], figures=["fig_01"], experiment="")
    project = mock_project(figures=[fig], claims=[claim])
    latex = _generate_sections(["introduction"], project)
    assert "\\includegraphics[width=\\columnwidth]{figures/x.png}" in latex

@patch("shutil.which")
@patch("subprocess.run")
def test_latexmk_preferred_over_pdflatex(mock_run, mock_which, tmp_path):
    mock_which.side_effect = lambda cmd: "/usr/bin/latexmk" if cmd == "latexmk" else "/usr/bin/pdflatex"
    
    class MockProcess:
        returncode = 0
    mock_run.return_value = MockProcess()
    
    tex_path = tmp_path / "paper.tex"
    tex_path.write_text("hello")
    output_dir = tmp_path
    
    ok, method = _compile_pdf(tex_path, output_dir)
    assert ok is True
    assert method == "latexmk"
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0][0] == "/usr/bin/latexmk"

@patch("shutil.which")
@patch("subprocess.run")
def test_pdflatex_fallback_used(mock_run, mock_which, tmp_path):
    mock_which.side_effect = lambda cmd: None if cmd == "latexmk" else "/usr/bin/pdflatex"
    
    class MockProcess:
        returncode = 0
    mock_run.return_value = MockProcess()
    
    tex_path = tmp_path / "paper.tex"
    tex_path.write_text("hello")
    output_dir = tmp_path
    
    ok, method = _compile_pdf(tex_path, output_dir)
    assert ok is True
    assert method == "pdflatex"
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0][0][0][0] == "/usr/bin/pdflatex"
