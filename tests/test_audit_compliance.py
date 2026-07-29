"""Audit compliance tests for Phase 34 features."""

import subprocess
from pathlib import Path

import pytest
import yaml

from paperforge.commands import build, init
from paperforge.commands.build import _check_latex_artifacts
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.models.citation import Citation
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _init_project(tmp_path: Path) -> None:
    init.run(tmp_path)


def test_author_structured_fields(tmp_path: Path) -> None:
    """authors in paper.yaml load into Author dataclass with full_name and cite_name."""
    _init_project(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["authors"] = [
        {
            "given_name": "Chidhvilasa",
            "family_name": "Yepuri",
            "display_name": "Chidhvilasa Yepuri",
            "citation_name": "C. Yepuri",
            "email": "chidhvilasa2004@gmail.com",
        }
    ]
    paper_yaml.write_text(yaml.dump(data), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    author = project.config.authors[0]
    assert author.family_name == "Yepuri"
    assert author.cite_name == "C. Yepuri"
    assert author.full_name == "Chidhvilasa Yepuri"


def test_author_no_membership_when_null(tmp_path: Path, monkeypatch) -> None:
    """When ieee_membership_grade is null or invalid, \\IEEEmembership{} is not emitted."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    paper_yaml = pf / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["authors"] = [
        {
            "given_name": "A.",
            "family_name": "Author",
            "display_name": "A. Author",
            "ieee_membership_grade": None,
        }
    ]
    paper_yaml.write_text(yaml.dump(data), encoding="utf-8")

    exp = Experiment(id="exp_01", metrics={"accuracy": 98.4})
    (pf / "experiments" / "exp_01.yaml").write_text(yaml.dump(exp.to_yaml()), encoding="utf-8")
    claim = Claim(
        id="claim_01",
        text="System achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results", "abstract", "introduction", "conclusion"],
        status="verified",
    )
    (pf / "claims" / "claim_01.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    monkeypatch.setattr("shutil.which", lambda name: None)
    build.run(tmp_path, target="ieee-access", force_anyway=True)

    tex_path = next(iter(tmp_path.rglob("paper.tex")))
    content = tex_path.read_text(encoding="utf-8")
    assert "\\IEEEmembership" not in content


def test_pdf_metadata_in_preamble(tmp_path: Path, monkeypatch) -> None:
    """Build emits \\hypersetup with title, author, subject, and keywords in preamble."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    paper_yaml = pf / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["title"] = "Test Paper Title"
    data["keywords"] = ["routing", "VANET"]
    data["authors"] = [{"given_name": "A.", "family_name": "Author", "display_name": "A. Author"}]
    paper_yaml.write_text(yaml.dump(data), encoding="utf-8")

    exp = Experiment(id="exp_01", metrics={"accuracy": 98.4})
    (pf / "experiments" / "exp_01.yaml").write_text(yaml.dump(exp.to_yaml()), encoding="utf-8")
    claim = Claim(
        id="claim_01",
        text="System achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results", "abstract", "introduction", "conclusion"],
        status="verified",
    )
    (pf / "claims" / "claim_01.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    monkeypatch.setattr("shutil.which", lambda name: None)
    build.run(tmp_path, target="ieee", force_anyway=True)

    tex_path = next(iter(tmp_path.rglob("paper.tex")))
    content = tex_path.read_text(encoding="utf-8")
    assert "pdftitle={Test Paper Title}" in content
    assert "pdfkeywords={routing, VANET}" in content


def test_draft_mode_cli_flag() -> None:
    """CLI build command includes --mode / -m flag in help output."""
    res = subprocess.run(["uv", "run", "paperforge", "build", "--help"], capture_output=True, text=True, check=False)
    assert "--mode" in res.stdout or "-m" in res.stdout


def test_submission_mode_requires_verified_claims(tmp_path: Path, monkeypatch) -> None:
    """Submission mode blocks build if there are unverified claims or mismatch."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    exp = Experiment(id="exp_01", metrics={"accuracy": 50.0})
    (pf / "experiments" / "exp_01.yaml").write_text(yaml.dump(exp.to_yaml()), encoding="utf-8")
    claim = Claim(
        id="claim_01",
        text="System achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results", "abstract", "introduction", "conclusion"],
        status="unverified",
    )
    (pf / "claims" / "claim_01.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(SystemExit) as exc:
        build.run(tmp_path, mode="submission")
    assert exc.value.code == 1


def test_reports_dir_created_after_build(tmp_path: Path, monkeypatch) -> None:
    """Build creates reports directory with doctor.md, claim_evidence_report.md, submission_checklist.md."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    exp = Experiment(id="exp_01", metrics={"accuracy": 98.4})
    (pf / "experiments" / "exp_01.yaml").write_text(yaml.dump(exp.to_yaml()), encoding="utf-8")
    claim = Claim(
        id="claim_01",
        text="System achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results", "abstract", "introduction", "conclusion"],
        status="verified",
    )
    (pf / "claims" / "claim_01.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    monkeypatch.setattr("shutil.which", lambda name: None)
    build.run(tmp_path, force_anyway=True)

    reports = list(tmp_path.rglob("reports"))
    assert len(reports) > 0 and reports[0].exists()
    report_dir = reports[0]
    assert (report_dir / "doctor.md").exists()
    assert (report_dir / "claim_evidence_report.md").exists()
    assert (report_dir / "submission_checklist.md").exists()


def test_latex_artifact_check_catches_bold_markdown() -> None:
    """_check_latex_artifacts identifies unresolved **bold** markdown in output."""
    content = "This is **bold** text in LaTeX output"
    issues = _check_latex_artifacts(content)
    assert len(issues) > 0
    assert "bold" in issues[0].lower()


def test_latex_artifact_check_passes_clean_content() -> None:
    """_check_latex_artifacts passes clean LaTeX content."""
    content = "This is \\textbf{bold} text in LaTeX output"
    issues = _check_latex_artifacts(content)
    assert issues == []


def test_claim_constraint_parse(tmp_path: Path) -> None:
    """Claim permitted_only_if condition evaluates against experiment metrics."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    exp = Experiment(id="exp_01", metrics={"accuracy": 98.4})
    (pf / "experiments" / "exp_01.yaml").write_text(yaml.dump(exp.to_yaml()), encoding="utf-8")

    claim = Claim(
        id="claim_01",
        text="System achieves high accuracy.",
        experiment="exp_01",
        sections=["results"],
        permitted_only_if=["accuracy >= 90.0"],
    )
    (pf / "claims" / "claim_01.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "CLAIM_CONSTRAINT_VIOLATED" for i in issues)


def test_citation_clean_notes_pass(tmp_path: Path) -> None:
    """Citation with standard publication notes does not trigger CITATION_HAS_INTERNAL_NOTE."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    cit = Citation(
        key="smith2024",
        title="Sample Paper",
        authors=["Smith, A."],
        year=2024,
        notes="Published in IEEE Access.",
    )
    (pf / "citations" / "smith2024.yaml").write_text(yaml.dump(cit.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "CITATION_HAS_INTERNAL_NOTE" for i in issues)
