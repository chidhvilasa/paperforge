"""Tests for the read-only `paperforge inspect` command."""

from __future__ import annotations

import subprocess
from pathlib import Path

from paperforge.commands.inspect import run_inspection


def test_inspect_empty_directory(tmp_path: Path) -> None:
    report = run_inspection(tmp_path)
    assert report.is_git_repo is False
    assert report.has_paperforge_project is False
    assert report.manuscripts == []
    assert report.bibliography_files == []
    assert report.likely_secrets == []


def test_inspect_detects_manuscript_and_bibliography(tmp_path: Path) -> None:
    (tmp_path / "paper.tex").write_text("\\documentclass{article}", encoding="utf-8")
    (tmp_path / "references.bib").write_text("@article{a2024,}", encoding="utf-8")
    report = run_inspection(tmp_path)
    assert "paper.tex" in report.manuscripts
    assert "references.bib" in report.bibliography_files


def test_inspect_detects_figures_tables_notebooks(tmp_path: Path) -> None:
    (tmp_path / "figures").mkdir()
    (tmp_path / "figures" / "plot.png").write_bytes(b"x")
    (tmp_path / "results.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "analysis.ipynb").write_text("{}", encoding="utf-8")
    report = run_inspection(tmp_path)
    assert "figures/plot.png" in report.figures
    assert "results.csv" in report.tables
    assert "analysis.ipynb" in report.notebooks


def test_inspect_detects_existing_paperforge_project(tmp_path: Path) -> None:
    from paperforge.commands import init

    init.run(tmp_path)
    report = run_inspection(tmp_path)
    assert report.has_paperforge_project is True
    assert report.paperforge_manifest_path


def test_inspect_detects_package_managers(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("numpy\n", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    report = run_inspection(tmp_path)
    assert "requirements.txt" in report.package_managers
    assert "package.json" in report.package_managers


def test_inspect_flags_likely_secret(tmp_path: Path) -> None:
    (tmp_path / "config.py").write_text(
        'AWS_KEY = "AKIAABCDEFGHIJKLMNOP"\n', encoding="utf-8"
    )
    report = run_inspection(tmp_path)
    assert any("config.py" in s["file"] for s in report.likely_secrets)


def test_inspect_flags_absolute_windows_path(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text(
        "See C:\\\\Users\\\\someone\\\\Documents\\\\data.csv for details.\n",
        encoding="utf-8",
    )
    report = run_inspection(tmp_path)
    assert any("notes.md" in p["file"] for p in report.absolute_paths)


def test_inspect_ignores_excluded_directories(tmp_path: Path) -> None:
    excluded = tmp_path / ".venv" / "lib"
    excluded.mkdir(parents=True)
    (excluded / "fake.tex").write_text("x", encoding="utf-8")
    report = run_inspection(tmp_path)
    assert report.manuscripts == []


def test_inspect_detects_candidate_output_dir(tmp_path: Path) -> None:
    (tmp_path / "paper_generated").mkdir()
    report = run_inspection(tmp_path)
    assert "paper_generated" in report.candidate_output_dirs


def test_inspect_git_state_detection(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=False)
    report = run_inspection(tmp_path)
    assert report.is_git_repo is True


def test_inspect_cli_json_output(tmp_path: Path) -> None:
    """`paperforge inspect --json` must produce valid, parseable JSON."""
    import json

    from paperforge.commands.inspect import run

    (tmp_path / "paper.tex").write_text("x", encoding="utf-8")
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run(tmp_path, json_output=True)
    data = json.loads(buf.getvalue())
    assert data["manuscripts"] == ["paper.tex"]
