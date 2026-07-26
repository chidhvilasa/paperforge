# Changelog

## [Unreleased]

### Fixed
- paperforge build no longer overwrites references.bib when
  real BibTeX entries exist. File is preserved if any @-block
  lacks "TODO". Stubs are only generated for new or stub-only files.
- Windows encoding: all open() calls in project.py and other
  commands now use encoding="utf-8" explicitly — em-dashes
  and non-ASCII content no longer corrupt on Windows cp1252
- compsoc hardcoded for all journal mode: IEEEPlugin now
  distinguishes "journal" (standard, non-compsoc) from
  "journal-compsoc" (CS Society journals only); ieee-journal
  and ieee-trans now correctly use \documentclass[journal]{IEEEtran}
- author block: non-compsoc journal mode uses \thanks{} form
  instead of \IEEEcompsocitemizethanks (compsoc-only macros)
- capture: nested JSON metrics now flattened recursively with
  dot-notation keys; silently-empty metrics replaced with
  warning message
- UNDEFINED_ACRONYM: plural forms (VANETs, RSUs) now handled;
  defining "(VANETs)" satisfies later bare "VANET" usage
- EXPERIMENT_NO_SEED: now accepts seeds: list[int] for
  multi-seed experiments; warning only fires if both
  seed and seeds are null

### Added
- acknowledgment: field in paper.yaml — build uses this
  instead of hardcoded TODO text; survives rebuilds
- Doctor check 42: MISSING_ACKNOWLEDGMENT (WARNING)
- ieee-access venue target: \documentclass[journal]{IEEEtran},
  no page limit, correct preamble for IEEE Access
- ieee-compsoc and ieee-tdsc venue targets for CS Society journals
- wide: bool field on Table and Figure — use table*/figure*
  for two-column spanning in IEEE layout
- Doctor check 43: WIDE_TABLE_RECOMMENDED (WARNING) when
  table has 6+ columns without wide: true
- seeds: list[int] field on Experiment for multi-seed support
- PyPI name conflict documented in README; package renamed
  "paperforge-research" in pyproject.toml

## [0.7.0] — 2026-07-26

### Added
- paperforge export traceability — full claim-evidence matrix
  generated in three formats in one command:
  * traceability.md: Markdown with emoji status indicators
    (✅ verified, ⚠️ unverified, ❌ stale), summary block
    showing evidence coverage %, one row per claim
  * traceability.csv: machine-readable with pipe-separated
    inner lists, full (untruncated) claim text, opens in Excel
  * traceability.tex: LaTeX longtable for appendix inclusion
    via \input{traceability}, multi-page continuation headers,
    \textcolor status, LaTeX-escaped claim text
- _escape_latex() helper (10 special character replacements,
  backslash first to prevent double-escaping)
- --output flag for traceability treats argument as directory
- docs/commands/traceability.md — full command reference
- 16 new tests in test_traceability.py (285 total)

## [0.6.0] — 2026-07-26

### Added
- Table as a first-class object: paperforge.models.table.Table
  with id, caption, columns, rows, notes, first_mentioned_in,
  source_experiment fields
- .paperforge/tables/ directory created by paperforge init
- PaperForgeProject loads all tbl_*.yaml files
- ResearchGraph.add_table(), get_table(), table_count
- paperforge add-table — interactive table YAML creation
  with row-by-row data entry
- LaTeX table generation: IEEE format with caption ABOVE
  tabular, \label{tab:id}, \arraystretch{1.3},
  no vertical lines, \hline at top/header/bottom
- 5 new doctor checks (37-41):
    37 TABLE_NO_CAPTION (ERROR — blocks build)
    38 TABLE_NO_COLUMNS (WARNING)
    39 TABLE_REFERENCED_BUT_NO_YAML (WARNING)
    40 TABLE_YAML_BUT_NO_CLAIM (WARNING)
    41 TABLE_ROW_COLUMN_MISMATCH (WARNING)
- paperforge impact shows table caption when YAML exists
- docs/commands/add-table.md
- 30 new tests (269 total)

## [0.5.0] — 2026-07-25

### Added
- affiliations field in paper.yaml — list of institution/department/
  city/country objects, matched to authors by index
- Affiliation dataclass in ProjectConfig
- Figure \label{fig:id} and \ref{fig:id} integration in
  LaTeX build output — figure environments emitted for claims
  with linked Figure objects
- latexmk support in paperforge build — preferred over pdflatex,
  falls back gracefully; build panel shows compiler used
- microtype and \usepackage[hidelinks]{hyperref} added to all
  IEEE venue preambles
- Doctor check 36: MISSING_AFFILIATION (WARNING)
- Competitive analysis: PaperShell, ieee-enhanced, and
  generator-latex-template reviewed; key improvements adopted
- Figure as a first-class object: paperforge.models.figure.Figure
  with id, caption, path, format, width_inches, resolution_dpi,
  first_mentioned_in, notes fields
- .paperforge/figures/ directory created by paperforge init
- PaperForgeProject loads all fig_*.yaml files from figures/
- ResearchGraph.add_figure(), get_figure(), figure_count
- paperforge add-figure — interactive figure YAML creation
- 5 new doctor checks (31-35): FIGURE_NO_CAPTION,
  FIGURE_NO_FIRST_MENTION, FIGURE_REFERENCED_BUT_NO_YAML,
  FIGURE_YAML_BUT_NO_CLAIM, LOW_RESOLUTION_FIGURE
- paperforge impact shows figure metadata when YAML exists,
  degrades gracefully when only bare string reference exists
- docs/commands/add-figure.md
- 24 new tests across test_figure_model.py, test_add_figure.py,
  test_doctor_figures.py (225 total)

### Fixed
- Journal author block now emits \IEEEcompsocitemizethanks
  structure when affiliations are provided

## [0.4.0] — 2026-07-25

### Added
- IEEE Transactions / journal LaTeX template (--target ieee-journal,
  ieee-trans): correct documentclass [10pt,journal,compsoc],
  abstract placement in \IEEEtitleabstractindextext,
  \IEEEraisesectionheading, \IEEEPARstart, \IEEEkeywords,
  acknowledgment block with compsoc conditional,
  references.bib stub generation
- paper_type field in paper.yaml ("conference" or "journal")
- keywords field in paper.yaml
- Venue targets: ieee-journal and ieee-trans registered
- 10 new doctor checks (21-30):
    21 UNDEFINED_ACRONYM (WARNING)
    22 ABSTRACT_TOO_LONG (WARNING, >250 words)
    23 ABSTRACT_TOO_SHORT (WARNING, <50 words)
    24 NO_INTRODUCTION_CLAIMS (WARNING)
    25 NO_CONCLUSION_CLAIMS (WARNING)
    26 EXPERIMENT_NO_RESULTS_FILE (WARNING)
    27 CLAIM_EXCESSIVE_LENGTH (WARNING, >80 words)
    28 EXPERIMENT_OVERCROWDED (WARNING, >=5 claims)
    29 RESULTS_SECTION_EMPTY (ERROR)
    30 EVIDENCE_COVERAGE (INFO)
- INFO severity level in doctor (never blocks build or commit)
- 22 new tests (201 total)

### Fixed
- Conference build: bibliography now generates references.bib stub
  when citations exist
- Existing test fixtures updated for RESULTS_SECTION_EMPTY check
  and expanded venue registry (5 targets)

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
