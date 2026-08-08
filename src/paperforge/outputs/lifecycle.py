"""Promotion and rollback of build outputs.

Mirrors the `current`/`previous` directory-naming convention already used
by `paperforge.commands.build._rotate_output` (kept as a small, duplicated
resolution helper here rather than importing a private helper from
`build.py`, to avoid coupling this package to build.py's internals).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paperforge.core.project import PaperForgeProject
from paperforge.outputs.models import PromoteResult, RollbackResult
from paperforge.outputs.verifier import verify_output_dir
from paperforge.utils.atomic import atomic_write_text

MANIFEST_NAME = "output_manifest.json"
SWAP_MARKER_NAME = ".rollback_in_progress.json"


@dataclass
class OutputPaths:
    current: Path
    previous: Path
    manifest: Path
    swap_marker: Path


def resolve_output_paths(project_root: Path) -> OutputPaths:
    # A project may have only the canonical paperforge.project.yaml
    # manifest (no .paperforge/paper.yaml) -- e.g. one that has run
    # `manifest`/`requirements`/`plan`/`generate` but never the older
    # `.paperforge/paper.yaml`-based `build`. In that case there is no
    # project-configured build_output_dir to read, so fall back to the
    # documented default rather than letting PaperForgeProject.load's
    # FileNotFoundError propagate as an unhandled traceback.
    try:
        project = PaperForgeProject.load(project_root)
        rel_output = project.config.build_output_dir or "paper_generated/current"
    except (FileNotFoundError, OSError):
        rel_output = "paper_generated/current"
    current = project_root / rel_output
    previous_name = (
        "previous" if current.name == "current" else f"{current.name}.previous"
    )
    previous = current.parent / previous_name
    pf_dir = project_root / ".paperforge"
    return OutputPaths(
        current=current,
        previous=previous,
        manifest=pf_dir / MANIFEST_NAME,
        swap_marker=pf_dir / SWAP_MARKER_NAME,
    )


def list_outputs(project_root: Path) -> dict[str, Any]:
    paths = resolve_output_paths(project_root)
    result: dict[str, Any] = {"current": None, "previous": None, "staging": []}
    if paths.current.exists():
        result["current"] = verify_output_dir(paths.current).to_dict()
    if paths.previous.exists():
        result["previous"] = verify_output_dir(paths.previous).to_dict()
    staging_root = paths.current.parent
    if staging_root.exists():
        result["staging"] = sorted(
            p.name for p in staging_root.glob(".staging-*") if p.is_dir()
        )
    if paths.manifest.exists():
        try:
            result["last_promotion"] = json.loads(
                paths.manifest.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            result["last_promotion"] = None
    else:
        result["last_promotion"] = None
    return result


def promote(project_root: Path) -> PromoteResult:
    paths = resolve_output_paths(project_root)
    verification = verify_output_dir(paths.current)
    if not verification.ok:
        return PromoteResult(
            ok=False,
            current_path=str(paths.current),
            verification=verification,
            message="Promotion refused: current output failed verification. "
            "current/previous were not modified.",
        )

    manifest = {
        "promoted_at": datetime.now(UTC).isoformat(),
        "current_path": str(paths.current),
        "artifacts": [a.to_dict() for a in verification.artifacts if a.exists],
    }
    atomic_write_text(
        paths.manifest, json.dumps(manifest, indent=2, ensure_ascii=False)
    )
    return PromoteResult(
        ok=True,
        current_path=str(paths.current),
        verification=verification,
        manifest_path=str(paths.manifest),
        message="Promoted: current output verified and recorded.",
    )


def _write_marker(paths: OutputPaths, step: int, tmp_dir: Path) -> None:
    atomic_write_text(
        paths.swap_marker,
        json.dumps(
            {
                "step": step,
                "tmp_dir": str(tmp_dir),
                "current": str(paths.current),
                "previous": str(paths.previous),
            },
            indent=2,
        ),
    )


def _read_marker(paths: OutputPaths) -> dict[str, Any] | None:
    if not paths.swap_marker.exists():
        return None
    try:
        return json.loads(paths.swap_marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def rollback(project_root: Path) -> RollbackResult:
    paths = resolve_output_paths(project_root)
    marker = _read_marker(paths)
    resumed = marker is not None
    tmp_dir = (
        Path(marker["tmp_dir"]) if marker else paths.current.parent / ".rollback_tmp"
    )

    previous_has_content = paths.previous.exists() and any(paths.previous.iterdir())
    if marker is None and not previous_has_content:
        return RollbackResult(
            ok=False,
            current_path=str(paths.current),
            previous_path=str(paths.previous),
            message="Nothing to roll back to: no 'previous' output exists.",
        )

    step = marker["step"] if marker else 0

    # Step 1: current -> tmp
    if step < 1:
        if paths.current.exists():
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)
            paths.current.rename(tmp_dir)
        _write_marker(paths, 1, tmp_dir)
        step = 1
    # Step 2: previous -> current
    if step < 2:
        if paths.previous.exists():
            paths.previous.rename(paths.current)
        _write_marker(paths, 2, tmp_dir)
        step = 2
    # Step 3: tmp -> previous
    if step < 3:
        if tmp_dir.exists():
            if paths.previous.exists():
                shutil.rmtree(paths.previous)
            tmp_dir.rename(paths.previous)
        step = 3

    if paths.swap_marker.exists():
        paths.swap_marker.unlink()

    verification_after = (
        verify_output_dir(paths.current) if paths.current.exists() else None
    )
    return RollbackResult(
        ok=True,
        current_path=str(paths.current),
        previous_path=str(paths.previous),
        resumed_interrupted=resumed,
        verification_after=verification_after,
        message="Rollback complete: current and previous swapped."
        + (" (resumed an interrupted rollback)" if resumed else ""),
    )


__all__ = [
    "MANIFEST_NAME",
    "SWAP_MARKER_NAME",
    "OutputPaths",
    "list_outputs",
    "promote",
    "resolve_output_paths",
    "rollback",
]
