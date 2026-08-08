"""Tests for the centralized, timeout-safe subprocess runner.

Uses only a neutral `python -c "import time; time.sleep(N)"` sleeper --
never a real LaTeX toolchain -- so these tests are fast and don't depend
on MiKTeX/TeX Live being installed.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from paperforge.utils.subprocess_runner import redact_command, run_subprocess


def _sleeper(seconds: float) -> list[str]:
    return [sys.executable, "-c", f"import time; time.sleep({seconds})"]


def test_successful_command_captures_stdout() -> None:
    result = run_subprocess(
        [sys.executable, "-c", "print('hello paperforge')"], timeout=10
    )
    assert result.ok
    assert not result.timed_out
    assert "hello paperforge" in result.stdout
    assert result.returncode == 0


def test_failing_command_reports_nonzero_returncode() -> None:
    result = run_subprocess(
        [sys.executable, "-c", "import sys; sys.exit(3)"], timeout=10
    )
    assert not result.ok
    assert result.returncode == 3
    assert not result.timed_out


def test_hanging_command_is_killed_at_timeout_not_left_running() -> None:
    start = time.monotonic()
    result = run_subprocess(_sleeper(30), timeout=1.5)
    elapsed = time.monotonic() - start
    assert result.timed_out
    assert not result.ok
    # The whole point: we must not block for anywhere near the full 30s sleep.
    assert elapsed < 15
    assert result.duration_seconds < 15


def test_missing_executable_does_not_raise() -> None:
    result = run_subprocess(
        ["paperforge-definitely-not-a-real-executable-xyz"], timeout=5
    )
    assert result.returncode == -1
    assert not result.timed_out
    assert not result.ok


def test_empty_args_raises_value_error() -> None:
    import pytest

    with pytest.raises(ValueError):
        run_subprocess([], timeout=5)


def test_retries_recover_from_transient_failure(tmp_path: Path) -> None:
    counter_file = tmp_path / "attempts.txt"
    script = tmp_path / "flaky.py"
    script.write_text(
        "import sys\n"
        f"p = r'{counter_file}'\n"
        "n = 0\n"
        "try:\n"
        "    n = int(open(p).read())\n"
        "except OSError:\n"
        "    pass\n"
        "n += 1\n"
        "open(p, 'w').write(str(n))\n"
        "sys.exit(0 if n >= 2 else 1)\n",
        encoding="utf-8",
    )
    result = run_subprocess(
        [sys.executable, str(script)], timeout=10, retries=2, retry_delay_seconds=0.05
    )
    assert result.ok
    assert result.attempts == 2


def test_redact_command_masks_sensitive_values() -> None:
    display = redact_command(
        ["curl", "--header", "Authorization=Bearer abc123", "api_key=SECRET456"]
    )
    assert "SECRET456" not in display
    assert "abc123" not in display
    assert "curl" in display


def test_redact_command_leaves_ordinary_args_untouched() -> None:
    display = redact_command(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "paper.tex"]
    )
    assert display == "latexmk -pdf -interaction=nonstopmode paper.tex"
