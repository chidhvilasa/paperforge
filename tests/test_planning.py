"""Tests for paperforge.planning: plan builder, approval hashing/invalidation,
and the `paperforge plan` CLI."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from paperforge.cli import app
from paperforge.planning.approval import approve_plan, check_approval_validity
from paperforge.planning.builder import build_plan
from paperforge.project_manifest.models import ClaimEntry, ProjectManifest

runner = CliRunner()

BASE_MANIFEST = """\
schema_version: "1.0"
project:
  title: "Example Research Project"
  research_domain: "Computer Science"
  study_type: "Simulation"
  language: "English"
  target_venue: "generic"
authors:
  - id: "author_1"
    name: "Alex Morgan"
research:
  primary_question: "What effect does the evaluated method have?"
  secondary_questions:
    - "Does the effect hold across all conditions?"
manuscript:
  generation_policy: "validation_only"
  required_sections:
    - introduction
    - methodology
    - results
    - discussion
"""


def _manifest(yaml_text: str = BASE_MANIFEST) -> ProjectManifest:
    return ProjectManifest.from_dict(yaml.safe_load(yaml_text))


def test_build_plan_uses_required_sections_when_no_explicit_order() -> None:
    m = _manifest()
    plan = build_plan(m)
    assert [s.name for s in plan.sections] == [
        "introduction",
        "methodology",
        "results",
        "discussion",
    ]
    assert plan.validation_gates == [
        "doctor",
        "build",
        "preflight",
        "references",
        "provenance.validate",
    ]


def test_build_plan_never_contains_prose() -> None:
    m = _manifest()
    plan = build_plan(m)
    md = plan.to_markdown()
    assert "prose" in md.lower()  # the plan explicitly says so
    for s in plan.sections:
        assert s.purpose  # purpose is a short description, not a paragraph of prose


def test_build_plan_routes_result_claims_to_results_section() -> None:
    m = _manifest()
    m.claims.append(
        ClaimEntry(
            id="c1",
            text="x",
            evidence_class="DIRECT_RESULT",
            evidence_refs=["results/data.csv"],
        )
    )
    plan = build_plan(m)
    results = next(s for s in plan.sections if s.name == "results")
    assert "c1" in results.claim_ids
    assert "results/data.csv" in results.evidence_refs


def test_build_plan_prohibits_placeholder_claims() -> None:
    m = _manifest()
    m.claims.append(ClaimEntry(id="c1", text="TBD", evidence_class="PLACEHOLDER"))
    plan = build_plan(m)
    assert "c1" in plan.prohibited_claims
    assert all("c1" not in s.claim_ids for s in plan.sections)


def test_build_plan_unresolved_questions_include_secondary_questions() -> None:
    m = _manifest()
    plan = build_plan(m)
    assert any("Does the effect hold" in q for q in plan.unresolved_questions)


def test_build_plan_venue_constraints_reflect_manuscript_config() -> None:
    m = _manifest()
    m.manuscript.abstract_limit = 250
    plan = build_plan(m)
    assert plan.venue_constraints["abstract_limit"] == 250
    assert plan.venue_constraints["target_venue"] == "generic"


def test_plan_hash_stable_across_rebuilds() -> None:
    from paperforge.planning.approval import plan_hash

    m = _manifest()
    plan1 = build_plan(m)
    plan2 = build_plan(m)
    # Timestamps may coincide or differ between the two builds; plan_hash
    # excludes generated_at, so equality must hold either way.
    assert plan_hash(plan1) == plan_hash(plan2)


def test_approval_valid_immediately_after_approving() -> None:
    m = _manifest()
    plan = build_plan(m)
    approval = approve_plan(m, plan, approver="tester", mode="submission")
    assert check_approval_validity(m, plan, approval) == []


def test_approval_invalidated_by_manifest_change() -> None:
    m = _manifest()
    plan = build_plan(m)
    approval = approve_plan(m, plan, approver="tester")
    m.project.title = "A Different Title"
    reasons = check_approval_validity(m, plan, approval)
    assert any("manifest has changed" in r for r in reasons)


def test_approval_invalidated_by_claim_change() -> None:
    m = _manifest()
    plan = build_plan(m)
    approval = approve_plan(m, plan, approver="tester")
    m.claims.append(ClaimEntry(id="c1", text="new", evidence_class="AUTHOR_ASSERTED"))
    reasons = check_approval_validity(m, plan, approval)
    assert any("claim set" in r for r in reasons)


def test_approval_invalidated_by_venue_change() -> None:
    m = _manifest()
    plan = build_plan(m)
    approval = approve_plan(m, plan, approver="tester")
    m.project.target_venue = "ieee"
    reasons = check_approval_validity(m, plan, approval)
    assert any("venue" in r.lower() for r in reasons)


def test_approval_invalidated_by_evidence_change() -> None:
    m = _manifest()
    plan = build_plan(m)
    approval = approve_plan(m, plan, approver="tester")
    m.evidence.raw_data.append("new_data.csv")
    reasons = check_approval_validity(m, plan, approval)
    assert any("evidence inventory" in r for r in reasons)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_plan_writes_files(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    result = runner.invoke(app, ["plan", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".paperforge" / "generation_plan.md").exists()
    assert (tmp_path / ".paperforge" / "generation_plan.json").exists()


def test_cli_plan_approve_then_valid(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    result = runner.invoke(
        app,
        ["plan", "--path", str(tmp_path), "--approve", "--non-interactive", "--json"],
    )
    payload = json.loads(result.stdout)
    assert payload["outputs"]["approved"] is True
    assert (tmp_path / ".paperforge" / "plan_approval.json").exists()

    result2 = runner.invoke(app, ["plan", "--path", str(tmp_path), "--json"])
    payload2 = json.loads(result2.stdout)
    assert payload2["outputs"]["approval_status"] == "valid"


def test_cli_plan_approval_goes_stale_after_manifest_edit(tmp_path: Path) -> None:
    manifest_path = tmp_path / "paperforge.project.yaml"
    manifest_path.write_text(BASE_MANIFEST, encoding="utf-8")
    runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--approve", "--non-interactive"]
    )

    data = yaml.safe_load(BASE_MANIFEST)
    data["project"]["title"] = "Changed Title"
    manifest_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    result = runner.invoke(app, ["plan", "--path", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["outputs"]["approval_status"] == "stale"
    assert payload["outputs"]["approval_stale_reasons"]


def test_cli_plan_revoke_approval(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--approve", "--non-interactive"]
    )
    assert (tmp_path / ".paperforge" / "plan_approval.json").exists()

    result = runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--revoke-approval", "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["outputs"]["approval_revoked"] is True
    assert not (tmp_path / ".paperforge" / "plan_approval.json").exists()


def test_cli_plan_approve_refuses_structurally_invalid_manifest(tmp_path: Path) -> None:
    broken = yaml.safe_load(BASE_MANIFEST)
    del broken["project"]["title"]
    (tmp_path / "paperforge.project.yaml").write_text(
        yaml.safe_dump(broken), encoding="utf-8"
    )
    result = runner.invoke(
        app,
        ["plan", "--path", str(tmp_path), "--approve", "--non-interactive", "--json"],
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["exit_code"] == 20  # EXIT_MISSING_STRUCTURAL_REQUIREMENT


def test_cli_plan_missing_manifest(tmp_path: Path) -> None:
    result = runner.invoke(app, ["plan", "--path", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["errors"][0]["code"] == "MANIFEST_NOT_FOUND"


def test_cli_plan_section_filter(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    result = runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--section", "results", "--json"]
    )
    payload = json.loads(result.stdout)
    assert [s["name"] for s in payload["outputs"]["plan"]["sections"]] == ["results"]
