# paperforge capture

Capture experiment results from a metrics JSON file and create (or update) an experiment YAML and a draft claim YAML.

## Usage

```
paperforge capture RESULTS --experiment EXPERIMENT_ID [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `RESULTS` | Path to the metrics JSON file | Yes |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--experiment`, `-e` | — | Experiment ID (e.g. `exp_01`, `exp_27`). **Required.** |
| `--path`, `-p` | `.` | Project root directory |
| `--help` | — | Show help and exit |

## Example

```bash
# Capture flat metrics JSON
paperforge capture results/exp_01/metrics.json --experiment exp_01

# Capture from a nested JSON file
paperforge capture training_output.json --experiment exp_27

# Specify project root explicitly
paperforge capture metrics.json --experiment exp_03 --path ~/papers/vanet
```

## Output

On success, prints a green "Captured" panel with the experiment name, a metrics
table, and the path to the new draft claim:

```
╭─ Captured ─────────────────────────────────────────╮
│ Experiment: exp_01                                 │
│ Updated: .paperforge/experiments/exp_01.yaml       │
│                                                     │
│ Metrics:                                           │
│   accuracy    98.4                                 │
│   precision   97.1                                 │
│                                                     │
│ Draft claim created: .paperforge/claims/claim_02.yaml │
╰─────────────────────────────────────────────────────╯
```

The experiment file is created or **merged** (existing metrics are updated, not replaced).
The draft claim file is always a new file with an auto-incremented ID.

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| `RESULTS` file not found | `Results file not found: <path>` (exit 1) |
| `RESULTS` is not valid JSON | `Invalid JSON: <path>` (exit 1) |
| Experiment ID contains spaces or slashes | `Experiment ID must not contain spaces or slashes.` (exit 1) |

## Notes

- **Flat JSON:** `{"accuracy": 98.4, "precision": 97.1}` — the entire dict is used as metrics.
- **Nested (MLflow-style) JSON:** `{"metrics": {"accuracy": 98.4}, "params": {"seed": 42}}` — only
  the `metrics` key is extracted; `params` and any other top-level keys are ignored.
- Only `int`/`float` values are kept as metrics; strings and other types are silently dropped.
- Merges into an existing `exp_<id>.yaml` if it already exists; adds new metrics and preserves existing ones.
- The draft claim has `status: unverified` and empty text — fill in the claim text before running `doctor`.
- Claim IDs are auto-incremented (`claim_01`, `claim_02`, ...) based on existing files.

**Related commands:** `paperforge add-claim`, `paperforge doctor`, `paperforge impact`
