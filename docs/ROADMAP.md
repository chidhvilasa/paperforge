# PaperForge Roadmap

## Released

### v0.1.0
Core research dependency engine.
init, capture, doctor (20 checks), impact, build,
review, venues (ieee/acm/neurips), add-claim,
install-hooks, export, status, find.

### v0.2.0
Full command reference documentation.
README updated for all 12 commands.
PyPI package v0.2.0.

### v0.3.0
Claim versioning.
paperforge log: full change history for any claim.
paperforge diff: field-level diff against history or experiment.
History recorded automatically by capture, add-claim, doctor --fix.
Rich markup injection fix.
Rich markup injection fix.

### v0.4.0
IEEE Transactions journal LaTeX template.
paper_type and keywords fields in paper.yaml.
10 new doctor checks (30 total, 3 severity levels: ERROR/WARNING/INFO).
ieee-journal and ieee-trans venue targets.

### v0.5.0
latexmk compilation support (preferred over pdflatex).
Figure \label/\ref LaTeX integration.
affiliations field in paper.yaml.
microtype and hyperref in all IEEE preambles.
Doctor check 36 (MISSING_AFFILIATION).

### v0.6.0
Table as a first-class object.
paperforge add-table with row-by-row data entry.
IEEE LaTeX table generation (caption above tabular, no vertical lines).
5 new doctor checks (41 total): TABLE_NO_CAPTION (ERROR),
TABLE_NO_COLUMNS, TABLE_REFERENCED_BUT_NO_YAML,
TABLE_YAML_BUT_NO_CLAIM, TABLE_ROW_COLUMN_MISMATCH.

### v0.7.0
Traceability matrix export.
paperforge export traceability: MD + CSV + LaTeX longtable
generated simultaneously. Full claim-evidence linkage visible
in one artifact.

### v0.8.0
Critical fixes: Windows encoding, compsoc mode, capture
nested JSON, acronym plurals, multi-seed support.
New venue targets: ieee-access, ieee-compsoc, ieee-tdsc.
Wide table/figure support (table*/figure*).
acknowledgment field in paper.yaml.
Build output now in paper/ at project root.
paperforge improve: AI-assisted claim editing with y/n confirm.

### v0.9.0
Citation data model.
paperforge add-citation with full BibTeX metadata.
Build generates references.bib from YAML source of truth.
5 new doctor checks (48 total).
No more TODO stubs for defined citations.

### v1.0.0
Non-interactive CLI flags for all add-* commands (--text, --caption, etc.).
--from-yaml bulk object creation.
Multi-experiment claim support (experiments: list[str]).
paperforge export overleaf zip export.
Doctor check 49 (MULTI_EXPERIMENT_CLAIM).
Production/Stable status on PyPI.

### v1.1.0 (this release)
paper_information/ input layer for human-friendly content entry.
paperforge import command with claim deduplication.
paperforge update with PyPI check and editable install detection.
Versioned output: paper_generated/current/ + previous/.
generate-figures metric filtering (metric_keys, x_labels).
Doctor check 74 (FIGURE_MIXED_METRIC_UNITS).
sections_overview full-sentence detection.
Critical bug fixes: LaTeX escaping, BibTeX pipeline,
claim deduplication, stale PDF handling.

## Planned

### v1.2.0 — Figure Quality + Comparison Tables
- Multi-experiment comparison figures: plot the same metric
  across multiple experiments (e.g. latency vs traffic density)
- paperforge compare-experiments: generates comparison table
  and figure from 2+ experiment YAMLs
- Figure annotation: add significance markers (*, **, ***)
  to bars based on linked Wilcoxon p-values
- Table auto-formatting: highlight best value per column

## Non-Goals

These will never be in PaperForge core:
- AI that writes paper content (AI assists, never sources truth)
- Cloud storage of research data
- Replacing Overleaf, Zotero, or MLflow
- A web interface in core (plugins may add this)

See CONSTITUTION.md for the design principles behind these decisions.

## Contributing

See CONTRIBUTING.md to add a venue plugin or new doctor check.
New features must pass the CONSTITUTION.md feature filter.
