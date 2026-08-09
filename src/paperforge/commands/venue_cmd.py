"""Implementation behind `paperforge venue show|validate`.

Distinct from the pre-existing `paperforge venues` (plural -- lists every
built-in plugin). This is the per-venue, versioned-metadata view: adapter
version, source URL, and checked date, so callers can tell a
verified-and-dated rule from a heuristic default.
"""

from __future__ import annotations

from pathlib import Path

from paperforge.utils.envelope import (
    EXIT_CLI_MISUSE,
    EXIT_EVIDENCE_ERROR,
    EXIT_SUCCESS,
    ResultEnvelope,
    print_envelope,
)
from paperforge.venues.custom import CustomVenueError, load_custom_venue
from paperforge.venues.registry import get_plugin, list_plugins


def _echo(env: ResultEnvelope, json_output: bool, lines: list[str]) -> int:
    if json_output:
        return print_envelope(env)
    import typer

    for line in lines:
        typer.echo(line)
    return env.exit_code


def _plugin_dict(plugin: object) -> dict[str, object]:
    from paperforge.venues.base import VenuePlugin

    assert isinstance(plugin, VenuePlugin)
    return {
        "id": plugin.name,
        "display_name": plugin.display_name,
        "documentclass": plugin.latex_documentclass,
        "required_sections": list(plugin.required_sections),
        "max_pages": plugin.max_pages,
        "adapter_version": plugin.adapter_version,
        "checked_date": plugin.checked_date,
        "source_url": plugin.source_url,
        "source_description": plugin.source_description,
        "source_verified": bool(plugin.checked_date),
    }


def run_show(
    *,
    project_root: Path,
    target: str | None,
    custom_file: str | None,
    json_output: bool,
) -> int:
    env = ResultEnvelope(command="venue show", project_root=str(project_root))

    if custom_file:
        try:
            cfg = load_custom_venue(project_root, custom_file)
        except CustomVenueError as exc:
            env.errors.append(
                {
                    "code": "CUSTOM_VENUE_ERROR",
                    "field_path": "",
                    "message": str(exc),
                    "remediation": "",
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
            env.finalize(EXIT_EVIDENCE_ERROR)
            return _echo(env, json_output, [str(exc)])
        data = cfg.to_dict()
        data["source_verified"] = bool(cfg.checked_date)
        env.outputs["venue"] = data
        env.outputs["kind"] = "custom"
        env.finalize(EXIT_EVIDENCE_ERROR)
        env.status, env.exit_code = "success", EXIT_SUCCESS
        lines = [f"Custom venue: {cfg.display_name or cfg.venue_id or custom_file}"]
        if not cfg.checked_date:
            lines.append("  WARNING: no checked_date -- treat as unverified.")
        return _echo(env, json_output, lines)

    if not target:
        env.errors.append(
            {
                "code": "VENUE_TARGET_REQUIRED",
                "field_path": "",
                "message": "Provide --target <venue-id> or --custom-file <path>.",
                "remediation": f"Available: {', '.join(list_plugins())}",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_CLI_MISUSE)
        return _echo(env, json_output, [env.errors[0]["message"]])

    try:
        plugin = get_plugin(target)
    except ValueError as exc:
        env.errors.append(
            {
                "code": "UNKNOWN_VENUE",
                "field_path": "",
                "message": str(exc),
                "remediation": "",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_CLI_MISUSE)
        return _echo(env, json_output, [str(exc)])

    data = _plugin_dict(plugin)
    env.outputs["venue"] = data
    env.outputs["kind"] = "builtin"
    if not data["source_verified"]:
        env.warnings.append(
            {
                "code": "VENUE_SOURCE_UNVERIFIED",
                "field_path": "",
                "message": f"'{target}' has no checked_date: these are PaperForge heuristic defaults, not verified against a dated official source.",
                "remediation": "Confirm current requirements against the venue's own CFP/author guide before submission.",
                "severity": "WARNING",
                "line": None,
                "column": None,
            }
        )
    env.finalize(EXIT_EVIDENCE_ERROR)
    if not env.errors:
        env.status = "success" if not env.warnings else "warning"
        env.exit_code = EXIT_SUCCESS

    lines = [
        f"{data['display_name']} ({data['id']}) -- adapter v{data['adapter_version']}"
    ]
    lines.append(f"  source_verified: {data['source_verified']}")
    if data["source_url"]:
        lines.append(f"  source_url: {data['source_url']}")
    return _echo(env, json_output, lines)


def run_validate(
    *,
    project_root: Path,
    target: str | None,
    custom_file: str | None,
    json_output: bool,
) -> int:
    env = ResultEnvelope(command="venue validate", project_root=str(project_root))

    if custom_file:
        try:
            cfg = load_custom_venue(project_root, custom_file)
        except CustomVenueError as exc:
            env.errors.append(
                {
                    "code": "CUSTOM_VENUE_ERROR",
                    "field_path": "",
                    "message": str(exc),
                    "remediation": "",
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
            env.finalize(EXIT_EVIDENCE_ERROR)
            return _echo(env, json_output, [str(exc)])
        if not cfg.venue_id:
            env.errors.append(
                {
                    "code": "CUSTOM_VENUE_MISSING_ID",
                    "field_path": "venue_id",
                    "message": "Custom venue file has no venue_id.",
                    "remediation": "",
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
        if not cfg.checked_date:
            env.warnings.append(
                {
                    "code": "VENUE_SOURCE_UNVERIFIED",
                    "field_path": "checked_date",
                    "message": "Custom venue has no checked_date -- treat as unverified.",
                    "remediation": "",
                    "severity": "WARNING",
                    "line": None,
                    "column": None,
                }
            )
        env.outputs["venue"] = cfg.to_dict()
        env.finalize(EXIT_EVIDENCE_ERROR)
        if not env.errors:
            env.status = "success" if not env.warnings else "warning"
            env.exit_code = EXIT_SUCCESS
        return _echo(
            env,
            json_output,
            [
                f"Custom venue '{cfg.venue_id or custom_file}': {len(env.errors)} errors, {len(env.warnings)} warnings."
            ],
        )

    if not target:
        env.errors.append(
            {
                "code": "VENUE_TARGET_REQUIRED",
                "field_path": "",
                "message": "Provide --target <venue-id> or --custom-file <path>.",
                "remediation": "",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_CLI_MISUSE)
        return _echo(env, json_output, [env.errors[0]["message"]])

    try:
        plugin = get_plugin(target)
    except ValueError as exc:
        env.errors.append(
            {
                "code": "UNKNOWN_VENUE",
                "field_path": "",
                "message": str(exc),
                "remediation": "",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_CLI_MISUSE)
        return _echo(env, json_output, [str(exc)])

    data = _plugin_dict(plugin)
    if not data["source_verified"]:
        env.warnings.append(
            {
                "code": "VENUE_SOURCE_UNVERIFIED",
                "field_path": "",
                "message": f"'{target}' has no checked_date.",
                "remediation": "",
                "severity": "WARNING",
                "line": None,
                "column": None,
            }
        )
    env.outputs["venue"] = data
    env.finalize(EXIT_EVIDENCE_ERROR)
    if not env.errors:
        env.status = "success" if not env.warnings else "warning"
        env.exit_code = EXIT_SUCCESS
    return _echo(
        env,
        json_output,
        [f"'{target}': {len(env.errors)} errors, {len(env.warnings)} warnings."],
    )


__all__ = ["run_show", "run_validate"]
