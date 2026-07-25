# paperforge venues

List all available venue targets that can be used with the `--target` option of `build` and `doctor`.

## Usage

```
paperforge venues
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| None | — | — |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--help` | — | Show help and exit |

## Example

```bash
# List all venue targets
paperforge venues
```

## Output

Prints a table of available venue targets:

```
             Available Venue Targets
 Target   Display Name   Document Class   Page Limit
 ──────   ────────────   ──────────────   ──────────
 ieee     IEEE           IEEEtran...      None
 acm      ACM sigconf    acmart...        None
 neurips  NeurIPS        neurips_2024...  None
```

## Errors

| Condition | Message |
|-----------|---------|
| None — this command always succeeds | — |

## Notes

- Three built-in targets: `ieee`, `acm`, `neurips`.
- Use the target name with `paperforge build --target <name>` or `paperforge doctor --target <name>`.
- Venue plugins control the LaTeX document class, preamble, author block format, required sections, and venue-specific doctor checks.
- To add a custom venue plugin, see [CONTRIBUTING.md](../../CONTRIBUTING.md).

**Related commands:** `paperforge build`, `paperforge doctor`
