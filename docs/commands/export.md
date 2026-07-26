# paperforge export

Export the research graph from `.paperforge/` as BibTeX stubs, a structured JSON file, a human-readable Markdown summary, or a full traceability matrix.

## Usage

```
paperforge export [FORMAT] [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `FORMAT` | Output format: `bibtex`, `json`, `markdown`, `traceability`, or `overleaf`. Defaults to `json`. | No |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--output`, `-o` | See Notes | Custom output file path or directory |
| `--help` | — | Show help and exit |

## Formats

| Format | Output File(s) | Description |
|--------|---------------|-------------|
| `json` | `research_graph.json` | Full graph schema |
| `bibtex` | `references.bib` | BibTeX stubs for all citation keys |
| `markdown` | `summary.md` | Human-readable project summary |
| `traceability` | `traceability.md` + `.csv` + `.tex` | Claim-evidence matrix |
| `overleaf` | `paper_overleaf.zip` | Complete Overleaf upload package |

## Example

```bash
# JSON graph export (default)
paperforge export json

# BibTeX stubs for reference manager
paperforge export bibtex

# Human-readable Markdown summary
paperforge export markdown

# Full traceability matrix (3 files)
paperforge export traceability

# Traceability to custom directory
paperforge export traceability --output docs/appendix/
```

## Output

On success, prints a green confirmation panel:
```
╭─ Export Complete ─────────────────────────────────╮
│ Format:      traceability                         │
│ Output:      .paperforge/output                   │
│ Files:       traceability.md, .csv, .tex          │
│ Claims:      4                                    │
│ Experiments: 2                                    │
╰───────────────────────────────────────────────────╯
```

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| Unknown format | `Unknown format '<fmt>'. Choose: bibtex, json, markdown, traceability` (exit 1) |

## Notes

### Default output paths

| Format | Default path |
|--------|-------------|
| `bibtex` | `.paperforge/output/references.bib` |
| `json` | `.paperforge/output/research_graph.json` |
| `markdown` | `.paperforge/output/summary.md` |
| `traceability` | `.paperforge/output/` (directory containing 3 files) |

Use `--output` to override any default path or output directory.

### Traceability format
- `traceability` is the only format that generates multiple files (`traceability.md`, `traceability.csv`, `traceability.tex`).
- `--output` for `traceability` is treated as a directory, not a single file.
- CSV uses pipe `|` as an inner separator for multi-value fields to avoid delimiter conflicts.
- LaTeX longtable requires `\usepackage{longtable}` in your LaTeX document preamble.

### BibTeX format
- Generates **stub entries only** — `@article{key, author={Author, A.}, ...}` with TODO placeholders.
- Replace stub entries with real bibliographic data before submitting.
- If no claims have citation keys, writes a comment-only file explaining how to add them.

### JSON format
The exported JSON follows this schema:
```json
{
  "paperforge_version": "0.7.0",
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

### Overleaf format
- Creates `paper_overleaf.zip` containing `paper.tex`, `references.bib`, `traceability.tex` (if exists), `figures/*` (all project figures), and `README.txt`.
- Requires `paperforge build` to have been run first (raises an error if `paper.tex` does not exist).
- Ready to upload directly to Overleaf (Overleaf includes `IEEEtran.cls` built-in).

**Related commands:** `paperforge status`, `paperforge find`, `paperforge build`
