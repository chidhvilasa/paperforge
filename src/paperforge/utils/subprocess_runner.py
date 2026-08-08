"""Centralized, timeout-safe subprocess execution.

Every external tool invocation that can hang (``pdflatex``, ``latexmk``,
``bibtex``, ``biber``, and any future validation/packaging tool) should go
through :func:`run_subprocess` instead of calling :mod:`subprocess`
directly. It guarantees:

- a configurable timeout with a safe, non-zero default -- no invocation
  through this module can hang the calling process indefinitely;
- on timeout, the *entire process tree* is terminated (not just the
  immediate child), using ``taskkill /T`` on Windows and a killed process
  group on POSIX, so a stuck ``latexmk`` cannot leave orphaned
  ``pdflatex``/``bibtex`` children running after the timeout fires;
- captured stdout/stderr are always returned, even on timeout;
- a redacted, human-readable command string for logging, so secrets never
  land in a log line;
- ``shell=True`` is never used.

This directly fixes a real, observed failure mode: a stuck ``latexmk``
process (waiting on a MiKTeX "check for updates" prompt) hanging an entire
build/test run with no way to recover short of manually finding and
killing the process by PID.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 180.0

#: Argument tokens that, if they *contain* one of these (case-insensitive),
#: have their value redacted in the command's display string.
_REDACT_MARKERS = ("token", "key", "secret", "password", "auth")


class SubprocessTimeoutError(RuntimeError):
    def __init__(self, command_display: str, timeout: float) -> None:
        self.command_display = command_display
        self.timeout = timeout
        super().__init__(f"Command timed out after {timeout}s: {command_display}")


@dataclass
class RunResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float
    command_display: str
    attempts: int = 1

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def redact_command(args: list[str]) -> str:
    parts = []
    for a in args:
        lowered = a.lower()
        if any(marker in lowered for marker in _REDACT_MARKERS) and "=" in a:
            key, _, _value = a.partition("=")
            parts.append(f"{key}=***")
        else:
            parts.append(a)
    return " ".join(parts)


def _kill_process_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if sys.platform.startswith("win"):
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
    else:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except OSError:
                pass
    try:
        proc.wait(timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        pass


def _popen_kwargs_for_tree_kill() -> dict[str, object]:
    if sys.platform.startswith("win"):
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"preexec_fn": os.setsid}  # noqa: PLW1509 - deliberate, POSIX-only


def run_subprocess(
    args: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = 0,
    retry_delay_seconds: float = 1.0,
) -> RunResult:
    """Run ``args`` with a hard timeout, killing the whole process tree if
    it fires. Never uses ``shell=True``. Returns a :class:`RunResult` even
    on timeout (never raises for a timeout -- check ``result.timed_out``);
    only raises for programming errors (e.g. an empty ``args`` list) or if
    the executable genuinely cannot be started (``FileNotFoundError`` is
    caught and turned into a ``RunResult`` with ``returncode=-1``).
    """

    if not args:
        raise ValueError("args must be a non-empty list")

    command_display = redact_command(args)
    attempts = 0
    last_result: RunResult | None = None

    while attempts <= retries:
        attempts += 1
        start = time.monotonic()
        try:
            proc = subprocess.Popen(  # type: ignore[call-overload] # noqa: S603 - args is a list, shell=False always
                args,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                **_popen_kwargs_for_tree_kill(),
            )
        except FileNotFoundError as exc:
            return RunResult(
                args=list(args),
                returncode=-1,
                stdout="",
                stderr=str(exc),
                timed_out=False,
                duration_seconds=time.monotonic() - start,
                command_display=command_display,
                attempts=attempts,
            )

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            duration = time.monotonic() - start
            last_result = RunResult(
                args=list(args),
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                timed_out=False,
                duration_seconds=duration,
                command_display=command_display,
                attempts=attempts,
            )
            if last_result.ok or attempts > retries:
                return last_result
        except subprocess.TimeoutExpired:
            _kill_process_tree(proc)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except (subprocess.TimeoutExpired, ValueError):
                stdout, stderr = "", ""
            duration = time.monotonic() - start
            last_result = RunResult(
                args=list(args),
                returncode=-9,
                stdout=stdout or "",
                stderr=stderr or "",
                timed_out=True,
                duration_seconds=duration,
                command_display=command_display,
                attempts=attempts,
            )
            if attempts > retries:
                return last_result

        if attempts <= retries:
            time.sleep(retry_delay_seconds)

    assert last_result is not None
    return last_result


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "RunResult",
    "SubprocessTimeoutError",
    "redact_command",
    "run_subprocess",
]
