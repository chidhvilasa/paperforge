# paperforge export traceability

Export claim-evidence matrix as Markdown, CSV, and LaTeX longtable files simultaneously.

## Usage

```bash
paperforge export traceability [OPTIONS]
```

## Description

The `export traceability` command generates a comprehensive matrix tracing every claim to its linked evidence (experiment, metrics, figures, tables, citations, sections, and verification date).

This fulfills Principle 2 of the PaperForge Constitution: *"Every published claim must trace to evidence and be fully explainable from that evidence."*

It writes three files in a single invocation:
- `traceability.md`: Human-readable Markdown with status emojis and evidence coverage summary.
- `traceability.csv`: Machine-readable CSV with full text and pipe-separated list fields.
- `traceability.tex`: LaTeX `longtable` environment for inclusion in paper appendices.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--output`, `-o` | `.paperforge/output/` | Output directory |

## Output Files

Three files are generated in one command:

| File | Format | Use |
|------|--------|-----|
| `traceability.md` | Markdown | Human-readable, renders on GitHub |
| `traceability.csv` | CSV | Machine-readable, opens in Excel |
| `traceability.tex` | LaTeX longtable | Include in paper appendix |

## Example

```bash
paperforge export traceability

# With custom output directory:
paperforge export traceability --output docs/
```

## Output Columns

| Column | Description |
|--------|-------------|
| Claim ID | Claim identifier |
| Text | Claim text (truncated in MD, full in CSV) |
| Status | verified / unverified / stale |
| Experiment | Linked experiment ID |
| Key Metric | First metric from linked experiment |
| Figures | Linked figure IDs |
| Tables | Linked table IDs |
| Citations | BibTeX citation keys |
| Sections | Paper sections where claim appears |
| Verified | Date of last verification |

## Notes

The traceability matrix answers CONSTITUTION principle 2:
"Every published claim must be explainable."

To include the LaTeX table in your paper appendix:

```latex
% In preamble:
\usepackage{longtable}

% In appendix:
\appendices
\section{Claim Traceability}
\input{traceability}
```

The traceability export is read-only. It never modifies
`.paperforge/` data. It can be run at any time.
