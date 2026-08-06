"""Tests for the mode-aware requirements engine."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from paperforge.cli import app
from paperforge.project_manifest.models import ClaimEntry, ProjectManifest
from paperforge.requirements_engine.engine import evaluate_requirements

runner = CliRunner()

BASE_MANIFEST = """\
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


def _manifest(yaml_text: str) -> ProjectManifest:
    return ProjectManifest.from_dict(yaml.safe_load(yaml_text))


def test_abstract_missing_blocks_submission_not_draft() -> None:
    m = _manifest(BASE_MANIFEST)
    reqs = evaluate_requirements(m, mode="submission")
    abstract = next(r for r in reqs if r.id == "REQ-ABSTRACT")
    assert abstract.status == "MISSING"
    assert abstract.blocks("submission")
    assert not abstract.blocks("draft")
    assert not abstract.blocks("outline")


def test_abstract_present_satisfies() -> None:
    m = _manifest(
        BASE_MANIFEST.replace("- introduction", "- abstract\n    - introduction")
    )
    reqs = evaluate_requirements(m, mode="submission")
    abstract = next(r for r in reqs if r.id == "REQ-ABSTRACT")
    assert abstract.status == "PROVIDED"
    assert not abstract.blocks("submission")


def test_bibliography_not_applicable_without_citations() -> None:
    m = _manifest(BASE_MANIFEST)
    reqs = evaluate_requirements(m, mode="submission")
    bib = next(r for r in reqs if r.id == "REQ-BIBLIOGRAPHY")
    assert bib.status == "NOT_APPLICABLE"
    assert not bib.required
    assert not bib.blocks("submission")


def test_bibliography_required_when_claim_has_citations() -> None:
    m = _manifest(BASE_MANIFEST)
    m.claims.append(
        ClaimEntry(
            id="c1",
            text="x",
            evidence_class="SOURCE_SUPPORTED",
            citation_keys=["smith2020"],
        )
    )
    reqs = evaluate_requirements(m, mode="submission")
    bib = next(r for r in reqs if r.id == "REQ-BIBLIOGRAPHY")
    assert bib.status == "MISSING"
    assert bib.required
    assert bib.blocks("submission")


def test_ethics_not_applicable_by_default() -> None:
    m = _manifest(BASE_MANIFEST)
    reqs = evaluate_requirements(m, mode="submission")
    ethics = next(r for r in reqs if r.id == "REQ-ETHICS-APPROVAL")
    assert ethics.status == "NOT_APPLICABLE"
    assert not ethics.blocks("submission")


def test_ethics_required_when_participants_present() -> None:
    m = _manifest(BASE_MANIFEST)
    m.methodology.participants = "42 undergraduate volunteers"
    reqs = evaluate_requirements(m, mode="submission")
    ethics = next(r for r in reqs if r.id == "REQ-ETHICS-APPROVAL")
    assert ethics.status == "MISSING"
    assert ethics.blocks("submission")

    m.declarations.ethics_approval = (
        "Approved by Example University IRB, protocol #123."
    )
    reqs2 = evaluate_requirements(m, mode="submission")
    ethics2 = next(r for r in reqs2 if r.id == "REQ-ETHICS-APPROVAL")
    assert ethics2.status == "PROVIDED"
    assert not ethics2.blocks("submission")


def test_no_external_funding_is_a_valid_complete_statement() -> None:
    m = _manifest(BASE_MANIFEST)
    m.declarations.funding = "This work received no external funding."
    reqs = evaluate_requirements(m, mode="submission")
    funding = next(r for r in reqs if r.id == "REQ-FUNDING-STATEMENT")
    assert funding.status == "PROVIDED"
    assert not funding.blocks("submission")


def test_missing_funding_statement_blocks_submission() -> None:
    m = _manifest(BASE_MANIFEST)
    reqs = evaluate_requirements(m, mode="submission")
    funding = next(r for r in reqs if r.id == "REQ-FUNDING-STATEMENT")
    assert funding.status == "MISSING"
    assert funding.blocks("submission")


def test_data_statement_required_even_when_data_cannot_be_shared() -> None:
    m = _manifest(BASE_MANIFEST)
    reqs_missing = evaluate_requirements(m, mode="submission")
    data_missing = next(r for r in reqs_missing if r.id == "REQ-DATA-AVAILABILITY")
    assert data_missing.status == "MISSING"
    assert data_missing.blocks("submission")

    m.declarations.data_availability = (
        "Data cannot be shared due to participant privacy agreements."
    )
    reqs_ok = evaluate_requirements(m, mode="submission")
    data_ok = next(r for r in reqs_ok if r.id == "REQ-DATA-AVAILABILITY")
    assert data_ok.status == "PROVIDED"
    assert not data_ok.blocks("submission")


def test_statistical_claim_requires_plan_and_evidence() -> None:

    m = _manifest(BASE_MANIFEST)
    m.claims.append(
        ClaimEntry(id="c1", text="p < 0.05", evidence_class="STATISTICAL_RESULT")
    )
    reqs = evaluate_requirements(m, mode="submission")
    plan = next(r for r in reqs if r.id == "REQ-STATISTICAL-PLAN")
    assert plan.status == "MISSING"
    assert plan.blocks("submission")
    evidence = next(r for r in reqs if r.id == "REQ-EVIDENCE-c1")
    assert evidence.status == "UNSUPPORTED"
    assert evidence.blocks("submission")
    assert evidence.author_review_required


