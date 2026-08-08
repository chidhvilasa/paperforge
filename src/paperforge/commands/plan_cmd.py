"""Implementation behind `paperforge plan`."""

from __future__ import annotations

import json as json_module
import subprocess
from pathlib import Path

from paperforge.planning.approval import approve_plan, check_approval_validity
from paperforge.planning.builder import build_plan
from paperforge.planning.models import PlanApproval
from paperforge.project_manifest.errors import ManifestError
from paperforge.project_manifest.loader import load_manifest_file
from paperforge.project_manifest.models import ProjectManifest
from paperforge.project_manifest.validator import validate_manifest_dict
from paperforge.utils.atomic import atomic_write_text
from paperforge.utils.envelope import (
    EXIT_MISSING_STRUCTURAL_REQUIREMENT,
    EXIT_SUCCESS,
    EXIT_UNSAFE_MANIFEST_OR_PATH,
    ResultEnvelope,
    print_envelope,
)

DEFAULT_MANIFEST_FILENAME = "paperforge.project.yaml"
PLAN_MD = "generation_plan.md"
PLAN_JSON = "generation_plan.json"
APPROVAL_JSON = "plan_approval.json"


def _git_user_name() -> str:
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        name = result.stdout.strip()
        return name or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def run(
    *,
    project_root: Path,
    manifest_path: Path | None = None,
    section: str | None = None,
    approve: bool = False,
    revoke_approval: bool = False,
    mode: str = "submission",
    json_output: bool = False,
    non_interactive: bool = False,
) -> int:
    env = ResultEnvelope(command="plan", project_root=str(project_root))
    paperforge_dir = project_root / ".paperforge"

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
        env.finalize(EXIT_MISSING_STRUCTURAL_REQUIREMENT)
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
    plan = build_plan(manifest)

    paperforge_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(paperforge_dir / PLAN_MD, plan.to_markdown())
    atomic_write_text(
        paperforge_dir / PLAN_JSON,
        json_module.dumps(plan.to_dict(), indent=2, ensure_ascii=False),
    )

    approval_path = paperforge_dir / APPROVAL_JSON

    if revoke_approval:
        if approval_path.exists():
            approval_path.unlink()
        env.outputs["approval_revoked"] = True

    if approve:
        structural = validate_manifest_dict(raw, mode="draft")
        if not structural.ok:
            for se in structural.errors:
                env.errors.append(se.to_dict())
            env.finalize(EXIT_MISSING_STRUCTURAL_REQUIREMENT)
            env.outputs["reason"] = (
                "Cannot approve a plan for a structurally invalid manifest."
            )
            if json_output:
                return print_envelope(env)
            import typer

            typer.echo("Cannot approve: manifest fails structural validation.")
            for e in env.errors:
                typer.echo(f"  [{e['severity']}] {e['code']}: {e['message']}")
            return env.exit_code

        approver = "agent" if non_interactive else _git_user_name()
        approval = approve_plan(manifest, plan, approver=approver, mode=mode)
        atomic_write_text(
            approval_path,
            json_module.dumps(approval.to_dict(), indent=2, ensure_ascii=False),
        )
        env.outputs["approved"] = True
        env.outputs["approval"] = approval.to_dict()

    approval_status = "none"
    approval_reasons: list[str] = []
    if approval_path.exists() and not revoke_approval:
        try:
            stored = PlanApproval.from_dict(
                json_module.loads(approval_path.read_text(encoding="utf-8"))
            )
            approval_reasons = check_approval_validity(manifest, plan, stored)
            approval_status = "valid" if not approval_reasons else "stale"
        except (OSError, ValueError, json_module.JSONDecodeError):
            approval_status = "corrupt"

    sections_out = plan.sections
    if section:
        sections_out = [s for s in plan.sections if s.name == section]
        if not sections_out:
            env.warnings.append(
                {
                    "code": "UNKNOWN_SECTION",
                    "field_path": "",
                    "message": f"No section named '{section}' in the plan.",
                    "remediation": "Check manuscript.required_sections / section_order in the manifest.",
                    "severity": "WARNING",
                    "line": None,
                    "column": None,
                }
            )

    env.outputs["plan"] = {
        **plan.to_dict(),
        "sections": [s.to_dict() for s in sections_out],
    }
    env.outputs["approval_status"] = approval_status
    env.outputs["approval_stale_reasons"] = approval_reasons
    env.outputs["written"] = {
        "markdown": str(paperforge_dir / PLAN_MD),
        "json": str(paperforge_dir / PLAN_JSON),
    }
    env.finalize(EXIT_MISSING_STRUCTURAL_REQUIREMENT)
    if not env.errors:
        env.status = "success" if not env.warnings else "warning"
        env.exit_code = EXIT_SUCCESS

    if json_output:
        return print_envelope(env)

    import typer

    typer.echo(f"Generation plan written: {paperforge_dir / PLAN_MD}")
    typer.echo(f"Sections: {', '.join(s.name for s in plan.sections)}")
    typer.echo(f"Approval status: {approval_status}")
    for reason in approval_reasons:
        typer.echo(f"  - {reason}")
    if approve and env.outputs.get("approved"):
        typer.echo(
            f"Plan approved by '{env.outputs['approval']['approver']}' for mode={mode}."
        )
    if revoke_approval:
        typer.echo("Approval revoked.")
    return env.exit_code


__all__ = ["run"]
