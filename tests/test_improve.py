"""Tests for paperforge improve command."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from paperforge.commands import improve, init
from paperforge.history import load_history
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _setup_project(tmp_path: Path, text: str = "This model achieves 98.4% accuracy.") -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    claim = Claim(
        id="claim_01",
        text=text,
        experiment="exp_01",
        sections=["results"],
        status="unverified",
    )
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    exp = Experiment(id="exp_01", metrics={"accuracy": 98.4}, seed=42)
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        yaml.dump(exp.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def test_improve_fails_without_init(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        improve.run(tmp_path, None, None, False)
    assert exc_info.value.code == 1


def test_improve_fails_no_claim_no_all(tmp_path: Path) -> None:
    init.run(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        improve.run(tmp_path, None, None, False)
    assert exc_info.value.code == 1


def test_improve_fails_unknown_claim_id(tmp_path: Path) -> None:
    init.run(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        improve.run(tmp_path, "claim_99", None, False)
    assert exc_info.value.code == 1


def test_improve_fails_if_llm_not_found(tmp_path: Path) -> None:
    init.run(tmp_path)
    with patch("shutil.which", return_value=None):
        with pytest.raises(SystemExit) as exc_info:
            improve.run(tmp_path, "claim_01", None, False)
        assert exc_info.value.code == 1


def test_improve_calls_llm_with_claim_context(tmp_path: Path) -> None:
    _setup_project(tmp_path, text="Original claim text")
    llm_response = (
        "ASSESSMENT: Good\n\n"
        "ISSUES:\n- None\n\n"
        "SUGGESTED TEXT:\nImproved claim text.\n\n"
        "REASONING: Better phrasing."
    )
    mock_run = MagicMock(
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=llm_response, stderr="")
    )

    with patch("shutil.which", return_value="/usr/bin/llm"), \
         patch("subprocess.run", mock_run), \
         patch("typer.prompt", return_value="n"):
        improve.run(tmp_path, "claim_01", None, False)

    assert mock_run.called
    called_args = str(mock_run.call_args)
    assert "claim_01" in called_args or "Original claim text" in called_args


def test_improve_applies_suggestion_on_yes(tmp_path: Path) -> None:
    _setup_project(tmp_path, text="old text")
    llm_response = (
        "ASSESSMENT: Needs precision\n\n"
        "ISSUES:\n- Vague wording\n\n"
        "SUGGESTED TEXT:\nnew improved text\n\n"
        "REASONING: Adds precision."
    )
    mock_run = MagicMock(
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=llm_response, stderr="")
    )

    with patch("shutil.which", return_value="/usr/bin/llm"), \
         patch("subprocess.run", mock_run), \
         patch("typer.prompt", return_value="y"):
        improve.run(tmp_path, "claim_01", None, False)

    claim_data = yaml.safe_load(
        (tmp_path / ".paperforge" / "claims" / "claim_01.yaml").read_text(encoding="utf-8")
    )
    assert claim_data["text"] == "new improved text"


def test_improve_skips_on_no(tmp_path: Path) -> None:
    _setup_project(tmp_path, text="original text")
    llm_response = (
        "ASSESSMENT: Fine\n\n"
        "ISSUES:\n- None\n\n"
        "SUGGESTED TEXT:\nnew text\n\n"
        "REASONING: Optional."
    )
    mock_run = MagicMock(
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=llm_response, stderr="")
    )

    with patch("shutil.which", return_value="/usr/bin/llm"), \
         patch("subprocess.run", mock_run), \
         patch("typer.prompt", return_value="n"):
        improve.run(tmp_path, "claim_01", None, False)

    claim_data = yaml.safe_load(
        (tmp_path / ".paperforge" / "claims" / "claim_01.yaml").read_text(encoding="utf-8")
    )
    assert claim_data["text"] == "original text"


def test_improve_records_snapshot_before_applying(tmp_path: Path) -> None:
    _setup_project(tmp_path, text="before")
    llm_response = (
        "ASSESSMENT: Needs edit\n\n"
        "ISSUES:\n- Weak\n\n"
        "SUGGESTED TEXT:\nafter\n\n"
        "REASONING: Stronger phrasing."
    )
    mock_run = MagicMock(
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=llm_response, stderr="")
    )

    with patch("shutil.which", return_value="/usr/bin/llm"), \
         patch("subprocess.run", mock_run), \
         patch("typer.prompt", return_value="y"):
        improve.run(tmp_path, "claim_01", None, False)

    snapshots = load_history(tmp_path / ".paperforge", "claim_01")
    assert len(snapshots) >= 1
    assert snapshots[0].snapshot["text"] == "before"
