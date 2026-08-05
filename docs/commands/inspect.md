# paperforge inspect

Read-only reconnaissance of a directory before running `paperforge init`
or importing existing material. Detects what already exists so a human
or an agent can decide how to proceed, without PaperForge inventing or
overwriting anything.

## Usage

```
paperforge inspect [PATH] [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `path` | Directory to inspect. Defaults to current directory. | No |

## Options

| Option | Default | Description |
|--------|---------|--------------|
| `--json` | off | Emit machine-readable JSON instead of a console panel |
| `--help` | — | Show help and exit |

## What it detects

- Existing manuscript files (`.tex`, `.docx`)
- Markdown files
- Bibliography files (`.bib`)
- Figures (`.png`, `.jpg`, `.jpeg`, `.pdf`, `.eps`, `.svg`, `.tiff`)
- Tables (`.csv`, `.tsv`)
- Notebooks (`.ipynb`)
- Other data files (`.json`, `.parquet`, `.xlsx`, `.h5`, `.npz`, `.npy`)
- Venue template files (`.cls`, `.sty`, `.bst`)
- Package managers (`pyproject.toml`, `requirements.txt`, `package.json`, etc.)
- Git repository state (present, branch, dirty/clean)
- An existing PaperForge project (`.paperforge/paper.yaml`)
- Candidate output directories (`paper_generated/`, `output/`, etc.)
- Likely secrets (high-confidence patterns only: private key blocks, AWS
  key IDs, `sk-...`-shaped tokens, GitHub tokens, hardcoded password
  literals)
- Absolute local filesystem paths embedded in text files

`inspect` never executes, imports, parses-and-runs, or modifies anything
it finds — it only reports.

## Example

```bash
# Inspect the current directory before deciding how to start
paperforge inspect

# Inspect another directory and get JSON for an agent workflow
paperforge inspect ~/papers/my-paper --json
```

## Agent usage

Agents should run `paperforge inspect --json` as the very first step
before any intake or generation decision, so they act on what actually
exists in the project rather than assuming an empty directory.
