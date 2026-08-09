# Version decision: 1.7.0 → 1.8.0

## Decision: minor version bump (1.8.0), not a major bump

Per semantic versioning: a minor bump is correct because every change in
this release is additive and backward compatible.

## Why not 2.0.0

No existing, shipped behavior was removed or changed incompatibly:

- Every pre-existing CLI command and flag keeps its existing behavior,
  defaults, and output format. Nothing under `manifest`, `requirements`,
  `plan`, `generate`, `provenance`, `outputs`, `promote`, `rollback`,
  `doctor`, `build`, `preflight`, `references`, or any of the legacy
  `.paperforge/paper.yaml`-workflow commands changed shape or default
  behavior.
- `paperforge.planning.approval.evidence_hash`/`approve_plan`/
  `check_approval_validity` gained a new optional `project_root` keyword
  argument (default `None`). Called without it (as any pre-1.8.0 caller
  necessarily was, since the parameter didn't exist), behavior is
  byte-identical to 1.7.0 -- verified by
  `test_evidence_hash_without_project_root_is_backward_compatible` in
  `tests/test_plan_evidence_integration.py`.
- `ProvenanceRecord`'s on-disk JSON shape is unchanged; per-sentence
  staleness is a smarter *check* against the same recorded `text_hash`
  field that already existed in 1.7.0, not a schema change. A project with
  no `.paperforge/evidence/` directory (i.e. every project that predates
  this release) sees an empty evidence store, an empty stale set, and
  therefore identical `provenance validate` / `plan` output to 1.7.0.
- All new surface area -- the `evidence`, `approvals`, and `venue`
  (singular) command groups, the `EXIT_EVIDENCE_ERROR` exit code, the
  `paperforge.evidence`/`paperforge.review` packages, and
  `VenuePlugin.adapter_version`/`checked_date`/`source_url`/
  `source_description` (new properties with safe defaults on the existing
  `VenuePlugin` ABC, not new abstract members, so no third-party subclass
  is broken) -- is purely additive. A project that never runs
  `paperforge evidence`/`approvals`/`venue` is unaffected by any of it.
- `paperforge review` (AI-assisted advisory review) and `paperforge
  venues` (plural, list built-in targets) were deliberately left
  untouched; the new author-review and per-venue-metadata commands were
  given different names (`approvals`, `venue` singular) specifically to
  avoid a breaking rename or behavior change on those two existing
  commands.

## Why not just a patch (1.7.1)

This release adds substantial new, backward-compatible functionality (a
real direct/derived/statistical evidence architecture with a sandboxed
formula evaluator, a dependency graph, an author-review workflow, and
versioned venue metadata) -- minor is the correct SemVer category for
"new, compatible functionality," not patch.

## What did not ship (does not affect this decision, but is relevant to
## anyone deciding whether to adopt this release)

This pass was explicitly scoped down (see the completion report) from a
much larger 30-phase specification. Not shipped in 1.8.0: the structured
interactive intake wizard (`init --interactive`/`--resume`/etc.), the safe
existing-project import workflow (`init --import-existing`), `init --json`
and `build --json`/`build --staging` (true isolated staging-build
lifecycle), reference support-status verification
(`references support`) and the broader reference-pipeline hardening pass,
automatic statistical test execution, and the three separate clean-room
(human wheel / agent wheel / sdist) acceptance passes. None of these
absences changes any *existing* behavior (so it doesn't affect the SemVer
category), but the product is not yet "feature complete" against the
original 30-phase specification -- see
`audit_output/product_completion_pass2/` for the itemized gap list and
concrete next steps for each.
