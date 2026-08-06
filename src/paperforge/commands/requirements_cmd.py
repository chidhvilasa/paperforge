"""Implementation behind `paperforge requirements`."""

from __future__ import annotations

import json as json_module
from pathlib import Path

import yaml

from paperforge.project_manifest.errors import ManifestError
from paperforge.project_manifest.loader import load_manifest_file
from paperforge.project_manifest.models import ProjectManifest
from paperforge.requirements_engine.engine import evaluate_requirements
from paperforge.requirements_engine.models import MODES, Requirement
from paperforge.utils.atomic import atomic_write_text
from paperforge.utils.envelope import (
    EXIT_CLI_MISUSE,
    EXIT_INVALID_MANIFEST,
    EXIT_SUBMISSION_BLOCKER,
    EXIT_UNSAFE_MANIFEST_OR_PATH,
    ResultEnvelope,
    print_envelope,
)

DEFAULT_MANIFEST_FILENAME = "paperforge.project.yaml"


def _render_missing_requirements_md(reqs: list[Requirement], mode: str) -> str:
    blockers = [r for r in reqs if r.blocks(mode)]
    unsatisfied_nonblocking = [
        r for r in reqs if not r.satisfied and not r.blocks(mode)
    ]
    lines = [f"# Missing requirements ({mode} mode)", ""]
    if not blockers and not unsatisfied_nonblocking:
        lines.append("All known requirements are satisfied.")
        return "\n".join(lines) + "\n"
    if blockers:
        lines.append(f"## Blocking {mode} ({len(blockers)})")
        lines.append("")
        for r in blockers:
            lines.append(
                f"- **{r.id}** ({r.category}, {r.severity}): {r.title} -- status `{r.status}`"
            )
            if r.remediation:
                lines.append(f"  - remediation: {r.remediation}")
        lines.append("")
    if unsatisfied_nonblocking:
        lines.append(
            f"## Not blocking {mode}, but unsatisfied ({len(unsatisfied_nonblocking)})"
        )
        lines.append("")
        for r in unsatisfied_nonblocking:
            lines.append(f"- {r.id} ({r.category}): {r.title} -- status `{r.status}`")
        lines.append("")
    return "\n".join(lines)


def run(
    *,
    project_root: Path,
    manifest_path: Path | None = None,
    mode: str = "draft",
    json_output: bool = False,
    output_dir: Path | None = None,
) -> int:
    env = ResultEnvelope(command="requirements", project_root=str(project_root))

    if mode not in MODES:
        env.errors.append(
            {
                "code": "INVALID_MODE",
                "field_path": "",
                "message": f"Unknown mode '{mode}'. Expected one of {MODES}.",
                "remediation": "Use --mode outline|draft|review|submission.",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_CLI_MISUSE)
        if json_output:
            return print_envelope(env)
        import typer

        typer.echo(f"error: unknown mode '{mode}'. Expected one of {MODES}.")
        return env.exit_code

    manifest_file = manifest_path or (project_root / DEFAULT_MANIFEST_FILENAME)
    if not manifest_file.exists():
        env.errors.append(
            {
                "code": "MANIFEST_NOT_FOUND",
                "field_path": "",
                "message": f"No manifest found at {manifest_file}.",
                "remediation": "Run `paperforge init` or create paperforge.project.yaml.",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_INVALID_MANIFEST)
        if json_output:
            return print_envelope(env)
        import typer

        typer.echo(env.errors[0]["message"])
        return env.exit_code

    try:
        raw = load_manifest_file(manifest_file)
    except ManifestError as exc:
        for iss in exc.issues:
            env.errors.append(iss.to_dict())
        env.finalize(EXIT_UNSAFE_MANIFEST_OR_PATH)
        if json_output:
            return print_envelope(env)
        import typer

        for e in env.errors:
            typer.echo(f"[{e['severity']}] {e['code']}: {e['message']}")
        return env.exit_code

    manifest = ProjectManifest.from_dict(raw)
    reqs = evaluate_requirements(manifest, project_root=project_root, mode=mode)

    target_dir = output_dir or (project_root / ".paperforge")
    target_dir.mkdir(parents=True, exist_ok=True)

    reqs_data = [r.to_dict() for r in reqs]
    atomic_write_text(
        target_dir / "requirements.yaml",
        yaml.safe_dump(
            {"mode": mode, "requirements": reqs_data},
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    atomic_write_text(
        target_dir / "requirements.json",
        json_module.dumps(
            {"mode": mode, "requirements": reqs_data}, indent=2, ensure_ascii=False
        ),
    )
    missing_md = _render_missing_requirements_md(reqs, mode)
    atomic_write_text(target_dir / "missing_requirements.md", missing_md)

    blockers = [r for r in reqs if r.blocks(mode)]
    for r in blockers:
        env.errors.append(
            {
                "code": r.id,
                "field_path": ", ".join(r.related_fields),
                "message": r.title,
                "remediation": r.remediation,
                "severity": r.severity,
                "line": None,
                "column": None,
            }
        )
    warnings_only = [
        r
        for r in reqs
        if not r.satisfied and not r.blocks(mode) and r.severity == "WARNING"
    ]
    for r in warnings_only:
        env.warnings.append(
            {
                "code": r.id,
                "field_path": ", ".join(r.related_fields),
                "message": r.title,
                "remediation": r.remediation,
                "severity": r.severity,
                "line": None,
                "column": None,
            }
        )

    env.outputs["mode"] = mode
    env.outputs["total_requirements"] = len(reqs)
    env.outputs["satisfied"] = sum(1 for r in reqs if r.satisfied)
    env.outputs["blocking"] = len(blockers)
    env.outputs["written"] = {
        "yaml": str(target_dir / "requirements.yaml"),
        "json": str(target_dir / "requirements.json"),
        "missing_md": str(target_dir / "missing_requirements.md"),
    }
    env.finalize(
        EXIT_SUBMISSION_BLOCKER if mode == "submission" else EXIT_INVALID_MANIFEST
    )
    if not env.errors:
        env.status = "success" if not env.warnings else "warning"
        env.exit_code = 0

    if json_output:
        return print_envelope(env)

    import typer

    typer.echo(
        f"Requirements ({mode} mode): {env.outputs['satisfied']}/{env.outputs['total_requirements']} satisfied, "
        f"{len(blockers)} blocking."
    )
    for r in blockers:
        typer.echo(f"  [{r.severity}] {r.id}: {r.title} (status={r.status})")
        if r.remediation:
            typer.echo(f"      remediation: {r.remediation}")
    typer.echo(f"\nWritten: {target_dir / 'missing_requirements.md'}")
    return env.exit_code


__all__ = ["run"]
