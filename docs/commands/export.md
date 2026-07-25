# paperforge export

Export the research graph from `.paperforge/` as BibTeX stubs, a structured JSON file, or a human-readable Markdown summary.

## Usage

```
paperforge export [FORMAT] [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `FORMAT` | Output format: `bibtex`, `json`, or `markdown`. Defaults to `json`. | No |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--output`, `-o` | See Notes | Custom output file path |
| `--help` | — | Show help and exit |

## Example

```bash
# Export as JSON (default)
paperforge export

# Export as BibTeX
paperforge export bibtex

# Export as Markdown
paperforge export markdown

# Export JSON to a custom path
paperforge export json --output ~/Desktop/graph.json

# Export BibTeX for a specific project
paperforge export bibtex --path ~/papers/vanet-paper
```

## Output

On success, prints a green confirmation panel:
```
╭─ Export Complete ─────────────────────────────────╮
│ Format:      bibtex                               │
│ Output:      .paperforge/output/references.bib    │
│ Claims:      4                                    │
│ Experiments: 2                                    │
╰───────────────────────────────────────────────────╯
```

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| Unknown format | `Unknown format '<fmt>'. Choose: bibtex, json, markdown` (exit 1) |

## Notes

### Default output paths

| Format | Default path |
|--------|-------------|
| `bibtex` | `.paperforge/output/references.bib` |
| `json` | `.paperforge/output/research_graph.json` |
| `markdown` | `.paperforge/output/summary.md` |

Use `--output` to override any default path.

### BibTeX format
- Generates **stub entries only** — `@article{key, author={Author, A.}, ...}` with TODO placeholders.
- Replace stub entries with real bibliographic data before submitting.
- If no claims have citation keys, writes a comment-only file explaining how to add them.

### JSON format
The exported JSON follows this schema:
```json
{
  "paperforge_version": "0.2.0",
  "exported_at": "<ISO 8601 datetime>",
  "project": { "title", "authors", "venue", "status", "sections" },
  "claims": [ { "id", "text", "experiment", "figures", "tables", "citations", "sections", "status", "last_verified" } ],
  "experiments": [ { "id", "description", "results_file", "metrics", "hardware", "dataset", "seed", "ran_at" } ],
  "graph": { "claim_count", "experiment_count", "edges": [ { "claim", "experiment" } ] }
}
```

### Markdown format
Generates a human-readable project summary with:
- Project metadata header
- Project summary table (claim counts by status)
- Claims listed by section
- Experiment details (description, dataset, hardware, seed, metrics)
- Alphabetical citation key list

**Related commands:** `paperforge status`, `paperforge find`, `paperforge build`
