"""Tests for paperforge install-hooks command."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from paperforge.commands import install_hooks


def make_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)


def _hook_path(path: Path) -> Path:
    return path / ".git" / "hooks" / "pre-commit"


def test_install_creates_hook_file(tmp_path: Path) -> None:
    """install-hooks creates the pre-commit hook file."""
    make_git_repo(tmp_path)
    install_hooks.run(tmp_path)
    assert _hook_path(tmp_path).exists()


def test_hook_file_is_executable(tmp_path: Path) -> None:
    """The installed hook is executable."""
    make_git_repo(tmp_path)
    install_hooks.run(tmp_path)
    hook = _hook_path(tmp_path)
    assert os.access(hook, os.X_OK)


def test_hook_contains_paperforge(tmp_path: Path) -> None:
    """Hook content references paperforge and paperforge doctor."""
    make_git_repo(tmp_path)
    install_hooks.run(tmp_path)
    content = _hook_path(tmp_path).read_text(encoding="utf-8")
    assert "paperforge" in content
    assert "paperforge doctor" in content


def test_install_already_installed_is_idempotent(tmp_path: Path) -> None:
    """Running install-hooks twice is safe and leaves hook intact."""
    make_git_repo(tmp_path)
    install_hooks.run(tmp_path)
    # Second install — should not raise
    install_hooks.run(tmp_path)
    hook = _hook_path(tmp_path)
    assert hook.exists()
    assert "paperforge" in hook.read_text(encoding="utf-8")


def test_install_existing_non_paperforge_hook_exits_1(tmp_path: Path) -> None:
    """Exits 1 when a non-PaperForge hook already exists."""
    make_git_repo(tmp_path)
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "pre-commit").write_text("#!/bin/sh\necho hello\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        install_hooks.run(tmp_path)
    assert exc_info.value.code == 1


def test_uninstall_removes_hook(tmp_path: Path) -> None:
    """--uninstall deletes the hook file."""
    make_git_repo(tmp_path)
    install_hooks.run(tmp_path)
    assert _hook_path(tmp_path).exists()
    install_hooks.run(tmp_path, uninstall=True)
    assert not _hook_path(tmp_path).exists()


def test_uninstall_no_hook_is_graceful(tmp_path: Path) -> None:
    """--uninstall with no hook present does not raise."""
    make_git_repo(tmp_path)
    # No hook installed — should not raise
    install_hooks.run(tmp_path, uninstall=True)


def test_no_git_repo_exits_1(tmp_path: Path) -> None:
    """Exits 1 when no git repository is found."""
    # No git init — plain tmp_path
    with pytest.raises(SystemExit) as exc_info:
        install_hooks.run(tmp_path)
    assert exc_info.value.code == 1
