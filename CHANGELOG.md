# Changelog

## [1.5.3] — 2026-08-04

### Fixed
- **PDF preflight false positive — drop-cap block clustering
  (`PDF_OBJECT_OVERLAP`)**: PyMuPDF's block extraction can split a
  drop-cap paragraph (e.g. IEEEtran's `\IEEEPARstart`) so that a short
  heading-sized block and the tall multi-line paragraph block beneath it
  end up with bounding boxes that touch at their shared vertical
  boundary, even though the rendered ink never collides. Added
  `_classify_block_overlap()`, a geometry-based classifier (heading-sized
  vs. multi-line block, same-column stacking, boundary-only touch) that
  recognizes this specific pattern as `LEGITIMATE_DROPCAP_WRAP` and
  reports it at `INFO` severity instead of blocking `ERROR`. A collision
  involving an actual "Index Terms" block is never exempted regardless of
  geometry, preserving the previously-tracked real defect class. Every
  other overlap shape (real body-text collisions, an oversized glyph
  embedded mid-paragraph, low-horizontal-overlap/cross-column cases)
  remains a full-severity finding.
- **PDF preflight false positive — Roman-numeral heading adjacent to a
  figure/table citation (`PDF_TEXT_ARTIFACT`, "orphan reference
  numeral")**: the previous detection regex (`[I|V|X]+`, a character
  class bug that matched any run of the literal characters I, |, V, X)
  flagged a sentence ending in `(see Fig. N)` immediately followed, in
  flat extracted reading order, by an unrelated new section/subsection
  heading beginning with a Roman numeral (e.g. `I. Traffic Density
  Sweep`, `VII. Discussion`) as if it were a broken citation. Replaced
  with `_find_orphan_reference_numerals()`, which excludes a match when
  the trailing numeral is immediately followed by `.` and a capitalized
  word — the signature of a genuine numbered heading — while still
  flagging a truly dangling numeral with no such continuation.
- **`paperforge build`'s "Visual overlap scan" / "Text artifact scan"
  summary lines**: previously flagged FAILED whenever *any*
  `PDF_OBJECT_OVERLAP`/`PDF_TEXT_ARTIFACT` finding existed regardless of
  severity, which would have kept showing FAILED for a
  correctly-downgraded `INFO`-level drop-cap finding. Now only counts
  `ERROR`-severity findings, consistent with `PreflightReport.passed`.

## [1.5.2] — 2026-08-04

### Fixed
- **Figure path resolution**: figure source paths are now resolved against
  the project root and the resolved asset is copied into the build output
  directory before LaTeX generation, so `\includegraphics` paths are
  package/output-relative rather than accidentally relative to
  project_root. Previously a figure whose asset genuinely existed on disk
  could still be reported as missing and silently replaced with an
  `\fbox` placeholder, because the existence check and the emitted LaTeX
  path used inconsistent bases. Works for nested paths
  (`assets/plots/figure-01.pdf`), custom output directories, and rejects
  absolute or parent-escaping (`../`) configured paths. Same-basename
  figures in different subdirectories no longer collide in the packaged
  output, since directory structure is preserved.
- **Submission-mode figure blocking**: a required figure whose source
  asset cannot be resolved now blocks `paperforge build --mode submission`
  with a specific, actionable error instead of silently emitting a
  placeholder. Draft mode still allows a placeholder, with a clear
  per-figure warning. PDF preflight additionally flags a "Figure
  placeholder" string that reaches a rendered page.
- **Overleaf zip export**: figure assets are now packaged using the same
  path-resolution logic (and the same relative paths) as the generated
  `paper.tex`, instead of a separate, older mechanism that only scanned
  two hardcoded directory names and flattened files by basename —
  which could both miss figures and desync from the actual
  `\includegraphics` paths.
- **IEEE Access first-page overlap**: the first ("introduction") section
  heading is no longer unconditionally wrapped in
  `\IEEEraisesectionheading`. That raised-heading layout only clears the
  Index Terms block when it happens to fit on one line; with a longer
  Index Terms list the raised heading (and drop cap) collided with it.
  First-section heading style is now a per-venue policy
  (`first_section_heading_policy`): IEEE Access renders a plain
  `\section{...}` (safe regardless of content length); generic IEEE
  journal/transactions/compsoc targets keep the existing raised-heading
  behavior unchanged.
- **Output rotation isolation**: `_rotate_output` no longer archives every
  output directory into one fixed, shared `previous/` sibling. The
  archive location is now scoped to the selected output directory's own
  name (a candidate directory `output/candidate-a` archives to
  `output/candidate-a.previous`, never `output/previous`), so building
  into one output directory can no longer silently overwrite an unrelated
  directory's preserved content. The conventional `current/` ->
  `previous/` pairing is unchanged for backward compatibility. Rotation
  is now configurable via `build.rotation` in `paper.yaml`
  (`preserve_previous` [default] / `disabled` / `timestamped`) and
  `build.rotation_archive_dir` for an explicit archive path. Rotation
  safely no-ops (rather than corrupting data) if the computed archive
  path would equal or nest inside the output directory.
- **`PVALUE_AMBIGUOUS` false positives**: p-value detection now
  recognizes explicit syntax (`p = .05`, `p<.01`, `p-value of .03`,
  `p value was 0.04`, Unicode `≤`/`≥`) instead of a narrower fixed-format
  regex. The "multiple quantities share one p-value" heuristic now
  strips structural references (`Figure 1`, `Section 3`) and generic
  labeled identifiers (`batch-50`, `model-7`, `protocol-v2`, `version 2`,
  `sample 10`, `experiment 5`, ...) before counting candidate quantities,
  so digit-bearing configuration/version identifiers are no longer
  mistaken for measured metrics.

## [1.5.1] — 2026-08-03

### Fixed
- **Pytest collection**: canonical `testpaths`/`norecursedirs` in
  `pyproject.toml` so backup, audit-output, dist, build, and venv
  directories are never discovered as duplicate test modules.
- **`paperforge build`**: `_compile_pdf_full` no longer hardcodes
  `latexmk = None` — latexmk is now correctly detected via `shutil.which`
  and preferred over the raw `pdflatex+bibtex` pipeline when available.
- **`AUTHOR_IDENTITY_INCONSISTENT` doctor check**: previously matched a
  single hardcoded name and was effectively dead code for any other
  project; rewritten as a generic given-name/surname mismatch detector
  that works for any author, and no longer scans the paper title (which
  produced false positives against ordinary prose).
- **`PVALUE_AMBIGUOUS` doctor check**: previously relied on a fixed,
  networking/ML-biased metric-keyword list (`latency`, `pdr`, `throughput`,
  `accuracy`, ...); rewritten as a domain-independent heuristic that counts
  distinct numeric quantities in the claim text instead.
- **Structural-reference exclusion**: scientific-number extraction now
  strips `Figure N` / `Section N` / `Table N` / `Eq. N` and `{{figure:id}}`
  -style symbolic references before flagging unsourced numeric claims.
- **Numeric tolerance**: claim-vs-evidence numeric matching tightened from
  a flat `0.5` tolerance to `1e-4`.
- **Citation evidence**: `Citation` now supports a structured
  `evidence: dict[str, float]` field (optional, backward compatible).
- **Test hygiene**: tests no longer trigger real OS side effects
  (`build.run()`'s reveal-in-file-explorer step is now disabled by default
  for the whole test session via an autouse fixture in `tests/conftest.py`,
  regardless of whether a real LaTeX toolchain happens to be installed on
  the machine running the tests).

### Changed — generalization and privacy hardening
- `paperforge init`'s generated project template no longer scaffolds a
  default affiliation with a real institution; the affiliation block is now
  blank/user-fillable with fictional examples in comments only.
- Removed a real person's name, a real email address, and a real
  institution name that had leaked into a doctor-check implementation, the
  `init` template, the README, the full CLI command-reference docs, and
  several test fixtures. Replaced throughout with fictional neutral
  examples (e.g. "Alex Example", "Example Institute of Technology").
- Crossref User-Agent string now derives its version from
  `paperforge.__version__` instead of a separately hardcoded literal.

## [1.5.0] — 2026-07-30

### Added (Phase 36 — Visual PDF Preflight, Template Fingerprinting, Structural Integrity, Reference Verification)
- **Rendered PDF Preflight Suite (`paperforge preflight`)**: PyMuPDF (`fitz`) visual rendering of all PDF pages to high-resolution PNG images (`paper_generated/reports/pdf_pages/page-XXX.png`).
- **Template Fingerprinting (`template_manifest.json`)**: Venue template manifests and verification for IEEE (`ieee`), IEEE Access (`ieee_access`), ACM (`acm`), and NeurIPS (`neurips`).
- **Visual Overlap & Bounding Box Detection**: Bounding box geometry analysis catching overlapping headings, text-on-text overlaps, and Index Terms overlapping Introduction headings.
- **Text Artifact & Escaping Corruption Detection**: Scans PDF text for raw LaTeX commands (`\textbf`, `\texttt`), escaping corruption (`extbf{`, `exttt{`), `[??]`, `[?]`, `undefined citation`, `TODO`, `TBD`, `[REQUIRED INFORMATION MISSING`, and malformed percentages (`73.6At`).
- **Blank & Near-Blank Page Detection**: Detects blank pages and displaced float pages.
- **Canonical Document Outline & Structural Integrity**: Section roadmap verification, float-after-conclusion detection (`FLOAT_AFTER_CONCLUSION`), duplicate label detection (`DUPLICATE_OR_CONFLICTING_LABEL`), and symbolic reference resolver (`{{section:id}}`, `{{figure:id}}`, `{{table:id}}`).
- **Reference Verification & Crossref API Integration (`paperforge references verify --online`)**: BibTeX citation validation with optional Crossref API DOI lookups and local caching.
- **13 New Doctor Checks (Checks 91–103)**:
  - Check 91: `VENUE_TEMPLATE_MISMATCH` (ERROR)
  - Check 92: `VENUE_TEMPLATE_UNVERIFIED` (WARNING/ERROR)
  - Check 93: `RAW_LATEX_ESCAPE_CORRUPTION` (ERROR)
  - Check 94: `PDF_RENDER_FAILED` (ERROR)
  - Check 95: `PDF_TEXT_ARTIFACT` (ERROR)
  - Check 96: `PDF_OBJECT_OVERLAP` (ERROR)
  - Check 97: `PDF_CONTENT_OUT_OF_BOUNDS` (ERROR)
  - Check 98: `PDF_NEAR_BLANK_PAGE` (WARNING/ERROR)
  - Check 99: `SECTION_ROADMAP_MISMATCH` (WARNING/ERROR)
  - Check 100: `FLOAT_AFTER_CONCLUSION` (WARNING/ERROR)
  - Check 101: `DUPLICATE_OR_CONFLICTING_LABEL` (ERROR)
  - Check 102: `UNRESOLVED_CROSS_REFERENCE` (ERROR)
  - Check 103: `REFERENCE_METADATA_MISMATCH` (WARNING)

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
