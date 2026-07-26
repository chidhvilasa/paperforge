"""Tests for LaTeX quality enhancements."""

from pathlib import Path

import yaml

from paperforge.commands import build, generate_figures, init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.models.algorithm import Algorithm


def write_test_project(tmp_path: Path) -> PaperForgeProject:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    p_data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    p_data["title"] = "Test Quality Paper Title"
    p_data["authors"] = ["Author One"]
    p_data["email"] = "author@example.com"
    p_data["sections_overview"] = "Related Work in Section II."
    paper_yaml.write_text(yaml.dump(p_data), encoding="utf-8")

    exp_yaml = tmp_path / ".paperforge" / "experiments" / "exp_01.yaml"
    e_data = yaml.safe_load(exp_yaml.read_text(encoding="utf-8"))
    e_data["description"] = "Test experiment description for reproducibility."
    e_data["metrics"] = {"accuracy": 98.4, "f1": 97.1}
    exp_yaml.write_text(yaml.dump(e_data), encoding="utf-8")

    claim_yaml = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    c_data = yaml.safe_load(claim_yaml.read_text(encoding="utf-8"))
    c_data["text"] = "Primary results claim text."
    c_data["experiment"] = "exp_01"
    c_data["sections"] = ["introduction"]
    c_data["status"] = "verified"
    claim_yaml.write_text(yaml.dump(c_data), encoding="utf-8")

    res_yaml = tmp_path / ".paperforge" / "claims" / "claim_res.yaml"
    res_data = {
        "id": "claim_res",
        "text": "Results claim text.",
        "experiment": "exp_01",
        "sections": ["results"],
        "status": "verified",
    }
    res_yaml.write_text(yaml.dump(res_data), encoding="utf-8")

    return PaperForgeProject.load(tmp_path)


def test_subsection_emitted_when_set(tmp_path: Path) -> None:
    write_test_project(tmp_path)
    claim_path = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    c_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    c_data["text"] = "Subsection test claim text."
    c_data["experiment"] = "exp_01"
    c_data["sections"] = ["introduction"]
    c_data["subsection"] = "System Architecture"
    claim_path.write_text(yaml.dump(c_data), encoding="utf-8")

    build.run(tmp_path, target="ieee", force=True, no_reveal=True)
    tex_content = (tmp_path / "paper" / "paper.tex").read_text(encoding="utf-8")
    assert "\\subsection{System Architecture}" in tex_content


def test_no_subsection_when_empty(tmp_path: Path) -> None:
    write_test_project(tmp_path)
    claim_path = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    c_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    c_data["text"] = "Plain claim text."
    c_data["experiment"] = "exp_01"
    c_data["sections"] = ["introduction"]
    c_data["subsection"] = ""
    claim_path.write_text(yaml.dump(c_data), encoding="utf-8")

    build.run(tmp_path, target="ieee", force=True, no_reveal=True)
    tex_content = (tmp_path / "paper" / "paper.tex").read_text(encoding="utf-8")
    assert "\\subsection{" not in tex_content


def test_figure_placeholder_when_no_image(tmp_path: Path) -> None:
    write_test_project(tmp_path)
    fig_data = {
        "id": "fig_01",
        "caption": "Missing Figure Caption",
        "path": "figures/missing.png",
    }
    (tmp_path / ".paperforge" / "figures" / "fig_01.yaml").write_text(
        yaml.dump(fig_data), encoding="utf-8"
    )
    claim_path = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    c_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    c_data["text"] = "Claim referencing missing figure."
    c_data["experiment"] = "exp_01"
    c_data["sections"] = ["introduction"]
    c_data["figures"] = ["fig_01"]
    claim_path.write_text(yaml.dump(c_data), encoding="utf-8")

    build.run(tmp_path, target="ieee", force=True, no_reveal=True)
    tex_content = (tmp_path / "paper" / "paper.tex").read_text(encoding="utf-8")
    assert "fbox" in tex_content or "placeholder" in tex_content.lower()
    assert "\\begin{figure}" in tex_content