def test_statistical_claim_with_plan_and_evidence_is_satisfied() -> None:

    m = _manifest(BASE_MANIFEST)
    m.methodology.statistical_plan = (
        "Two-sided Welch's t-test, alpha=0.05, Holm correction."
    )
    m.claims.append(
        ClaimEntry(
            id="c1",
            text="p < 0.05",
            evidence_class="STATISTICAL_RESULT",
            evidence_refs=["results/stats.csv"],
        )
    )
    reqs = evaluate_requirements(m, mode="submission")
    plan = next(r for r in reqs if r.id == "REQ-STATISTICAL-PLAN")
    assert plan.status == "PROVIDED"
    evidence = next(r for r in reqs if r.id == "REQ-EVIDENCE-c1")
    assert evidence.status == "PROVIDED"


def test_no_statistical_claims_means_no_statistical_plan_requirement() -> None:
    m = _manifest(BASE_MANIFEST)
    reqs = evaluate_requirements(m, mode="submission")
    assert not any(r.id == "REQ-STATISTICAL-PLAN" for r in reqs)


def test_orcid_optional_by_default() -> None:
    m = _manifest(BASE_MANIFEST)
    reqs = evaluate_requirements(m, mode="submission")
    orcid = next(r for r in reqs if r.id.startswith("REQ-ORCID-"))
    assert not orcid.required
    assert not orcid.blocks("submission")
    assert orcid.severity == "WARNING"


def test_biography_venue_required_for_ieee() -> None:
    m = _manifest(BASE_MANIFEST)
    m.project.target_venue = "ieee"
    reqs = evaluate_requirements(m, mode="submission")
    bio = next(r for r in reqs if r.id.startswith("REQ-BIOGRAPHY-"))
    assert bio.status == "MISSING"
    assert bio.venue_origin == "ieee"


def test_biography_not_required_for_generic_venue() -> None:
    m = _manifest(BASE_MANIFEST)
    m.project.target_venue = "generic"
    reqs = evaluate_requirements(m, mode="submission")
    assert not any(r.id.startswith("REQ-BIOGRAPHY-") for r in reqs)


def test_placeholder_claim_passes_draft_blocks_submission() -> None:

    m = _manifest(BASE_MANIFEST)
    m.claims.append(ClaimEntry(id="c1", text="TBD", evidence_class="PLACEHOLDER"))
    reqs_draft = evaluate_requirements(m, mode="draft")
    ph_draft = next(r for r in reqs_draft if r.id == "REQ-PLACEHOLDER-c1")
    assert not ph_draft.blocks("draft")

    reqs_submission = evaluate_requirements(m, mode="submission")
    ph_sub = next(r for r in reqs_submission if r.id == "REQ-PLACEHOLDER-c1")
    assert ph_sub.blocks("submission")


def test_conflicting_manifest_values_reported() -> None:
    """Statistical claims lacking a plan AND evidence should surface both
    problems distinctly, not silently collapse into one."""

    m = _manifest(BASE_MANIFEST)
    m.claims.append(ClaimEntry(id="c1", text="x", evidence_class="STATISTICAL_RESULT"))
    reqs = evaluate_requirements(m, mode="submission")
    ids = {r.id for r in reqs if r.blocks("submission")}
    assert "REQ-STATISTICAL-PLAN" in ids
    assert "REQ-EVIDENCE-c1" in ids


def test_evaluation_is_deterministically_ordered() -> None:
    m = _manifest(BASE_MANIFEST)
    reqs1 = [r.id for r in evaluate_requirements(m, mode="submission")]
    reqs2 = [r.id for r in evaluate_requirements(m, mode="submission")]
    assert reqs1 == reqs2
    assert reqs1 == sorted(reqs1)


def test_missing_bibliography_file_on_disk_is_inaccessible(tmp_path: Path) -> None:
    m = _manifest(BASE_MANIFEST)
    m.literature.bibliography = ["references.bib"]
    reqs = evaluate_requirements(m, project_root=tmp_path, mode="submission")
    file_req = next(r for r in reqs if r.id.startswith("REQ-BIBLIOGRAPHY-FILE-"))
    assert file_req.status == "INACCESSIBLE"
    assert file_req.blocks("submission")

    (tmp_path / "references.bib").write_text("@article{a, title={x}}\n")
    reqs2 = evaluate_requirements(m, project_root=tmp_path, mode="submission")
    file_req2 = next(r for r in reqs2 if r.id.startswith("REQ-BIBLIOGRAPHY-FILE-"))
    assert file_req2.status == "VERIFIED"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_requirements_writes_reports(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    result = runner.invoke(
        app, ["requirements", "--path", str(tmp_path), "--mode", "draft"]
    )
    assert result.exit_code == 0
    assert (tmp_path / ".paperforge" / "requirements.yaml").exists()
    assert (tmp_path / ".paperforge" / "requirements.json").exists()
    assert (tmp_path / ".paperforge" / "missing_requirements.md").exists()


def test_cli_requirements_submission_mode_json_exit_code(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    result = runner.invoke(
        app, ["requirements", "--path", str(tmp_path), "--mode", "submission", "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["exit_code"] == 21
    assert payload["outputs"]["blocking"] > 0
    assert result.exit_code == 21


def test_cli_requirements_missing_manifest(tmp_path: Path) -> None:
    result = runner.invoke(app, ["requirements", "--path", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["errors"][0]["code"] == "MANIFEST_NOT_FOUND"


def test_cli_requirements_invalid_mode(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    result = runner.invoke(
        app, ["requirements", "--path", str(tmp_path), "--mode", "bogus", "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["exit_code"] == 2


def test_cli_requirements_custom_output_dir(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    out_dir = tmp_path / "reports"
    result = runner.invoke(
        app,
        [
            "requirements",
            "--path",
            str(tmp_path),
            "--output",
            str(out_dir),
            "--mode",
            "draft",
        ],
    )
    assert result.exit_code == 0
    assert (out_dir / "requirements.yaml").exists()
