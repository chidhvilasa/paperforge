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
| `--target`, `-t` | `ieee` | Venue target: `ieee`, `acm`, `neurips` |
| `--help` | — | Show help and exit |

## Example

```bash
# Build for IEEE (default)
paperforge build

# Build for NeurIPS
paperforge build --target neurips

# Build for ACM
paperforge build --target acm

# Build from a specific project root
paperforge build --path ~/papers/vanet-paper --target ieee
```

## Output

On success, prints a green "Build Complete" panel with the output directory,
file checklist, and summary counts:

```
╭─ Build Complete ──────────────────────────────────╮
│ Output: .paperforge/output/                       │
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
- `--target` selects the venue plugin: `ieee` (default), `acm`, `neurips`. Each sets the correct LaTeX document class, preamble, and author block.
- Attempts `pdflatex` compilation if `pdflatex` is on the system PATH.
- Output goes to `.paperforge/output/` by default.
- Use `paperforge venues` to see all available targets.

**Related commands:** `paperforge doctor`, `paperforge venues`, `paperforge review`
