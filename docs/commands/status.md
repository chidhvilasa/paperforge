# paperforge status

Display a project health dashboard showing claim counts, section coverage, doctor issue summary, and submission readiness.

## Usage

```
paperforge status [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| None | — | — |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--help` | — | Show help and exit |

## Example

```bash
# Show status for the current project
paperforge status

# Show status for a project in another directory
paperforge status --path ~/papers/my-paper
```

## Output

Prints a rich panel with five sections:

```
╭─ PaperForge Status — Example Paper Title ──────────────────╮
│ Project                                                     │
│   Title:    Example Paper Title                             │
│   Authors:  A. Example                                      │
│   Venue:    IEEE                                            │
│   Status:   draft                                           │
│                                                             │
│ Research Graph  Count  Health                               │
│   Claims (total)    4                                       │
│   Verified          3   ✓                                   │
│   Unverified        1   !                                   │
│   Stale             0   ✓                                   │
│   Experiments       2                                       │
│   With metrics      2   ✓                                   │
│                                                             │
│ Section Coverage  Claims  Status                            │
│   abstract            2   ✓                                 │
│   results             3   ✓                                 │
│   discussion          0   empty                             │
│                                                             │
│ Doctor Summary                                              │
│   Errors:   0                                               │
│   Warnings: 1                                               │
│                                                             │
│ ✓ Ready for paperforge build                                │
╰─────────────────────────────────────────────────────────────╯
```

Panel border is **green** if submission-ready, **yellow** otherwise.

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |

## Notes

- **Read-only** — never modifies any file.
- Calls `collect_issues()` internally to compute doctor checks — same engine as `paperforge doctor`.
- **Submission-ready** is defined as: zero ERROR-severity issues **and** at least one claim.
- Never exits 1 for any reason other than missing initialization. It is a display-only dashboard.
- Section coverage counts claims that include each configured section name in their `sections` field.
- Error details (code + message) are listed under the Doctor Summary if errors exist.

**Related commands:** `paperforge doctor`, `paperforge export`, `paperforge find`
