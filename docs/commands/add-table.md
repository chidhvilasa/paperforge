# paperforge add-table

Interactively create a new table YAML file.

## Usage

```bash
paperforge add-table [OPTIONS]
```

## Description

The `add-table` command provides an interactive wizard to create table definitions. Tables in PaperForge are first-class objects with structured metadata, columns, and rows, allowing the `doctor` command to verify completeness and `build` to generate clean LaTeX tables automatically.

The command auto-increments the table ID (e.g. `tbl_01`, `tbl_02`) based on existing files in the `.paperforge/tables/` directory.

## Options

* `--path, -p <PATH>`
  Project root directory. Defaults to the current directory.

## Example

```bash
$ paperforge add-table
Existing tables: none
Existing experiments: exp_01
Fill in table details below.
Caption: Authentication Latency Comparison
Experiment: exp_01
Columns: Scenario,B2 (ms),Adaptive (ms),Reduction
Row (or 'done'): Low (20v),71.9,19.4,73.0%
Row (or 'done'): High (500v),89.3,22.1,75.3%
Row (or 'done'): done
Section: results
Notes: 
```

## Output

Creates a YAML file in `.paperforge/tables/tbl_NN.yaml` containing:

```yaml
id: tbl_01
caption: Authentication Latency Comparison
columns:
  - Scenario
  - B2 (ms)
  - Adaptive (ms)
  - Reduction
rows:
  - - Low (20v)
    - "71.9"
    - "19.4"
    - 73.0%
  - - High (500v)
    - "89.3"
    - "22.1"
    - 75.3%
notes: ""
first_mentioned_in: results
source_experiment: exp_01
```

## Errors

* **Exit Code 1**: If run outside a PaperForge project directory (no `.paperforge/` found).

## Notes

- **Directory**: Creates `.paperforge/tables/tbl_NN.yaml`.
- **Auto-Increment**: Table IDs are auto-incremented: `tbl_01`, `tbl_02`, ...
- **IEEE Captions**: IEEE CRITICAL: Table captions appear ABOVE the table (opposite of figures). Missing caption is an ERROR in `doctor`.
- **LaTeX Generation**: Columns and rows are stored as YAML lists; `build` generates LaTeX tabular environment automatically.
- **ERROR Severity**: `TABLE_NO_CAPTION` is an ERROR (not a warning) because an uncaptioned table cannot appear in IEEE submissions.
- **Traceability**: `source_experiment` links the table to its generating experiment for traceability.
- **IEEE Style Rules**: Generated tables enforce IEEE style rules: no vertical lines, `\arraystretch` 1.3, and `\hline` only at the top, after the column headers, and at the bottom.
