# paperforge doctor

Run all deterministic consistency checks on a PaperForge research project and report errors, warnings, and info.

## Usage

```
paperforge doctor [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| None | — | — |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--fix` | `False` | Auto-resolve fixable warnings (sets unverified claims to stale) |
| `--target`, `-t` | `None` | Venue target for additional checks: `ieee`, `acm`, `neurips` |
| `--self-check` | `False` | Check PaperForge installation health |
| `--help` | — | Show help and exit |

## Example

```bash
# Run all checks
paperforge doctor

# Auto-fix fixable warnings
paperforge doctor --fix

# Run with IEEE-specific checks
paperforge doctor --target ieee

# Check a project in a different directory
paperforge doctor --path ~/papers/my-paper
```

## Output

Prints a panel with all issues. On a clean project:
```
╭─ Doctor ──────────────────────────────────────────╮
│ ✓ All checks passed.                              │
╰───────────────────────────────────────────────────╯
```

On a project with issues, each issue is printed with its code and severity:
```
[ERROR]   ORPHAN_CLAIM          claim_03 has no linked experiment
[WARNING] UNVERIFIED_CLAIM      claim_01 status is unverified
```

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| Any ERROR-severity issue found | Exit code 1 |

## Notes

### All 43 checks

| # | Code | Severity | Description |
|---|------|----------|-------------|
| 1 | `ORPHAN_CLAIM` | ERROR | Claim has no linked experiment |
| 2 | `MISSING_EXPERIMENT` | ERROR | Claim references an experiment that does not exist |
| 3 | `STALE_CLAIM` | ERROR | Claim status is stale |
| 4 | `EMPTY_CLAIM_TEXT` | ERROR | Claim text field is empty |
| 5 | `UNVERIFIED_CLAIM` | WARNING | Claim status is unverified |
| 6 | `EMPTY_EXPERIMENT_METRICS` | WARNING | Experiment has no captured metrics |
| 7 | `NO_CLAIMS` | WARNING | Project has no claims at all |
| 8 | `NO_EXPERIMENTS` | WARNING | Project has no experiments at all |
| 9 | `MISSING_PAPER_TITLE` | WARNING | paper.yaml title field is empty |
| 10 | `MISSING_AUTHORS` | WARNING | paper.yaml authors list is empty |
| 11 | `METRIC_CLAIM_MISMATCH` | ERROR | A percentage in claim text does not match any experiment metric |
| 12 | `DUPLICATE_CLAIM_TEXT` | WARNING | Two or more claims have identical text |
| 13 | `CLAIM_IN_NO_SECTION` | WARNING | Claim lists no sections |
| 14 | `EXPERIMENT_NO_DESCRIPTION` | WARNING | Experiment description is empty |
| 15 | `EXPERIMENT_NO_HARDWARE` | WARNING | Experiment has no hardware field |
| 16 | `EXPERIMENT_NO_DATASET` | WARNING | Experiment has no dataset field |
| 17 | `EXPERIMENT_NO_SEED` | WARNING | Experiment has no seed field |
| 18 | `UNCLAIMED_EXPERIMENT` | WARNING | Experiment has no claims linked to it |
| 19 | `INVALID_FIGURE_ID` | WARNING | Figure ID does not start with `fig_` |
| 20 | `INVALID_TABLE_ID` | WARNING | Table ID does not start with `tbl_` |
| 21 | `UNDEFINED_ACRONYM` | WARNING | An acronym is used without definition |
| 22 | `ABSTRACT_TOO_LONG` | WARNING | Abstract exceeds 250 words |
| 23 | `ABSTRACT_TOO_SHORT` | WARNING | Abstract is under 50 words |
| 24 | `NO_INTRODUCTION_CLAIMS` | WARNING | No claims are mapped to the introduction section |
| 25 | `NO_CONCLUSION_CLAIMS` | WARNING | No claims are mapped to the conclusion section |
| 26 | `EXPERIMENT_NO_RESULTS_FILE` | WARNING | Experiment has no results file attached |
| 27 | `CLAIM_EXCESSIVE_LENGTH` | WARNING | Claim text exceeds 80 words |
| 28 | `EXPERIMENT_OVERCROWDED` | WARNING | Experiment is linked to 5 or more claims |
| 29 | `RESULTS_SECTION_EMPTY` | ERROR | Results section contains no claims |
| 30 | `EVIDENCE_COVERAGE` | INFO | Informational score of claim evidence coverage |
| 31 | `FIGURE_NO_CAPTION` | WARNING | Figure has no caption |
| 32 | `FIGURE_NO_FIRST_MENTION` | WARNING | Figure has no first_mentioned_in section |
| 33 | `FIGURE_REFERENCED_BUT_NO_YAML` | WARNING | Claim references figure ID with no YAML |
| 34 | `FIGURE_YAML_BUT_NO_CLAIM` | WARNING | Figure YAML exists but is not referenced in any claim |
| 35 | `LOW_RESOLUTION_FIGURE` | WARNING | Raster figure has resolution under 300 DPI |
| 36 | `MISSING_AFFILIATION` | WARNING | Authors are defined but affiliations are missing |
| 37 | `TABLE_NO_CAPTION` | ERROR | Table has no caption (placed ABOVE table in IEEE) |
| 38 | `TABLE_NO_COLUMNS` | WARNING | Table has no column headers defined |
| 39 | `TABLE_REFERENCED_BUT_NO_YAML` | WARNING | Claim references table ID with no YAML |
| 40 | `TABLE_YAML_BUT_NO_CLAIM` | WARNING | Table YAML exists but is not referenced in any claim |
| 41 | `TABLE_ROW_COLUMN_MISMATCH` | WARNING | Table row cell count does not match column count |
| 42 | `MISSING_ACKNOWLEDGMENT` | WARNING | paper.yaml acknowledgment field is empty |
| 43 | `WIDE_TABLE_RECOMMENDED` | WARNING | Table has 6+ columns without wide: true |
| 44 | `CITED_KEY_NO_YAML` | WARNING | Citation key used in claims but has no YAML file |
| 45 | `CITATION_YAML_NO_CLAIM` | WARNING | Citation YAML file exists but is not referenced in any claim |
| 46 | `CITATION_NO_TITLE` | ERROR | Citation has no title field defined |
| 47 | `CITATION_NO_YEAR` | WARNING | Citation has no year field defined |
| 48 | `CITATION_NO_AUTHORS` | WARNING | Citation has no authors list defined |
| 49 | `MULTI_EXPERIMENT_CLAIM` | INFO | Claim links to additional experiments beyond primary |
| 75 | `MATH_CLAIM_MISSING_FLAG` | WARNING | Claim text contains LaTeX math commands but is_math: false |
| 76 | `PROOF_WITHOUT_THEOREM` | WARNING | Proof claim has no preceding theorem/lemma |
| 81 | `AUTHOR_IDENTITY_INCONSISTENT` | ERROR | Author family name inconsistent across biography, metadata, or title |
| 81 | `AUTHOR_NAME_INCOMPLETE` | ERROR | Author entry missing given_name, family_name, or display_name |
| 82 | `MISSING_PDF_METADATA` | WARNING | paper.yaml missing title, keywords, or author email for PDF metadata |
| 83 | `LATEX_ARTIFACT_IN_CLAIM` | ERROR | Claim text contains unresolved markdown/LaTeX artifacts |
| 84 | `REQUIRED_PLACEHOLDER_IN_CLAIM` | ERROR | Claim text contains required-information missing placeholder |
| 85 | `CLAIM_CONSTRAINT_VIOLATED` | ERROR | Claim permitted_only_if condition violated by experiment metrics |
| 86 | `PVALUE_AMBIGUOUS` | WARNING | Single p-value reported for multiple metrics in claim text |
| 87 | `SIGNIFICANCE_LANGUAGE_MISMATCH` | WARNING | Non-significant language combined with positive claim framing |
| 88 | `CITATION_HAS_INTERNAL_NOTE` | ERROR | Citation notes contain internal research commentary |
| 89 | `NUMERIC_VALUE_UNSOURCED` | WARNING | Claim contains numeric value not traceable to experiments or citations |
| 90 | `BUILD_PDF_INCOMPLETE` | WARNING | PDF compilation log contains warnings, missing files, or draft fallback |

