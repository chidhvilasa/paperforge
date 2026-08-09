"""Implementation behind `paperforge outputs list|verify`, `promote`, and
`rollback`."""

from __future__ import annotations

from pathlib import Path

from paperforge.outputs.lifecycle import (
    list_outputs,
    resolve_output_paths,
)
from paperforge.outputs.lifecycle import (
    promote as do_promote,
)
from paperforge.outputs.lifecycle import (
    rollback as do_rollback,
)
from paperforge.outputs.verifier import verify_output_dir
from paperforge.utils.envelope import (
    EXIT_PACKAGING_OUTPUT_ERROR,
    EXIT_SUCCESS,
    ResultEnvelope,
    print_envelope,
)


def run_list(*, project_root: Path, json_output: bool) -> int:
    env = ResultEnvelope(command="outputs.list", project_root=str(project_root))
    env.outputs.update(list_outputs(project_root))
    env.finalize(EXIT_PACKAGING_OUTPUT_ERROR)
    env.status, env.exit_code = "success", EXIT_SUCCESS
    if json_output:
        return print_envelope(env)

    import typer

    for label in ("current", "previous"):
        info = env.outputs.get(label)
        if info is None:
            typer.echo(f"{label}: (none)")
        else:
            typer.echo(f"{label}: {info['path']} -- {'OK' if info['ok'] else 'ISSUES'}")
    if env.outputs.get("staging"):
        typer.echo(f"staging: {', '.join(env.outputs['staging'])}")
    return EXIT_SUCCESS


def run_verify(*, project_root: Path, target: str, json_output: bool) -> int:
    env = ResultEnvelope(command="outputs.verify", project_root=str(project_root))
    paths = resolve_output_paths(project_root)
    target_path = paths.current if target == "current" else paths.previous
    verification = verify_output_dir(target_path)
    env.outputs["verification"] = verification.to_dict()
    if not verification.ok:
        for issue in verification.issues:
            env.errors.append(
                {
                    "code": "OUTPUT_ARTIFACT_ISSUE",
                    "field_path": target,
                    "message": issue,
                    "remediation": "Rebuild, or run `paperforge rollback` if a previous good build exists.",
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
    env.finalize(EXIT_PACKAGING_OUTPUT_ERROR)
    if not env.errors:
        env.status, env.exit_code = "success", EXIT_SUCCESS

    if json_output:
        return print_envelope(env)

    import typer

    typer.echo(f"{target}: {'OK' if verification.ok else 'ISSUES'} ({target_path})")
    for issue in verification.issues:
        typer.echo(f"  - {issue}")
    return env.exit_code


def run_promote(*, project_root: Path, json_output: bool) -> int:
    env = ResultEnvelope(command="promote", project_root=str(project_root))
    result = do_promote(project_root)
    env.outputs["result"] = result.to_dict()
    if not result.ok:
        env.errors.append(
            {
                "code": "PROMOTION_REFUSED",
                "field_path": "",
                "message": result.message,
                "remediation": "Fix the reported artifact issues, rebuild, then retry.",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
    env.finalize(EXIT_PACKAGING_OUTPUT_ERROR)
    if not env.errors:
        env.status, env.exit_code = "success", EXIT_SUCCESS

    if json_output:
        return print_envelope(env)

    import typer

    typer.echo(result.message)
    return env.exit_code


def run_rollback(*, project_root: Path, json_output: bool) -> int:
    env = ResultEnvelope(command="rollback", project_root=str(project_root))
    result = do_rollback(project_root)
    env.outputs["result"] = result.to_dict()
    if not result.ok:
        env.errors.append(
            {
                "code": "ROLLBACK_FAILED",
                "field_path": "",
                "message": result.message,
                "remediation": "",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
    env.finalize(EXIT_PACKAGING_OUTPUT_ERROR)
    if not env.errors:
        env.status, env.exit_code = "success", EXIT_SUCCESS

    if json_output:
        return print_envelope(env)

    import typer

    typer.echo(result.message)
    return env.exit_code


__all__ = ["run_list", "run_promote", "run_rollback", "run_verify"]
