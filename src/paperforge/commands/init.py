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
  output_dir: "paper"
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

PAPER_GITIGNORE = """\
# Auto-generated LaTeX auxiliary files
*.aux
*.log
*.out
*.toc
*.lof
*.lot
*.fls
*.fdb_latexmk
*.synctex.gz
*.bbl
*.blg

# Keep these:
!paper.tex
!paper.pdf
!references.bib
!traceability.tex
"""

SUCCESS_PANEL_BODY = """\
.paperforge/
├── paper.yaml          ← project metadata
├── claims/
│   └── claim_01.yaml   ← your first claim (fill in text)
├── experiments/
│   └── exp_01.yaml     ← your first experiment (fill in metrics)
├── figures/            ← drop figure YAMLs here (paperforge add-figure)
├── tables/             ← add table data (paperforge add-table)
├── citations/          ← add citation metadata (paperforge add-citation)
└── .gitignore
paper/
└── .gitignore          ← paper.tex, paper.pdf committed, aux files ignored

Next steps:
  1. Edit .paperforge/paper.yaml — add title and authors
  2. Fill in .paperforge/experiments/exp_01.yaml with your results
  3. Fill in .paperforge/claims/claim_01.yaml — link claim to experiment
  4. Run paperforge doctor to check consistency"""


def run(path: Path) -> None:
    pf_dir = path / ".paperforge"

    if pf_dir.exists():
        console.print("[red]PaperForge already initialized in this directory.[/red]")
        sys.exit(1)

    claims_dir = pf_dir / "claims"
    experiments_dir = pf_dir / "experiments"
    figures_dir = pf_dir / "figures"
    tables_dir = pf_dir / "tables"
    citations_dir = pf_dir / "citations"
    paper_dir = path / "paper"
    claims_dir.mkdir(parents=True)
    experiments_dir.mkdir(parents=True)
    figures_dir.mkdir(parents=True)
    tables_dir.mkdir(parents=True)
    citations_dir.mkdir(parents=True)
    paper_dir.mkdir(parents=True, exist_ok=True)

    (pf_dir / "paper.yaml").write_text(PAPER_YAML, encoding="utf-8")
    (claims_dir / "claim_01.yaml").write_text(CLAIM_01_YAML, encoding="utf-8")
    (experiments_dir / "exp_01.yaml").write_text(EXP_01_YAML, encoding="utf-8")
    (pf_dir / ".gitignore").write_text(PAPERFORGE_GITIGNORE, encoding="utf-8")
    (paper_dir / ".gitignore").write_text(PAPER_GITIGNORE, encoding="utf-8")

    console.print(
        Panel(
            SUCCESS_PANEL_BODY,
            title="PaperForge Initialized",
            border_style="green",
        )
    )
