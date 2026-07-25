# paperforge log

Show the full change history of a claim, newest first, with per-entry diffs against the previous snapshot.

## Usage

```
paperforge log CLAIM_ID [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `CLAIM_ID` | The claim ID to show history for (e.g. `claim_01`) | Yes |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--limit`, `-n` | `10` | Maximum number of history entries to show |
| `--help` | — | Show help and exit |

## Example

```bash
# Show full history for claim_01
paperforge log claim_01

# Show only the last 3 changes
paperforge log claim_01 --limit 3

# Check history in a different project
paperforge log claim_02 --path ~/papers/vanet-paper
```

## Output

```
History: claim_01
  Current status: verified
  Showing 2 snapshot(s)
───────────────────────────────────────────────────────
╭─ 2026-07-25 14:32 UTC  [paperforge capture] ─────────╮
│ status:     unverified                               │
│ experiment: exp_01                                   │
│ sections:   results                                  │
│ text:       This model achieves 97.8% accuracy.      │
╰───────────────────────────────────────────────────────╯
[dim]Changed from previous: status, text[/dim]
╭─ 2026-07-25 14:01 UTC  [paperforge capture] ─────────╮
│ status:     unverified                               │
│ experiment: exp_01                                   │
│ sections:   results                                  │
│ text:       This model achieves 98.4% accuracy.      │
╰───────────────────────────────────────────────────────╯
```

If no history exists, prints a yellow panel and exits 0:
```
╭────────────────────────────────────────────────────╮
│ No history found for claim_01.                     │
│ History is recorded when PaperForge writes a claim.│
│ Capture or edit the claim to start building history.│
╰────────────────────────────────────────────────────╯
```

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| Claim ID not found | `Claim '<id>' not found in .paperforge/claims/` (exit 1) |

## Notes

- **History is recorded automatically** — you never create it manually. Every time
  `paperforge capture`, `paperforge add-claim`, or `paperforge doctor --fix` writes an
  *existing* claim file, the state before the write is appended to
  `.paperforge/history/<claim_id>.yaml`.
- **New claims have no history yet** — history only accumulates once a claim is
  updated for the first time.
- Snapshots are stored newest-last on disk (cheap to append) but always displayed
  **newest first**.
- Each panel after the first shows a `Changed from previous: ...` line listing the
  field names that differ from the next-older snapshot.
- `--limit` caps how many entries are shown — it does not delete or truncate the
  underlying history file.
- History files live in `.paperforge/history/` and should be committed to git —
  they are part of the research provenance record.
- This command is **read-only**; it never modifies any file.

**Related commands:** `paperforge diff`, `paperforge capture`, `paperforge add-claim`
