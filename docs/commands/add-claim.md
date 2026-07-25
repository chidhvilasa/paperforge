# paperforge add-claim

Interactively create a new claim YAML file linked to an existing experiment, using guided terminal prompts.

## Usage

```
paperforge add-claim [OPTIONS]
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
# Start interactive claim creation
paperforge add-claim

# Create a claim in a different project
paperforge add-claim --path ~/papers/vanet-paper
```

## Output

First prints a cyan "Add Claim" panel showing existing experiments, sections,
and claim count, then walks through a series of prompts (in this order: Text,
Experiment, Sections, Figures, Tables, Citations, Status):

```
╭─ Add Claim ────────────────────────────────────────╮
│ Existing experiments: exp_01                       │
│ Existing sections:    abstract, introduction, ...  │
│ Existing claims:      1                            │
│                                                     │
│ Fill in the claim details below.                   │
│ Press Enter to leave a field empty.                │
╰─────────────────────────────────────────────────────╯
Text: This model achieves 98.4% accuracy on CICDDoS2019.
Experiment: exp_01
Sections: abstract,results
Figures: fig_01
Tables: tbl_02
Citations: smith2024,jones2023
Status: verified

╭─ Claim Added ──────────────────────────────────────╮
│ Created: .paperforge/claims/claim_02.yaml          │
│                                                     │
│ claim_02: "This model achieves 98.4% accuracy..."  │
│ Experiment: exp_01                                 │
│ Sections:   abstract, results                      │
│                                                     │
│ Next steps:                                        │
│       Run `paperforge doctor` to check consistency.│
│       Run `paperforge impact exp_01` to see affected nodes. │
╰─────────────────────────────────────────────────────╯
```

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |

## Notes

- The claim ID is **always auto-assigned** (`claim_01`, `claim_02`, ...) based on
  existing files — there is no prompt for it.
- There is no hard requirement that experiments already exist; the "Available"
  hint simply shows `none` if there aren't any yet, and you can still type any
  experiment ID (run `paperforge doctor` afterward to catch a typo or missing link).
- Status must be one of `verified`, `unverified`, or `stale`. An invalid entry
  triggers one re-prompt; if still invalid, it silently defaults to `unverified`.
- All list fields (sections, figures, tables, citations) accept comma-separated
  values; surrounding whitespace around each item is stripped.
- Sections, figures, tables, citations, and experiment are all optional — press
  Enter to leave them empty (an empty experiment will trigger `ORPHAN_CLAIM` in `doctor`).
- After creation, run `paperforge doctor` to validate the new claim.

**Related commands:** `paperforge capture`, `paperforge doctor`
