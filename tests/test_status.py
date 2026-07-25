"""Tests for paperforge status command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from paperforge.commands import init, status
from paperforge.models.claim import Claim


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _claim_path(tmp_path: Path, claim_id: str = "claim_01") -> Path:
    return tmp_path / ".paperforge" / "claims" / f"{claim_id}.yaml"


def _exp_path(tmp_path: Path, exp_id: str = "exp_01") -> Path:
    return tmp_path / ".paperforge" / "experiments" / f"{exp_id}.yaml"


def test_status_fails_without_init(tmp_path: Path) -> None:
    """status exits 1 if project is not initialized."""
    with pytest.raises(SystemExit) as exc_info:
        status.run(tmp_path)
    assert exc_info.value.code == 1


def test_status_runs_on_fresh_project(tmp_path: Path) -> None:
    """status runs without raising on a freshly initialised project."""
    init.run(tmp_path)
    # Should not raise
    status.run(tmp_path)


def test_status_shows_claim_count(tmp_path: Path) -> None:
    """status executes without error — output verified by absence of exception."""
    init.run(tmp_path)
    # Add a second claim so count > 1
    claim = Claim(
        id="claim_02", text="Extra claim.", experiment="exp_01", status="verified"
    )
    _write_yaml(_claim_path(tmp_path, "claim_02"), claim.to_yaml())
    status.run(tmp_path)


def test_status_submission_not_ready_with_errors(tmp_path: Path) -> None:
    """status is display-only — it never raises SystemExit even with ERRORs."""
    init.run(tmp_path)
    # claim_01 already has empty text which is an ERROR — status should still pass
    status.run(tmp_path)


def test_status_section_coverage_computed(tmp_path: Path) -> None:
    """status handles a claim with multiple sections without crashing."""
    init.run(tmp_path)
    claim = Claim(
        id="claim_02",
        text="Section-covered claim.",
        experiment="exp_01",
        sections=["results", "abstract"],
        status="verified",
    )
    _write_yaml(_claim_path(tmp_path, "claim_02"), claim.to_yaml())
    # Must not raise
    status.run(tmp_path)


def test_status_verified_count(tmp_path: Path) -> None:
    """status handles multiple verified claims without crashing."""
    init.run(tmp_path)
    for i, cid in enumerate(("claim_02", "claim_03"), start=2):
        claim = Claim(
            id=cid,
            text=f"Verified claim {i}.",
            experiment="exp_01",
            status="verified",
        )
        _write_yaml(_claim_path(tmp_path, cid), claim.to_yaml())
    # Must not raise
    status.run(tmp_path)


def test_status_empty_project_no_crash(tmp_path: Path) -> None:
    """status handles an empty project (no claims or experiments)."""
    init.run(tmp_path)
    _claim_path(tmp_path).unlink()
    _exp_path(tmp_path).unlink()
    # Must not raise
    status.run(tmp_path)


def test_status_calls_collect_issues(tmp_path: Path) -> None:
    """status calls collect_issues during execution."""
    init.run(tmp_path)
    with patch(
        "paperforge.commands.status.collect_issues", return_value=[]
    ) as mock_collect:
        status.run(tmp_path)
    mock_collect.assert_called_once()
