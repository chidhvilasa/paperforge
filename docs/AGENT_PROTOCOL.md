# Agent protocol

PaperForge commands that support `--json` print exactly one JSON object to
stdout and exit with a stable, documented code — never a Python traceback
by default. This document is the authoritative reference for that
envelope and exit-code table.

## JSON envelope

```json
{
  "command": "manifest.validate",
  "status": "success",
  "exit_code": 0,
  "version": "1.7.0",
  "project_root": "/path/to/project",
  "outputs": {},
  "summary": { "errors": 0, "warnings": 0 },
  "warnings": [],
  "errors": []
}
```

- `status` is `"success"`, `"warning"`, or `"failure"`.
- `errors`/`warnings` are lists of `{code, field_path, message,
  remediation, severity, line, column}` — `line`/`column` are `null` when
  not applicable (most non-YAML-parse errors).
- `outputs` is command-specific (documented per command below).

## Commands supporting `--json` today

| Command | Notes |
|---|---|
| `paperforge inspect --json` | Pre-dates this pass; own envelope shape (not the shared one above). |
| `paperforge manifest schema --json` | `outputs.schema` = the JSON Schema document. |
| `paperforge manifest validate PATH --json` | `outputs.mode`. |
| `paperforge manifest migrate --json` | `outputs.report`, `outputs.dry_run` or `outputs.output_path`. |
| `paperforge requirements --json` | `outputs.total_requirements`, `outputs.satisfied`, `outputs.blocking`, `outputs.written`. |
| `paperforge plan --json` | `outputs.plan`, `outputs.approval_status`, `outputs.approval_stale_reasons`. |
| `paperforge generate --json` | `outputs.mode`, `outputs.provider`, `outputs.sections`. |
| `paperforge provenance show\|validate\|export --json` | `outputs.index`/`outputs.records` (show/export), errors list (validate). |
| `paperforge outputs list\|verify --json` | `outputs.current`/`outputs.previous`/`outputs.staging` (list), `outputs.verification` (verify). |
| `paperforge promote --json` | `outputs.result` (`PromoteResult`). |
| `paperforge rollback --json` | `outputs.result` (`RollbackResult`). |
| `paperforge references --json` | `outputs.report` (`ReferenceVerificationReport`). |
| `paperforge doctor --json` | Pre-dates this pass; own envelope shape. |
| `paperforge preflight --json` | Pre-dates this pass; own envelope shape. |

`paperforge init` and `paperforge build` do not yet support `--json` —
see "Remaining limitations" in the release notes. Agents driving those two
commands today should parse console output or rely on exit codes /
generated file presence.

## Exit-code groups

| Range | Meaning |
|---|---|
| `0` | Success |
| `2` | CLI misuse (bad arguments/flags) |
| `10` | Invalid manifest |
| `11` | Unsupported (future) schema version |
| `12` | Migration required before this manifest can be used |
| `20` | Missing structural requirement |
| `21` | Submission blocker (mode=submission validation/requirements failure) |
| `30` | Unsafe manifest or path (safe-YAML/path-security rejection) |
| `40` | Generation/provenance error (e.g. no valid approved plan) |
| `50` | Build/preflight error *(reserved — build/preflight don't use the shared envelope yet)* |
| `60` | References error |
| `70` | Packaging/output-lifecycle error (`outputs`/`promote`/`rollback`) |
| `80` | Timeout *(reserved for future subprocess-runner integration into a `--json` command)* |
| `90` | Internal error *(reserved)* |

No command using the shared envelope waits for terminal input in
non-interactive/`--json` mode — every command documented in the table
above runs to completion or fails with a structured error, never a
blocking prompt.

## Recommended agent workflow

See [AGENT_INTEGRATION.md](AGENT_INTEGRATION.md) for a worked, step-by-step
example using `examples/agent_project/`.
