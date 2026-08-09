"""Implementation behind the ``paperforge manifest`` command group.

Subcommands: ``schema``, ``validate``, ``migrate``. All three support a
``--json`` machine-readable mode using the shared
:class:`~paperforge.utils.envelope.ResultEnvelope`, and never print Python
tracebacks unless ``--debug`` is passed.
"""

from __future__ import annotations

import json as json_module
from pathlib import Path
from typing import Any

from paperforge.project_manifest.errors import ManifestError
from paperforge.project_manifest.loader import load_manifest_file
from paperforge.project_manifest.migrations import (
    detect_version,
    is_future_version,
    migrate,
    migrate_file,
    needs_migration,
)
from paperforge.project_manifest.schema import export_json_schema
from paperforge.project_manifest.validator import MODES, validate_manifest_dict
from paperforge.utils.envelope import (
    EXIT_CLI_MISUSE,
    EXIT_INVALID_MANIFEST,
    EXIT_MIGRATION_REQUIRED,
    EXIT_SUBMISSION_BLOCKER,
    EXIT_SUCCESS,
    EXIT_UNSAFE_MANIFEST_OR_PATH,
    EXIT_UNSUPPORTED_SCHEMA_VERSION,
    ResultEnvelope,
    print_envelope,
)

DEFAULT_MANIFEST_FILENAME = "paperforge.project.yaml"


def _console_print_issues(title: str, issues: list[dict[str, Any]]) -> None:
    import typer

    if not issues:
        return
    typer.echo(title)
    for i in issues:
        loc = f" ({i['field_path']})" if i.get("field_path") else ""
        typer.echo(f"  [{i['severity']}] {i['code']}{loc}: {i['message']}")
        if i.get("remediation"):
            typer.echo(f"      remediation: {i['remediation']}")


def run_schema(*, output: Path | None, json_output: bool) -> int:
    schema = export_json_schema()
    text = json_module.dumps(schema, indent=2, ensure_ascii=False)
    if output:
        output.write_text(text, encoding="utf-8")
    if json_output:
        env = ResultEnvelope(command="manifest.schema", outputs={"schema": schema})
        if output:
            env.outputs["written_to"] = str(output)
        env.finalize(EXIT_CLI_MISUSE)
        return print_envelope(env)

    import typer

    typer.echo(text)
    if output:
        typer.echo(f"\nSchema written to {output}")
    return EXIT_SUCCESS


