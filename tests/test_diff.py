"""Tests for the paperforge diff command."""

from pathlib import Path

import pytest
import yaml

from paperforge.commands import diff, init
from paperforge.history import record_snapshot
from paperforge.models.experiment import Experiment


def test_diff_fails_without_init(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        diff.run("claim_01", tmp_path, "previous")
    assert exc_info.value.code == 1


def test_diff_fails_unknown_claim(tmp_path: Path) -> None:
    init.run(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        diff.run("claim_99", tmp_path, "previous")
    assert exc_info.value.code == 1


def test_diff_previous_no_history_exits_0(tmp_path: Path) -> None:
    init.run(tmp_path)
    diff.run("claim_01", tmp_path, "previous")


def test_diff_previous_shows_changes(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    record_snapshot(
        pf_dir,
        "claim_01",
        {
            "id": "claim_01",
            "text": "old version",
            "status": "unverified",
            "experiment": "",
            "sections": [],
            "figures": [],
            "tables": [],
            "citations": [],
            "last_verified": None,
        },
        "capture",
    )

    claim_path = pf_dir / "claims" / "claim_01.yaml"
    data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    data["text"] = "new version"
    claim_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    diff.run("claim_01", tmp_path, "previous")


def test_diff_previous_no_changes(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    claim_path = pf_dir / "claims" / "claim_01.yaml"
    data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    record_snapshot(pf_dir, "claim_01", data, "capture")

    diff.run("claim_01", tmp_path, "previous")


def test_diff_experiment_no_linked_experiment(tmp_path: Path) -> None:
    init.run(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        diff.run("claim_01", tmp_path, "experiment")
    assert exc_info.value.code == 1


def test_diff_experiment_no_percentages(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    exp_path = pf_dir / "experiments" / "exp_01.yaml"
    experiment = Experiment(id="exp_01", metrics={"accuracy": 98.4})
    exp_path.write_text(
        yaml.dump(experiment.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    claim_path = pf_dir / "claims" / "claim_01.yaml"
    data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    data["text"] = "no percentages here"
    data["experiment"] = "exp_01"
    claim_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    diff.run("claim_01", tmp_path, "experiment")


def test_diff_unknown_against_exits(tmp_path: Path) -> None:
    init.run(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        diff.run("claim_01", tmp_path, "invalid")
    assert exc_info.value.code == 1
