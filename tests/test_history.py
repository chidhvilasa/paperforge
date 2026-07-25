"""Tests for the paperforge.history module."""

from pathlib import Path

import yaml

from paperforge.commands import doctor, init
from paperforge.history import (
    ClaimSnapshot,
    diff_snapshots,
    load_history,
    record_snapshot,
)
from paperforge.models.claim import Claim


def test_record_snapshot_creates_history_dir(tmp_path: Path) -> None:
    record_snapshot(
        tmp_path / ".paperforge",
        "claim_01",
        {"id": "claim_01", "text": "test"},
        "paperforge capture",
    )
    assert (tmp_path / ".paperforge" / "history").is_dir()


def test_record_snapshot_creates_history_file(tmp_path: Path) -> None:
    record_snapshot(
        tmp_path / ".paperforge",
        "claim_01",
        {"id": "claim_01", "text": "test"},
        "paperforge capture",
    )
    assert (tmp_path / ".paperforge" / "history" / "claim_01.yaml").exists()


def test_record_snapshot_appends(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    record_snapshot(pf_dir, "claim_01", {"text": "first"}, "paperforge capture")
    record_snapshot(pf_dir, "claim_01", {"text": "second"}, "paperforge capture")

    path = pf_dir / "history" / "claim_01.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert len(data) == 2


def test_load_history_empty_when_no_file(tmp_path: Path) -> None:
    result = load_history(tmp_path / ".paperforge", "claim_99")
    assert result == []


def test_load_history_returns_newest_first(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    record_snapshot(pf_dir, "claim_01", {"text": "first"}, "capture")
    record_snapshot(pf_dir, "claim_01", {"text": "second"}, "capture")

    snapshots = load_history(pf_dir, "claim_01")

    assert snapshots[0].snapshot["text"] == "second"
    assert snapshots[1].snapshot["text"] == "first"


def test_load_history_returns_claim_snapshots(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    record_snapshot(
        pf_dir,
        "claim_01",
        {"id": "claim_01", "text": "v1", "status": "unverified"},
        "paperforge capture",
    )

    snapshots = load_history(pf_dir, "claim_01")

    assert len(snapshots) == 1
    assert isinstance(snapshots[0], ClaimSnapshot)
    assert snapshots[0].recorded_by == "paperforge capture"


def test_diff_snapshots_detects_text_change() -> None:
    old = {"text": "98.4% accuracy", "status": "unverified"}
    new = {"text": "97.8% accuracy", "status": "unverified"}

    changes = diff_snapshots(old, new)

    assert "text" in changes
    assert "status" not in changes


def test_diff_snapshots_detects_status_change() -> None:
    old = {"text": "same", "status": "unverified"}
    new = {"text": "same", "status": "verified"}

    changes = diff_snapshots(old, new)

    assert "status" in changes
    assert changes["status"] == ("unverified", "verified")


def test_diff_snapshots_empty_when_identical() -> None:
    data = {"text": "same", "status": "unverified"}
    changes = diff_snapshots(data, data.copy())
    assert changes == {}


def test_diff_snapshots_handles_new_field() -> None:
    old = {"text": "x"}
    new = {"text": "x", "experiment": "exp_01"}

    changes = diff_snapshots(old, new)

    assert "experiment" in changes
    assert changes["experiment"] == (None, "exp_01")


def test_capture_records_snapshot_on_update(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    claim_path = pf_dir / "claims" / "claim_02.yaml"
    claim = Claim(id="claim_02", text="first version", experiment="exp_01")
    claim_path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    current_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    record_snapshot(pf_dir, "claim_02", current_data, "paperforge capture")

    history_file = pf_dir / "history" / "claim_02.yaml"
    assert history_file.exists()
    snapshots = load_history(pf_dir, "claim_02")
    assert len(snapshots) == 1
    assert snapshots[0].snapshot["text"] == "first version"


def test_doctor_fix_records_snapshot(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    claim_path = pf_dir / "claims" / "claim_01.yaml"
    claim = Claim(
        id="claim_01",
        text="A claim awaiting verification.",
        experiment="exp_01",
        sections=["results"],
        status="unverified",
    )
    claim_path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    doctor.run(tmp_path, fix=True)

    history_file = pf_dir / "history" / "claim_01.yaml"
    assert history_file.exists()
    snapshots = load_history(pf_dir, "claim_01")
    assert len(snapshots) >= 1
    assert snapshots[0].recorded_by == "paperforge doctor --fix"