def test_figure_includegraphics_when_file_exists(tmp_path: Path) -> None:
    write_test_project(tmp_path)
    fig_dir = tmp_path / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    img_file = fig_dir / "fig_01.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")

    fig_data = {
        "id": "fig_01",
        "caption": "Existing Image Map",
        "path": "figures/fig_01.png",
    }
    (tmp_path / ".paperforge" / "figures" / "fig_01.yaml").write_text(
        yaml.dump(fig_data), encoding="utf-8"
    )
    claim_path = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    c_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    c_data["text"] = "Claim referencing existing figure image."
    c_data["experiment"] = "exp_01"
    c_data["sections"] = ["introduction"]
    c_data["figures"] = ["fig_01"]
    claim_path.write_text(yaml.dump(c_data), encoding="utf-8")

    build.run(tmp_path, target="ieee", force=True, no_reveal=True)
    tex_content = (tmp_path / "paper" / "paper.tex").read_text(encoding="utf-8")
    assert "\\includegraphics" in tex_content


def test_contribution_claims_emit_itemize(tmp_path: Path) -> None:
    write_test_project(tmp_path)
    c1 = {
        "id": "claim_c1",
        "text": "First contribution claim.",
        "experiment": "exp_01",
        "sections": ["introduction"],
        "is_contribution": True,
    }
    c2 = {
        "id": "claim_c2",
        "text": "Second contribution claim.",
        "experiment": "exp_01",
        "sections": ["introduction"],
        "is_contribution": True,
    }
    (tmp_path / ".paperforge" / "claims" / "claim_c1.yaml").write_text(
        yaml.dump(c1), encoding="utf-8"
    )
    (tmp_path / ".paperforge" / "claims" / "claim_c2.yaml").write_text(
        yaml.dump(c2), encoding="utf-8"
    )

    build.run(tmp_path, target="ieee", force=True, no_reveal=True)
    tex_content = (tmp_path / "paper" / "paper.tex").read_text(encoding="utf-8")
    assert "\\begin{itemize}" in tex_content
    assert "main contributions" in tex_content.lower()


def test_no_contribution_warning(tmp_path: Path) -> None:
    write_test_project(tmp_path)
    claim_path = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    c_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    c_data["text"] = "Intro claim without contribution flag."
    c_data["sections"] = ["introduction"]
    c_data["is_contribution"] = False
    claim_path.write_text(yaml.dump(c_data), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "NO_CONTRIBUTION_CLAIMS" for i in issues)


def test_sections_overview_in_paper_yaml(tmp_path: Path) -> None:
    write_test_project(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    p_data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    p_data["sections_overview"] = "Related Work in Section II."
    paper_yaml.write_text(yaml.dump(p_data), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    assert project.config.sections_overview == "Related Work in Section II."


def test_algorithm_model_round_trip() -> None:
    alg = Algorithm(
        id="alg_01",
        caption="Adaptive Batching Algorithm",
        steps=["\\Require batch size $B$", "\\State $B \\gets 50$"],
        notes="Optional notes",
    )
    data = alg.to_yaml()
    alg2 = Algorithm.from_yaml(data)
    assert alg2.id == alg.id
    assert alg2.caption == alg.caption
    assert alg2.steps == alg.steps
    assert alg2.notes == alg.notes


def test_algorithm_to_latex() -> None:
    alg = Algorithm(
        id="alg_01",
        caption="Test Algorithm Caption",
        steps=["\\State step 1"],
    )
    latex = alg.to_latex()
    assert "\\begin{algorithm}" in latex
    assert "\\begin{algorithmic}" in latex
    assert "caption{Test Algorithm Caption}" in latex


def test_generate_figures_command_exists() -> None:
    assert callable(generate_figures.run)


def test_bar_chart_generated_from_experiment(tmp_path: Path) -> None:
    write_test_project(tmp_path)
    fig_data = {
        "id": "fig_01",
        "caption": "Experiment Bar Chart",
        "source_experiment": "exp_01",
        "chart_type": "bar",
        "path": "figures/fig_01.png",
    }
    (tmp_path / ".paperforge" / "figures" / "fig_01.yaml").write_text(
        yaml.dump(fig_data), encoding="utf-8"
    )

    generate_figures.run(tmp_path, "fig_01")
    assert (tmp_path / "figures" / "fig_01.png").exists()


def test_missing_sections_overview_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "MISSING_SECTIONS_OVERVIEW" for i in issues)
