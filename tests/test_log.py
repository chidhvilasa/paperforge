"""Tests for the paperforge log command."""

from pathlib import Path

import pytest

from paperforge.commands import init, log_cmd
from paperforge.history import record_snapshot


def test_log_fails_without_init(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        log_cmd.run("claim_01", tmp_path, limit=10)
    assert exc_info.value.code == 1


def test_log_fails_unknown_claim(tmp_path: Path) -> None:
    init.run(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        log_cmd.run("claim_99", tmp_path, limit=10)
    assert exc_info.value.code == 1


def test_log_no_history_exits_0(tmp_path: Path) -> None:
    init.run(tmp_path)
    log_cmd.run("claim_01", tmp_path, limit=10)


def test_log_shows_history(tmp_path: Path) -> None:
    init.run(tmp_path)
    record_snapshot(
        tmp_path / ".paperforge",
        "claim_01",
        {
            "id": "claim_01",
            "text": "old text",
            "status": "unverified",
            "experiment": "",
            "sections": [],
            "figures": [],
            "tables": [],
            "citations": [],
            "last_verified": None,
        },
        "paperforge capture",
    )
    log_cmd.run("claim_01", tmp_path, limit=10)


def test_log_limit_respected(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    for i in range(5):
        record_snapshot(
            pf_dir,
            "claim_01",
            {"id": "claim_01", "text": f"version {i}"},
            "paperforge capture",
        )
    log_cmd.run("claim_01", tmp_path, limit=3)


def test_log_shows_diff_between_snapshots(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    record_snapshot(
        pf_dir, "claim_01", {"id": "claim_01", "text": "first"}, "paperforge capture"
    )
    record_snapshot(
        pf_dir, "claim_01", {"id": "claim_01", "text": "second"}, "paperforge capture"
    )
    log_cmd.run("claim_01", tmp_path, limit=10)
