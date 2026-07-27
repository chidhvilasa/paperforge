"""Tests for IEEE template compliance, unicode escaping, algorithms, and build blocking."""

import inspect
from pathlib import Path

import pytest

from paperforge.commands.build import run as build_run
from paperforge.commands.doctor import collect_issues
from paperforge.commands.doctor import run as doctor_run
from paperforge.commands.init import run as init_run
from paperforge.core.project import PaperForgeProject
from paperforge.models.algorithm import Algorithm
from paperforge.utils.latex import escape_latex, markdown_to_latex_inline


def test_ieeeparstart_uses_actual_first_words(tmp_path: Path) -> None:
    init_run(tmp_path)
    claims_dir = tmp_path / ".paperforge" / "claims"
    for f in claims_dir.glob("*.yaml"):
        f.unlink()

    (claims_dir / "claim_01.yaml").write_text(
        "id: claim_01\ntext: The problem of X is significant.\nexperiment: exp_01\nsections: [introduction]\nstatus: verified\n",
        encoding="utf-8",
    )
    build_run(tmp_path, target="ieee-journal", force_anyway=True)
    tex_path = tmp_path / "paper_generated" / "current" / "paper.tex"
    if not tex_path.exists():
        tex_path = tmp_path / "paper" / "paper_generated" / "current" / "paper.tex"
    tex_content = tex_path.read_text(encoding="utf-8")
    assert "\\IEEEPARstart{T}{he}" in tex_content or "\\IEEEPARstart{T}{he problem" in tex_content
    assert "problem of X is significant" in tex_content


def test_no_membership_for_student_member(tmp_path: Path) -> None:
    init_run(tmp_path)
    author_yaml = tmp_path / "paper_information" / "author.yaml"
    author_yaml.write_text(
        "authors:\n  - Firstname Lastname\naffiliations:\n  - name: Author\n    institution: Uni\n    membership: 'Student Member'\n",
        encoding="utf-8",
    )
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    if paper_yaml.exists():
        paper_yaml.write_text(
            paper_yaml.read_text(encoding="utf-8") + "\naffiliations:\n  - name: Author\n    institution: Uni\n    membership: 'Student Member'\n",
            encoding="utf-8",
        )

    build_run(tmp_path, target="ieee-journal", force_anyway=True)
    tex_path = tmp_path / "paper_generated" / "current" / "paper.tex"
    if not tex_path.exists():
        tex_path = tmp_path / "paper" / "paper_generated" / "current" / "paper.tex"
    tex_content = tex_path.read_text(encoding="utf-8")
    assert "IEEEmembership" not in tex_content


def test_membership_for_senior_member(tmp_path: Path) -> None:
    init_run(tmp_path)
    author_yaml = tmp_path / "paper_information" / "author.yaml"
    author_yaml.write_text(
        "authors:\n  - Firstname Lastname\naffiliations:\n  - name: Author\n    institution: Uni\n    membership: 'Senior Member'\n",
        encoding="utf-8",
    )
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    if paper_yaml.exists():
        paper_yaml.write_text(
            paper_yaml.read_text(encoding="utf-8") + "\naffiliations:\n  - name: Author\n    institution: Uni\n    membership: 'Senior Member'\n",
            encoding="utf-8",
        )

    build_run(tmp_path, target="ieee-journal", force_anyway=True)
    tex_path = tmp_path / "paper_generated" / "current" / "paper.tex"
    if not tex_path.exists():
        tex_path = tmp_path / "paper" / "paper_generated" / "current" / "paper.tex"
    tex_content = tex_path.read_text(encoding="utf-8")
    assert "Senior Member" in tex_content


def test_unicode_emdash_escaped() -> None:
    assert escape_latex("A—B") == "A---B"


def test_unicode_curly_quotes_escaped() -> None:
    assert escape_latex("\u201cquoted\u201d") == "``quoted''"


def test_markdown_link_converts() -> None:
    result = markdown_to_latex_inline("[IEEE](https://ieee.org)")
    assert "\\href{https://ieee.org}{IEEE}" in result


def test_duplicate_claim_text_now_error(tmp_path: Path) -> None:
    init_run(tmp_path)
    claims_dir = tmp_path / ".paperforge" / "claims"
    (claims_dir / "c1.yaml").write_text(
        "id: c1\ntext: Duplicate text sentence.\nexperiment: exp_01\nsections: [introduction]\n", encoding="utf-8"
    )
    (claims_dir / "c2.yaml").write_text(
        "id: c2\ntext: Duplicate text sentence.\nexperiment: exp_01\nsections: [methodology]\n", encoding="utf-8"
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    dup = next(i for i in issues if i.code == "DUPLICATE_CLAIM_TEXT")
    assert dup.severity == "ERROR"


def test_build_blocked_by_duplicate_claim(tmp_path: Path) -> None:
    init_run(tmp_path)
    claims_dir = tmp_path / ".paperforge" / "claims"
    (claims_dir / "c1.yaml").write_text(
        "id: c1\ntext: Duplicate text sentence.\nexperiment: exp_01\nsections: [introduction]\n", encoding="utf-8"
    )
    (claims_dir / "c2.yaml").write_text(
        "id: c2\ntext: Duplicate text sentence.\nexperiment: exp_01\nsections: [methodology]\n", encoding="utf-8"
    )
    with pytest.raises(SystemExit) as excinfo:
        build_run(tmp_path)
    assert excinfo.value.code == 1


def test_algorithm_emits_proper_latex() -> None:
    alg = Algorithm(
        id="alg_01",
        caption="Batch Verify",
        steps=["\\Require batch B", "\\State verify(B)"],
    )
    latex = alg.to_latex()
    assert "\\begin{algorithm}" in latex
    assert "\\begin{algorithmic}[1]" in latex
    assert "\\Require batch B" in latex


def test_pre_submission_check_exists() -> None:
    sig = inspect.signature(doctor_run)
    assert "pre_submission" in sig.parameters
