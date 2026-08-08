# Version decision: 1.6.0 → 1.7.0

## Decision: minor version bump (1.7.0), not a major bump

Per semantic versioning: a minor bump is correct because every change in
this release is additive and backward compatible.

## Why not 2.0.0

No existing, shipped behavior was removed or changed incompatibly:

- Every pre-existing CLI command (`init`, `capture`, `doctor`, `build`,
  `review`, `improve`, `add-claim`, `add-figure`, `add-table`,
  `add-citation`, `generate-figures`, `install-hooks`, `export`, `status`,
  `find`, `log`, `diff`, `venues`, `update`, `sync`, `validate`, `clean`,
  `preflight`, `references`, `import`, `inspect`) keeps its existing
  flags, defaults, and output format. `references` gained a new optional
  `--json` flag; nothing about its default (no-flag) behavior changed.
- The pre-existing `.paperforge/paper.yaml` project format, claim/figure/
  table/citation YAML schemas, venue plugin interface, and Doctor check
  set are all unchanged.
- The new `paperforge.project.yaml` canonical manifest, and every command
  under it (`manifest`, `requirements`, `plan`, `generate`, `provenance`,
  `outputs`, `promote`, `rollback`), is entirely new surface area — a
  project that doesn't create `paperforge.project.yaml` is completely
  unaffected by this release.
- The one dependency floor raised (`pillow>=10.0.0` → `>=12.3.0`, a
  security fix — see [SECURITY_AUDIT.md](SECURITY_AUDIT.md)) does not
  change any PaperForge-facing behavior; `PIL.Image` is imported but never
  called anywhere in this codebase.
- One heuristic bugfix (`REQ-ETHICS-APPROVAL` no longer treats generic
  `study_type: "Experimental"` as implying human-subject involvement) only
  affects the brand-new `requirements` command's own output, which did
  not exist before this release.

## Why not just a patch (1.6.1)

This release adds substantial new, backward-compatible functionality
(the entire canonical-manifest/planning/generation/provenance/output-
lifecycle subsystem, ~12 new top-level commands), not merely bug fixes —
minor is the correct SemVer category for "new, compatible functionality".

## What did not ship (does not affect this decision, but is relevant to
## anyone deciding whether to adopt this release)

The full scope originally specified for this pass included an interactive
intake wizard, safe import of existing LaTeX/BibTeX projects into the
manifest, a real (non-template) AI provider, versioned venue adapters, and
a hardened/Crossref-integrated reference pipeline. None of these shipped.
Their absence does not change any *existing* behavior (so it doesn't
affect the SemVer category), but it does mean the canonical-manifest
workflow is less complete than "full product" implies — see the release's
completion report for the itemized gap list.
