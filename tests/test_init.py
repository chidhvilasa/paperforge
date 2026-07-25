"""Tests for the paperforge init command."""

from pathlib import Path

import pytest
import yaml

from paperforge.commands import init
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def test_init_creates_paperforge_dir(tmp_path: Path) -> None:
    init.run(tmp_path)
    assert (tmp_path / ".paperforge").is_dir()


def test_init_creates_paper_yaml(tmp_path: Path) -> None:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    assert paper_yaml.exists()
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    assert data["version"] == "0.1"
    assert data["status"] == "draft"
    assert isinstance(data["sections"], list)
    assert len(data["sections"]) == 8


def test_init_creates_claims_dir(tmp_path: Path) -> None:
    init.run(tmp_path)
    assert (tmp_path / ".paperforge" / "claims").is_dir()
    assert (tmp_path / ".paperforge" / "claims" / "claim_01.yaml").exists()


def test_init_creates_experiments_dir(tmp_path: Path) -> None:
    init.run(tmp_path)
    assert (tmp_path / ".paperforge" / "experiments").is_dir()
    assert (tmp_path / ".paperforge" / "experiments" / "exp_01.yaml").exists()


def test_init_creates_gitignore(tmp_path: Path) -> None:
    init.run(tmp_path)
    assert (tmp_path / ".paperforge" / ".gitignore").exists()


def test_init_fails_if_already_initialized(tmp_path: Path) -> None:
    init.run(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        init.run(tmp_path)
    assert exc_info.value.code == 1


def test_init_blank_templates_are_valid(tmp_path: Path) -> None:
    init.run(tmp_path)

    claim_yaml = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    claim = Claim.from_yaml(yaml.safe_load(claim_yaml.read_text(encoding="utf-8")))
    assert claim.id == "claim_01"
    assert claim.status == "unverified"

    exp_yaml = tmp_path / ".paperforge" / "experiments" / "exp_01.yaml"
    experiment = Experiment.from_yaml(
        yaml.safe_load(exp_yaml.read_text(encoding="utf-8"))
    )
    assert experiment.id == "exp_01"
    assert experiment.metrics == {}
