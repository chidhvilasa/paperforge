"""CLI-level tests for `paperforge manifest schema|validate|migrate`."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from paperforge.cli import app

runner = CliRunner()

MINIMAL_VALID = """\
schema_version: "1.0"
project:
  title: "Example Research Project"
  research_domain: "Computer Science"
  study_type: "Experimental"
  language: "English"
authors:
  - id: "author_1"
    name: "Alex Morgan"
research:
  primary_question: "What effect does the evaluated method have?"
manuscript:
  generation_policy: "validation_only"
  required_sections:
    - abstract
    - introduction
"""

LEGACY_0_1 = """\
schema_version: "0.1"
title: "A Legacy-Format Study"
research_domain: "Biology"
study_type: "Observational"
author_name: "Sam Rivera"
primary_question: "Does the intervention change the outcome?"
"""


def test_manifest_schema_console() -> None:
    result = runner.invoke(app, ["manifest", "schema"])
    assert result.exit_code == 0
    assert '"PaperForge canonical project manifest"' in result.stdout


def test_manifest_schema_json_envelope() -> None:
    result = runner.invoke(app, ["manifest", "schema", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "manifest.schema"
    assert payload["status"] == "success"
    assert "properties" in payload["outputs"]["schema"]


def test_manifest_schema_output_file(tmp_path: Path) -> None:
    out = tmp_path / "schema.json"
    result = runner.invoke(app, ["manifest", "schema", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8"))["type"] == "object"


def test_manifest_validate_draft_success(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    p.write_text(MINIMAL_VALID, encoding="utf-8")
    result = runner.invoke(app, ["manifest", "validate", str(p), "--mode", "draft"])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_manifest_validate_json_envelope_and_exit_code(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    data = MINIMAL_VALID.replace('title: "Example Research Project"', "")
    p.write_text(data, encoding="utf-8")
    result = runner.invoke(
        app, ["manifest", "validate", str(p), "--mode", "submission", "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["command"] == "manifest.validate"
    assert payload["status"] == "failure"
    assert payload["exit_code"] == 21  # EXIT_SUBMISSION_BLOCKER
    assert result.exit_code == 21
    assert any(e["code"] == "MISSING_TITLE" for e in payload["errors"])


def test_manifest_validate_rejects_unsafe_manifest(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    p.write_text("root: &a\n  self: *a\n", encoding="utf-8")
    result = runner.invoke(app, ["manifest", "validate", str(p), "--json"])
    payload = json.loads(result.stdout)
    assert payload["exit_code"] == 30  # EXIT_UNSAFE_MANIFEST_OR_PATH
    assert payload["errors"][0]["code"] == "YAML_RECURSIVE_ALIAS"


def test_manifest_validate_missing_file(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["manifest", "validate", str(tmp_path / "nope.yaml"), "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["exit_code"] == 10  # EXIT_INVALID_MANIFEST


def test_manifest_validate_future_schema_version(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    p.write_text('schema_version: "9.9"\n', encoding="utf-8")
    result = runner.invoke(app, ["manifest", "validate", str(p), "--json"])
    payload = json.loads(result.stdout)
    assert payload["exit_code"] == 11  # EXIT_UNSUPPORTED_SCHEMA_VERSION


def test_manifest_validate_requires_migration(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    p.write_text(LEGACY_0_1, encoding="utf-8")
    result = runner.invoke(app, ["manifest", "validate", str(p), "--json"])
    payload = json.loads(result.stdout)
    assert payload["exit_code"] == 12  # EXIT_MIGRATION_REQUIRED


def test_manifest_validate_invalid_mode() -> None:
    result = runner.invoke(
        app, ["manifest", "validate", "x.yaml", "--mode", "bogus", "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["exit_code"] == 2  # EXIT_CLI_MISUSE


def test_manifest_migrate_dry_run(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    p.write_text(LEGACY_0_1, encoding="utf-8")
    original = p.read_bytes()
    result = runner.invoke(
        app, ["manifest", "migrate", "--input", str(p), "--dry-run", "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["outputs"]["dry_run"] is True
    assert payload["outputs"]["report"]["changed"] is True
    assert p.read_bytes() == original


def test_manifest_migrate_writes_and_yes_skips_prompt(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    p.write_text(LEGACY_0_1, encoding="utf-8")
    result = runner.invoke(
        app, ["manifest", "migrate", "--input", str(p), "--yes", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["outputs"]["report"]["target_version"] == "1.0"
    import yaml as yaml_module

    migrated = yaml_module.safe_load(p.read_text(encoding="utf-8"))
    assert migrated["schema_version"] == "1.0"


def test_manifest_migrate_already_current(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    p.write_text(MINIMAL_VALID, encoding="utf-8")
    result = runner.invoke(
        app, ["manifest", "migrate", "--input", str(p), "--yes", "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert "already at the current" in payload["outputs"]["message"]


def test_example_fixtures_validate_cleanly() -> None:
    """The example manifests shipped under examples/ must themselves be
    valid, since they double as documentation."""
    from pathlib import Path as _Path

    repo_root = _Path(__file__).resolve().parents[1]
    for name in ("minimal_project", "complete_project"):
        fixture = repo_root / "examples" / name / "paperforge.project.yaml"
        result = runner.invoke(
            app, ["manifest", "validate", str(fixture), "--mode", "draft", "--json"]
        )
        payload = json.loads(result.stdout)
        assert payload["status"] in {"success", "warning"}, (name, payload["errors"])
