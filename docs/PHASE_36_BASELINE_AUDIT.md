# Phase 36 Baseline Audit

**Date:** 2026-07-30
**Project:** PaperForge

## 1. Baseline Metrics

- **Current Package Version:** `1.4.0` (in `pyproject.toml`, `src/paperforge/__init__.py`, CLI `paperforge --version`)
- **Actual Test Count:** `489 passed` (`uv run pytest tests/ -q`)
- **Actual Doctor Check Count:** `90 checks` (checks 1-49, 75-76, 81-90 in `src/paperforge/commands/doctor.py`)
- **Actual CLI Command Count:** `24 CLI commands` (`init`, `capture`, `impact`, `build`, `doctor`, `review`, `venues`, `add-claim`, `add-figure`, `add-table`, `add-citation`, `generate-figures`, `install-hooks`, `export`, `status`, `find`, `log`, `diff`, `improve`, `import`, `clean`, `sync`, `update`, `validate`)

## 2. Architecture & Implementation Baselines

### Template Storage & Selection
- Venue templates are located under venue plugin definitions (e.g., `src/paperforge/venues/ieee.py`, `acm.py`, `neurips.py`).
- Preambles and document classes are generated via python string templates inside venue plugins.
- Current template selection has no SHA-256 fingerprinting or manifest verification for immutable template assets.

### LaTeX Escaping Implementation
- LaTeX escaping is handled by `src/paperforge/utils/latex.py` (`escape_latex()`).
- Prose escaping uses simple regex replacements. Unsafe escape handling (such as `\t`, `\n`, `\b` inside string literals or JSON parsing) can cause `\textbf` to become a tab plus `extbf`.

### PDF Compilation Implementation
- Compilation is handled in `src/paperforge/commands/build.py`.
- Supports `latexmk` with fallback to `pdflatex`.
- Copies figures to build output directory before compiling.
- Parses `pdflatex.log` for warnings, missing files, and `[?]` references.

### PDF Inspection Capabilities
- Currently limited to log parsing (`_check_compilation_quality()`).
- No rendered PDF page image generation, no PyMuPDF page preflight, no visual bounding box overlap detection, no extracted PDF text artifact scanning.

### Fixture Coverage
- `tests/fixtures/failed_builds/vanet_2026_07/fixture.yaml` documents 24 failure modes from the real VANET manuscript.
- Additional failing and passing synthetic fixtures needed for Phase 36 (rendered PDF overlap, raw LaTeX injection, escape corruption, section roadmap mismatch, float after conclusion, etc.).

### Affected Public APIs & Commands
- CLI: Adding `paperforge preflight` command.
- `paperforge build --mode submission`: auto-invokes preflight.
- `paperforge doctor --mode submission`: includes preflight results.
- `paperforge references verify --online`: optional Crossref verification command.
- New Doctor checks (13 new checks: `VENUE_TEMPLATE_MISMATCH`, `VENUE_TEMPLATE_UNVERIFIED`, `RAW_LATEX_ESCAPE_CORRUPTION`, `PDF_RENDER_FAILED`, `PDF_TEXT_ARTIFACT`, `PDF_OBJECT_OVERLAP`, `PDF_CONTENT_OUT_OF_BOUNDS`, `PDF_NEAR_BLANK_PAGE`, `SECTION_ROADMAP_MISMATCH`, `FLOAT_AFTER_CONCLUSION`, `DUPLICATE_OR_CONFLICTING_LABEL`, `UNRESOLVED_CROSS_REFERENCE`, `REFERENCE_METADATA_MISMATCH`).

### Known Risks & Backward Compatibility
- Existing v1.4.0 projects must continue to build in `--mode draft`.
- PyMuPDF (fitz) or pdfplumber dependency must be handled cleanly. If PyMuPDF is installed or PyMuPDF/Pillow available, rendered page inspection and object geometry extraction will use it.
- Offline behavior for reference verification must default to disabled and fall back gracefully without breaking builds.

## 3. Baseline Audit Execution Commands & Results

```
$ uv run pytest tests/ -q
........................................................................ [ 14%]
........................................................................ [ 29%]
........................................................................ [ 44%]
........................................................................ [ 58%]
........................................................................ [ 73%]
........................................................................ [ 88%]
.........................................................                [100%]
489 passed in 61.97s (0:01:01)

$ uv run ruff check src/ tests/
All checks passed!

$ uv run mypy src/
Success: no issues found in 48 source files

$ uv run paperforge --version
paperforge 1.4.0

$ uv run paperforge doctor --self-check
PaperForge Environment Diagnostics (v1.4.0)
Self-check completed.
```
