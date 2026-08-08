"""Tests for paperforge.outputs (list/verify/promote/rollback) and the
corresponding CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from paperforge.cli import app
from paperforge.commands import init
from paperforge.outputs.lifecycle import (
    list_outputs,
    promote,
    resolve_output_paths,
    rollback,
)
from paperforge.outputs.verifier import verify_output_dir

runner = CliRunner()

_MIN_PDF = b"%PDF-1.4\n" + b"x" * 200 + b"\n%%EOF"


def _init_project(tmp_path: Path) -> None:
    init.run(tmp_path)


def _write_pdf(directory: Path, content: bytes = _MIN_PDF) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "paper.pdf").write_bytes(content)
    (directory / "paper.tex").write_text("\\documentclass{article}", encoding="utf-8")


# ---------------------------------------------------------------------------
# verify_output_dir
# ---------------------------------------------------------------------------


def test_verify_missing_directory() -> None:
    v = verify_output_dir(Path("/definitely/does/not/exist/xyz"))
    assert not v.ok
    assert "does not exist" in v.issues[0]


def test_verify_missing_pdf(tmp_path: Path) -> None:
    out = tmp_path / "current"
    out.mkdir()
    v = verify_output_dir(out)
    assert not v.ok
    assert any("Missing required artifact: paper.pdf" in i for i in v.issues)


def test_verify_trivially_small_pdf(tmp_path: Path) -> None:
    out = tmp_path / "current"
    out.mkdir()
    (out / "paper.pdf").write_bytes(b"%PDF-x")
    v = verify_output_dir(out)
    assert not v.ok
    assert any("suspiciously small" in i for i in v.issues)


def test_verify_bad_pdf_header(tmp_path: Path) -> None:
    out = tmp_path / "current"
    out.mkdir()
    (out / "paper.pdf").write_bytes(b"NOTPDF" + b"x" * 200)
    v = verify_output_dir(out)
    assert not v.ok
    assert any("valid PDF header" in i for i in v.issues)


def test_verify_good_output_passes_and_hashes_recorded(tmp_path: Path) -> None:
    out = tmp_path / "current"
    _write_pdf(out)
    v = verify_output_dir(out)
    assert v.ok, v.issues
    pdf_info = next(a for a in v.artifacts if a.name == "paper.pdf")
    assert pdf_info.exists
    assert len(pdf_info.sha256) == 64


# ---------------------------------------------------------------------------
# list_outputs
# ---------------------------------------------------------------------------


def test_list_outputs_no_current(tmp_path: Path) -> None:
    _init_project(tmp_path)
    # `init` scaffolds empty current/previous directories; remove them to
    # exercise the genuine "nothing built yet" state.
    import shutil as _shutil

    _shutil.rmtree(tmp_path / "paper_generated" / "current")
    _shutil.rmtree(tmp_path / "paper_generated" / "previous")
    result = list_outputs(tmp_path)
    assert result["current"] is None
    assert result["previous"] is None


def test_list_outputs_current_only(tmp_path: Path) -> None:
    _init_project(tmp_path)
    import shutil as _shutil

    _shutil.rmtree(tmp_path / "paper_generated" / "previous")
    _write_pdf(tmp_path / "paper_generated" / "current")
    result = list_outputs(tmp_path)
    assert result["current"]["ok"] is True
    assert result["previous"] is None


def test_list_outputs_current_and_previous(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write_pdf(tmp_path / "paper_generated" / "current")
    _write_pdf(tmp_path / "paper_generated" / "previous")
    result = list_outputs(tmp_path)
    assert result["current"]["ok"] is True
    assert result["previous"]["ok"] is True


# ---------------------------------------------------------------------------
# promote
# ---------------------------------------------------------------------------


def test_promote_fails_validation_leaves_dirs_untouched(tmp_path: Path) -> None:
    _init_project(tmp_path)
    current = tmp_path / "paper_generated" / "current"
    # `init` already scaffolds an empty current/ directory (no paper.pdf
    # yet) -- exactly the "fails verification" state we want to test.
    result = promote(tmp_path)
    assert not result.ok
    assert current.exists()
    assert not (tmp_path / ".paperforge" / "output_manifest.json").exists()


def test_promote_succeeds_and_writes_manifest(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write_pdf(tmp_path / "paper_generated" / "current")
    result = promote(tmp_path)
    assert result.ok
    manifest_path = Path(result.manifest_path)
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "promoted_at" in data


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------


def test_rollback_fails_with_no_previous(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write_pdf(tmp_path / "paper_generated" / "current")
    result = rollback(tmp_path)
    assert not result.ok
    assert "Nothing to roll back" in result.message


def test_rollback_swaps_current_and_previous(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write_pdf(tmp_path / "paper_generated" / "current", content=_MIN_PDF + b"CURRENT")
    _write_pdf(
        tmp_path / "paper_generated" / "previous", content=_MIN_PDF + b"PREVIOUS"
    )

    result = rollback(tmp_path)
    assert result.ok
    assert not result.resumed_interrupted

    current_bytes = (
        tmp_path / "paper_generated" / "current" / "paper.pdf"
    ).read_bytes()
    previous_bytes = (
        tmp_path / "paper_generated" / "previous" / "paper.pdf"
    ).read_bytes()
    assert current_bytes.endswith(b"PREVIOUS")
    assert previous_bytes.endswith(b"CURRENT")
    assert result.verification_after is not None
    assert result.verification_after.ok


def test_rollback_hash_mismatch_after_manual_edit_is_detectable(tmp_path: Path) -> None:
    """Verifies that rollback's post-swap verification records hashes that
    would reveal a hand-edited (vs. build-produced) artifact."""
    _init_project(tmp_path)
    _write_pdf(tmp_path / "paper_generated" / "current", content=_MIN_PDF + b"CURRENT")
    _write_pdf(
        tmp_path / "paper_generated" / "previous", content=_MIN_PDF + b"PREVIOUS"
    )
    before_previous_hash = (
        verify_output_dir(tmp_path / "paper_generated" / "previous").artifacts[0].sha256
    )

    result = rollback(tmp_path)
    after_current_hash = result.verification_after.artifacts[0].sha256
    assert after_current_hash == before_previous_hash


def test_rollback_resumes_interrupted_swap(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write_pdf(tmp_path / "paper_generated" / "current", content=_MIN_PDF + b"CURRENT")
    _write_pdf(
        tmp_path / "paper_generated" / "previous", content=_MIN_PDF + b"PREVIOUS"
    )

    paths = resolve_output_paths(tmp_path)
    # Simulate a crash after step 1 (current renamed to tmp) by doing step 1
    # manually and writing the marker, without calling rollback().
    import json as json_module

    tmp_dir = paths.current.parent / ".rollback_tmp"
    paths.current.rename(tmp_dir)
    paths.swap_marker.parent.mkdir(parents=True, exist_ok=True)
    paths.swap_marker.write_text(
        json_module.dumps(
            {
                "step": 1,
                "tmp_dir": str(tmp_dir),
                "current": str(paths.current),
                "previous": str(paths.previous),
            }
        ),
        encoding="utf-8",
    )

    result = rollback(tmp_path)
    assert result.ok
    assert result.resumed_interrupted
    assert not paths.swap_marker.exists()
    current_bytes = (
        tmp_path / "paper_generated" / "current" / "paper.pdf"
    ).read_bytes()
    assert current_bytes.endswith(b"PREVIOUS")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_outputs_list_json(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write_pdf(tmp_path / "paper_generated" / "current")
    result = runner.invoke(app, ["outputs", "list", "--path", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["outputs"]["current"]["ok"] is True


def test_cli_outputs_verify_json(tmp_path: Path) -> None:
    _init_project(tmp_path)
    result = runner.invoke(
        app, ["outputs", "verify", "--path", str(tmp_path), "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"


def test_cli_promote_and_rollback_roundtrip(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write_pdf(tmp_path / "paper_generated" / "current", content=_MIN_PDF + b"V1")
    r1 = runner.invoke(app, ["promote", "--path", str(tmp_path), "--json"])
    assert json.loads(r1.stdout)["status"] == "success"

    # simulate a new build producing "previous" via the existing rotation
    # convention, then a second promote for V2 current:
    import shutil as _shutil

    _shutil.rmtree(tmp_path / "paper_generated" / "previous")
    (tmp_path / "paper_generated" / "current").rename(
        tmp_path / "paper_generated" / "previous"
    )
    _write_pdf(tmp_path / "paper_generated" / "current", content=_MIN_PDF + b"V2")
    r2 = runner.invoke(app, ["promote", "--path", str(tmp_path), "--json"])
    assert json.loads(r2.stdout)["status"] == "success"

    r3 = runner.invoke(app, ["rollback", "--path", str(tmp_path), "--json"])
    payload3 = json.loads(r3.stdout)
    assert payload3["status"] == "success"
    current_bytes = (
        tmp_path / "paper_generated" / "current" / "paper.pdf"
    ).read_bytes()
    assert current_bytes.endswith(b"V1")


def test_cli_rollback_no_previous_reports_failure(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _write_pdf(tmp_path / "paper_generated" / "current")
    result = runner.invoke(app, ["rollback", "--path", str(tmp_path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["exit_code"] == 70  # EXIT_PACKAGING_OUTPUT_ERROR
