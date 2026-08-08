"""Tests for paperforge.generation (providers, no-AI templates, provenance)
and the `paperforge generate` / `paperforge provenance` CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from paperforge.cli import app
from paperforge.generation.no_ai import generate_outline, generate_section
from paperforge.generation.provenance import (
    build_records,
    validate_provenance,
    write_provenance,
)
from paperforge.generation.providers import (
    ClaimContext,
    FixtureProvider,
    NoAIProvider,
    ProviderConfig,
    get_provider,
)
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
authors:
  - id: "author_1"
    name: "Alex Morgan"
research:
  primary_question: "What effect does the evaluated method have?"
manuscript:
  generation_policy: "validation_only"
  required_sections:
    - introduction
    - results
"""


def _manifest(yaml_text: str = BASE_MANIFEST) -> ProjectManifest:
    return ProjectManifest.from_dict(yaml.safe_load(yaml_text))


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------


def test_provider_config_validates_bounds() -> None:
    with pytest.raises(ValueError):
        NoAIProvider(ProviderConfig(name="no_ai", timeout_seconds=-1))


def test_external_provider_config_requires_redaction() -> None:
    problems = ProviderConfig(
        name="x", privacy_class="external", redaction_enabled=False
    ).validate()
    assert any("redaction" in p for p in problems)


def test_no_ai_provider_never_invents_facts() -> None:
    provider = NoAIProvider()
    ctx = ClaimContext(
        claim_id="c1",
        text="the method improves throughput",
        evidence_class="DIRECT_RESULT",
    )
    text = provider.render_claim_sentence(ctx)
    assert "the method improves throughput" in text
    assert "c1" in text


def test_no_ai_provider_placeholder_template_is_visibly_marked() -> None:
    provider = NoAIProvider()
    ctx = ClaimContext(claim_id="c9", text="TBD", evidence_class="PLACEHOLDER")
    text = provider.render_claim_sentence(ctx)
    assert "PLACEHOLDER" in text
    assert "TODO" in text


def test_fixture_provider_is_deterministic_and_offline() -> None:
    provider = FixtureProvider({"c1": "canned sentence"})
    ctx = ClaimContext(claim_id="c1", text="ignored", evidence_class="AUTHOR_ASSERTED")
    assert provider.render_claim_sentence(ctx) == "canned sentence"
    assert provider.config.privacy_class == "local"
    assert provider.config.offline_supported


def test_get_provider_unknown_raises() -> None:
    with pytest.raises(ValueError):
        get_provider("openai-gpt-5000")


def test_get_provider_no_ai_and_fixture() -> None:
    assert get_provider("no_ai").config.name == "no_ai"
    assert get_provider("fixture").config.name == "fixture"


# ---------------------------------------------------------------------------
# No-AI generation
# ---------------------------------------------------------------------------


def test_generate_outline_has_no_prose() -> None:
    m = _manifest()
    m.claims.append(
        ClaimEntry(id="c1", text="x improves y", evidence_class="DIRECT_RESULT")
    )
    plan = build_plan(m)
    results_section = next(s for s in plan.sections if s.name == "results")
    outline = generate_outline(results_section)
    assert outline["section"] == "results"
    assert "c1" in outline["permitted_claims"]
    assert "purpose" in outline


def test_generate_section_produces_one_sentence_per_claim() -> None:
    m = _manifest()
    m.claims.append(
        ClaimEntry(
            id="c1",
            text="x improves y",
            evidence_class="DIRECT_RESULT",
            evidence_refs=["data.csv"],
        )
    )
    m.claims.append(
        ClaimEntry(id="c2", text="z also improves", evidence_class="DIRECT_RESULT")
    )
    plan = build_plan(m)
    results_section = next(s for s in plan.sections if s.name == "results")
    provider = NoAIProvider()
    generated = generate_section(
        results_section, m, provider=provider, mode="validated"
    )
    assert len(generated.sentences) == 2
    ids = {s.claim_id for s in generated.sentences}
    assert ids == {"c1", "c2"}
    unsupported = next(s for s in generated.sentences if s.claim_id == "c2")
    assert unsupported.warnings  # DIRECT_RESULT with no evidence_refs/citation_keys


def test_generate_section_excludes_placeholder_claims_by_default() -> None:
    m = _manifest()
    m.claims.append(ClaimEntry(id="c1", text="x", evidence_class="PLACEHOLDER"))
    plan = build_plan(m)
    # placeholder claims never even reach a section in the plan (prohibited),
    # so nothing to generate for them.
    assert all("c1" not in s.claim_ids for s in plan.sections)


