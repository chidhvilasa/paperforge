# paperforge install-hooks

Install a git pre-commit hook that runs `paperforge doctor` before every commit, blocking commits on ERROR-severity issues.

## Usage

```
paperforge install-hooks [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| None | — | — |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory (used to find the git repository) |
| `--uninstall` | `False` | Remove the PaperForge pre-commit hook |
| `--help` | — | Show help and exit |

## Example

```bash
# Install the pre-commit hook
paperforge install-hooks

# Uninstall the hook
paperforge install-hooks --uninstall

# Install in a project in another directory
paperforge install-hooks --path ~/papers/my-paper
```

## Output

On successful install, prints a green "Git Hook Installed" panel:
```
╭─ Git Hook Installed ──────────────────────────────╮
│ Hook: /path/to/repo/.git/hooks/pre-commit         │
│                                                    │
│ PaperForge will now run `paperforge doctor` before │
│ every commit.                                     │
│ Commits are blocked if any ERRORs exist.          │
│ Warnings do not block commits.                    │
│                                                    │
│ To uninstall:                                     │
│       paperforge install-hooks --uninstall        │
│                                                    │
│ To test the hook:                                 │
│       git commit --allow-empty -m "test"          │
╰────────────────────────────────────────────────────╯
```

If the PaperForge hook is already installed, running install again is a no-op:
`PaperForge hook already installed.`

On successful uninstall: `PaperForge git hook uninstalled.`
If there was no PaperForge hook to remove: `No PaperForge hook found to uninstall.`
(both exit 0)

## Errors

| Condition | Message |
|-----------|---------|
| No `.git/` directory found (walking up from `--path`) | `No git repository found. Initialize git first: git init` (exit 1) |
| A non-PaperForge hook already exists | Panel: `A pre-commit hook already exists and was not created by PaperForge.` + the existing hook path + instructions to manually add `paperforge doctor` to it (exit 1) |

## Notes

- Walks **up** the directory tree from `--path` to find the nearest `.git/` directory.
- **Idempotent:** Installing when the PaperForge hook is already present is a no-op (prints a message, does not overwrite, exits 0).
- **Does not overwrite** non-PaperForge hooks. Detection is a simple substring check for the word `paperforge` in the existing hook file; if not found, the command exits 1 and tells you how to add PaperForge alongside the existing hook manually.
- `--uninstall` only removes the hook file if it contains the string `paperforge` — otherwise it reports nothing to uninstall.
- The installed hook script is made executable (`chmod 0o755`).
- The hook shells out to `paperforge doctor` (found on PATH or under `.venv/`) and blocks the commit only if doctor exits non-zero (i.e. an ERROR was found); WARNINGs do not block. If `paperforge` can't be found at all, the hook prints a notice and lets the commit through.

**Related commands:** `paperforge doctor`
