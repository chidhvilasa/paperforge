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
 ieee-journal   IEEE Transactions / Journal   10pt,journal,compsoc   14
 ieee-trans     IEEE Transactions (alias)     10pt,journal,compsoc   14
 acm            ACM                           sigconf                12
 neurips        NeurIPS                       article                9
```

## Errors

| Condition | Message |
|-----------|---------|
| None — this command always succeeds | — |

## Notes

- Five built-in targets: `ieee`, `ieee-journal`, `ieee-trans`, `acm`, `neurips`.
- Use the target name with `paperforge build --target <name>` or `paperforge doctor --target <name>`.
- Venue plugins control the LaTeX document class, preamble, author block format, required sections, and venue-specific doctor checks.
- To add a custom venue plugin, see [CONTRIBUTING.md](../../CONTRIBUTING.md).

For IEEE journal / transactions papers:
1. Set `paper_type: "journal"` in `.paperforge/paper.yaml`
2. Optionally set `keywords: [...]` in paper.yaml
3. Build with `--target ieee-journal` or `--target ieee-trans`

The journal template generates the full IEEEtran journal
structure including `\IEEEtitleabstractindextext`,
`\IEEEraisesectionheading`, `\IEEEPARstart`, and
`\IEEEdisplaynontitleabstractindextext`.

**Related commands:** `paperforge build`, `paperforge doctor`
