"""Tests for paperforge build command."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from paperforge.commands import build, init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _make_valid_project(
    tmp_path: Path,
    title: str = "A Valid IEEE Research Title",
    authors: list[str] | None = None,
    sections: list[str] | None = None,
    text: str = "This model achieves 98.4% accuracy.",
) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    claim_path = pf_dir / "claims" / "claim_01.yaml"
    claim = Claim(
        id="claim_01",
        text=text,
        experiment="exp_01",
        sections=sections or ["results"],
        status="verified",
    )
    claim_path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    exp_path = pf_dir / "experiments" / "exp_01.yaml"
    experiment = Experiment(id="exp_01", metrics={"accuracy": 98.4}, seed=42)
    exp_path.write_text(
        yaml.dump(experiment.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    paper_yaml = pf_dir / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = title
    data["authors"] = authors or ["Alice Smith"]
    data["sections_overview"] = "Related Work in Section II."
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def _get_out(tmp_path: Path) -> Path:
    p = tmp_path / "paper_generated" / "current"
    return p if p.exists() else tmp_path / "paper"


def test_build_fails_without_init(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        build.run(tmp_path)
    assert exc_info.value.code == 1


def test_build_blocked_by_errors(tmp_path: Path) -> None:
    init.run(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        build.run(tmp_path)
    assert exc_info.value.code == 1


def test_build_creates_output_directory(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)
    build.run(tmp_path)
    assert _get_out(tmp_path).is_dir()


def test_build_creates_tex_file(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)
    build.run(tmp_path)
    assert (_get_out(tmp_path) / "paper.tex").exists()


def test_build_tex_contains_title(tmp_path: Path) -> None:
    _make_valid_project(tmp_path, title="Test Paper Title")
    build.run(tmp_path)
    content = (_get_out(tmp_path) / "paper.tex").read_text(encoding="utf-8")
    assert "Test Paper Title" in content


def test_build_tex_contains_author(tmp_path: Path) -> None:
    _make_valid_project(tmp_path, authors=["Alice Smith"])
    build.run(tmp_path)
    content = (_get_out(tmp_path) / "paper.tex").read_text(encoding="utf-8")
    assert "Alice Smith" in content


def test_build_tex_contains_claim_text(tmp_path: Path) -> None:
    _make_valid_project(tmp_path, text="This model achieves 98.4% accuracy.")
    build.run(tmp_path)
    content = (_get_out(tmp_path) / "paper.tex").read_text(encoding="utf-8")
    assert "This model achieves 98.4\\% accuracy." in content


def test_build_tex_contains_documentclass(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)
    build.run(tmp_path)
    content = (_get_out(tmp_path) / "paper.tex").read_text(encoding="utf-8")
    assert "\\documentclass[conference]{IEEEtran}" in content


def test_build_tex_contains_section_headings(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)
    build.run(tmp_path)
    content = (_get_out(tmp_path) / "paper.tex").read_text(encoding="utf-8")
    assert "\\section{" in content


def test_build_abstract_from_claims(tmp_path: Path) -> None:
    _make_valid_project(
        tmp_path,
        text="This model achieves 98.4% accuracy.",
        sections=["abstract", "results"],
    )
    build.run(tmp_path)
    content = (_get_out(tmp_path) / "paper.tex").read_text(encoding="utf-8")
    abstract_block = content.split("\\begin{abstract}")[1].split("\\end{abstract}")[0]
    assert "This model achieves 98.4\\% accuracy." in abstract_block


def test_build_no_claims_in_section_emits_todo(tmp_path: Path) -> None:
    _make_valid_project(tmp_path, sections=["results"])
    build.run(tmp_path)
    content = (_get_out(tmp_path) / "paper.tex").read_text(encoding="utf-8")
    assert "% TODO" in content


def test_build_collect_issues_exposed(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert isinstance(issues, list)
    assert all(hasattr(issue, "severity") for issue in issues)
