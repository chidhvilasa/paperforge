"""Tests for paperforge update and output rotation."""

import importlib.metadata
from pathlib import Path
from unittest.mock import patch

from paperforge.commands import build, init, update


def test_update_command_exists() -> None:
    assert callable(update.run)


def test_update_checks_current_version() -> None:
    version = importlib.metadata.version("paperforge-research")
    assert version is not None


def test_update_handles_pypi_failure_gracefully() -> None:
    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        update.run(pre=False)


def test_rotate_output_copies_files(tmp_path: Path) -> None:
    init.run(tmp_path)
    current_dir = tmp_path / "paper_generated" / "current"
    current_dir.mkdir(parents=True, exist_ok=True)
    (current_dir / "paper.tex").write_text("v1 content", encoding="utf-8")

    build._rotate_output(tmp_path)

    prev_file = tmp_path / "paper_generated" / "previous" / "paper.tex"
    assert prev_file.exists()
    assert prev_file.read_text(encoding="utf-8") == "v1 content"
