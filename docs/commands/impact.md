# paperforge impact

Show all claims, sections, figures, and tables affected by a change to a given experiment.

## Usage

```
paperforge impact EXPERIMENT_ID [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `EXPERIMENT_ID` | The experiment ID to trace (e.g. `exp_01`, `exp_27`) | Yes |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--help` | — | Show help and exit |

## Example

```bash
# Show impact of exp_01
paperforge impact exp_01

# Check impact in a different project
paperforge impact exp_27 --path ~/papers/my-paper
```

## Output

```
Source: Experiment exp_01

Affected Claims:
  claim_02    "This model achieves 98.4% accuracy on CICDDoS2019."
  claim_05    "Our approach reduces false positives by 14.2%."

Affected Sections:
  abstract
  results

Affected Figures:
  fig_01

Affected Tables:
  tbl_02

Verification Status:
  2 claims require verification
  1 figure should be reviewed
  1 table should be reviewed
```

If no claims are linked, prints a yellow panel and exits 0:
```
╭────────────────────────────────────────────────────╮
│ No claims are linked to experiment 'exp_01'.       │
│ Add claims using `paperforge capture`.             │
╰────────────────────────────────────────────────────╯
```

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| Experiment ID not found | `Experiment 'exp_99' not found.` followed by `Available experiments: [...]` and `Check .paperforge/experiments/` (exit 1) |

## Notes

- Pure dependency graph traversal — no confidence scores or AI involved.
- Exits 0 with a yellow panel if the experiment exists but has no linked claims.
- Sections are deduplicated even if multiple claims reference the same section.
- Figures and tables are aggregated from all affected claims.
- Use this after re-running an experiment to identify exactly what needs updating in your paper.

**Related commands:** `paperforge doctor`, `paperforge capture`, `paperforge find`
