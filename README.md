# PaperForge

**A research dependency engine for academics.**

PaperForge tracks the dependency graph between experiments
and scientific claims so your paper is always internally
consistent.

You change one experiment result.
PaperForge tells you exactly which claims, sections, figures,
and tables need updating.

[![PyPI](https://img.shields.io/pypi/v/paperforge-research)](https://pypi.org/project/paperforge-research/)
[![Python](https://img.shields.io/pypi/pyversions/paperforge-research)](https://pypi.org/project/paperforge-research/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Install note:** There is currently a PyPI name conflict.
> `pip install paperforge` installs an unrelated tool.
> Install from source (see below) until this is resolved.

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
pip install paperforge-research==1.4.0
# or always latest:
pip install paperforge-research
```

> **Note:** The package is named `paperforge-research` on PyPI due to a name conflict with an inactive project.

Requires Python 3.11+.

## Updating

```bash
paperforge update          # check PyPI and upgrade
paperforge update --git    # update from git (dev installs)
```

## Quick Start

```bash
# Check your PaperForge installation
paperforge doctor --self-check

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
  - institution: "Example Institute of Technology"
    department: "Dept. of CSE"
    city: "Example City"
    country: "Exampleland"
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

# 9b. Export full traceability matrix
paperforge export traceability
# Creates: traceability.md, traceability.csv, traceability.tex

# 9a. Check claim history
paperforge log claim_01

# 9b. Diff a claim against its linked experiment
paperforge diff claim_01 --against experiment

# 9c. Add a data table
paperforge add-table

# 9d. Add real citation metadata (no more TODO stubs)
paperforge add-citation smith2024

# 10. AI-assisted claim improvement
paperforge improve claim_01

# 11. Optional: AI-assisted review (requires llm)
paperforge review

# 12. Preflight visual rendering & visual overlap scan
paperforge preflight --mode submission

# 13. Reference & DOI verification
paperforge references --online
```

## Math and Equations

PaperForge v1.2.0 supports LaTeX equations in claims.
Set `is_math: true` in any claim that contains equations:

```yaml
# .paperforge/claims/claim_05.yaml
id: claim_05
text: "The verification equation is $\\alpha_i^T M = pk_i + h_1^i k_{\\mathrm{Pub}} + h_2^i X_i$."
is_math: true
sections: [methodology]
```

Inline math spans (`$...$`) in regular claims are automatically
protected from LaTeX escaping.

For theorem/lemma/proof environments:

```yaml
id: claim_06
text: "The proposed scheme achieves EUF-CMA security under the SIS assumption."
claim_type: theorem
sections: [methodology]
```

Generates `\begin{theorem}...\end{theorem}` with automatic labeling.

## The paper_information/ Workflow

PaperForge v1.1.0 introduces a human-friendly input layer.
After `paperforge init`, write your paper in plain Markdown:
paper_information/
├── content/
│   ├── abstract.md       ← write your abstract here
│   ├── introduction.md   ← motivation, gap, contributions
│   ├── related_work.md   ← surveyed papers
│   ├── methodology.md    ← system design
│   ├── results.md        ← your findings
│   └── ...
├── graphs/
│   └── latency.py        ← matplotlib scripts, auto-executed
├── tables/
│   └── results.csv       ← auto-converted to LaTeX tables
├── author.yaml           ← name, affiliation, email, ORCID
└── metadata.yaml         ← title, venue, keywords, COI

Then run:
```bash
paperforge import          # read paper_information/ → .paperforge/
paperforge doctor          # validate consistency
paperforge build           # compile LaTeX + PDF
```

Output goes to `paper_generated/current/`. The previous build
is preserved in `paper_generated/previous/` for comparison.

## Commands

| Command | Description |
|---------|-------------|
| `paperforge init` | Initialize PaperForge in a project directory |
| `paperforge import` | Import markdown files, CSV tables, and graph scripts from `paper_information/` |
| `paperforge update` | Check PyPI for updates and upgrade in-place (or `--git` for dev installs) |
| `paperforge capture` | Capture experiment results, create draft claim |
| `paperforge add-claim` | Interactively create a new claim |
| `paperforge add-figure` | Interactively create a new figure YAML |
| `paperforge add-table` | Interactively create a new table YAML |
| `paperforge add-citation` | Add real BibTeX metadata for a citation key |
| `paperforge generate-figures` | Generate matplotlib plots from experiment metrics |
| `paperforge doctor` | Run deterministic consistency checks |
| `paperforge impact` | Show everything affected by an experiment change |
| `paperforge build` | Compile research data into LaTeX paper and PDF |
| `paperforge review` | AI-assisted review via llm (advisory only) |
| `paperforge improve` | AI-assisted claim improvement via llm (advisory only) |
| `paperforge venues` | List available venue targets |
| `paperforge install-hooks` | Install git pre-commit hook |
| `paperforge export` | Export BibTeX, JSON, Markdown, traceability, Overleaf zip |
| `paperforge status` | Project health dashboard |
| `paperforge find` | Search claims and experiments by keyword |
| `paperforge log` | Show change history for a claim |
| `paperforge diff` | Diff a claim against its history or experiment |

## Venue Targets

```bash
paperforge build --target ieee          # IEEE Conference (default)
paperforge build --target ieee-journal  # IEEE Transactions / Journal
paperforge build --target ieee-trans    # IEEE Transactions (alias)
paperforge build --target ieee-access   # IEEE Access
paperforge build --target ieee-compsoc  # IEEE Computer Society Journals
paperforge build --target ieee-tdsc     # IEEE TDSC
paperforge build --target acm           # ACM sigconf
paperforge build --target neurips       # NeurIPS
```
For journal papers, set `paper_type: "journal"` in `.paperforge/paper.yaml`.

## Doctor Checks

`paperforge doctor` runs 43 deterministic checks with three severity levels:

- **ERROR** — blocks `paperforge build` and git commits (if hook installed)
- **WARNING** — reported but does not block
- **INFO** — informational only, never blocks anything

Key checks include: claim-experiment traceability, metric
consistency, acronym definition, abstract length, section
coverage, and IEEE reproducibility requirements (seed, dataset,
hardware).

Run `paperforge doctor --target ieee-journal` to add
venue-specific checks on top of the core 43.

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

Build outputs go to `paper/` at your project root:
- `paper.tex` (compiled LaTeX paper)
- `paper.pdf` (compiled PDF)
- `references.bib` (stub or preserved references)

LaTeX auxiliary files (`*.aux`, `*.log`, etc.) are gitignored automatically.

After a successful PDF compilation, PaperForge opens the `paper/` folder automatically. Use `--no-reveal` to suppress this.

## Build Modes

```bash
paperforge build --target ieee-access            # draft mode (default)
paperforge build --target ieee-access --mode submission  # strict
```

**Draft mode** blocks on critical errors only
(empty claims, missing captions, LaTeX artifacts).

**Submission mode** adds additional blocking checks:
metric mismatches, abstract/intro overlap, duplicate claims,
author identity inconsistencies, citation internal notes,
and claim constraint violations.

## Data Objects

PaperForge tracks three types of structured research data
alongside claims and experiments:

**Figures** (`.paperforge/figures/fig_NN.yaml`) — image
metadata including caption, path, resolution, and first
mention section. Build generates `\begin{figure}` environments.

**Tables** (`.paperforge/tables/tbl_NN.yaml`) — tabular data
with columns, rows, caption, and source experiment. Build
generates IEEE-compliant `\begin{table}` environments with
caption above the tabular (IEEE requirement).

**History** (`.paperforge/history/`) — automatic snapshots
of claim state recorded whenever PaperForge writes a claim.
Use `paperforge log` and `paperforge diff` to inspect.

All three are committed to git as part of your research record.

## AI-Assisted Improvement

`paperforge improve` suggests edits to claim text using
your linked experiment data as ground truth:

```bash
paperforge improve claim_01              # single claim
paperforge improve --all                 # all unverified claims
paperforge improve --model gpt-4o --all  # specify model
```

Suggestions are shown with a y/n/s prompt.
Nothing is applied without explicit confirmation.
A history snapshot is recorded before any change.
Requires `llm` on PATH: `uv add llm && llm keys set openai`

## Traceability Matrix

`paperforge export traceability` generates three files at once:

```
paper/ (or .paperforge/output/)
├── traceability.md ← human-readable, renders on GitHub
├── traceability.csv ← opens in Excel
└── traceability.tex ← \input{} in paper appendix
```

Each row answers: "Is this claim explainable?" with columns
for experiment, key metric, figures, tables, citations,
sections, and verification date.

Include in your paper appendix:
```latex
\usepackage{longtable}  % in preamble
\input{traceability}    % in appendix
```

## Citations

`paperforge add-citation` stores real BibTeX metadata in
`.paperforge/citations/{key}.yaml`. Every subsequent build
generates `paper/references.bib` from these files instead
of TODO stubs.

```bash
paperforge add-citation smith2024
# Key:     smith2024
# Type:    article
# Authors: Smith, Alice; Jones, Bob
# Title:   Adaptive Authentication in VANETs
# Venue:   IEEE Access
# Year:    2024
# DOI:     10.1109/ACCESS.2024.123456
```

Generated BibTeX:

```bibtex
@article{smith2024,
  author    = {Smith, Alice and Jones, Bob},
  title     = {Adaptive Authentication in VANETs},
  journal   = {IEEE Access},
  year      = {2024},
  doi       = {10.1109/ACCESS.2024.123456},
}
```

Citation YAML is the **source of truth** — rebuild any time
without losing real bibliography entries.

## Overleaf Export

No local LaTeX? Export directly to Overleaf:

```bash
paperforge build --target ieee-access   # generate paper.tex first
paperforge export overleaf              # creates paper_overleaf.zip
```

Upload `paper_overleaf.zip` to Overleaf. IEEEtran is built
into Overleaf -- no extra setup needed.

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

## What Was Fixed in v1.4.0

**Critical:** Every PDF generated before v1.4.0 had blank
figure boxes and `[?]` citation placeholders because pdflatex
ran from the build directory where `figures/` did not exist.
The tool reported "PDF generated ✓" anyway by only checking
that the PDF file existed. This is fixed: figures are now
copied into the build directory before compilation, and the
pdflatex log is parsed to detect broken compilations.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
