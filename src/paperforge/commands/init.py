"""paperforge init command."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()

PAPER_YAML = """\
# PaperForge paper.yaml — project configuration
# Run 'paperforge doctor' after changes to validate.

version: "0.1"
title: ""              # Title case. Under 15 words. No period.
authors:
  - ""                 # Full name, e.g. "Alice Smith"
venue: ""              # e.g. "IEEE Access"
status: "draft"        # draft | submitted | accepted | published
paper_type: "journal"  # conference | journal

# IEEE Access specific
email: ""              # Corresponding author email (required)
orcid: ""              # ORCID iD, e.g. 0000-0000-0000-0000
funding: ""            # Grant/funding for \\thanks{} footnote
                       # e.g. "This work was supported by..."
manuscript_received: "" # Leave blank; IEEE fills this at production

# Statements (IEEE Access increasingly requires these)
conflict_of_interest: "" # e.g. "The authors declare no conflicts of interest."
data_availability: ""  # e.g. "Data available on reasonable request."
code_availability: ""  # e.g. "Code at https://github.com/..."

acknowledgment: ""     # People/institutions only (not funding)

keywords: []           # 4-8 keywords, alphabetical order

affiliations:
  - name: ""
    institution: ""
    department: ""
    city: ""
    country: ""
    email: ""          # Per-author email if multi-author

sections:
  - abstract
  - introduction
  - related_work
  - methodology
  - experiments
  - results
  - discussion
  - conclusion

build:
  output_dir: "paper_generated/current"
  latex_template: "ieee"

