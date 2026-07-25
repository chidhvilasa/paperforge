# paperforge init

Initialize PaperForge in a research project directory by creating the `.paperforge/` structure.

## Usage

```
paperforge init [PATH]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `PATH` | Directory to initialize. Defaults to current directory (`.`) | No |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--help` | — | Show help and exit |

## Example

```bash
# Initialize in the current directory
cd my-research-project
paperforge init

# Initialize in a specific directory
paperforge init ~/papers/vanet-paper
```

## Output

On success, prints a green "PaperForge Initialized" panel listing the created
tree and next steps:

```
╭─ PaperForge Initialized ──────────────────────────╮
│ .paperforge/                                      │
│ ├── paper.yaml          ← project metadata        │
│ ├── claims/                                       │
│ │   └── claim_01.yaml   ← your first claim         │
│ ├── experiments/                                  │
│ │   └── exp_01.yaml     ← your first experiment    │
│ └── .gitignore                                    │
│                                                    │
│ Next steps:                                       │
│   1. Edit .paperforge/paper.yaml — title, authors │
│   2. Fill in exp_01.yaml with your results         │
│   3. Fill in claim_01.yaml — link to experiment    │
│   4. Run paperforge doctor to check consistency    │
╰───────────────────────────────────────────────────╯
```

## Errors

| Condition | Message |
|-----------|---------|
| `.paperforge/` already exists | `PaperForge already initialized in this directory.` (exit 1) |

## Notes

- Creates blank template files `claim_01.yaml` and `exp_01.yaml` to guide initial data entry.
- Does **not** overwrite an existing `.paperforge/` directory.
- The `.paperforge/` directory should be committed to version control.
- `paper.yaml` contains project metadata: title, authors, venue, status, sections.
- The created `.paperforge/.gitignore` excludes `review/` (AI output) from git.

**Related commands:** `paperforge capture`, `paperforge doctor`
