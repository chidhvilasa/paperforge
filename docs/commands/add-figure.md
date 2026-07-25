# paperforge add-figure

Interactively create a new figure YAML file.

## Usage

```bash
paperforge add-figure [OPTIONS]
```

## Description

The `add-figure` command provides an interactive wizard to create figure definitions. Figures in PaperForge are first-class objects with metadata, allowing the `doctor` command to verify completeness (e.g. ensuring captions exist and resolution is adequate) and the `impact` command to trace claims to specific figures.

The command auto-increments the figure ID (e.g. `fig_01`, `fig_02`) based on existing files in the `.paperforge/figures/` directory.

## Options

* `--path, -p <PATH>`
  Project root directory. Defaults to the current directory.

## Example

```bash
$ paperforge add-figure
Existing figures: none
Existing claims: 3
Fill in figure details below.
Caption: Authentication latency comparison across traffic scenarios.
Path: figures/fig_01.png
Format: png
Width inches: 3.5
DPI: 300
Section: results
Notes: 
```

## Output

Creates a YAML file in `.paperforge/figures/fig_NN.yaml` containing:

```yaml
id: fig_01
caption: Authentication latency comparison across traffic scenarios.
path: figures/fig_01.png
format: png
width_inches: 3.5
resolution_dpi: 300
first_mentioned_in: results
notes: ""
```

## Errors

* **Exit Code 1**: If run outside a PaperForge project directory (no `.paperforge/` found).

## Notes

- **Completeness**: After creating a figure, reference it in a claim using the `figures: [fig_NN]` array.
- **Doctor Checks**: The `doctor` command will check for missing captions, missing `first_mentioned_in` section, and adequate resolution (minimum 300 DPI for raster formats).
- **Widths**: Standard IEEE widths are 3.5 inches for a single column and 7.16 inches for a full page.
