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
| [doctor](doctor.md) | Run deterministic consistency checks |
| [impact](impact.md) | Show dependency graph for an experiment |
| [build](build.md) | Compile research data to LaTeX paper |
| [review](review.md) | AI-assisted review via llm (advisory only) |
| [venues](venues.md) | List venue targets for --target flag |
| [install-hooks](install-hooks.md) | Install git pre-commit hook |
| [export](export.md) | Export as BibTeX, JSON, or Markdown |
| [status](status.md) | Project health dashboard |
| [find](find.md) | Search claims and experiments by keyword |

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
