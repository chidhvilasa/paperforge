"""Implementation behind `paperforge generate`."""

from __future__ import annotations

import json as json_module
from pathlib import Path

from paperforge.generation.no_ai import generate_outline, generate_section
from paperforge.generation.provenance import build_records, write_provenance
from paperforge.generation.providers import get_provider
from paperforge.planning.approval import check_approval_validity
from paperforge.planning.builder import build_plan
from paperforge.planning.models import PlanApproval
from paperforge.project_manifest.errors import ManifestError
from paperforge.project_manifest.loader import load_manifest_file
from paperforge.project_manifest.models import ProjectManifest
from paperforge.utils.atomic import atomic_write_text
from paperforge.utils.envelope import (
    EXIT_GENERATION_PROVENANCE_ERROR,
    EXIT_MISSING_STRUCTURAL_REQUIREMENT,
    EXIT_SUCCESS,
    EXIT_UNSAFE_MANIFEST_OR_PATH,
    ResultEnvelope,
    print_envelope,
)

DEFAULT_MANIFEST_FILENAME = "paperforge.project.yaml"
GENERATED_DIRNAME = "generated_sections"


def _load_manifest(
    project_root: Path, manifest_path: Path | None
) -> tuple[dict | None, ProjectManifest | None, dict | None]:
    manifest_file = manifest_path or (project_root / DEFAULT_MANIFEST_FILENAME)
    if not manifest_file.exists():
        return (
            None,
            None,
            {
                "code": "MANIFEST_NOT_FOUND",
                "field_path": "",
                "message": f"No manifest found at {manifest_file}.",
                "remediation": "Run `paperforge init` or create paperforge.project.yaml.",
                "severity": "ERROR",
                "line": None,
                "column": None,
            },
        )
    try:
        raw = load_manifest_file(manifest_file)
    except ManifestError as exc:
        return (
            None,
            None,
            exc.issues[0].to_dict()
            if exc.issues
            else {
                "code": "MANIFEST_UNSAFE",
                "field_path": "",
                "message": str(exc),
                "remediation": "",
                "severity": "ERROR",
                "line": None,
                "column": None,
            },
        )
    return raw, ProjectManifest.from_dict(raw), None


