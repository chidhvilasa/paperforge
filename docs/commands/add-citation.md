# paperforge add-citation

Interactively create or update citation metadata in `.paperforge/citations/{key}.yaml`.

## Usage

```
paperforge add-citation [KEY] [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `KEY` | BibTeX key (e.g. `smith2024`). Prompted if omitted. | Optional |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--help` | — | Show help and exit |

## Examples

```bash
# Interactively add a citation by key
paperforge add-citation smith2024

# Prompt for key interactively
paperforge add-citation
```

## Data Fields

`paperforge add-citation` prompts for the following fields:

- **Type**: `article` (default), `inproceedings`, `book`, `techreport`, `misc`, `phdthesis`, `mastersthesis`, `online`
- **Authors**: Semicolon-separated list of authors in `Last, First` format (e.g. `Smith, Alice; Jones, Bob`)
- **Title**: Title of the publication
- **Year**: Publication year (e.g. `2024`)
- **Venue**: Journal name, conference name, publisher, or institution depending on type
- **Volume**: Journal volume number
- **Issue**: Journal issue or number
- **Pages**: Page range (e.g. `123--135`)
- **DOI**: Digital Object Identifier without the `https://doi.org/` prefix
- **Notes**: Free-form notes

## Output File

Creates `.paperforge/citations/{key}.yaml`:

```yaml
key: smith2024
type: article
authors:
  - "Smith, Alice"
  - "Jones, Bob"
title: "A Sample Study of Example Systems"
year: 2024
venue: "IEEE Access"
volume: "12"
number: "4"
pages: "12345--12360"
doi: "10.1109/ACCESS.2024.123456"
url: ""
publisher: ""
institution: ""
notes: ""
```

## Notes

- Once a citation YAML file exists in `.paperforge/citations/`, `paperforge build` generates real BibTeX entries instead of TODO stubs.
- Citation YAML files are the single source of truth for bibliography data.
- `CITATION_NO_TITLE` is an ERROR severity check in `paperforge doctor` because reference entries without titles are invalid in IEEE LaTeX submissions.
- Commit `.paperforge/citations/*.yaml` to git alongside claims and experiments.

**Related commands:** `paperforge build`, `paperforge doctor`, `paperforge add-claim`, `paperforge export`
