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
 Target         Display Name                  Document Class         Page Limit
 ────────────   ───────────────────────────   ────────────────────   ──────────
 ieee           IEEE (Generic)                conference             8
 ieee-journal   IEEE Transactions / Journal   journal                14
 ieee-trans     IEEE Transactions (alias)     journal                14
 ieee-access    IEEE Access                   journal                None
 ieee-compsoc   IEEE Computer Society         journal,compsoc        14
 ieee-tdsc      IEEE TDSC                     journal,compsoc        14
 acm            ACM                           sigconf                12
 neurips        NeurIPS                       article                9
```

## Critical Note

`ieee-journal` and `ieee-trans` use standard non-compsoc mode (`\documentclass[journal]{IEEEtran}`).
Use `ieee-compsoc` or `ieee-tdsc` for CS Society journals (TDSC, TPDS, TC, TSE, TIFS).
Use `ieee-access` for IEEE Access submissions.

## Errors

| Condition | Message |
|-----------|---------|
| None — this command always succeeds | — |

## Notes

- Eight built-in targets: `ieee`, `ieee-journal`, `ieee-trans`, `ieee-access`, `ieee-compsoc`, `ieee-tdsc`, `acm`, `neurips`.
- Use the target name with `paperforge build --target <name>` or `paperforge doctor --target <name>`.
- Venue plugins control the LaTeX document class, preamble, author block format, required sections, and venue-specific doctor checks.
- To add a custom venue plugin, see [CONTRIBUTING.md](../../CONTRIBUTING.md).

For IEEE journal / transactions papers:
1. Set `paper_type: "journal"` in `.paperforge/paper.yaml`
2. Optionally set `keywords: [...]` in paper.yaml
3. Build with `--target ieee-journal`, `--target ieee-access`, or `--target ieee-compsoc`

The journal template generates the full IEEEtran journal
structure including `\IEEEtitleabstractindextext`,
`\IEEEraisesectionheading`, `\IEEEPARstart`, and
`\IEEEdisplaynontitleabstractindextext`.

**Related commands:** `paperforge build`, `paperforge doctor`
