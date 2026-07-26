# paperforge build

Compile structured research data from `.paperforge/` into a LaTeX paper for a specified venue target.

## Usage

```
paperforge build [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| None | — | — |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--target`, `-t` | `ieee` | Venue target: `ieee`, `ieee-journal`, `ieee-trans`, `ieee-access`, `acm`, `neurips` |
| `--no-reveal` | `false` | Do not open output folder after successful PDF build |
| `--help` | — | Show help and exit |

## Example

```bash
# Conference paper (default)
paperforge build

# IEEE Transactions journal paper
paperforge build --target ieee-journal

# ACM conference
paperforge build --target acm

# With custom output path
# After custom output path or target selection
paperforge build --target ieee-journal --path /path/to/project

# Suppress automatic folder opening
paperforge build --no-reveal
```

## Output

On success, prints a green "Build Complete" panel with the output directory,
file checklist, and summary counts:

```
╭─ Build Complete ──────────────────────────────────╮
│ Output: paper/                                    │
│                                                    │
│ Files:                                             │
│   paper.tex          ✓                             │
│   paper.pdf          pdflatex not found — install TeX Live │
│                                                    │
│ Claims compiled:    3                              │
│ Sections:           8                              │
│ Citations:          2                              │
╰────────────────────────────────────────────────────╯
```

If `pdflatex` is on PATH, it is run twice against `paper.tex` and the `paper.pdf`
line shows a checkmark on success or a compilation-failed note (with the `.tex`
file still delivered) on failure. Any venue-plugin WARNINGs are printed after the
panel under a `VENUE (<display name>)` heading.

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| Doctor ERRORs or venue-plugin ERRORs found | `Build blocked. Fix all ERRORs before building.` — lists each issue, exits 1 before generating any output |
| Unknown `--target` | `Unknown venue '<target>'. Available: acm, ieee, neurips` (exit 1) |

## Notes

- **Runs doctor checks first.** Any ERROR-severity issue blocks the build. Fix issues with `paperforge doctor` before building.
- WARNINGs do not block the build.
- `--target` selects the venue plugin: `ieee` (default), `acm`, `neurips`, etc. Each sets the correct LaTeX document class, preamble, and author block.
- `paper_type` in `paper.yaml` controls template selection ("conference" default, "journal" for transactions).
- `keywords` field in `paper.yaml` used in `\IEEEkeywords` block.
- `references.bib` generated in output directory when citations exist.
- `latexmk` is used when available, `pdflatex` as fallback.
- Figure environments with `\label` and `\ref` generated automatically.
- Tables with YAML data generate full `\begin{table}` environments with IEEE-compliant formatting (caption above tabular).
- `TABLE_NO_CAPTION` is an ERROR that blocks build.
- Table row/column data is embedded directly in the LaTeX output.
- `affiliations` in `paper.yaml` improve author block for journals.
- `hyperref` and `microtype` now included in all IEEE preambles.
- `wide: true` on Figure or Table YAMLs generates `figure*` / `table*` environments for two-column spanning in IEEE layout.
- Output goes to `paper/` at project root by default (configured in `paper.yaml`).
- Creates `paper/.gitignore` automatically to exclude auxiliary build files.
- Automatically opens/selects the generated PDF in OS file explorer via `_reveal_output` behavior unless `--no-reveal` is passed.
- Use `paperforge venues` to see all available targets.

**Related commands:** `paperforge doctor`, `paperforge venues`, `paperforge review`, `paperforge add-table`
