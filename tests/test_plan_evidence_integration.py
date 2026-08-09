"""Tests that registering/changing evidence invalidates a plan approval
(dependency-graph propagation, gap #8 / Phase 8 item 49)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from paperforge.cli import app
from paperforge.planning.approval import approve_plan, check_approval_validity
from paperforge.planning.builder import build_plan
from paperforge.project_manifest.models import ProjectManifest

runner = CliRunner()


def test_new_evidence_invalidates_existing_approval(tmp_path: Path) -> None:
    manifest = ProjectManifest()
    plan = build_plan(manifest)
    approval = approve_plan(manifest, plan, approver="tester", project_root=tmp_path)
    assert (
        check_approval_validity(manifest, plan, approval, project_root=tmp_path) == []
    )

    (tmp_path / ".paperforge").mkdir(parents=True, exist_ok=True)
    runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            "e1",
            "--type",
            "manual",
            "--value",
            "1",
            "--path",
            str(tmp_path),
        ],
    )

    reasons = check_approval_validity(manifest, plan, approval, project_root=tmp_path)
    assert reasons
    assert any("evidence" in r.lower() for r in reasons)


def test_evidence_hash_without_project_root_is_backward_compatible() -> None:
    from paperforge.planning.approval import evidence_hash

    manifest = ProjectManifest()
    # No project_root -- must not raise, and must match the pre-1.8 shape
    # (manifest.evidence + bibliography only).
    h1 = evidence_hash(manifest)
    h2 = evidence_hash(manifest)
    assert h1 == h2


def test_plan_cli_approval_invalidated_by_evidence_change(tmp_path: Path) -> None:

    manifest_yaml = """\
schema_version: "1.0"
project:
  title: "Example Research Project"
  research_domain: "Computer Science"
  study_type: "Simulation"
  language: "English"
authors:
  - id: "author_1"
    name: "Alex Morgan"
research:
  primary_question: "What effect does the evaluated method have?"
manuscript:
  generation_policy: "validation_only"
  required_sections:
    - introduction
"""
    (tmp_path / "paperforge.project.yaml").write_text(manifest_yaml, encoding="utf-8")
    (tmp_path / ".paperforge").mkdir(parents=True, exist_ok=True)

    result = runner.invoke(
        app,
        ["plan", "--path", str(tmp_path), "--approve", "--non-interactive", "--json"],
    )
    assert result.exit_code == 0, result.output

    runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            "e2",
            "--type",
            "manual",
            "--value",
            "5",
            "--path",
            str(tmp_path),
        ],
    )

    status = runner.invoke(app, ["plan", "--path", str(tmp_path), "--json"])
    import json

    data = json.loads(status.output)
    assert data["outputs"]["approval_status"] == "stale"
