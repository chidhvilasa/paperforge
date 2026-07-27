"""Tests for math mode escaping and markdown inline conversion."""

from pathlib import Path

from paperforge.core.project import PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.models.figure import Figure
from paperforge.models.table import Table
from paperforge.utils.latex import (
    escape_latex,
    escape_latex_safe,
    markdown_to_latex_inline,
)


def test_escape_latex_safe_math_passthrough() -> None:
    text = r"\alpha + \beta = 73.6% \gamma"
    assert escape_latex_safe(text, raw=True) == text


def test_escape_latex_inline_math() -> None:
    text = r"Achieves 73.6% accuracy with $\alpha + \beta$ and $x > y$."
    escaped = escape_latex(text)
    assert r"73.6\%" in escaped
    assert r"$\alpha + \beta$" in escaped
    assert r"$x > y$" in escaped


def test_markdown_to_latex_inline() -> None:
    text = "This is **bold** and *italic* and `code` text."
    converted = markdown_to_latex_inline(text)
    assert r"\textbf{bold}" in converted
    assert r"\textit{italic}" in converted
    assert r"\texttt{code}" in converted


def test_claim_math_flag_yaml() -> None:
    c = Claim.from_yaml({
        "id": "claim_math",
        "text": r"\alpha = \beta",
        "is_math": True,
        "raw_latex": True,
        "claim_type": "theorem",
    })
    assert c.is_math is True
    assert c.raw_latex is True
    assert c.claim_type == "theorem"
    dumped = c.to_yaml()
    assert dumped["is_math"] is True
    assert dumped["raw_latex"] is True
    assert dumped["claim_type"] == "theorem"


def test_table_raw_rows_yaml() -> None:
    t = Table.from_yaml({
        "id": "tbl_math",
        "caption": "Math Table",
        "is_math": True,
        "raw_latex_rows": True,
    })
    assert t.is_math is True
    assert t.raw_latex_rows is True
    dumped = t.to_yaml()
    assert dumped["is_math"] is True
    assert dumped["raw_latex_rows"] is True


def test_figure_math_flag_yaml() -> None:
    f = Figure.from_yaml({
        "id": "fig_math",
        "caption": r"$\alpha$ figure",
        "is_math": True,
    })
    assert f.is_math is True
    dumped = f.to_yaml()
    assert dumped["is_math"] is True


def test_math_claim_missing_flag_doctor_check(tmp_path: Path) -> None:
    from paperforge.commands.doctor import collect_issues

    pf = tmp_path / ".paperforge"
    pf.mkdir()
    (pf / "paper.yaml").write_text("version: '0.1'\ntitle: T\nauthors: [A]\nvenue: IEEE\nstatus: draft\nsections: []\n")
    (pf / "claims").mkdir()
    (pf / "experiments").mkdir()
    (pf / "claims" / "c1.yaml").write_text(
        "id: c1\ntext: r'\\alpha + \\beta'\nexperiment: ''\nis_math: false\nraw_latex: false\n"
    )
    proj = PaperForgeProject.load(tmp_path)
    issues = collect_issues(proj)
    math_issues = [i for i in issues if i.code == "MATH_CLAIM_MISSING_FLAG"]
    assert len(math_issues) == 1


def test_proof_without_theorem_doctor_check(tmp_path: Path) -> None:
    from paperforge.commands.doctor import collect_issues

    pf = tmp_path / ".paperforge"
    pf.mkdir()
    (pf / "paper.yaml").write_text("version: '0.1'\ntitle: T\nauthors: [A]\nvenue: IEEE\nstatus: draft\nsections: []\n")
    (pf / "claims").mkdir()
    (pf / "experiments").mkdir()
    (pf / "claims" / "c1.yaml").write_text(
        "id: c1\ntext: Proof body\nexperiment: ''\nclaim_type: proof\n"
    )
    proj = PaperForgeProject.load(tmp_path)
    issues = collect_issues(proj)
    proof_issues = [i for i in issues if i.code == "PROOF_WITHOUT_THEOREM"]
    assert len(proof_issues) == 1
