# Changelog

## [Unreleased]

## [1.4.0] — 2026-07-30

### Fixed (CRITICAL — Phase 34 figure path bug)
- Figure path resolution: figures/ now copied into the build
  directory before pdflatex runs. Previously pdflatex silently
  fell back to draft placeholders (blank boxes) and exited 0,
  causing paperforge to report "PDF generated ✓" for a broken
  PDF with blank figures and [?] citations.
- PDF quality verification: pdflatex log now parsed after
  compilation for undefined references, missing files, and
  draft mode. Quality warnings printed to console.
- Build success panel now shows "complete" vs "may be incomplete".

### Added (Phase 34 — Audit Compliance)
- Structured author fields: given_name, family_name,
  display_name, citation_name, ieee_membership_grade (null
  unless verified), affiliation_ids, orcid
- affiliations: dict in paper.yaml (separate from authors)
- Author.full_name and cite_name properties
- PDF metadata via \hypersetup (pdftitle, pdfauthor,
  pdfsubject, pdfkeywords) in all build output
- Draft vs submission build modes (--mode draft/submission);
  submission mode has extended blocking check set
- --force-anyway flag overrides blocking checks
- paper_generated/reports/ with doctor.md,
  claim_evidence_report.md, submission_checklist.md
- Claim.permitted_only_if: conditions evaluated against
  experiment metrics, violations block build
- REQUIRED_PLACEHOLDER_PATTERN: structured placeholder
  when required info missing, blocks build
- tests/fixtures/failed_builds/vanet_2026_07/ regression
  fixture (24 known failure modes from real manuscript)
- _copy_figures_to_build_dir(): copies figures into build dir
- _check_compilation_quality(): parses pdflatex log
- Doctor check 90: BUILD_PDF_INCOMPLETE (WARNING)

### Fixed (Phase 34 — Author/Identity)
- Author block never emits \IEEEmembership{} unless
  ieee_membership_grade is explicitly set to a valid grade
- Student Member and null grades suppressed from author block
- Author name never derived by heuristic token splitting

### Added (Doctor Checks 81-90)
- 81 AUTHOR_IDENTITY_INCONSISTENT (ERROR)
- 82 MISSING_PDF_METADATA (WARNING)
- 83 LATEX_ARTIFACT_IN_CLAIM (ERROR)
- 84 REQUIRED_PLACEHOLDER_IN_CLAIM (ERROR)
- 85 CLAIM_CONSTRAINT_VIOLATED (ERROR)
- 86 PVALUE_AMBIGUOUS (WARNING)
- 87 SIGNIFICANCE_LANGUAGE_MISMATCH (WARNING)
- 88 CITATION_HAS_INTERNAL_NOTE (ERROR)
- 89 NUMERIC_VALUE_UNSOURCED (WARNING)
- 90 BUILD_PDF_INCOMPLETE (WARNING)

## [1.3.0] — 2026-07-29

### Fixed (Phase 33)
- **CRITICAL: import no longer creates duplicate claims.**
  Re-running `paperforge import` on existing content now merges instead of
  appends. The root cause of doubled sections in generated papers is resolved.
  Each paragraph is identified by a 12-char MD5 hash of its first 120 chars.
  --force now UPDATES matched claim text (not creates duplicates).

### Added (Phase 33)
- `import_hash: str` field on Claim — tracks paragraph identity across import runs
- Doctor check 78: CLAIM_MISSING_IMPORT_HASH (INFO) — legacy claims without hash
- `paperforge sync` command — bidirectional sync between paper_information/ and .paperforge/
  - `--direction to-md`: claims are source of truth → rewrites *.md
  - `--direction to-claims`: same as import with merge mode
  - `--direction status`: shows per-section MD vs claims timestamps and in-sync state
- Biography support in paper.yaml: `biographies:` list with author/text/photo_path
  - `Biography.to_latex()` emits `\\IEEEbiography` (with photo) or
    `\\IEEEbiographynophoto` (without) in compiled LaTeX
  - Doctor check 79: MISSING_BIOGRAPHY (WARNING) — IEEE Access encourages biographies