def test_generate_section_draft_with_placeholders_includes_and_marks_them() -> None:
    m = _manifest()
    m.claims.append(ClaimEntry(id="c1", text="x", evidence_class="PLACEHOLDER"))
    plan = build_plan(m)
    intro = next(s for s in plan.sections if s.name == "introduction")
    provider = NoAIProvider()
    generated = generate_section(
        intro,
        m,
        provider=provider,
        mode="draft_with_placeholders",
        include_placeholders=True,
    )
    placeholder_sentences = [s for s in generated.sentences if s.claim_id == "c1"]
    assert placeholder_sentences and placeholder_sentences[0].is_placeholder
    md = generated.to_markdown()
    assert "DRAFT WITH PLACEHOLDERS" in md
    assert "[PLACEHOLDER]" in md


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_provenance_round_trips_and_validates_clean(tmp_path: Path) -> None:
    m = _manifest()
    m.claims.append(
        ClaimEntry(
            id="c1",
            text="x improves y",
            evidence_class="DIRECT_RESULT",
            evidence_refs=["data.csv"],
        )
    )
    plan = build_plan(m)
    results_section = next(s for s in plan.sections if s.name == "results")
    provider = NoAIProvider()
    generated = generate_section(
        results_section, m, provider=provider, mode="validated"
    )

    gen_dir = tmp_path / ".paperforge" / "generated_sections"
    gen_dir.mkdir(parents=True)
    (gen_dir / "results.md").write_text(generated.to_markdown(), encoding="utf-8")

    records = build_records(
        generated, provider_name="no_ai", model_identifier="x", approval_status="valid"
    )
    for r in records:
        r.author_review_status = "approved"
    write_provenance(tmp_path, generated, records)

    issues = validate_provenance(tmp_path, m, generated_sections_dir=gen_dir)
    assert issues == []


def test_provenance_detects_stale_hash_after_hand_edit(tmp_path: Path) -> None:
    m = _manifest()
    m.claims.append(ClaimEntry(id="c1", text="x", evidence_class="AUTHOR_ASSERTED"))
    plan = build_plan(m)
    intro = next(s for s in plan.sections if s.name == "introduction")
    provider = NoAIProvider()
    generated = generate_section(intro, m, provider=provider, mode="validated")

    gen_dir = tmp_path / ".paperforge" / "generated_sections"
    gen_dir.mkdir(parents=True)
    (gen_dir / "introduction.md").write_text(generated.to_markdown(), encoding="utf-8")
    records = build_records(
        generated, provider_name="no_ai", model_identifier="x", approval_status="valid"
    )
    write_provenance(tmp_path, generated, records)

    (gen_dir / "introduction.md").write_text("hand-edited content", encoding="utf-8")
    issues = validate_provenance(tmp_path, m, generated_sections_dir=gen_dir)
    assert any(i["code"] == "PROVENANCE_STALE_HASH" for i in issues)


def test_provenance_detects_missing_claim(tmp_path: Path) -> None:
    m = _manifest()
    m.claims.append(ClaimEntry(id="c1", text="x", evidence_class="AUTHOR_ASSERTED"))
    plan = build_plan(m)
    intro = next(s for s in plan.sections if s.name == "introduction")
    provider = NoAIProvider()
    generated = generate_section(intro, m, provider=provider, mode="validated")
    gen_dir = tmp_path / ".paperforge" / "generated_sections"
    gen_dir.mkdir(parents=True)
    (gen_dir / "introduction.md").write_text(generated.to_markdown(), encoding="utf-8")
    records = build_records(
        generated, provider_name="no_ai", model_identifier="x", approval_status="valid"
    )
    write_provenance(tmp_path, generated, records)

    m.claims.clear()  # claim removed from manifest after generation
    issues = validate_provenance(tmp_path, m, generated_sections_dir=gen_dir)
    assert any(i["code"] == "PROVENANCE_MISSING_CLAIM" for i in issues)


