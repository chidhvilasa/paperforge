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

### v1.1.0
paper_information/ input layer for human-friendly content entry.
paperforge import command with claim deduplication.
paperforge update with PyPI check and editable install detection.
Versioned output: paper_generated/current/ + previous/.
generate-figures metric filtering (metric_keys, x_labels).
Doctor check 74 (FIGURE_MIXED_METRIC_UNITS).
sections_overview full-sentence detection.
Critical bug fixes: LaTeX escaping, BibTeX pipeline,
claim deduplication, stale PDF handling.

### v1.5.0 (Phase 36 — Released)
- PyMuPDF PDF page image rendering (`pdf_pages/page-XXX.png`).
- Template fingerprinting for IEEE, IEEE Access, ACM, NeurIPS.
- Visual overlap & bounding box defect detection (`PDF_OBJECT_OVERLAP`).
- Text artifact scanner (`PDF_TEXT_ARTIFACT`).
- Blank & near-blank page detector (`PDF_NEAR_BLANK_PAGE`).
- Structural integrity & canonical outline engine (`SECTION_ROADMAP_MISMATCH`, `FLOAT_AFTER_CONCLUSION`, `DUPLICATE_OR_CONFLICTING_LABEL`).
- Reference verification with optional Crossref API lookups (`paperforge references verify --online`).
- CLI command `paperforge preflight`.
- 13 new doctor checks (91-103, total 103 doctor checks).
- 25 CLI commands.
- 499 tests.

### v1.6.0 - v1.7.0

Entries for v1.2.0-v1.4.0 and v1.6.0 were not backfilled into this
document by the sessions that shipped them; see `CHANGELOG.md` for the
complete, accurate history.

v1.7.0 added a second, optional workflow around a canonical
`paperforge.project.yaml` manifest, entirely additive to everything
above: safe-YAML/path-secured manifest validation and migration,
mode-aware requirements evaluation, approval-gated structural planning
with automatic staleness detection, deterministic template-only
generation (explicitly not an AI source of truth — see Constitution
principle 5), sentence-level provenance sidecars, build-output
promotion/rollback, and a centralized timeout-safe subprocess runner.
Full details in `CHANGELOG.md`'s `[1.7.0]` entry and this pass's honest
completion report (interactive intake, safe LaTeX/BibTeX import into the
new manifest, a real AI provider, versioned venue adapters, and reference-
pipeline hardening were scoped for this pass but not completed).

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
