"""Tests for output directory changes and reveal behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from paperforge.commands import build, init
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _fix_all_errors(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    claim_path = pf_dir / "claims" / "claim_01.yaml"
    claim = Claim(
        id="claim_01",
        text="This model achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results"],
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
    data["title"] = "Test Paper"
    data["authors"] = ["Test Author"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def test_init_creates_paper_directory(tmp_path: Path) -> None:
    init.run(tmp_path)
    assert (tmp_path / "paper").is_dir()


def test_init_paper_gitignore_exists(tmp_path: Path) -> None:
    init.run(tmp_path)
    gitignore = tmp_path / "paper" / ".gitignore"
    assert gitignore.exists()

    content = gitignore.read_text(encoding="utf-8")
    assert "*.aux" in content
    assert "!paper.tex" in content
    assert "!paper.pdf" in content


def test_build_writes_to_paper_directory(tmp_path: Path) -> None:
    _fix_all_errors(tmp_path)
    build.run(tmp_path, target="ieee")
    assert (tmp_path / "paper" / "paper.tex").exists()


def test_build_tex_not_in_paperforge_output(tmp_path: Path) -> None:
    _fix_all_errors(tmp_path)
    build.run(tmp_path, target="ieee")
    assert not (tmp_path / ".paperforge" / "output" / "paper.tex").exists()


def test_reveal_not_called_when_no_pdf(tmp_path: Path) -> None:
    _fix_all_errors(tmp_path)
    mock_reveal = MagicMock()
    with patch("paperforge.commands.build._reveal_output", mock_reveal):
        build.run(tmp_path, target="ieee")
    assert not mock_reveal.called


def test_no_reveal_flag_suppresses_reveal(tmp_path: Path) -> None:
    _fix_all_errors(tmp_path)
    mock_reveal = MagicMock()
    with patch("paperforge.commands.build._reveal_output", mock_reveal), \
         patch("paperforge.commands.build._compile_pdf", return_value=(True, "pdflatex")):
        build.run(tmp_path, target="ieee", no_reveal=True)
    assert not mock_reveal.called
