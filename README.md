# PaperForge

**A research dependency engine for academics.**

PaperForge tracks the dependency graph between experiments
and scientific claims so your paper is always internally
consistent.

You change one experiment result.
PaperForge tells you exactly which claims, sections, figures,
and tables need updating.

[![PyPI](https://img.shields.io/pypi/v/paperforge)](https://pypi.org/project/paperforge/)
[![Python](https://img.shields.io/pypi/pyversions/paperforge)](https://pypi.org/project/paperforge/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The Problem

You run experiment 27. Accuracy improves from 98.4% to 98.7%.

Now you manually hunt through your paper for every mention
of that number, every figure it affects, every section
that needs updating. You miss one. The reviewer catches it.
Desk rejection.

## The Solution

```bash
$ paperforge impact exp_27

Source: Experiment exp_27

Affected Claims:
  claim_07    "The model achieves 98.4% accuracy on CICDDoS2019."
  claim_12    "Our approach outperforms the B2 baseline by 14.2%."

Affected Sections:
  abstract
  results
  discussion

Affected Figures:
  fig_03

Affected Tables:
  tbl_02

Verification Status:
  2 claims require verification
  1 figure should be reviewed
  1 table should be reviewed
```

## Philosophy

PaperForge is a **compiler**, not a writer.
Research Data
│
▼
paperforge doctor ← deterministic consistency checks
│
▼
paperforge build ← compiles to IEEE LaTeX + PDF
│
▼
Submission Package
AI-assisted review is one optional stage at the end.
It never becomes the source of truth.
See [CONSTITUTION.md](CONSTITUTION.md).

## Install

```bash
pip install paperforge
# or
uv add paperforge
```

Requires Python 3.11+.

## Quick Start

```bash
# 1. Initialize inside any research project
cd my-research-project
paperforge init

```yaml
# .paperforge/paper.yaml
title: "My Paper"
authors: ["A. Author"]
paper_type: "journal"
keywords: ["security", "IoT"]
affiliations:
  - institution: "VIT Vellore"
    department: "Dept. of CSE"
    city: "Vellore"
    country: "India"
```

# 2. Capture experiment results
paperforge capture results/exp_01/metrics.json --experiment exp_01

# 3. Add a claim interactively
paperforge add-claim

# 4. Check project health
paperforge status

# 5. Search your research
paperforge find "accuracy"

# 6. Check consistency
paperforge doctor

# 7. See impact of any experiment change
paperforge impact exp_01

# 8. Build IEEE LaTeX paper
paperforge build                         # conference (default)
paperforge build --target ieee-journal   # transactions/journal

# 9. Export for reference managers
paperforge export bibtex

# 9a. Check claim history
paperforge log claim_01

# 9b. Diff a claim against its linked experiment
paperforge diff claim_01 --against experiment

# 11. Optional: AI-assisted review (requires llm)
paperforge review
```

## Commands

| Command | Description |
|---------|-------------|
| `paperforge init` | Initialize PaperForge in a project directory |
| `paperforge capture` | Capture experiment results, create draft claim |
| `paperforge add-claim` | Interactively create a new claim |
| `paperforge doctor` | Run 20 deterministic consistency checks |
| `paperforge impact` | Show everything affected by an experiment change |
| `paperforge build` | Compile research data into LaTeX paper |
| `paperforge review` | AI-assisted review via llm (advisory only) |
| `paperforge venues` | List available venue targets |
| `paperforge install-hooks` | Install git pre-commit hook |
| `paperforge export` | Export as BibTeX, JSON, or Markdown |
| `paperforge status` | Project health dashboard |
| `paperforge find` | Search claims and experiments by keyword |
| `paperforge log` | Show change history for a claim |
| `paperforge diff` | Diff a claim against its history or experiment |

## Venue Targets

```bash
paperforge build --target ieee          # IEEE Conference (default)
paperforge build --target ieee-journal  # IEEE Transactions / Journal
paperforge build --target ieee-trans    # IEEE Transactions (alias)
paperforge build --target acm           # ACM sigconf
paperforge build --target neurips       # NeurIPS
```
For journal papers, set `paper_type: "journal"` in `.paperforge/paper.yaml`.

## Doctor Checks

`paperforge doctor` runs 30 deterministic checks with three severity levels:

- **ERROR** — blocks `paperforge build` and git commits (if hook installed)
- **WARNING** — reported but does not block
- **INFO** — informational only, never blocks anything

Key checks include: claim-experiment traceability, metric
consistency, acronym definition, abstract length, section
coverage, and IEEE reproducibility requirements (seed, dataset,
hardware).

Run `paperforge doctor --target ieee-journal` to add
venue-specific checks on top of the core 30.

## Build Quality

PaperForge uses `latexmk` for PDF compilation when available
(preferred over raw `pdflatex` — handles cross-references
automatically). Falls back to `pdflatex` if latexmk is absent.

Install TeX Live for full compilation support:
- Linux: `sudo apt install texlive-full`
- macOS: install MacTeX
- Windows: install MiKTeX or TeX Live

Figure environments with `\label{}` and `\ref{}` are generated
automatically when figures have YAML metadata.

## Documentation

Full command reference: [docs/commands/](docs/commands/INDEX.md)

Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)

## Data Storage

All research data lives locally in `.paperforge/` inside your
project. Nothing is sent to any cloud. No account required.
PaperForge works fully offline.

Add `.paperforge/` to your git repository.
Your claims and experiments should be version controlled.

## AI Review

`paperforge review` uses [llm](https://llm.datasette.io/) for
model-agnostic AI calls. Install and configure separately:

```bash
uv add llm
llm keys set openai    # or any supported provider
paperforge review --model gpt-4o
```

AI output is advisory only. It is never a source of truth.
Review output is saved locally and never committed to git.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
