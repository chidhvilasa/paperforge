# paperforge find

Case-insensitive full-text keyword search across all claims and experiments in the research graph.

## Usage

```
paperforge find QUERY [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `QUERY` | The search term to look for | Yes |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--field`, `-f` | `all` | Search scope: `claims`, `experiments`, or `all` |
| `--help` | — | Show help and exit |

## Example

```bash
# Search across everything
paperforge find "accuracy"

# Search only claims
paperforge find "98.4%" --field claims

# Search only experiments
paperforge find "CICDDoS" --field experiments

# Search for a citation key
paperforge find "smith2024" --field claims

# Search in a specific project
paperforge find "neural network" --path ~/papers/vanet-paper
```

## Output

On match:
```
Search results for 'accuracy'

Claims (2 found)
  claim_02  (verified)
  This model achieves 98.4% accuracy on CICDDoS2019.
  Experiment: exp_01 | Sections: results, abstract

  claim_05  (unverified)
  Our approach reduces false positives by 14.2%.
  Experiment: exp_01 | Sections: results

Experiments (1 found)
  exp_01
  Benchmark run on CICDDoS2019 dataset.
  Metrics: accuracy, precision
  Dataset: CICDDoS2019

Found 2 claim(s) and 1 experiment(s)
```

Matched terms are highlighted in **bold yellow** in the output.

When no results are found, prints a yellow panel:
```
╭────────────────────────────────────────╮
│ No results for 'zzz'                  │
│ Searched: all                         │
╰────────────────────────────────────────╯
```

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| Empty query string | `Search query cannot be empty.` (exit 1) |

## Notes

- **Plain substring match only** — case-insensitive. No AI, no embeddings, no fuzzy matching.
- Exits 0 (not 1) when no results are found — a yellow panel is shown.
- Exits 1 **only** on empty query or missing initialization.
- Claims are searched across: text, experiment ID, claim ID, sections, figures, tables, citations.
- Experiments are searched across: ID, description, dataset, hardware, metrics (as `key:value` strings).
- `--field claims` skips experiment search entirely; `--field experiments` skips claim search.
- Matched substrings are wrapped in bold yellow in the terminal output for easy scanning.

**Related commands:** `paperforge status`, `paperforge impact`, `paperforge export`