def test_provenance_detects_unreviewed_result(tmp_path: Path) -> None:
    m = _manifest()
    m.claims.append(
        ClaimEntry(
            id="c1", text="x", evidence_class="DIRECT_RESULT", evidence_refs=["d.csv"]
        )
    )
    plan = build_plan(m)
    results_section = next(s for s in plan.sections if s.name == "results")
    provider = NoAIProvider()
    generated = generate_section(
        results_section, m, provider=provider, mode="validated"
    )
    gen_dir = tmp_path / ".paperforge" / "generated_sections"
    gen_dir.mkdir(parents=True)
    (gen_dir / "results.md").write_text(generated.to_markdown(), encoding="utf-8")
    records = build_records(
        generated, provider_name="no_ai", model_identifier="x", approval_status="valid"
    )
    # author_review_status left at default "pending"
    write_provenance(tmp_path, generated, records)

    issues = validate_provenance(tmp_path, m, generated_sections_dir=gen_dir)
    assert any(i["code"] == "PROVENANCE_UNREVIEWED_RESULT" for i in issues)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_generate_outline_only_requires_no_approval(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    result = runner.invoke(
        app, ["generate", "--path", str(tmp_path), "--outline-only", "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert (
        tmp_path / ".paperforge" / "generated_sections" / "introduction.outline.json"
    ).exists()


def test_cli_generate_validated_refuses_without_approval(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    result = runner.invoke(app, ["generate", "--path", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["errors"][0]["code"] == "GENERATION_PLAN_NOT_APPROVED"
    assert payload["exit_code"] == 40  # EXIT_GENERATION_PROVENANCE_ERROR


def test_cli_generate_validated_succeeds_after_approval(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--approve", "--non-interactive"]
    )
    result = runner.invoke(app, ["generate", "--path", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert (
        tmp_path / ".paperforge" / "generated_sections" / "introduction.md"
    ).exists()
    assert (tmp_path / ".paperforge" / "provenance" / "index.json").exists()


def test_cli_generate_refuses_after_approval_goes_stale(tmp_path: Path) -> None:
    manifest_path = tmp_path / "paperforge.project.yaml"
    manifest_path.write_text(BASE_MANIFEST, encoding="utf-8")
    runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--approve", "--non-interactive"]
    )
    data = yaml.safe_load(BASE_MANIFEST)
    data["project"]["title"] = "Changed"
    manifest_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    result = runner.invoke(app, ["generate", "--path", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["errors"][0]["code"] == "GENERATION_PLAN_APPROVAL_STALE"


def test_cli_generate_draft_with_placeholders_watermarked(tmp_path: Path) -> None:
    data = yaml.safe_load(BASE_MANIFEST)
    data["claims"] = [{"id": "c1", "text": "TBD", "evidence_class": "PLACEHOLDER"}]
    (tmp_path / "paperforge.project.yaml").write_text(
        yaml.safe_dump(data), encoding="utf-8"
    )
    result = runner.invoke(
        app,
        ["generate", "--path", str(tmp_path), "--draft-with-placeholders", "--json"],
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    content = (
        tmp_path / ".paperforge" / "generated_sections" / "introduction.md"
    ).read_text(encoding="utf-8")
    assert "DRAFT WITH PLACEHOLDERS" in content


def test_cli_generate_single_section(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--approve", "--non-interactive"]
    )
    result = runner.invoke(
        app, ["generate", "--path", str(tmp_path), "--section", "results", "--json"]
    )
    payload = json.loads(result.stdout)
    assert list(payload["outputs"]["sections"].keys()) == ["results"]
    assert not (
        tmp_path / ".paperforge" / "generated_sections" / "introduction.md"
    ).exists()


def test_cli_generate_review_existing(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--approve", "--non-interactive"]
    )
    runner.invoke(app, ["generate", "--path", str(tmp_path)])
    result = runner.invoke(
        app, ["generate", "--path", str(tmp_path), "--review-existing", "--json"]
    )
    payload = json.loads(result.stdout)
    assert "introduction" in payload["outputs"]["existing_sections"]


def test_cli_generate_fixture_provider(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--approve", "--non-interactive"]
    )
    result = runner.invoke(
        app, ["generate", "--path", str(tmp_path), "--provider", "fixture", "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["outputs"]["provider"] == "fixture"


def test_cli_generate_missing_manifest(tmp_path: Path) -> None:
    result = runner.invoke(app, ["generate", "--path", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"


def test_cli_provenance_show_empty(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["provenance", "show", "--path", str(tmp_path), "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["outputs"]["index"]["sections"] == {}


def test_cli_provenance_validate_clean_after_generation(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--approve", "--non-interactive"]
    )
    runner.invoke(app, ["generate", "--path", str(tmp_path)])
    result = runner.invoke(
        app, ["provenance", "validate", "--path", str(tmp_path), "--json"]
    )
    payload = json.loads(result.stdout)
    # sections have no claims, so no provenance records exist yet (only
    # generated when a section has >=1 claim in scope); validate should
    # still succeed cleanly (no stale hashes, no missing claims).
    assert payload["status"] == "success"


def test_cli_provenance_validate_detects_issues(tmp_path: Path) -> None:
    data = yaml.safe_load(BASE_MANIFEST)
    data["claims"] = [
        {
            "id": "c1",
            "text": "x improves y",
            "evidence_class": "DIRECT_RESULT",
            "evidence_refs": ["d.csv"],
        }
    ]
    (tmp_path / "paperforge.project.yaml").write_text(
        yaml.safe_dump(data), encoding="utf-8"
    )
    runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--approve", "--non-interactive"]
    )
    runner.invoke(app, ["generate", "--path", str(tmp_path)])
    result = runner.invoke(
        app, ["provenance", "validate", "--path", str(tmp_path), "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert any(e["code"] == "PROVENANCE_UNREVIEWED_RESULT" for e in payload["errors"])


def test_cli_provenance_export(tmp_path: Path) -> None:
    (tmp_path / "paperforge.project.yaml").write_text(BASE_MANIFEST, encoding="utf-8")
    runner.invoke(
        app, ["plan", "--path", str(tmp_path), "--approve", "--non-interactive"]
    )
    runner.invoke(app, ["generate", "--path", str(tmp_path)])
    out = tmp_path / "exported.json"
    result = runner.invoke(
        app, ["provenance", "export", "--path", str(tmp_path), "--output", str(out)]
    )
    assert result.exit_code == 0
    assert out.exists()
    assert "index" in json.loads(out.read_text(encoding="utf-8"))
