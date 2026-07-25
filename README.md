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

# 2. Capture experiment results
paperforge capture results/exp_01/metrics.json --experiment exp_01

# 3. Edit .paperforge/claims/claim_02.yaml
#    Fill in text, sections, figures, tables, citations

# 4. Check consistency
paperforge doctor

# 5. See impact of any experiment change
paperforge impact exp_01

# 6. Build IEEE LaTeX paper
paperforge build

# 7. Optional: AI-assisted review (requires llm)
paperforge review
```

## Commands

| Command | Description |
|---------|-------------|
| `paperforge init` | Initialize PaperForge in a project directory |
| `paperforge capture` | Capture experiment results, create draft claim |
| `paperforge doctor` | Run deterministic consistency checks |
| `paperforge impact` | Show everything affected by an experiment change |
| `paperforge build` | Compile research data into IEEE LaTeX paper |
| `paperforge review` | AI-assisted review via llm (advisory only) |
| `paperforge venues` | List available venue targets |

## Venue Targets

```bash
paperforge build --target ieee      # IEEE (default)
paperforge build --target acm       # ACM sigconf
paperforge build --target neurips   # NeurIPS
```

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