def run_validate(
    path: Path, *, mode: str, json_output: bool, debug: bool = False
) -> int:
    if mode not in MODES:
        if json_output:
            env = ResultEnvelope(command="manifest.validate", project_root=str(path))
            env.errors.append(
                {
                    "code": "INVALID_MODE",
                    "field_path": "",
                    "message": f"Unknown mode '{mode}'. Expected one of {MODES}.",
                    "remediation": "Use --mode draft|review|submission.",
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
            env.finalize(EXIT_CLI_MISUSE)
            return print_envelope(env)
        import typer

        typer.echo(f"error: unknown mode '{mode}'. Expected one of {MODES}.")
        return EXIT_CLI_MISUSE

    env = ResultEnvelope(command="manifest.validate", project_root=str(path))

    try:
        raw = load_manifest_file(path)
    except ManifestError as exc:
        for iss in exc.issues:
            env.errors.append(iss.to_dict())
        env.finalize(EXIT_UNSAFE_MANIFEST_OR_PATH)
        if json_output:
            return print_envelope(env)
        _console_print_issues("Manifest is unsafe or unreadable:", env.errors)
        return env.exit_code
    except OSError as exc:
        env.errors.append(
            {
                "code": "MANIFEST_NOT_FOUND",
                "field_path": "",
                "message": str(exc),
                "remediation": f"Ensure {path} exists and is readable.",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_INVALID_MANIFEST)
        if json_output:
            return print_envelope(env)
        _console_print_issues("Manifest could not be read:", env.errors)
        return env.exit_code

    if is_future_version(raw):
        env.errors.append(
            {
                "code": "MANIFEST_UNSUPPORTED_FUTURE_VERSION",
                "field_path": "schema_version",
                "message": f"schema_version '{detect_version(raw)}' is newer than this "
                "installation of PaperForge supports.",
                "remediation": "Upgrade PaperForge.",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_UNSUPPORTED_SCHEMA_VERSION)
        if json_output:
            return print_envelope(env)
        _console_print_issues("Unsupported schema version:", env.errors)
        return env.exit_code

    if needs_migration(raw):
        env.errors.append(
            {
                "code": "MANIFEST_MIGRATION_REQUIRED",
                "field_path": "schema_version",
                "message": f"schema_version '{detect_version(raw)}' is older than current. "
                "Run `paperforge manifest migrate` first.",
                "remediation": "Run `paperforge manifest migrate --input <path>`.",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_MIGRATION_REQUIRED)
        if json_output:
            return print_envelope(env)
        _console_print_issues("Migration required:", env.errors)
        return env.exit_code

    result = validate_manifest_dict(raw, mode=mode)
    for e in result.errors:
        env.errors.append(e.to_dict())
    for w in result.warnings:
        env.warnings.append(w.to_dict())

    exit_code = (
        EXIT_SUBMISSION_BLOCKER if mode == "submission" else EXIT_INVALID_MANIFEST
    )
    env.finalize(exit_code)
    env.outputs["mode"] = mode

    if json_output:
        return print_envelope(env)

    import typer

    if env.errors:
        _console_print_issues(f"Manifest validation FAILED ({mode} mode):", env.errors)
    if env.warnings:
        _console_print_issues("Warnings:", env.warnings)
    if not env.errors and not env.warnings:
        typer.echo(f"Manifest is valid ({mode} mode). No issues found.")
    elif not env.errors:
        typer.echo(
            f"\nManifest is valid ({mode} mode) with {len(env.warnings)} warning(s)."
        )
    return env.exit_code


def run_migrate(
    *,
    input_path: Path,
    output_path: Path | None,
    dry_run: bool,
    yes: bool,
    json_output: bool,
) -> int:
    env = ResultEnvelope(command="manifest.migrate", project_root=str(input_path))

    try:
        raw = load_manifest_file(input_path)
    except ManifestError as exc:
        for iss in exc.issues:
            env.errors.append(iss.to_dict())
        env.finalize(EXIT_UNSAFE_MANIFEST_OR_PATH)
        if json_output:
            return print_envelope(env)
        _console_print_issues("Manifest is unsafe or unreadable:", env.errors)
        return env.exit_code

    if not needs_migration(raw):
        env.outputs["message"] = (
            f"Manifest is already at the current schema version ({detect_version(raw)})."
        )
        env.finalize(EXIT_INVALID_MANIFEST)
        env.status = "success"
        env.exit_code = EXIT_SUCCESS
        if json_output:
            return print_envelope(env)
        import typer

        typer.echo(env.outputs["message"])
        return EXIT_SUCCESS

    if dry_run:
        _migrated, report = migrate(raw)
        env.outputs["report"] = report.to_dict()
        env.outputs["dry_run"] = True
        env.finalize(EXIT_INVALID_MANIFEST)
        env.status = "success" if not report.unresolved_conflicts else "warning"
        env.exit_code = EXIT_SUCCESS
        for c in report.unresolved_conflicts:
            env.warnings.append(
                {
                    "code": "MIGRATION_UNRESOLVED_CONFLICT",
                    "field_path": "",
                    "message": c,
                    "remediation": "Resolve manually and re-run migration.",
                    "severity": "WARNING",
                    "line": None,
                    "column": None,
                }
            )
        if json_output:
            return print_envelope(env)
        import typer

        typer.echo(
            f"Dry run: would migrate {report.source_version} -> {report.target_version}"
        )
        for t in report.transformations:
            typer.echo(f"  - {t}")
        return EXIT_SUCCESS

    target = output_path or input_path
    if target == input_path and not yes and not json_output:
        import typer

        typer.confirm(
            f"This will overwrite {input_path} in place (a .bak backup will be kept). Continue?",
            abort=True,
        )

    report = migrate_file(input_path, output_path, dry_run=False, make_backup=True)
    env.outputs["report"] = report.to_dict()
    env.outputs["output_path"] = str(target)
    env.finalize(EXIT_INVALID_MANIFEST)
    env.status = "success"
    env.exit_code = EXIT_SUCCESS
    if json_output:
        return print_envelope(env)

    import typer

    typer.echo(f"Migrated {report.source_version} -> {report.target_version}: {target}")
    for t in report.transformations:
        typer.echo(f"  - {t}")
    return EXIT_SUCCESS


__all__ = ["DEFAULT_MANIFEST_FILENAME", "run_migrate", "run_schema", "run_validate"]