- AI disclosure support: `ai_disclosure:` field in paper.yaml
  - Emits `\\subsection*{Use of Artificial Intelligence Tools}` when non-empty
  - Doctor check 80: MISSING_AI_DISCLOSURE (INFO) — IEEE policy compliance
- `paperforge validate` command — numerical claim audit against experiment data
  - Extracts ALL numbers (not just percentages) from claim text
  - Cross-checks against linked experiment metrics with 0.5 tolerance
  - Reports VERIFIED / UNVERIFIED / EXEMPT (is_math) per number
  - Writes `paper_information/VALIDATION_LOG.md`
- Colorblind-safe figure palette (Wong 2011) applied to all chart types
  - IEEE_STYLE dict centralizes all rcParams for consistent IEEE publication look
  - COLORS and HATCH_PATTERNS constants shared across bar/grouped_bar/line charts
- Doctor `--fix-hints` flag: shows concrete fix suggestion per issue
- Doctor `--json` flag: outputs issues as JSON for tooling integration
- Doctor shows issues grouped by section after summary line
- 15 new tests in test_capabilities.py (466 total)

### Fixed (Phase 32 — carried forward)
- IEEE Access author block: Student Member and empty membership suppressed from \\IEEEmembership{}
- \\IEEEPARstart now uses actual first two chars of first introduction claim text (not hardcoded)
- Unicode typography escaped: em-dash, en-dash, curly quotes, ellipsis, degree, multiplication, Greek letters
- Markdown links [text](url) → \\href{url}{text}
- Markdown bullet/numbered lists → itemize/enumerate
- Bare URLs → \\url{} via hyperref
- DUPLICATE_CLAIM_TEXT severity upgraded to ERROR (blocks build)
- Algorithm.to_latex() emits algorithmic[1] with proper \\State wrapping for plain-text steps
- \\usepackage{algorithm} and \\usepackage{algorithmic} added to preamble when algorithms exist in project

### Added (Phase 32)
- Figure.error_bars and std_metric_keys fields for uncertainty visualization in bar charts
- Figure.significance_markers field for *, **, n.s. annotation
- generate-figures chart_type: "grouped_bar" for multi-series grouped bar charts
- paperforge doctor --pre-submission: full submission readiness report
- build --force-anyway: override blocking doctor checks
- 10 new tests in test_ieee_template.py (451 total before Phase 33)


### Fixed (Phase 29 — critical bugs from production use)
- CRITICAL: escape_latex() now protects inline math spans
  ($...$, $$...$$, \(...\)) from escaping; claim.is_math and
  raw_latex bypass escaping entirely for full LaTeX content.
  Equations, subscripts, superscripts no longer corrupted.
- CRITICAL: export overleaf exits 1 if paper.tex not found
  at configured output_dir — no more silent stale-content fallback
- All output paths (output_dir, paper_information_dir, base_dir)
  now read from paper.yaml build section; no hardcoded
  project-root assumptions; _rotate_output uses configured path
- Citations rendered as \cite{key1,key2} inline before sentence
  period — not trailing separate \cite{} calls on their own line
- paperforge import now preserves ## subsection headers into
  claim.subsection field
- paperforge import now parses [citation-key] bracket notation
  into claim.citations (verifies key exists in .paperforge/citations/)
- paperforge import warns about claims with no linked experiment
- METRIC_CLAIM_MISMATCH now checks claim.experiments list
  in addition to primary claim.experiment

### Added (Phase 29)
- Claim.is_math and raw_latex fields: bypass escape_latex()
  for LaTeX math content
- Claim.claim_type field: "theorem", "lemma", "definition",
  "proof", "corollary", "remark" — emits correct LaTeX environments
  (\begin{theorem}, \begin{proof}, etc.) with \label{}