## Self-Check

`paperforge doctor --self-check` validates your installation
without requiring a PaperForge project. Checks:
- PaperForge version vs PyPI latest
- Required Python packages (python-docx, matplotlib, etc.)
- LaTeX toolchain (pdflatex, latexmk)
- AI review tool (llm)
- Configured paths exist
- PyPI name collision warning (paperforge vs paperforge-research)

These checks are always run by `collect_issues()`, independent of `--target`.

### Severity Breakdown (90 Checks Total)
- **14 ERRORs**: `ORPHAN_CLAIM`, `MISSING_EXPERIMENT`, `STALE_CLAIM`, `EMPTY_CLAIM_TEXT`, `METRIC_CLAIM_MISMATCH`, `RESULTS_SECTION_EMPTY`, `TABLE_NO_CAPTION`, `CITATION_NO_TITLE`, `AUTHOR_IDENTITY_INCONSISTENT`, `AUTHOR_NAME_INCOMPLETE`, `LATEX_ARTIFACT_IN_CLAIM`, `REQUIRED_PLACEHOLDER_IN_CLAIM`, `CLAIM_CONSTRAINT_VIOLATED`, `CITATION_HAS_INTERNAL_NOTE` (blocks build and git hook).
- **74 WARNINGs**: advisory issues that report potential problems but do not block draft builds.
- **2 INFOs**: `EVIDENCE_COVERAGE` score, `MULTI_EXPERIMENT_CLAIM` notice, informational only.

### Build Modes (--mode)
- **Draft mode (`--mode draft`, default)**: blocks only on critical P0 structural errors.
- **Submission mode (`--mode submission`)**: strict mode, blocks on extended set including metric mismatches, abstract/intro overlap, author identity inconsistencies, claim constraint violations, and internal citation notes.

Note on `TABLE_NO_CAPTION` vs `FIGURE_NO_CAPTION`: `TABLE_NO_CAPTION` is an **ERROR** (unlike `FIGURE_NO_CAPTION` which is a WARNING) because a table without a caption cannot appear in any IEEE submission, whereas figures may occasionally be used inline or in draft contexts without captions.

- `--fix` only auto-resolves `UNVERIFIED_CLAIM` by setting those claims to `stale`.
- `--target` runs the venue plugin's own `validate()` on top of these 90 checks and
  prints the results under a separate `VENUE (<display name>)` heading. Venue checks
  include things like `UNCITED_CLAIM` (IEEE), `MISSING_SEED`/`MISSING_DATASET` (NeurIPS),
  and `MISSING_RELATED_WORK` (ACM) — see `paperforge venues` and each plugin's source
  for the full list.

**Related commands:** `paperforge build`, `paperforge status`, `paperforge add-claim`, `paperforge add-table`
