"""Claim history storage: append-only snapshots recorded on every write."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

HISTORY_DIR = "history"


@dataclass
class ClaimSnapshot:
    recorded_at: datetime
    recorded_by: str
    snapshot: dict[str, Any]


def history_path(paperforge_dir: Path, claim_id: str) -> Path:
    return paperforge_dir / HISTORY_DIR / f"{claim_id}.yaml"


def record_snapshot(
    paperforge_dir: Path,
    claim_id: str,
    claim_data: dict[str, Any],
    recorded_by: str,
) -> None:
    """Append current claim state to its history file before the claim is updated."""
    hist_dir = paperforge_dir / HISTORY_DIR
    hist_dir.mkdir(parents=True, exist_ok=True)

    path = history_path(paperforge_dir, claim_id)

    existing: list[dict[str, Any]] = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, list):
                existing = data

    entry = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "recorded_by": recorded_by,
        "snapshot": claim_data,
    }
    existing.append(entry)

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(existing, f, default_flow_style=False, allow_unicode=True)


def load_history(
    paperforge_dir: Path,
    claim_id: str,
) -> list[ClaimSnapshot]:
    """Load full history for a claim, newest-first. Empty list if none exists."""
    path = history_path(paperforge_dir, claim_id)
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        return []

    snapshots = []
    for entry in data:
        try:
            recorded_at = datetime.fromisoformat(entry["recorded_at"])
            snapshots.append(
                ClaimSnapshot(
                    recorded_at=recorded_at,
                    recorded_by=entry.get("recorded_by", "unknown"),
                    snapshot=entry.get("snapshot", {}),
                )
            )
        except (KeyError, ValueError):
            continue

    return list(reversed(snapshots))


def diff_snapshots(
    old: dict[str, Any],
    new: dict[str, Any],
) -> dict[str, tuple[Any, Any]]:
    """Compare two claim snapshot dicts. Returns {field: (old, new)} for changes."""
    all_keys = set(old.keys()) | set(new.keys())
    changes: dict[str, tuple[Any, Any]] = {}
    for key in sorted(all_keys):
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            changes[key] = (old_val, new_val)
    return changes
