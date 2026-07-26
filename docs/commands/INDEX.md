# PaperForge Command Reference

All commands follow the pattern: `paperforge <command> [OPTIONS]`

All commands accept `--path` to specify a project root.
Defaults to the current directory.

## Commands

| Command | Description |
|---------|-------------|
| [init](init.md) | Initialize PaperForge in a project |
| [capture](capture.md) | Capture experiment results, create draft claim |
| [add-claim](add-claim.md) | Interactively create a new claim |
| [add-figure](add-figure.md) | Interactively create a new figure YAML file |
| [add-table](add-table.md) | Interactively create a new table YAML file |
| [doctor](doctor.md) | Run deterministic consistency checks |
| [impact](impact.md) | Show dependency graph for an experiment |
| [build](build.md) | Compile research data to LaTeX paper |
| [review](review.md) | AI-assisted review via llm (advisory only) |
| [improve](improve.md) | AI-assisted claim improvement (advisory only) |
| [venues](venues.md) | List venue targets for --target flag |
| [install-hooks](install-hooks.md) | Install git pre-commit hook |
| [export](export.md) | Export as BibTeX, JSON, or Markdown |
| [export traceability](traceability.md) | Full claim-evidence matrix as MD, CSV, LaTeX |
| [status](status.md) | Project health dashboard |
| [find](find.md) | Search claims and experiments by keyword |
| [log](log.md) | Show change history for a claim |
| [diff](diff.md) | Show what changed vs history or linked experiment |

## Common Workflows

### Start a new paper

```bash
paperforge init
paperforge capture results/exp_01.json --experiment exp_01
paperforge add-claim
paperforge doctor
```

### Before every commit

```bash
paperforge doctor
# or install the git hook:
paperforge install-hooks
```

### Experiment result changed

```bash
paperforge impact exp_01
# update affected claims
paperforge doctor
```

### Submission day

```bash
paperforge doctor --target ieee
paperforge build --target ieee
paperforge export bibtex
```

## What's New in v0.7.0

Traceability matrix export.

One command generates three files:

```bash
paperforge export traceability
```

The Markdown file renders on GitHub and shows verification
status at a glance. The CSV opens in Excel for further
analysis. The LaTeX longtable can be included directly in
your paper appendix.

The matrix directly answers CONSTITUTION principle 2:
"Every published claim must be explainable." Every row
shows exactly what evidence, figures, tables, and citations
support that claim.

## What's New in v0.6.0

Table objects are now fully supported.

Run `paperforge add-table` to create `.paperforge/tables/tbl_NN.yaml`
with column headers and row data. The build command generates
correct IEEE LaTeX tables automatically:

```latex
\begin{table}[!t]
\renewcommand{\arraystretch}{1.3}
\caption{Performance Comparison}      % Caption ABOVE tabular
\label{tab:tbl_01}
\centering
\begin{tabular}{c c c}
\hline
Method & Accuracy & F1 \\
\hline
Baseline & 91.2\% & 90.8\% \\
Proposed & 98.4\% & 97.9\% \\
\hline
\end{tabular}
\end{table}
```

`TABLE_NO_CAPTION` is an ERROR (not a warning) because
IEEE submissions cannot contain uncaptioned tables.

`paperforge doctor` now runs 41 checks total across
ERROR, WARNING, and INFO severity levels.

## What's New in v0.4.0

IEEE Transactions journal support.

Set `paper_type: "journal"` in `.paperforge/paper.yaml` and
build with `--target ieee-journal` for a fully structured
IEEEtran journal paper with abstract in title block,
drop letter, raised section heading, and keywords.

`paperforge doctor` now runs 30 checks across three levels:
ERROR (blocks build), WARNING (advisory), and INFO
(EVIDENCE_COVERAGE score, always shown).

Run `paperforge doctor --target ieee-journal` for 30 core checks
plus IEEE journal-specific venue rules in one pass.

## What's New in v0.3.0

Claim versioning is now built into PaperForge.

Every time PaperForge writes a claim (via `capture`,
`add-claim`, or `doctor --fix`), it snapshots the previous
state to `.paperforge/history/`.

Use `paperforge log` to see when and how a claim changed.
Use `paperforge diff` to compare the current state against
history or a linked experiment.

History files live in `.paperforge/history/` and should be
committed to git. They are part of your research record.