publisher_id: ""       # Leave blank; IEEE fills at production
"""

CLAIM_01_YAML = """\
id: claim_01
text: ""
experiment: ""
figures: []
tables: []
citations: []
sections: []
status: unverified
last_verified: null
"""

EXP_01_YAML = """\
id: exp_01
description: ""
results_file: null
metrics: {}
hardware: null
dataset: null
seed: null
ran_at: null
"""

PAPERFORGE_GITIGNORE = """\
# PaperForge data — commit everything
# All claims, experiments, figures, paper.yaml, and history should be version controlled
!*
"""

PAPER_GENERATED_GITIGNORE = """\
# Keep generated files but ignore aux files
current/*.aux
current/*.log
current/*.out
current/*.toc
current/*.fls
current/*.fdb_latexmk
current/*.synctex.gz
current/*.bbl
current/*.blg
previous/*.aux
previous/*.log
previous/*.out
previous/*.toc
previous/*.fls
previous/*.fdb_latexmk
previous/*.synctex.gz
previous/*.bbl
previous/*.blg
# Keep these in both directories:
!current/paper.tex
!current/paper.pdf
!current/paper.docx
!current/references.bib
!current/traceability.tex
!previous/paper.tex
!previous/paper.pdf
!previous/paper.docx
!previous/references.bib
"""

ABSTRACT_MD = """\
# Abstract
<!-- Write your abstract here. One paragraph. 150-250 words.
     No citations. No equations. No numbered references. -->

Write your abstract here.
"""

INTRODUCTION_MD = """\
# Introduction
<!-- Structure:
     1. Problem motivation (2-3 sentences)
     2. Gap in existing work (1-2 sentences)
     3. Proposed solution (1-2 sentences)
     4. Contributions (bullet list)
     5. Paper organization (1 sentence) -->

## Problem Motivation

## Gap in Existing Work

## Proposed Solution

## Contributions

- Contribution 1
- Contribution 2
- Contribution 3

## Paper Organization
"""

RELATED_WORK_MD = """\
# Related Work
<!-- Review related work. Compare existing approaches. -->

## Background
"""

METHODOLOGY_MD = """\
# Methodology
<!-- System model, architecture, design decisions. -->

## System Overview
"""

EXPERIMENTS_MD = """\
# Experimental Setup
<!-- Datasets, hardware, baseline methods, metrics. -->

## Setup
"""

RESULTS_MD = """\
# Results
<!-- Main experimental findings and comparisons. -->

## Performance Results
"""

DISCUSSION_MD = """\
# Discussion
<!-- Analysis, trade-offs, limitations. -->

## Analysis
"""

CONCLUSION_MD = """\
# Conclusion
<!-- Summary of findings and future work. -->

## Summary
"""

AUTHOR_YAML = """\
# Author information
# One entry per author. Mark corresponding: true for the
# corresponding author.
authors:
  - name: "Your Name"
    affiliation: "Your Institution"
    department: "Your Department"
    city: "Your City"
    country: "Your Country"
    email: "your@email.com"
    orcid: ""
    corresponding: true
"""

METADATA_YAML = """\
# Paper metadata
title: "Your Paper Title"
venue: "IEEE Access"
paper_type: "journal"  # journal or conference
keywords:
  - "keyword1"
  - "keyword2"
funding: ""
conflict_of_interest: "The authors declare no conflicts of interest."
data_availability: ""
code_availability: ""
acknowledgment: ""
sections_overview: ""
"""

MATH_MD = """\
# Mathematical Notation and Equations
<!-- List all equations here in LaTeX notation.
     PaperForge will number them sequentially.
     Format: ## Equation: Description
             $$latex here$$ -->

## Notation Table
| Symbol | Description |
|--------|-------------|
| x | variable x |
"""

SUCCESS_PANEL_BODY = """\
.paperforge/
├── paper.yaml          ← project metadata
├── claims/
│   └── claim_01.yaml   ← your first claim
├── experiments/
│   └── exp_01.yaml     ← your first experiment
├── figures/            ← figure YAMLs
├── tables/             ← table YAMLs
├── citations/          ← citation YAMLs
└── algorithms/         ← algorithm YAMLs
paper_information/
├── content/            ← Markdown files for sections (abstract, intro, etc.)
├── figures/            ← figure images
├── graphs/             ← graph generation scripts
├── tables/             ← CSV data tables
├── math.md             ← equations & notation
├── author.yaml         ← author & affiliation info
└── metadata.yaml       ← title, venue, keywords
paper_generated/
├── current/            ← latest compiled paper.tex, paper.pdf, paper.docx
└── previous/           ← prior build snapshot for comparison

Next steps:
  1. Edit paper_information/content/*.md or metadata.yaml
  2. Run paperforge import to update .paperforge/
  3. Fill in .paperforge/experiments/exp_01.yaml with your results
  4. Run paperforge doctor to check consistency
  5. Run paperforge build to generate paper_generated/current/"""


def run(path: Path) -> None:
    pf_dir = path / ".paperforge"

    if pf_dir.exists():
        console.print("[red]PaperForge already initialized in this directory.[/red]")
        sys.exit(1)

    # .paperforge/
    claims_dir = pf_dir / "claims"
    experiments_dir = pf_dir / "experiments"
    figures_dir = pf_dir / "figures"
    tables_dir = pf_dir / "tables"
    citations_dir = pf_dir / "citations"
    algorithms_dir = pf_dir / "algorithms"

    claims_dir.mkdir(parents=True)
    experiments_dir.mkdir(parents=True)
    figures_dir.mkdir(parents=True)
    tables_dir.mkdir(parents=True)
    citations_dir.mkdir(parents=True)
    algorithms_dir.mkdir(parents=True)

    (pf_dir / "paper.yaml").write_text(PAPER_YAML, encoding="utf-8")
    (claims_dir / "claim_01.yaml").write_text(CLAIM_01_YAML, encoding="utf-8")
    (experiments_dir / "exp_01.yaml").write_text(EXP_01_YAML, encoding="utf-8")
    (pf_dir / ".gitignore").write_text(PAPERFORGE_GITIGNORE, encoding="utf-8")

    # paper_information/
    info_dir = path / "paper_information"
    info_content_dir = info_dir / "content"
    info_figures_dir = info_dir / "figures"
    info_graphs_dir = info_dir / "graphs"
    info_tables_dir = info_dir / "tables"

    info_content_dir.mkdir(parents=True, exist_ok=True)
    info_figures_dir.mkdir(parents=True, exist_ok=True)
    info_graphs_dir.mkdir(parents=True, exist_ok=True)
    info_tables_dir.mkdir(parents=True, exist_ok=True)

    (info_figures_dir / ".gitkeep").write_text("", encoding="utf-8")
    (info_graphs_dir / ".gitkeep").write_text("", encoding="utf-8")
    (info_tables_dir / ".gitkeep").write_text("", encoding="utf-8")

    (info_content_dir / "abstract.md").write_text(ABSTRACT_MD, encoding="utf-8")
    (info_content_dir / "introduction.md").write_text(
        INTRODUCTION_MD, encoding="utf-8"
    )
    (info_content_dir / "related_work.md").write_text(
        RELATED_WORK_MD, encoding="utf-8"
    )
    (info_content_dir / "methodology.md").write_text(
        METHODOLOGY_MD, encoding="utf-8"
    )
    (info_content_dir / "experiments.md").write_text(
        EXPERIMENTS_MD, encoding="utf-8"
    )
    (info_content_dir / "results.md").write_text(RESULTS_MD, encoding="utf-8")
    (info_content_dir / "discussion.md").write_text(
        DISCUSSION_MD, encoding="utf-8"
    )
    (info_content_dir / "conclusion.md").write_text(
        CONCLUSION_MD, encoding="utf-8"
    )

    (info_dir / "author.yaml").write_text(AUTHOR_YAML, encoding="utf-8")
    (info_dir / "metadata.yaml").write_text(METADATA_YAML, encoding="utf-8")
    (info_dir / "math.md").write_text(MATH_MD, encoding="utf-8")

    # paper_generated/
    gen_dir = path / "paper_generated"
    gen_current = gen_dir / "current"
    gen_previous = gen_dir / "previous"

    gen_current.mkdir(parents=True, exist_ok=True)
    gen_previous.mkdir(parents=True, exist_ok=True)
    (gen_dir / ".gitignore").write_text(
        PAPER_GENERATED_GITIGNORE, encoding="utf-8"
    )

    # Legacy paper/ folder compatibility (also create if needed)
    paper_dir = path / "paper"
    paper_dir.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel(
            SUCCESS_PANEL_BODY,
            title="PaperForge Initialized",
            border_style="green",
        )
    )
