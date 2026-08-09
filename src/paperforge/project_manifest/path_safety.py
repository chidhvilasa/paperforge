"""Path-field security for project-local paths referenced from a manifest.

Manifest fields such as ``evidence.raw_data`` or ``literature.bibliography``
hold *project-local* path strings. This module resolves those strings safely
relative to the manifest's directory and rejects anything that could escape
the project root: ``..`` traversal, external absolute paths, Windows
drive-letter absolute paths, UNC paths, and symlinks that resolve outside the
root. It never follows a symlink blindly and never executes anything.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from paperforge.project_manifest.errors import ManifestSecurityError, issue

_DRIVE_LETTER_RE = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_RE = re.compile(r"^[\\/]{2}[^\\/]")


@dataclass(frozen=True)
class PathCheckResult:
    """Outcome of resolving a single project-local path field."""

    ok: bool
    resolved: Path | None
    raw: str
    reason: str = ""
    code: str = ""


def _is_drive_absolute(raw: str) -> bool:
    return bool(_DRIVE_LETTER_RE.match(raw))


def _is_unc(raw: str) -> bool:
    return bool(_UNC_RE.match(raw))


def _is_posix_absolute(raw: str) -> bool:
    return raw.startswith("/")


def check_project_path(
    project_root: Path,
    raw_path: str,
    *,
    field_path: str = "",
    allow_external: bool = False,
) -> PathCheckResult:
    """Resolve ``raw_path`` relative to ``project_root`` and reject escapes.

    Returns a :class:`PathCheckResult`; never raises for a *bad* path so
    callers can collect many issues at once. Raises only on programming
    errors (e.g. a non-absolute ``project_root``).
    """

    if not project_root.is_absolute():
        raise ValueError("project_root must be an absolute path")

    raw = raw_path.strip() if raw_path else ""
    if not raw:
        return PathCheckResult(
            ok=False,
            resolved=None,
            raw=raw_path,
            reason="Path value is empty.",
            code="PATH_EMPTY",
        )

    if not allow_external:
        if _is_unc(raw):
            return PathCheckResult(
                ok=False,
                resolved=None,
                raw=raw_path,
                reason="UNC network paths are not permitted for project-local fields.",
                code="PATH_UNC_ESCAPE",
            )
        if _is_drive_absolute(raw):
            return PathCheckResult(
                ok=False,
                resolved=None,
                raw=raw_path,
                reason="Drive-letter absolute paths are not permitted for project-local fields.",
                code="PATH_DRIVE_ESCAPE",
            )
        if _is_posix_absolute(raw) or Path(raw).is_absolute():
            return PathCheckResult(
                ok=False,
                resolved=None,
                raw=raw_path,
                reason="Absolute paths outside the project are not permitted for this field.",
                code="PATH_EXTERNAL_ABSOLUTE",
            )

    candidate = (project_root / raw).resolve(strict=False)

    try:
        candidate.relative_to(project_root.resolve(strict=False))
    except ValueError:
        return PathCheckResult(
            ok=False,
            resolved=None,
            raw=raw_path,
            reason=f"Path '{raw}' resolves outside the project root.",
            code="PATH_TRAVERSAL_ESCAPE",
        )

    symlink_escape = _find_symlink_escape(project_root, raw)
    if symlink_escape:
        return PathCheckResult(
            ok=False,
            resolved=None,
            raw=raw_path,
            reason=(
                f"Path '{raw}' passes through a symlink "
                f"('{symlink_escape}') that resolves outside the project root."
            ),
            code="PATH_SYMLINK_ESCAPE",
        )

    return PathCheckResult(ok=True, resolved=candidate, raw=raw_path)


def _find_symlink_escape(project_root: Path, raw: str) -> str | None:
    """Walk each existing ancestor component of ``raw`` and check whether a
    symlink along the way resolves outside ``project_root``. Does not follow
    symlinks for inspection purposes beyond ``os.path.realpath`` comparison
    (no file content is read or executed).
    """

    root_real = os.path.realpath(str(project_root))
    parts = Path(raw).parts
    current = project_root
    for part in parts:
        current = current / part
        # `current.exists() or current.is_symlink()` was equivalent to just
        # `current.is_symlink()` here (Path.is_symlink() already returns
        # False, never raises, for a component that doesn't exist), so the
        # two nested checks collapse into one with no behavior change.
        if current.is_symlink():
            target_real = os.path.realpath(str(current))
            if not (
                target_real == root_real or target_real.startswith(root_real + os.sep)
            ):
                return str(current)
    return None


def enforce_project_path(
    project_root: Path,
    raw_path: str,
    *,
    field_path: str = "",
    allow_external: bool = False,
) -> Path:
    """Like :func:`check_project_path` but raises :class:`ManifestSecurityError`
    on any violation instead of returning a result object.
    """

    result = check_project_path(
        project_root, raw_path, field_path=field_path, allow_external=allow_external
    )
    if not result.ok:
        raise ManifestSecurityError(
            [
                issue(
                    result.code,
                    result.reason,
                    remediation="Use a path inside the project root, without '..' segments.",
                    field_path=field_path,
                    severity="ERROR",
                )
            ]
        )
    assert result.resolved is not None
    return result.resolved


__all__ = [
    "PathCheckResult",
    "check_project_path",
    "enforce_project_path",
]
