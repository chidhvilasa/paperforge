"""Tests for the author-review approvals workflow and CLI."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from paperforge.cli import app
from paperforge.review.approvals import (
    ApprovalError,
    find_object,
    reconcile,
    record_decision,
)

runner = CliRunner()


def _add_manual_evidence(tmp_path: Path, evidence_id: str, value: int = 1) -> None:
    (tmp_path / ".paperforge").mkdir(parents=True, exist_ok=True)
    runner.invoke(
        app,
        [
            "evidence",
            "direct",
            "add",
            "--id",
            evidence_id,
            "--type",
            "manual",
            "--value",
            str(value),
            "--path",
            str(tmp_path),
        ],
    )


def test_approve_then_status_is_approved(tmp_path: Path) -> None:
    _add_manual_evidence(tmp_path, "x")
    record_decision(tmp_path, "x", "approved", reviewer="alice")
    result = reconcile(tmp_path)
    assert result.entries[0].effective_status == "approved"
    assert not result.entries[0].stale


def test_reject_then_status_is_rejected(tmp_path: Path) -> None:
    _add_manual_evidence(tmp_path, "x")
    record_decision(tmp_path, "x", "rejected", reviewer="alice")
    result = reconcile(tmp_path)
    assert result.entries[0].effective_status == "rejected"


def test_stale_approval_downgrades_to_pending(tmp_path: Path) -> None:
    _add_manual_evidence(tmp_path, "x")
    record_decision(tmp_path, "x", "approved", reviewer="alice")

    # Mutate the underlying evidence record directly (simulating an edit).
    p = tmp_path / ".paperforge" / "evidence" / "direct.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    data[0]["value"] = 999
    p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = reconcile(tmp_path)
    assert result.downgraded == ["x"]
    assert result.entries[0].effective_status == "pending"
    assert result.entries[0].stale


def test_find_object_unknown_id_raises(tmp_path: Path) -> None:
    (tmp_path / ".paperforge").mkdir(parents=True, exist_ok=True)
    import pytest

    with pytest.raises(ApprovalError):
        find_object(tmp_path, "does-not-exist")


def test_cli_approve_and_list(tmp_path: Path) -> None:
    _add_manual_evidence(tmp_path, "y")
    result = runner.invoke(
        app, ["approvals", "approve", "y", "--non-interactive", "--path", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output

    listed = runner.invoke(
        app, ["approvals", "list", "--json", "--path", str(tmp_path)]
    )
    data = json.loads(listed.output)
    assert data["outputs"]["entries"][0]["effective_status"] == "approved"
    assert data["outputs"]["entries"][0]["reviewer"] == "agent"


def test_cli_reject(tmp_path: Path) -> None:
    _add_manual_evidence(tmp_path, "z")
    result = runner.invoke(
        app, ["approvals", "reject", "z", "--non-interactive", "--path", str(tmp_path)]
    )
    assert result.exit_code == 0

    listed = runner.invoke(
        app, ["approvals", "list", "--json", "--path", str(tmp_path)]
    )
    data = json.loads(listed.output)
    assert data["outputs"]["entries"][0]["effective_status"] == "rejected"


def test_cli_reset_after_approve(tmp_path: Path) -> None:
    _add_manual_evidence(tmp_path, "w")
    runner.invoke(
        app, ["approvals", "approve", "w", "--non-interactive", "--path", str(tmp_path)]
    )
    result = runner.invoke(
        app, ["approvals", "reset", "w", "--non-interactive", "--path", str(tmp_path)]
    )
    assert result.exit_code == 0

    listed = runner.invoke(
        app, ["approvals", "list", "--json", "--path", str(tmp_path)]
    )
    data = json.loads(listed.output)
    assert data["outputs"]["entries"][0]["effective_status"] == "pending"


def test_section_approval(tmp_path: Path) -> None:
    from paperforge.generation.no_ai import GeneratedSection, GeneratedSentence
    from paperforge.generation.provenance import build_records, write_provenance

    (tmp_path / ".paperforge").mkdir(parents=True, exist_ok=True)
    sec = GeneratedSection(
        section="results",
        mode="validated",
        sentences=[
            GeneratedSentence(
                claim_id="c1", text="One.", evidence_class="AUTHOR_ASSERTED"
            ),
            GeneratedSentence(
                claim_id="c2", text="Two.", evidence_class="AUTHOR_ASSERTED"
            ),
        ],
    )
    recs = build_records(
        sec, provider_name="no_ai", model_identifier="", approval_status="approved"
    )
    write_provenance(tmp_path, sec, recs)

    result = runner.invoke(
        app,
        [
            "approvals",
            "approve",
            "--section",
            "results",
            "--non-interactive",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output

    listed = runner.invoke(
        app,
        [
            "approvals",
            "list",
            "--section",
            "results",
            "--json",
            "--path",
            str(tmp_path),
        ],
    )
    data = json.loads(listed.output)
    assert len(data["outputs"]["entries"]) == 2
    assert all(e["effective_status"] == "approved" for e in data["outputs"]["entries"])
