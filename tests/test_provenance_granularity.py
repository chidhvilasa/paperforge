"""Tests for per-sentence provenance staleness granularity (gap #13)."""

from __future__ import annotations

from pathlib import Path

from paperforge.generation.no_ai import GeneratedSection, GeneratedSentence
from paperforge.generation.provenance import (
    build_records,
    validate_provenance,
    write_provenance,
)
from paperforge.project_manifest.models import ClaimEntry, ProjectManifest


def _write_section(
    tmp_path: Path, sentences: list[GeneratedSentence]
) -> GeneratedSection:
    gen_dir = tmp_path / ".paperforge" / "generated_sections"
    gen_dir.mkdir(parents=True, exist_ok=True)
    sec = GeneratedSection(section="results", mode="validated", sentences=sentences)
    recs = build_records(
        sec, provider_name="no_ai", model_identifier="", approval_status="approved"
    )
    write_provenance(tmp_path, sec, recs)
    (gen_dir / "results.md").write_text(sec.to_markdown(), encoding="utf-8")
    return sec


def _manifest() -> ProjectManifest:
    return ProjectManifest(
        claims=[ClaimEntry(id="c1", text="x"), ClaimEntry(id="c2", text="y")]
    )


def test_no_edit_means_no_issues(tmp_path: Path) -> None:
    _write_section(
        tmp_path,
        [
            GeneratedSentence(
                claim_id="c1", text="Sentence one.", evidence_class="AUTHOR_ASSERTED"
            ),
            GeneratedSentence(
                claim_id="c2", text="Sentence two.", evidence_class="AUTHOR_ASSERTED"
            ),
        ],
    )
    assert validate_provenance(tmp_path, _manifest()) == []


def test_editing_one_sentence_flags_only_that_sentence(tmp_path: Path) -> None:
    _write_section(
        tmp_path,
        [
            GeneratedSentence(
                claim_id="c1", text="Sentence one.", evidence_class="AUTHOR_ASSERTED"
            ),
            GeneratedSentence(
                claim_id="c2", text="Sentence two.", evidence_class="AUTHOR_ASSERTED"
            ),
        ],
    )
    md_path = tmp_path / ".paperforge" / "generated_sections" / "results.md"
    text = md_path.read_text(encoding="utf-8").replace(
        "Sentence two.", "Sentence TWO edited."
    )
    md_path.write_text(text, encoding="utf-8")

    issues = validate_provenance(tmp_path, _manifest())
    stale = [i for i in issues if i["code"] == "PROVENANCE_STALE_SENTENCE"]
    assert len(stale) == 1
    assert "results:c2" in stale[0]["message"]
    # Sentence one must NOT be reported stale.
    assert not any("results:c1" in i["message"] for i in stale)


def test_sentence_count_change_falls_back_to_whole_section(tmp_path: Path) -> None:
    _write_section(
        tmp_path,
        [
            GeneratedSentence(
                claim_id="c1", text="Sentence one.", evidence_class="AUTHOR_ASSERTED"
            ),
            GeneratedSentence(
                claim_id="c2", text="Sentence two.", evidence_class="AUTHOR_ASSERTED"
            ),
        ],
    )
    md_path = tmp_path / ".paperforge" / "generated_sections" / "results.md"
    md_path.write_text(
        md_path.read_text(encoding="utf-8") + "\nAn extra hand-written line.\n",
        encoding="utf-8",
    )

    issues = validate_provenance(tmp_path, _manifest())
    codes = {i["code"] for i in issues}
    assert "PROVENANCE_STALE_HASH" in codes
    assert any(
        i["severity"] == "ERROR" for i in issues if i["code"] == "PROVENANCE_STALE_HASH"
    )


def test_evidence_staleness_propagates_to_provenance(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from paperforge.cli import app

    runner = CliRunner()
    (tmp_path / ".paperforge").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data.csv").write_text("run,val\n0,10\n", encoding="utf-8")
    runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            "ev1",
            "--type",
            "csv",
            "--source-path",
            "data.csv",
            "--source-locator",
            "row=0;col=val",
            "--path",
            str(tmp_path),
        ],
    )

    _write_section(
        tmp_path,
        [
            GeneratedSentence(
                claim_id="c1",
                text="Sentence one.",
                evidence_class="DIRECT_RESULT",
                evidence_refs=["ev1"],
            ),
        ],
    )

    assert not any(
        i["code"] == "PROVENANCE_STALE_EVIDENCE"
        for i in validate_provenance(tmp_path, _manifest())
    )

    (tmp_path / "data.csv").write_text("run,val\n0,999\n", encoding="utf-8")
    issues = validate_provenance(tmp_path, _manifest())
    assert any(i["code"] == "PROVENANCE_STALE_EVIDENCE" for i in issues)
