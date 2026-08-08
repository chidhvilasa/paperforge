"""Implementation behind `paperforge provenance show|validate|export`."""

from __future__ import annotations

import json as json_module
from pathlib import Path

from paperforge.generation.provenance import load_provenance, validate_provenance
from paperforge.project_manifest.errors import ManifestError
from paperforge.project_manifest.loader import load_manifest_file
from paperforge.project_manifest.models import ProjectManifest
from paperforge.utils.envelope import (
    EXIT_GENERATION_PROVENANCE_ERROR,
    EXIT_MISSING_STRUCTURAL_REQUIREMENT,
    EXIT_SUCCESS,
    EXIT_UNSAFE_MANIFEST_OR_PATH,
    ResultEnvelope,
    print_envelope,
)

DEFAULT_MANIFEST_FILENAME = "paperforge.project.yaml"


def _load_manifest(
    project_root: Path, manifest_path: Path | None
) -> tuple[ProjectManifest | None, dict | None]:
    manifest_file = manifest_path or (project_root / DEFAULT_MANIFEST_FILENAME)
    if not manifest_file.exists():
        return None, {
            "code": "MANIFEST_NOT_FOUND",
            "field_path": "",
            "message": f"No manifest found at {manifest_file}.",
            "remediation": "Run `paperforge init` or create paperforge.project.yaml.",
            "severity": "ERROR",
            "line": None,
            "column": None,
        }
    try:
        raw = load_manifest_file(manifest_file)
    except ManifestError as exc:
        return None, exc.issues[0].to_dict() if exc.issues else None
    return ProjectManifest.from_dict(raw), None


def run_show(*, project_root: Path, json_output: bool) -> int:
    env = ResultEnvelope(command="provenance.show", project_root=str(project_root))
    index, records_by_section = load_provenance(project_root)
    env.outputs["index"] = index
    env.outputs["records"] = {
        name: [r.to_dict() for r in recs] for name, recs in records_by_section.items()
    }
    env.finalize(EXIT_GENERATION_PROVENANCE_ERROR)
    env.status, env.exit_code = "success", EXIT_SUCCESS
    if json_output:
        return print_envelope(env)

    import typer

    sections = index.get("sections", {})
    if not sections:
        typer.echo("No provenance recorded yet.")
    for name, meta in sections.items():
        typer.echo(
            f"{name}: {meta.get('sentence_count', 0)} sentence(s), mode={meta.get('mode')}"
        )
    return EXIT_SUCCESS


def run_validate(
    *, project_root: Path, manifest_path: Path | None, json_output: bool
) -> int:
    env = ResultEnvelope(command="provenance.validate", project_root=str(project_root))
    manifest, err = _load_manifest(project_root, manifest_path)
    if err is not None or manifest is None:
        env.errors.append(
            err
            or {
                "code": "MANIFEST_ERROR",
                "message": "unknown manifest error",
                "severity": "ERROR",
                "field_path": "",
                "remediation": "",
                "line": None,
                "column": None,
            }
        )
        env.finalize(
            EXIT_UNSAFE_MANIFEST_OR_PATH
            if (err and "UNSAFE" in str(err.get("code", "")))
            else EXIT_MISSING_STRUCTURAL_REQUIREMENT
        )
        if json_output:
            return print_envelope(env)
        import typer

        typer.echo(env.errors[0]["message"])
        return env.exit_code

    issues = validate_provenance(project_root, manifest)
    for i in issues:
        env.errors.append(
            {
                "code": i["code"],
                "field_path": i.get("section", ""),
                "message": i["message"],
                "remediation": "",
                "severity": i.get("severity", "ERROR"),
                "line": None,
                "column": None,
            }
        )
    env.finalize(EXIT_GENERATION_PROVENANCE_ERROR)
    if not env.errors:
        env.status, env.exit_code = "success", EXIT_SUCCESS

    if json_output:
        return print_envelope(env)

    import typer

    if not issues:
        typer.echo("Provenance is valid: no issues found.")
    else:
        typer.echo(f"Provenance validation found {len(issues)} issue(s):")
        for i in issues:
            typer.echo(
                f"  [{i['severity']}] {i['code']} ({i.get('section', '')}): {i['message']}"
            )
    return env.exit_code


def run_export(*, project_root: Path, output: Path | None, json_output: bool) -> int:
    env = ResultEnvelope(command="provenance.export", project_root=str(project_root))
    index, records_by_section = load_provenance(project_root)
    payload = {
        "index": index,
        "records": {
            name: [r.to_dict() for r in recs]
            for name, recs in records_by_section.items()
        },
    }
    if output:
        output.write_text(
            json_module.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        env.outputs["written_to"] = str(output)
    else:
        env.outputs["export"] = payload
    env.finalize(EXIT_GENERATION_PROVENANCE_ERROR)
    env.status, env.exit_code = "success", EXIT_SUCCESS
    if json_output:
        return print_envelope(env)

    import typer

    if output:
        typer.echo(f"Provenance exported to {output}")
    else:
        typer.echo(json_module.dumps(payload, indent=2, ensure_ascii=False))
    return EXIT_SUCCESS


__all__ = ["run_export", "run_show", "run_validate"]
