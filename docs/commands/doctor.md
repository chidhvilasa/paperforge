# paperforge doctor

Run all deterministic consistency checks on a PaperForge research project and report errors and warnings.

## Usage

```
paperforge doctor [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| None | — | — |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--fix` | `False` | Auto-resolve fixable warnings (sets unverified claims to stale) |
| `--target`, `-t` | `None` | Venue target for additional checks: `ieee`, `acm`, `neurips` |
| `--help` | — | Show help and exit |

## Example

```bash
# Run all checks
paperforge doctor

# Auto-fix fixable warnings
paperforge doctor --fix

# Run with IEEE-specific checks
paperforge doctor --target ieee

# Check a project in a different directory
paperforge doctor --path ~/papers/vanet-paper
```

## Output

Prints a panel with all issues. On a clean project:
```
╭─ Doctor ──────────────────────────────────────────╮
│ ✓ All checks passed.                              │
╰───────────────────────────────────────────────────╯
```

On a project with issues, each issue is printed with its code and severity:
```
[ERROR]   ORPHAN_CLAIM          claim_03 has no linked experiment
[WARNING] UNVERIFIED_CLAIM      claim_01 status is unverified
```

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| Any ERROR-severity issue found | Exit code 1 |

## Notes

### All 20 checks

| # | Code | Severity | Description |
|---|------|----------|-------------|
| 1 | `ORPHAN_CLAIM` | ERROR | Claim has no linked experiment |
| 2 | `MISSING_EXPERIMENT` | ERROR | Claim references an experiment that does not exist |
| 3 | `STALE_CLAIM` | ERROR | Claim status is stale |
| 4 | `EMPTY_CLAIM_TEXT` | ERROR | Claim text field is empty |
| 5 | `UNVERIFIED_CLAIM` | WARNING | Claim status is unverified |
| 6 | `EMPTY_EXPERIMENT_METRICS` | WARNING | Experiment has no captured metrics |
| 7 | `NO_CLAIMS` | WARNING | Project has no claims at all |
| 8 | `NO_EXPERIMENTS` | WARNING | Project has no experiments at all |
| 9 | `MISSING_PAPER_TITLE` | WARNING | paper.yaml title field is empty |
| 10 | `MISSING_AUTHORS` | WARNING | paper.yaml authors list is empty |
| 11 | `METRIC_CLAIM_MISMATCH` | ERROR | A percentage in claim text does not match any experiment metric |
| 12 | `DUPLICATE_CLAIM_TEXT` | WARNING | Two or more claims have identical text |
| 13 | `CLAIM_IN_NO_SECTION` | WARNING | Claim lists no sections |
| 14 | `EXPERIMENT_NO_DESCRIPTION` | WARNING | Experiment description is empty |
| 15 | `EXPERIMENT_NO_HARDWARE` | WARNING | Experiment has no hardware field |
| 16 | `EXPERIMENT_NO_DATASET` | WARNING | Experiment has no dataset field |
| 17 | `EXPERIMENT_NO_SEED` | WARNING | Experiment has no seed field |
| 18 | `UNCLAIMED_EXPERIMENT` | WARNING | Experiment has no claims linked to it |
| 19 | `INVALID_FIGURE_ID` | WARNING | Figure ID does not start with `fig_` |
| 20 | `INVALID_TABLE_ID` | WARNING | Table ID does not start with `tbl_` |

These 20 checks are always run by `collect_issues()`, independent of `--target`.

- **ERRORs block `paperforge build`** and `paperforge review`.
- **WARNINGs do not block** any command.
- `--fix` only auto-resolves `UNVERIFIED_CLAIM` by setting those claims to `stale`.
- `--target` runs the venue plugin's own `validate()` on top of these 20 checks and
  prints the results under a separate `VENUE (<display name>)` heading. Venue checks
  include things like `UNCITED_CLAIM` (IEEE), `MISSING_SEED`/`MISSING_DATASET` (NeurIPS),
  and `MISSING_RELATED_WORK` (ACM) — see `paperforge venues` and each plugin's source
  for the full list.

**Related commands:** `paperforge build`, `paperforge status`, `paperforge add-claim`
