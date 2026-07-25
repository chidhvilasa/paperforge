"""Tests for the paperforge capture command."""

import json
from pathlib import Path

import pytest
import yaml

from paperforge.commands import capture, init
from paperforge.models.experiment import Experiment


def _experiment_data(tmp_path: Path, experiment_id: str) -> dict:
    exp_path = tmp_path / ".paperforge" / "experiments" / f"{experiment_id}.yaml"
    return yaml.safe_load(exp_path.read_text(encoding="utf-8"))


def test_capture_flat_json(tmp_path: Path) -> None:
    init.run(tmp_path)
    metrics_json = tmp_path / "metrics.json"
    metrics_json.write_text(
        json.dumps({"accuracy": 98.4, "precision": 97.1}), encoding="utf-8"
    )

    capture.run(results=metrics_json, experiment_id="exp_01", project_root=tmp_path)

    data = _experiment_data(tmp_path, "exp_01")
    assert data["metrics"]["accuracy"] == 98.4


def test_capture_nested_json(tmp_path: Path) -> None:
    init.run(tmp_path)
    metrics_json = tmp_path / "metrics.json"
    metrics_json.write_text(
        json.dumps({"metrics": {"f1": 0.95}, "params": {"seed": 42}}),
        encoding="utf-8",
    )

    capture.run(results=metrics_json, experiment_id="exp_01", project_root=tmp_path)

    data = _experiment_data(tmp_path, "exp_01")
    assert data["metrics"]["f1"] == 0.95
    assert "seed" not in data["metrics"]


def test_capture_creates_experiment_file(tmp_path: Path) -> None:
    init.run(tmp_path)
    metrics_json = tmp_path / "metrics.json"
    metrics_json.write_text(json.dumps({"accuracy": 90.0}), encoding="utf-8")

    capture.run(results=metrics_json, experiment_id="exp_99", project_root=tmp_path)

    assert (tmp_path / ".paperforge" / "experiments" / "exp_99.yaml").exists()


def test_capture_updates_existing_experiment(tmp_path: Path) -> None:
    init.run(tmp_path)
    exp_path = tmp_path / ".paperforge" / "experiments" / "exp_01.yaml"
    existing = Experiment(id="exp_01", metrics={"accuracy": 90.0, "precision": 88.0})
    exp_path.write_text(
        yaml.dump(existing.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    metrics_json = tmp_path / "metrics.json"
    metrics_json.write_text(
        json.dumps({"accuracy": 98.4, "recall": 97.0}), encoding="utf-8"
    )

    capture.run(results=metrics_json, experiment_id="exp_01", project_root=tmp_path)

    data = _experiment_data(tmp_path, "exp_01")
    assert data["metrics"]["accuracy"] == 98.4
    assert data["metrics"]["precision"] == 88.0
    assert data["metrics"]["recall"] == 97.0


def test_capture_creates_claim_file(tmp_path: Path) -> None:
    init.run(tmp_path)
    metrics_json = tmp_path / "metrics.json"
    metrics_json.write_text(json.dumps({"accuracy": 90.0}), encoding="utf-8")

    capture.run(results=metrics_json, experiment_id="exp_01", project_root=tmp_path)

    claim_path = tmp_path / ".paperforge" / "claims" / "claim_02.yaml"
    assert claim_path.exists()
    data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert data["experiment"] == "exp_01"
    assert data["status"] == "unverified"
    assert data["text"] == ""


def test_capture_claim_id_increments(tmp_path: Path) -> None:
    init.run(tmp_path)
    claims_dir = tmp_path / ".paperforge" / "claims"
    for n in range(1, 6):
        (claims_dir / f"claim_{n:02d}.yaml").write_text(
            f"id: claim_{n:02d}\ntext: x\nexperiment: exp_01\n", encoding="utf-8"
        )

    metrics_json = tmp_path / "metrics.json"
    metrics_json.write_text(json.dumps({"accuracy": 90.0}), encoding="utf-8")

    capture.run(results=metrics_json, experiment_id="exp_01", project_root=tmp_path)

    assert (claims_dir / "claim_06.yaml").exists()


def test_capture_drops_non_numeric_metrics(tmp_path: Path) -> None:
    init.run(tmp_path)
    metrics_json = tmp_path / "metrics.json"
    metrics_json.write_text(
        json.dumps({"accuracy": 98.4, "model": "ResNet", "epochs": 50}),
        encoding="utf-8",
    )

    capture.run(results=metrics_json, experiment_id="exp_01", project_root=tmp_path)

    data = _experiment_data(tmp_path, "exp_01")
    assert "model" not in data["metrics"]
    assert data["metrics"]["accuracy"] == 98.4
    assert data["metrics"]["epochs"] == 50


def test_capture_fails_missing_json(tmp_path: Path) -> None:
    init.run(tmp_path)
    missing = tmp_path / "does_not_exist.json"

    with pytest.raises(SystemExit) as exc_info:
        capture.run(results=missing, experiment_id="exp_01", project_root=tmp_path)
    assert exc_info.value.code == 1


def test_capture_fails_invalid_json(tmp_path: Path) -> None:
    init.run(tmp_path)
    metrics_json = tmp_path / "metrics.json"
    metrics_json.write_text("not json at all", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        capture.run(results=metrics_json, experiment_id="exp_01", project_root=tmp_path)
    assert exc_info.value.code == 1


def test_capture_fails_experiment_id_with_spaces(tmp_path: Path) -> None:
    init.run(tmp_path)
    metrics_json = tmp_path / "metrics.json"
    metrics_json.write_text(json.dumps({"accuracy": 90.0}), encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        capture.run(results=metrics_json, experiment_id="exp 27", project_root=tmp_path)
    assert exc_info.value.code == 1