- Inline Markdown in claim text converted to LaTeX:
  **bold** → \textbf{}, *italic* → \textit{}, `code` → \texttt{}
- Table.raw_rows field: bypass escaping for pre-formatted LaTeX rows
- Figure.line_experiments and x_values fields for multi-series
  line charts
- generate-figures chart_type: "line" with multi-experiment overlay
- Affiliation.membership field: IEEE membership grade
  ("Member", "Senior Member", "Fellow")
- Affiliation.shared_with field: grouped author footnotes
  (two authors sharing one \thanks{} block)
- Doctor check 75: MATH_CLAIM_MISSING_FLAG (WARNING) — fires
  when claim text contains LaTeX math commands but is_math: false
- Doctor check 76: PROOF_WITHOUT_THEOREM (WARNING) — fires
  when a proof claim has no preceding theorem/lemma
- paperforge doctor --self-check: installation health check
  (version, dependencies, LaTeX toolchain, path validation)
- 18 new tests (441 total)

## [1.1.0] — 2026-07-26

### Added
- paper_information/ input layer: human-friendly directory created by paperforge init with content/*.md section files, graphs/*.py, tables/*.csv, author.yaml, metadata.yaml
- paperforge import: reads paper_information/ and populates .paperforge/ objects; deduplicates existing claims by first 80 chars; executes graph scripts; converts CSV to table YAMLs; parses contribution bullets from introduction.md
- paper_generated/current/ and paper_generated/previous/ versioned output: previous/ holds prior build for comparison; rotated at start of every successful build
- paperforge update: checks PyPI for latest version and upgrades in-place; detects editable installs and shows git instructions; --git flag for development installs; --pre for pre-releases
- generate-figures metric_keys field: plot specific metrics only, preventing mixed-unit charts (ms + ratios on same axis)
- generate-figures x_labels field: readable axis tick labels
- Doctor check 74: FIGURE_MIXED_METRIC_UNITS (WARNING)
- Algorithm model: id, caption, steps, notes; to_latex() generates algorithmic environment
- paperforge generate-figures command: matplotlib plots from experiment metrics at 300 DPI with IEEE-compatible styling
- Claim.subsection field: emits \subsection{} in LaTeX
- Claim.is_contribution field: renders as \begin{itemize} list in introduction
- sections_overview in paper.yaml with full-sentence detection
- Figure placeholder \fbox for missing image files
- 19 new tests across this release cycle (423 total)

### Fixed
- sections_overview: auto-detects full sentences vs completion fragments; no longer prepends "organized as follows:" to complete sentences
- generate-figures: metric filtering prevents scientifically misleading mixed-unit charts
- update command: detects editable install, provides correct git pull instructions rather than PyPI upgrade
- LaTeX special character escaping applied to all user text (%, &, $, #, _, {, }, ~, ^) -- resolves truncated abstract and missing % signs in compiled PDF
- Claim deduplication: multi-section claims emit text once (first section only); subsequent sections emit comment ref
- BibTeX pipeline: pdflatex -> bibtex -> pdflatex -> pdflatex resolves [?] citation placeholders in compiled output
- Stale PDF detection and deletion before rebuild
- references.bib preserved when real entries exist; rebuilt from citation YAMLs when they exist (source of truth)
- Windows encoding: explicit UTF-8 on all open() calls

## [1.0.0] — 2026-07-26

### Added
- Non-interactive flags for add-claim (--text, --experiment, --sections, --figures, --tables, --citations, --status), add-figure (--caption, --path-file, --format, --width, --dpi, --section, --notes, --wide), add-table (--caption, --experiment, --columns, --section, --notes, --wide), add-citation (--type, --authors, --title, --year, --venue, --volume, --number, --pages, --doi, --notes)
- --from-yaml flag on all add-* commands for bulk object creation from YAML files
- Multi-experiment claim support: experiments: list[str] field on Claim alongside primary experiment field; get_affected() traverses both primary and additional experiments
- Doctor check 49: MULTI_EXPERIMENT_CLAIM (INFO)
- paperforge export overleaf: bundles paper.tex + references.bib + traceability.tex + figures/ into paper_overleaf.zip for Overleaf upload
- 15 new tests in test_noninteractive.py (360 total)

## [0.9.0] — 2026-07-26

### Added
- Citation as a first-class object: Citation dataclass (key, type, authors, title, year, venue, volume, number, pages, doi, url, publisher, institution, notes)
- Citation.to_bibtex() with type-correct BibTeX field names (journal/booktitle/school/institution/howpublished/url) and empty-field omission
- .paperforge/citations/ directory created by paperforge init
- PaperForgeProject loads all *.yaml from citations/; citation_map property for O(1) key lookup
- paperforge add-citation — interactive citation entry; semicolon-separated authors; year validation
- paperforge build generates references.bib from real citation YAMLs (source of truth, rebuilt every build); stubs generated only for keys without YAMLs; mixed real+stub supported in same file
- 5 new doctor checks (44-48): 44 CITED_KEY_NO_YAML (WARNING), 45 CITATION_YAML_NO_CLAIM (WARNING), 46 CITATION_NO_TITLE (ERROR), 47 CITATION_NO_YEAR (WARNING), 48 CITATION_NO_AUTHORS (WARNING)
- docs/commands/add-citation.md
- 22 new tests (345 total)

## [0.8.0] — 2026-07-26

### Added
- Default build output directory changed from `.paperforge/output/` to `paper/` at project root
- `paperforge init` creates `paper/` directory with `paper/.gitignore` for LaTeX auxiliary file exclusions
- Automatic folder reveal in OS file explorer upon successful PDF compilation (`--no-reveal` CLI flag added to `paperforge build`)
- `paperforge improve` command for interactive AI-assisted claim text improvement via `llm` CLI with history snapshot recording
- `paperforge export traceability` copies `traceability.tex` to `paper/` when `paper/` directory exists
- `acknowledgment` field in `paper.yaml` — build uses this instead of hardcoded TODO text; survives rebuilds
- Doctor check 42: `MISSING_ACKNOWLEDGMENT` (WARNING)
- `ieee-access` venue target: `\documentclass[journal]{IEEEtran}`, no page limit, correct preamble for IEEE Access
- `ieee-compsoc` and `ieee-tdsc` venue targets for CS Society journals
- `wide: bool` field on Table and Figure — use `table*`/`figure*` for two-column spanning in IEEE layout
- Doctor check 43: `WIDE_TABLE_RECOMMENDED` (WARNING) when table has 6+ columns without `wide: true`
- `seeds: list[int]` field on Experiment for multi-seed support
- PyPI name conflict documented in README; package renamed `"paperforge-research"` in `pyproject.toml`

### Fixed
- `paperforge build` no longer overwrites `references.bib` when real BibTeX entries exist. File is preserved if any @-block lacks "TODO". Stubs are only generated for new or stub-only files.
- Windows encoding: all `open()` calls in `project.py` and other commands now use `encoding="utf-8"` explicitly — em-dashes and non-ASCII content no longer corrupt on Windows cp1252
- compsoc hardcoded for all journal mode: IEEEPlugin now distinguishes "journal" (standard, non-compsoc) from "journal-compsoc" (CS Society journals only); `ieee-journal` and `ieee-trans` now correctly use `\documentclass[journal]{IEEEtran}`
- author block: non-compsoc journal mode uses `\thanks{}` form instead of `\IEEEcompsocitemizethanks` (compsoc-only macros)
- capture: nested JSON metrics now flattened recursively with dot-notation keys; silently-empty metrics replaced with warning message
- `UNDEFINED_ACRONYM`: plural forms (VANETs, RSUs) now handled; defining "(VANETs)" satisfies later bare "VANET" usage
- `EXPERIMENT_NO_SEED`: now accepts `seeds: list[int]` for multi-seed experiments; warning only fires if both `seed` and `seeds` are null

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
