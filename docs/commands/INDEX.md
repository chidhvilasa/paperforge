# PaperForge Command Reference

All commands follow the pattern: `paperforge <command> [OPTIONS]`

All commands accept `--path` to specify a project root.
Defaults to the current directory.

## Commands

| Command | Description |
|---------|-------------|
| [inspect](inspect.md) | Read-only reconnaissance of a directory before intake/import |
| [init](init.md) | Initialize PaperForge in a project |
| [capture](capture.md) | Capture experiment results, create draft claim |
| [add-claim](add-claim.md) | Interactively create a new claim |
| [add-figure](add-figure.md) | Interactively create a new figure YAML file |
| [add-table](add-table.md) | Interactively create a new table YAML file |
| [add-citation](add-citation.md) | Interactively create a new citation YAML file |
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

## What's New in v1.0.0

PaperForge v1.0.0 is the production release of the research dependency engine.

**Non-interactive CLI flags.** Script object creation in CI or agent workflows without interactive prompts:
```bash
paperforge add-claim --text "98.4% accuracy." --experiment exp_01 --sections results
```

**--from-yaml import.** Import objects in bulk from YAML files.

**Multi-experiment claims.** Synthesize evidence from multiple experiments (`experiments: [exp_02, exp_03]`).

**Overleaf export.** `paperforge export overleaf` packages `paper.tex`, `references.bib`, `traceability.tex`, and `figures/` into `paper_overleaf.zip` for instant Overleaf upload.

## What's New in v0.9.0

Citation data model eliminates TODO stubs permanently.

Add real BibTeX metadata once:
```bash
paperforge add-citation wani2024
```

Every `paperforge build` generates `paper/references.bib`
from your citation YAMLs automatically. The YAML is the
source of truth — updating it updates the bibliography.

`paperforge doctor` now checks for undefined citation keys,
unused citation files, and missing required fields (48 checks
total, 8 ERROR severity).

## What's New in v0.8.0

Two major improvements for production use:

**Build output in paper/.** Everything you submit goes to
`paper/` at your project root -- visible, committable, and
exactly where you expect it.

**AI-assisted claim improvement.** `paperforge improve`
uses your linked experiment data to suggest better claim
phrasing, with explicit y/n confirmation before any change.

**Critical fixes** from production testing on a real
IEEE Access paper: Windows encoding, wrong compsoc mode for
non-CS journals, nested JSON capture, multi-seed experiments,
acronym plural detection.

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