def run(
    *,
    project_root: Path,
    manifest_path: Path | None = None,
    section: str | None = None,
    regenerate: str | None = None,
    outline_only: bool = False,
    draft_with_placeholders: bool = False,
    provider_name: str = "no_ai",
    review_existing: bool = False,
    non_interactive: bool = False,
    json_output: bool = False,
) -> int:
    env = ResultEnvelope(command="generate", project_root=str(project_root))
    _ = non_interactive  # this implementation never prompts regardless

    _raw, manifest, err = _load_manifest(project_root, manifest_path)
    if err is not None or manifest is None:
        env.errors.append(
            err
            or {
                "code": "MANIFEST_ERROR",
                "message": "unknown",
                "severity": "ERROR",
                "field_path": "",
                "remediation": "",
                "line": None,
                "column": None,
            }
        )
        env.finalize(
            EXIT_UNSAFE_MANIFEST_OR_PATH
            if (err and "UNSAFE" in err.get("code", ""))
            else EXIT_MISSING_STRUCTURAL_REQUIREMENT
        )
        if json_output:
            return print_envelope(env)
        import typer

        typer.echo(env.errors[0]["message"])
        return env.exit_code

    plan = build_plan(manifest)
    gen_dir = project_root / ".paperforge" / GENERATED_DIRNAME

    if review_existing:
        gen_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(p.stem for p in gen_dir.glob("*.md"))
        env.outputs["existing_sections"] = existing
        env.finalize(EXIT_SUCCESS)
        if json_output:
            return print_envelope(env)
        import typer

        typer.echo(f"Existing generated sections: {', '.join(existing) or '(none)'}")
        return EXIT_SUCCESS

    if outline_only:
        mode = "outline"
    elif draft_with_placeholders:
        mode = "draft_with_placeholders"
    else:
        mode = "validated"

    if mode == "validated":
        approval_path = project_root / ".paperforge" / "plan_approval.json"
        if not approval_path.exists():
            env.errors.append(
                {
                    "code": "GENERATION_PLAN_NOT_APPROVED",
                    "field_path": "",
                    "message": "No approved generation plan found.",
                    "remediation": "Run `paperforge plan --approve` first, or use --outline-only / --draft-with-placeholders.",
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
            env.finalize(EXIT_GENERATION_PROVENANCE_ERROR)
            if json_output:
                return print_envelope(env)
            import typer

            typer.echo(env.errors[0]["message"])
            return env.exit_code
        try:
            stored = PlanApproval.from_dict(
                json_module.loads(approval_path.read_text(encoding="utf-8"))
            )
        except (OSError, ValueError):
            stored = None
        reasons = (
            check_approval_validity(manifest, plan, stored, project_root=project_root)
            if stored
            else ["Approval file is corrupt."]
        )
        if reasons:
            for r in reasons:
                env.errors.append(
                    {
                        "code": "GENERATION_PLAN_APPROVAL_STALE",
                        "field_path": "",
                        "message": r,
                        "remediation": "Run `paperforge plan --approve` again.",
                        "severity": "ERROR",
                        "line": None,
                        "column": None,
                    }
                )
            env.finalize(EXIT_GENERATION_PROVENANCE_ERROR)
            if json_output:
                return print_envelope(env)
            import typer

            typer.echo("Cannot generate: plan approval is stale.")
            for r in reasons:
                typer.echo(f"  - {r}")
            return env.exit_code
        approval_status = "valid"
    else:
        approval_status = "not_required"

    if regenerate:
        target_names = [regenerate]
    elif section:
        target_names = [section]
    else:
        target_names = [s.name for s in plan.sections]

    provider = get_provider(provider_name)
    section_by_name = {s.name: s for s in plan.sections}
    results: dict[str, dict] = {}
    gen_dir.mkdir(parents=True, exist_ok=True)

    for name in target_names:
        sp = section_by_name.get(name)
        if sp is None:
            env.warnings.append(
                {
                    "code": "UNKNOWN_SECTION",
                    "field_path": "",
                    "message": f"No section named '{name}' in the plan.",
                    "remediation": "Check manuscript.required_sections / section_order.",
                    "severity": "WARNING",
                    "line": None,
                    "column": None,
                }
            )
            continue

        if mode == "outline":
            outline = generate_outline(sp)
            atomic_write_text(
                gen_dir / f"{name}.outline.json",
                json_module.dumps(outline, indent=2, ensure_ascii=False),
            )
            results[name] = {
                "mode": "outline",
                "permitted_claims": outline["permitted_claims"],
            }
            continue

        generated = generate_section(
            sp,
            manifest,
            provider=provider,
            mode=mode,
            include_placeholders=(mode == "draft_with_placeholders"),
        )
        atomic_write_text(gen_dir / f"{name}.md", generated.to_markdown())
        records = build_records(
            generated,
            provider_name=provider.config.name,
            model_identifier=provider.config.model_identifier,
            approval_status=approval_status,
        )
        write_provenance(project_root, generated, records)
        results[name] = {
            "mode": mode,
            "sentence_count": len(generated.sentences),
            "placeholder_count": sum(
                1 for s in generated.sentences if s.is_placeholder
            ),
            "warning_count": sum(len(s.warnings) for s in generated.sentences),
        }

    env.outputs["mode"] = mode
    env.outputs["provider"] = provider.config.name
    env.outputs["sections"] = results
    env.outputs["generated_dir"] = str(gen_dir)
    env.finalize(EXIT_GENERATION_PROVENANCE_ERROR)
    if not env.errors:
        env.status = "success" if not env.warnings else "warning"
        env.exit_code = EXIT_SUCCESS

    if json_output:
        return print_envelope(env)

    import typer

    typer.echo(f"Generated ({mode}): {', '.join(results) or '(none)'}")
    for name, info in results.items():
        typer.echo(f"  {name}: {info}")
    return env.exit_code


__all__ = ["run"]
