"""Tests for paperforge find command."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from paperforge.commands import find, init
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _claim_path(tmp_path: Path, claim_id: str = "claim_01") -> Path:
    return tmp_path / ".paperforge" / "claims" / f"{claim_id}.yaml"


def _exp_path(tmp_path: Path, exp_id: str = "exp_01") -> Path:
    return tmp_path / ".paperforge" / "experiments" / f"{exp_id}.yaml"


def test_find_matches_claim_text(tmp_path: Path) -> None:
    """find matches a term in claim text without raising."""
    init.run(tmp_path)
    claim = Claim(
        id="claim_01",
        text="neural network achieves 98% accuracy",
        experiment="exp_01",
        status="unverified",
    )
    _write_yaml(_claim_path(tmp_path), claim.to_yaml())
    # Should not raise
    find.run("neural", tmp_path, "all")


def test_find_no_results(tmp_path: Path) -> None:
    """find exits 0 with a yellow panel when there are no matches."""
    init.run(tmp_path)
    # Should not raise — exits 0 with "No results" panel
    find.run("zzznomatch999", tmp_path, "all")


def test_find_matches_experiment_id(tmp_path: Path) -> None:
    """find matches the experiment id string."""
    init.run(tmp_path)
    # exp_01 is created by init
    find.run("exp_01", tmp_path, "experiments")


def test_find_case_insensitive(tmp_path: Path) -> None:
    """find is case-insensitive — lowercase query matches uppercase text."""
    init.run(tmp_path)
    claim = Claim(
        id="claim_01",
        text="UPPERCASE ACCURACY",
        experiment="exp_01",
        status="unverified",
    )
    _write_yaml(_claim_path(tmp_path), claim.to_yaml())
    find.run("uppercase", tmp_path, "claims")


def test_find_empty_query_exits(tmp_path: Path) -> None:
    """find exits 1 when query is empty."""
    init.run(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        find.run("", tmp_path, "all")
    assert exc_info.value.code == 1


def test_find_field_claims_only(tmp_path: Path) -> None:
    """find with --field claims searches only claims."""
    init.run(tmp_path)
    claim = Claim(
        id="claim_01",
        text="blockchain security model",
        experiment="exp_01",
        status="unverified",
    )
    _write_yaml(_claim_path(tmp_path), claim.to_yaml())
    find.run("blockchain", tmp_path, "claims")


def test_find_field_experiments_only(tmp_path: Path) -> None:
    """find with --field experiments searches only experiments."""
    init.run(tmp_path)
    exp = Experiment(id="exp_01", description="accuracy benchmark run")
    _write_yaml(_exp_path(tmp_path), exp.to_yaml())
    find.run("benchmark", tmp_path, "experiments")


def test_find_matches_citation_key(tmp_path: Path) -> None:
    """find matches a citation key in a claim."""
    init.run(tmp_path)
    claim = Claim(
        id="claim_01",
        text="A well-cited claim.",
        experiment="exp_01",
        citations=["smith2024"],
        status="unverified",
    )
    _write_yaml(_claim_path(tmp_path), claim.to_yaml())
    find.run("smith2024", tmp_path, "claims")


def test_find_matches_section_name(tmp_path: Path) -> None:
    """find matches a section name in a claim."""
    init.run(tmp_path)
    claim = Claim(
        id="claim_01",
        text="A claim about methods.",
        experiment="exp_01",
        sections=["methodology"],
        status="unverified",
    )
    _write_yaml(_claim_path(tmp_path), claim.to_yaml())
    find.run("methodology", tmp_path, "claims")


def test_find_fails_without_init(tmp_path: Path) -> None:
    """find exits 1 when the project is not initialized."""
    with pytest.raises(SystemExit) as exc_info:
        find.run("test", tmp_path, "all")
    assert exc_info.value.code == 1
