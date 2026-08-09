"""End-to-end tests for `paperforge evidence ...` via the Typer CLI."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from paperforge.cli import app

runner = CliRunner()


def _init(tmp_path: Path) -> None:
    (tmp_path / ".paperforge").mkdir(parents=True, exist_ok=True)


def test_direct_add_manual_and_show(tmp_path: Path) -> None:
    _init(tmp_path)
    result = runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            "sample_count",
            "--type",
            "manual",
            "--value",
            "42",
            "--value-type",
            "number",
            "--unit",
            "count",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output

    show = runner.invoke(app, ["evidence", "show", "--json", "--path", str(tmp_path)])
    data = json.loads(show.output)
    assert data["outputs"]["total"] == 1
    assert data["outputs"]["evidence"]["direct"][0]["id"] == "sample_count"


def test_direct_add_csv(tmp_path: Path) -> None:
    _init(tmp_path)
    (tmp_path / "latency.csv").write_text(
        "run,latency_ms\n0,120.5\n1,80.2\n", encoding="utf-8"
    )

    result = runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            "baseline_latency",
            "--type",
            "csv",
            "--source-path",
            "latency.csv",
            "--source-locator",
            "row=0;col=latency_ms",
            "--unit",
            "ms",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "120.5" in result.output


def test_direct_add_duplicate_id_rejected(tmp_path: Path) -> None:
    _init(tmp_path)
    runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            "x",
            "--type",
            "manual",
            "--value",
            "1",
            "--path",
            str(tmp_path),
        ],
    )
    result = runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            "x",
            "--type",
            "manual",
            "--value",
            "2",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_derived_add_percentage_reduction(tmp_path: Path) -> None:
    _init(tmp_path)
    (tmp_path / "latency.csv").write_text(
        "run,latency_ms\n0,120.5\n1,80.2\n", encoding="utf-8"
    )
    runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            "baseline",
            "--type",
            "csv",
            "--source-path",
            "latency.csv",
            "--source-locator",
            "row=0;col=latency_ms",
            "--unit",
            "ms",
            "--path",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            "adaptive",
            "--type",
            "csv",
            "--source-path",
            "latency.csv",
            "--source-locator",
            "row=1;col=latency_ms",
            "--unit",
            "ms",
            "--path",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        [
            "evidence",
            "derived",
            "add",
            "--id",
            "latency_reduction",
            "--formula",
            "(baseline - adaptive) / baseline * 100",
            "--operands",
            "baseline,adaptive",
            "--unit",
            "percent",
            "--precision",
            "2",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "33.44" in result.output


def test_derived_add_rejects_injection_formula(tmp_path: Path) -> None:
    _init(tmp_path)
    result = runner.invoke(
        app,
        [
            "evidence",
            "derived",
            "add",
            "--id",
            "bad",
            "--formula",
            "__import__('os')",
            "--operands",
            "",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0


def test_evidence_graph_reports_cycle_from_tampered_state(tmp_path: Path) -> None:
    import yaml

    _init(tmp_path)
    edir = tmp_path / ".paperforge" / "evidence"
    edir.mkdir(parents=True)
    (edir / "derived.yaml").write_text(
        yaml.safe_dump(
            [
                {"id": "x", "formula": "y + 1", "operand_ids": ["y"], "result": 1.0},
                {"id": "y", "formula": "x + 1", "operand_ids": ["x"], "result": 1.0},
            ]
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        app, ["evidence", "graph", "--json", "--path", str(tmp_path)]
    )
    data = json.loads(result.output)
    assert data["outputs"]["cycles"]
    assert result.exit_code != 0


def test_statistical_add_valid(tmp_path: Path) -> None:
    _init(tmp_path)
    result = runner.invoke(
        app,
        [
            "evidence",
            "statistical",
            "add",
            "--id",
            "stat_1",
            "--test-name",
            "paired_t_test",
            "--statistic",
            "-2.5",
            "--p-value",
            "0.03",
            "--sample-size",
            "30",
            "--paired",
            "--alpha",
            "0.05",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output


def test_statistical_add_invalid_p_value_rejected(tmp_path: Path) -> None:
    _init(tmp_path)
    result = runner.invoke(
        app,
        [
            "evidence",
            "statistical",
            "add",
            "--id",
            "stat_bad",
            "--test-name",
            "t",
            "--p-value",
            "1.5",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0


def test_evidence_validate_json_envelope_shape(tmp_path: Path) -> None:
    _init(tmp_path)
    runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            "x",
            "--type",
            "manual",
            "--value",
            "1",
            "--path",
            str(tmp_path),
        ],
    )
    result = runner.invoke(
        app, ["evidence", "validate", "--json", "--path", str(tmp_path)]
    )
    data = json.loads(result.output)
    assert data["command"] == "evidence validate"
    assert data["status"] == "success"
    assert result.exit_code == 0
