"""Tests for `paperforge references --json`."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from paperforge.cli import app
from paperforge.commands import init

runner = CliRunner()


def test_references_json_envelope_on_fresh_project(tmp_path: Path) -> None:
    init.run(tmp_path)
    result = runner.invoke(app, ["references", "--path", str(tmp_path), "--json"])
    assert result.exit_code in (0, 60)  # success or EXIT_REFERENCES_ERROR
    payload = json.loads(result.stdout)
    assert payload["command"] == "references"
    assert "report" in payload["outputs"]
    assert "total_citations" in payload["outputs"]["report"]


def test_references_console_output_unchanged(tmp_path: Path) -> None:
    init.run(tmp_path)
    result = runner.invoke(app, ["references", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Reference verification complete" in result.stdout
