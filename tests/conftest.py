"""Shared pytest fixtures for the PaperForge test suite."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_os_reveal_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent tests from opening real OS file-explorer windows.

    build.run() calls _reveal_output() to open the containing folder of a
    freshly built PDF. On a machine with a real LaTeX toolchain installed,
    any test that exercises build.run() without explicitly mocking this
    would otherwise open a real Explorer/Finder/xdg-open window as a side
    effect of running the test suite. Tests that specifically assert on
    _reveal_output's call behavior patch it themselves within their own
    scope, which still takes precedence over this default no-op.
    """
    monkeypatch.setattr(
        "paperforge.commands.build._reveal_output", lambda *args, **kwargs: None
    )
