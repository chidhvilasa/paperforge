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

### v0.6.0 (this release)
Table as a first-class object.
paperforge add-table with row-by-row data entry.
IEEE LaTeX table generation (caption above tabular, no vertical lines).
5 new doctor checks (41 total): TABLE_NO_CAPTION (ERROR),
TABLE_NO_COLUMNS, TABLE_REFERENCED_BUT_NO_YAML,
TABLE_YAML_BUT_NO_CLAIM, TABLE_ROW_COLUMN_MISMATCH.

## Planned

### v0.7.0 — Citation Verification
- Integrate with Semantic Scholar API (opt-in, offline default)
- Verify that citation keys in claims actually exist in the
  literature
- Flag citations that appear hallucinated or unreachable
- paperforge cite-check command

### v0.8.0 — Traceability Matrix Export
- paperforge export traceability: generates a full matrix
  showing every claim's linked experiment, figures, tables,
  citations, and verification status
- Output formats: Markdown table, CSV, and LaTeX longtable
- Machine-readable for integration with review workflows
- Answers "which claim is supported by what?" at a glance

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
