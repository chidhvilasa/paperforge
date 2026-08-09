"""Implementation behind `paperforge approvals list|approve|reject|reset`.

This is the author-review CLI: it does not overload the pre-existing
`paperforge review` command (AI-assisted advisory review, unrelated), so it
gets its own top-level name. See `docs/EVIDENCE_AND_PROVENANCE.md`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from paperforge.review.approvals import (
    ApprovalError,
    reconcile,
    record_decision,
    record_decision_for_section,
)
from paperforge.utils.envelope import (
    EXIT_CLI_MISUSE,
    EXIT_EVIDENCE_ERROR,
    EXIT_SUCCESS,
    ResultEnvelope,
    print_envelope,
)


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


def _echo(env: ResultEnvelope, json_output: bool, lines: list[str]) -> int:
    if json_output:
        return print_envelope(env)
    import typer

    for line in lines:
        typer.echo(line)
    return env.exit_code


def run_list(*, project_root: Path, section: str | None, json_output: bool) -> int:
    env = ResultEnvelope(command="approvals list", project_root=str(project_root))
    result = reconcile(project_root)

    entries = result.entries
    if section:
        entries = [e for e in entries if e.object_id.startswith(f"{section}:")]

    env.outputs["entries"] = [
        {
            "object_id": e.object_id,
            "object_kind": e.object_kind,
            "effective_status": e.effective_status,
            "ledger_decision": e.ledger_decision,
            "reviewer": e.reviewer,
            "timestamp": e.timestamp,
            "stale": e.stale,
        }
        for e in entries
    ]
    env.outputs["downgraded_stale"] = result.downgraded
    if result.downgraded:
        env.warnings.append(
            {
                "code": "APPROVAL_STALE_DOWNGRADED",
                "field_path": "",
                "message": f"{len(result.downgraded)} approval(s) were stale (object changed since approval) and downgraded to pending: {', '.join(result.downgraded)}.",
                "remediation": "Re-review and re-approve the affected object(s).",
                "severity": "WARNING",
                "line": None,
                "column": None,
            }
        )
    env.finalize(EXIT_EVIDENCE_ERROR)
    if not env.errors:
        env.status = "success" if not env.warnings else "warning"
        env.exit_code = EXIT_SUCCESS

    lines = [f"{len(entries)} reviewable object(s)."]
    for e in entries:
        stale_marker = " (STALE)" if e.stale else ""
        lines.append(
            f"  [{e.effective_status}]{stale_marker} {e.object_kind} {e.object_id}"
        )
    return _echo(env, json_output, lines)


def run_decide(
    *,
    project_root: Path,
    object_id: str | None,
    section: str | None,
    decision: str,
    reviewer: str | None,
    note: str,
    non_interactive: bool,
    json_output: bool,
) -> int:
    env = ResultEnvelope(
        command=f"approvals {decision}", project_root=str(project_root)
    )

    if not object_id and not section:
        env.errors.append(
            {
                "code": "APPROVALS_MISSING_TARGET",
                "field_path": "",
                "message": "Provide an object id, or --section to act on every sentence in a section.",
                "remediation": "paperforge approvals approve <ID> or --section <SECTION>.",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_CLI_MISUSE)
        return _echo(env, json_output, [env.errors[0]["message"]])

    who = reviewer or ("agent" if non_interactive else _git_user_name())

    try:
        if section:
            records = record_decision_for_section(
                project_root, section, decision, reviewer=who, note=note
            )
            env.outputs["decisions"] = [r.to_dict() for r in records]
            env.outputs["count"] = len(records)
        else:
            assert object_id is not None
            record = record_decision(
                project_root, object_id, decision, reviewer=who, note=note
            )
            env.outputs["decision"] = record.to_dict()
    except ApprovalError as exc:
        env.errors.append(
            {
                "code": "APPROVALS_OBJECT_NOT_FOUND",
                "field_path": "",
                "message": str(exc),
                "remediation": "Run `paperforge approvals list` or `paperforge evidence show` to see valid ids.",
                "severity": "ERROR",
                "line": None,
                "column": None,
            }
        )
        env.finalize(EXIT_EVIDENCE_ERROR)
        return _echo(env, json_output, [str(exc)])

    env.finalize(EXIT_EVIDENCE_ERROR)
    env.status, env.exit_code = "success", EXIT_SUCCESS
    if section:
        return _echo(
            env,
            json_output,
            [
                f"{decision}: {env.outputs['count']} sentence(s) in section '{section}' by {who}."
            ],
        )
    return _echo(env, json_output, [f"{decision}: '{object_id}' by {who}."])


__all__ = ["run_decide", "run_list"]
