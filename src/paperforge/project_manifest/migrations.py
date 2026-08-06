"""Manifest schema migrations.

Migrations are registered as ``(from_version) -> (to_version, transform)``
steps and applied one at a time until the document reaches
:data:`~paperforge.project_manifest.models.CURRENT_SCHEMA_VERSION`. A
manifest declaring a version newer than current is rejected outright
(:class:`UnsupportedSchemaVersionError`) rather than guessed at.

Only one real migration ships today: ``"0.1"`` (a flat, pre-canonical
layout used by early experimental drafts of this schema) to ``"1.0"``. It
exists to prove the mechanism end-to-end and to give downstream tooling a
stable place to add future migrations without redesigning the registry.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

from paperforge.project_manifest.errors import UnsupportedSchemaVersionError, issue
from paperforge.project_manifest.models import CURRENT_SCHEMA_VERSION
from paperforge.utils.atomic import atomic_write_text

MigrationFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class MigrationStep:
    from_version: str
    to_version: str
    description: str
    transform: MigrationFn


@dataclass
class MigrationReport:
    source_version: str
    target_version: str
    applied_steps: list[str] = field(default_factory=list)
    transformations: list[str] = field(default_factory=list)
    unresolved_conflicts: list[str] = field(default_factory=list)
    source_hash: str = ""
    output_hash: str = ""
    changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_version": self.source_version,
            "target_version": self.target_version,
            "applied_steps": self.applied_steps,
            "transformations": self.transformations,
            "unresolved_conflicts": self.unresolved_conflicts,
            "source_hash": self.source_hash,
            "output_hash": self.output_hash,
            "changed": self.changed,
        }


def _parse_version(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in str(v).split("."))
    except ValueError:
        raise UnsupportedSchemaVersionError(
            [
                issue(
                    "MANIFEST_UNPARSEABLE_VERSION",
                    f"schema_version '{v}' is not a dotted-integer version string.",
                    remediation='Use a version like "1.0".',
                    field_path="schema_version",
                    severity="ERROR",
                )
            ]
        ) from None


def _migrate_0_1_to_1_0(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate the synthetic legacy 0.1 flat layout to the 1.0 canonical
    nested layout. 0.1 fields: title, author_name, author_email, venue,
    primary_question."""

    out: dict[str, Any] = {
        "schema_version": "1.0",
        "project": {
            "title": data.get("title", ""),
            "research_domain": data.get("research_domain", ""),
            "study_type": data.get("study_type", ""),
            "language": data.get("language", "English"),
            "target_venue": data.get("venue", ""),
        },
        "authors": (
            [
                {
                    "id": "author_1",
                    "name": data.get("author_name", ""),
                    "email": data.get("author_email", ""),
                }
            ]
            if data.get("author_name")
            else []
        ),
        "research": {"primary_question": data.get("primary_question", "")},
        "manuscript": {
            "generation_policy": "validation_only",
            "required_sections": list(
                data.get(
                    "sections",
                    [
                        "abstract",
                        "introduction",
                        "methodology",
                        "results",
                        "discussion",
                        "conclusion",
                    ],
                )
            ),
        },
    }
    return out


REGISTRY: list[MigrationStep] = [
    MigrationStep(
        from_version="0.1",
        to_version="1.0",
        description=(
            "Flatten legacy 0.1 top-level fields (title, author_name, "
            "author_email, venue, primary_question, sections) into the "
            "nested 1.0 project/authors/research/manuscript sections."
        ),
        transform=_migrate_0_1_to_1_0,
    ),
]

_BY_FROM_VERSION: dict[str, MigrationStep] = {s.from_version: s for s in REGISTRY}


def detect_version(data: dict[str, Any]) -> str:
    return str(data.get("schema_version", "0.1") or "0.1")


def needs_migration(data: dict[str, Any]) -> bool:
    return _parse_version(detect_version(data)) < _parse_version(CURRENT_SCHEMA_VERSION)


def is_future_version(data: dict[str, Any]) -> bool:
    return _parse_version(detect_version(data)) > _parse_version(CURRENT_SCHEMA_VERSION)


def migrate(data: dict[str, Any]) -> tuple[dict[str, Any], MigrationReport]:
    """Migrate ``data`` step by step to :data:`CURRENT_SCHEMA_VERSION`.

    Raises :class:`UnsupportedSchemaVersionError` if ``data`` declares a
    version newer than current. Returns the migrated document alongside a
    :class:`MigrationReport` describing exactly what happened, with source
    and output hashes so the caller can verify nothing else was touched.
    """

    source_version = detect_version(data)
    source_bytes = yaml.safe_dump(data, sort_keys=True).encode("utf-8")
    source_hash = hashlib.sha256(source_bytes).hexdigest()

    if is_future_version(data):
        raise UnsupportedSchemaVersionError(
            [
                issue(
                    "MANIFEST_UNSUPPORTED_FUTURE_VERSION",
                    f"Manifest declares schema_version '{source_version}', which is "
                    f"newer than the schema this installation of PaperForge supports "
                    f"('{CURRENT_SCHEMA_VERSION}').",
                    remediation="Upgrade PaperForge, or downgrade the manifest's schema_version.",
                    field_path="schema_version",
                    severity="ERROR",
                )
            ]
        )

    report = MigrationReport(
        source_version=source_version, target_version=CURRENT_SCHEMA_VERSION
    )
    current = data
    current_version = source_version
    guard = 0
    while _parse_version(current_version) < _parse_version(CURRENT_SCHEMA_VERSION):
        guard += 1
        if guard > len(REGISTRY) + 1:
            report.unresolved_conflicts.append(
                f"No migration path found from version '{current_version}' to "
                f"'{CURRENT_SCHEMA_VERSION}'."
            )
            break
        step = _BY_FROM_VERSION.get(current_version)
        if step is None:
            report.unresolved_conflicts.append(
                f"No migration registered starting at version '{current_version}'."
            )
            break
        current = step.transform(current)
        report.applied_steps.append(f"{step.from_version} -> {step.to_version}")
        report.transformations.append(step.description)
        current_version = step.to_version

    output_bytes = yaml.safe_dump(current, sort_keys=True).encode("utf-8")
    report.source_hash = source_hash
    report.output_hash = hashlib.sha256(output_bytes).hexdigest()
    report.changed = report.source_hash != report.output_hash
    return current, report


def migrate_file(
    input_path: Path,
    output_path: Path | None = None,
    *,
    dry_run: bool = False,
    make_backup: bool = True,
) -> MigrationReport:
    """Migrate a manifest file on disk. Writes atomically; on request, backs
    up the original before overwriting it in place."""

    from paperforge.project_manifest.loader import load_manifest_file

    raw = load_manifest_file(input_path)
    migrated, report = migrate(raw)

    target = output_path or input_path
    if dry_run:
        return report

    if make_backup and target == input_path and input_path.exists():
        backup_path = input_path.with_suffix(input_path.suffix + ".bak")
        atomic_write_text(backup_path, input_path.read_text(encoding="utf-8"))

    text = yaml.safe_dump(
        migrated, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    atomic_write_text(target, text)
    return report


__all__ = [
    "REGISTRY",
    "MigrationReport",
    "MigrationStep",
    "detect_version",
    "is_future_version",
    "migrate",
    "migrate_file",
    "needs_migration",
]
