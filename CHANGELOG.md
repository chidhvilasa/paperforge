# Changelog

## [Unreleased]

### Added
- IEEE Transactions / journal LaTeX template (--target ieee-journal,
  ieee-trans): correct documentclass, abstract placement in
  \IEEEtitleabstractindextext, \IEEEraisesectionheading,
  \IEEEPARstart, \IEEEkeywords, acknowledgment block,
  references.bib generation
- paper_type field in paper.yaml ("conference" or "journal")
- keywords field in paper.yaml
- venue targets: ieee-journal and ieee-trans aliases added
- 10 new doctor checks (21-30): UNDEFINED_ACRONYM,
  ABSTRACT_TOO_LONG, ABSTRACT_TOO_SHORT, NO_INTRODUCTION_CLAIMS,
  NO_CONCLUSION_CLAIMS, EXPERIMENT_NO_RESULTS_FILE,
  CLAIM_EXCESSIVE_LENGTH, EXPERIMENT_OVERCROWDED,
  RESULTS_SECTION_EMPTY (ERROR), EVIDENCE_COVERAGE (INFO)
- INFO severity level in doctor (never blocks, informational only)
- 22 new tests across test_build_ieee.py, test_doctor_hardened.py
  (201 total)

### Fixed
- conference build: bibliography now generates references.bib stub
  alongside paper.tex when citations exist

## [0.3.0] — 2026-07-25

### Added
- Claim versioning: history snapshots recorded in
  .paperforge/history/ whenever PaperForge writes a claim
- paperforge log — shows full change history of a claim,
  newest first, with per-entry diffs between snapshots
- paperforge diff --against previous: field-level diff
  between current claim and most recent history snapshot
- paperforge diff --against experiment: compares percentage
  values in claim text to linked experiment metrics
- paperforge.history module: record_snapshot, load_history,
  diff_snapshots
- History integrated into capture, add-claim, and doctor --fix
- docs/commands/log.md and docs/commands/diff.md
- 26 new tests (179 total)

### Fixed
- Rich markup injection: log and diff commands now use
  rich.text.Text objects for user-controlled strings to
  prevent bracket sequences in data from being parsed
  as Rich markup tags

## [0.2.0] — 2026-07-25

### Added
- paperforge add-claim — interactive terminal claim creation
  with guided prompts for all claim fields
- paperforge install-hooks — installs git pre-commit hook that
  runs paperforge doctor and blocks commits on ERRORs
- 10 new deterministic doctor checks (checks 11-20):
  METRIC_CLAIM_MISMATCH, DUPLICATE_CLAIM_TEXT,
  CLAIM_IN_NO_SECTION, EXPERIMENT_NO_DESCRIPTION,
  EXPERIMENT_NO_HARDWARE, EXPERIMENT_NO_DATASET,
  EXPERIMENT_NO_SEED, UNCLAIMED_EXPERIMENT,
  INVALID_FIGURE_ID, INVALID_TABLE_ID
- paperforge.utils.numbers — number extraction and matching
  utilities used by METRIC_CLAIM_MISMATCH check
- 36 new tests across test_add_claim.py, test_install_hooks.py,
  test_numbers.py, test_doctor_extended.py (125 total)
- paperforge export — BibTeX stubs, JSON graph schema, Markdown summary
- paperforge status — project health dashboard with section coverage
  and submission readiness indicator
- paperforge find — case-insensitive full-text search across claims
  and experiments
- Full command reference: docs/commands/ (12 files + INDEX.md)
- docs/ROADMAP.md — planned versions v0.3.0 through v0.6.0
- 28 new tests (153 total)

### Changed
- README.md updated for all 12 commands with new Quick Start guide
- pyproject.toml version bumped to 0.2.0

## [0.1.0] — 2026-07-25

### Added
- Project bootstrap
- CONSTITUTION.md with 10 core principles
- Directory structure for src layout
- Typer CLI shell (--version, --help)
- Placeholder modules for models, graph, core
- Claim dataclass with from_yaml / to_yaml and ClaimStatus literal type
- Experiment dataclass with from_yaml / to_yaml
- ResearchGraph with add_claim, add_experiment, get_affected
- AffectedNodes dataclass returned by get_affected
- 12 passing tests across test_models.py and test_graph.py
- paperforge init command — creates .paperforge/ in any project directory
- PaperForgeProject loader — reads paper.yaml, claims/, experiments/ into typed objects
- ProjectConfig dataclass for paper.yaml deserialization
- commands/ package for future CLI command modules
- 13 new tests across test_init.py and test_project.py (25 total)
- paperforge capture — parses flat and nested metrics JSON,
  creates/updates Experiment, generates draft Claim file
- paperforge doctor — 10 deterministic checks, ERROR/WARNING
  severity split, --fix flag auto-sets unverified claims to stale
- 22 new tests across test_capture.py and test_doctor.py (47 total)
- paperforge impact — dependency graph traversal showing all
  claims, sections, figures, tables affected by an experiment
- paperforge build — compiles structured research data into
  IEEE-style LaTeX; attempts PDF via pdflatex if available
- collect_issues() refactored out of doctor.run() for reuse
  by build's pre-flight ERROR check
- 22 new tests across test_impact.py and test_build.py (69 total)
- paperforge review — AI-assisted paper review via llm CLI tool;
  advisory only; runs doctor checks first; saves to .paperforge/review/
- Venue plugin architecture — VenuePlugin ABC with name, display_name,
  latex_documentclass, required_sections, max_pages, validate(),
  generate_preamble(), generate_author_block()
- IEEEPlugin, ACMPlugin, NeurIPSPlugin venue implementations
- Venue registry with get_plugin() and list_plugins()
- paperforge venues command — lists all available venue targets
- paperforge build --target and paperforge doctor --target options
- 20 new tests across test_review.py and test_venues.py (89 total)
- PyPI packaging metadata (classifiers, keywords, project URLs)
- LICENSE (MIT)
- CONTRIBUTING.md with venue plugin extension guide
- README.md rewritten for public audience with quick start guide
