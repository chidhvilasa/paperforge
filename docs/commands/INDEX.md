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
| [doctor](doctor.md) | Run deterministic consistency checks |
| [impact](impact.md) | Show dependency graph for an experiment |
| [build](build.md) | Compile research data to LaTeX paper |
| [review](review.md) | AI-assisted review via llm (advisory only) |
| [venues](venues.md) | List venue targets for --target flag |
| [install-hooks](install-hooks.md) | Install git pre-commit hook |
| [export](export.md) | Export as BibTeX, JSON, or Markdown |
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
