# Venue Adapters

PaperForge ships a small set of built-in venue plugins (`ieee`,
`ieee-journal`, `ieee-trans`, `ieee-compsoc`, `ieee-tdsc`, `ieee-access`,
`acm`, `neurips`) implementing `paperforge.venues.base.VenuePlugin`: a
LaTeX documentclass line, required sections, a page limit, venue-specific
Doctor checks, and preamble/author-block generation.

## Two distinct things: rules vs. their currency

**Rules** are what the plugin actually does — required sections, page
limit, documentclass options, generated preamble packages. These are
tested code paths and are exercised by the existing venue test suite.

**Currency** is whether those rules were checked against a specific,
dated, official source recently enough to trust as "current." This is
what's new in 1.8.0.

```bash
paperforge venue show --target ieee
```

```json
{
  "id": "ieee",
  "adapter_version": "1.0",
  "checked_date": "",
  "source_url": "https://template-selector.ieee.org/",
  "source_description": "IEEEtran class conventions ... PaperForge heuristic defaults, not a per-call/CFP check against a specific journal's current requirements.",
  "source_verified": false
}
```

`source_verified` is `bool(checked_date)`. **Every built-in adapter
currently ships with an empty `checked_date`** — none of them were
re-verified against a live, dated official source as part of this pass.
`paperforge venue show`/`validate` surface this as an explicit
`VENUE_SOURCE_UNVERIFIED` warning rather than staying silent about it.
This is a deliberate, honest default: a page limit or section requirement
that hasn't been checked against a currently-published CFP/author-guide
should never be presented as verified-current.

If you (or an agent) do verify a venue's rules against its live author
guide, record that by setting `checked_date` on a custom venue file (see
below) — PaperForge itself does not auto-verify anything over the network
for venue rules, and never will silently claim it did.

## Custom venue configuration

For a venue with no built-in plugin, `paperforge venue show --custom-file
<path>` reads a local YAML file (never executed, never a Python object —
`yaml.safe_load` only) describing the same fields:

```yaml
venue_id: my_workshop_2026
display_name: "My Workshop 2026"
adapter_version: "1.0"
checked_date: "2026-08-01"          # set this only if you actually checked
source_url: "https://myworkshop.example.org/cfp"
compiler: pdflatex
max_pages: 6
abstract_requirements: "150-200 words, no citations"
keyword_requirements: "3-5 keywords"
anonymous_review_rules: "double-blind; no author names in PDF metadata"
declaration_requirements:
  - "conflicts of interest"
  - "data availability"
```

The file path is resolved through the same traversal guard used for
manifest-referenced paths
(`paperforge.project_manifest.path_safety.check_project_path`): `..`
segments, external absolute paths, drive-letter/UNC paths, and
symlink escapes out of the project root are all rejected before the file
is read. `paperforge venue validate --custom-file <path>` additionally
requires a non-empty `venue_id` and warns (does not error) on a missing
`checked_date`.

A custom venue is currently **read-only metadata** — `paperforge venue
show|validate` display and validate it, but `paperforge build --target`
does not yet accept a custom venue id (only the built-in plugin names).

## Fallback

There is no implicit "generic" venue plugin selected automatically; `build
--target` requires one of the built-in names (`paperforge venues` lists
them) or, in future, a registered custom venue id. A project targeting an
unlisted venue should pick the closest built-in adapter (typically `ieee`
or `acm`) and treat its section/page-limit checks as a starting heuristic,
adjusted by hand against the actual CFP.

## What this does not do

- No network fetch of a venue's live requirements happens anywhere in
  PaperForge. `checked_date`/`source_url` are metadata fields an author or
  agent fills in after manually verifying — not something PaperForge
  populates automatically.
- Custom venues are not yet wired into `build`/`doctor --target`.
- There is no per-year template-version tracking (e.g. "neurips_2024" vs.
  a future "neurips_2027" style package) beyond the free-text
  `source_description` note on the `neurips` plugin.
