# paperforge diff

Show what changed in a claim — either against its most recent history snapshot, or against the percentage values recorded in its linked experiment.

## Usage

```
paperforge diff CLAIM_ID [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `CLAIM_ID` | The claim ID to diff (e.g. `claim_01`) | Yes |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--against`, `-a` | `previous` | Diff target: `previous`, `HEAD~1`, or `experiment` |
| `--help` | — | Show help and exit |

## Example

```bash
# Diff against the most recent history snapshot (default)
paperforge diff claim_01

# Same as above — HEAD~1 is an alias for previous
paperforge diff claim_01 --against HEAD~1

# Compare claim text percentages against the linked experiment's metrics
paperforge diff claim_01 --against experiment

# Diff a claim in a different project
paperforge diff claim_02 --path ~/papers/my-paper
```

## Output

`--against previous` (or `HEAD~1`):
```
Diff: claim_01
vs snapshot from 2026-07-25 14:01 UTC [paperforge capture]

- text: This model achieves 98.4% accuracy.
+ text: This model achieves 97.8% accuracy.

1 field(s) changed
```

If nothing changed since the last snapshot, prints a green panel and exits 0:
```
╭────────────────────────────────────────────────────╮
│ claim_01 is unchanged since last snapshot.         │
│ Last recorded: 2026-07-25 14:01 UTC                │
╰────────────────────────────────────────────────────╯
```

`--against experiment`:
```
      Claim vs Experiment: claim_01 vs exp_01
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Claim Text Value ┃ Closest Metric ┃ Metric Value ┃ Status      ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ 97.8%            │ accuracy       │ 98.4         │ ✗ mismatch  │
└──────────────────┴────────────────┴──────────────┴─────────────┘
```

If the claim text contains no percentage values:
```
claim_01 contains no percentage values to compare.
```

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| Claim ID not found | `Claim '<id>' not found.` (exit 1) |
| `--against experiment` and claim has no linked experiment | `<claim_id> has no linked experiment.` (exit 1) |
| `--against experiment` and the linked experiment file doesn't exist | `Experiment '<exp_id>' not found.` (exit 1) |
| Unknown `--against` value | `Unknown diff target '<value>'. Use: previous, HEAD~1, experiment` (exit 1) |

## Notes

- **`previous` / `HEAD~1`** compares the current claim file against the single
  most recent entry in `.paperforge/history/<claim_id>.yaml`. Requires at least
  one history entry — if there's no history yet, prints a yellow message and
  exits 0 (nothing to diff against is not an error).
- **`experiment`** extracts every percentage number from the claim's `text`
  field and finds the closest metric (by absolute difference) in the linked
  experiment's `metrics`. Each is marked consistent (green) if within tolerance
  of that metric, or a mismatch (red) otherwise — this is the same matching
  logic `paperforge doctor`'s `METRIC_CLAIM_MISMATCH` check uses.
- This command is **read-only**; it never modifies any file, unlike `doctor --fix`.
- Use `paperforge log` to see the full history rather than just the latest diff.

**Related commands:** `paperforge log`, `paperforge doctor`, `paperforge impact`
