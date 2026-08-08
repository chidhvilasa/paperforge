# Privacy

## What PaperForge sends over the network, by default

Nothing. `paperforge manifest`, `requirements`, `plan`, `generate`,
`provenance`, `outputs`, `promote`, `rollback`, `doctor`, `build`, and
`preflight` never make a network call.

Two commands are the only exceptions, and both are explicitly opt-in:

- `paperforge references --online` — verifies DOIs against the public
  Crossref API. Sends only the DOI/citation metadata already present in
  your `references.bib`, nothing else.
- `paperforge doctor` — some checks may query Crossref for DOI validation
  under the same conditions as `references --online`.

## Generation

`paperforge generate`'s default and only shipped provider (`no_ai`) is
local-only: it never leaves the process. See [AI_PROVIDERS.md](AI_PROVIDERS.md)
for the provider interface's `privacy_class`/`redaction_enabled` contract,
which any future external provider implementation would need to satisfy
before it could even be constructed.

## What PaperForge stores locally

Manifests, plans, provenance records, requirements reports, and build
outputs are written under `.paperforge/` and `paper_generated/` inside
your project directory. Nothing is written outside the project root
except when you explicitly point `--output`/`--manifest` elsewhere.

## Secrets

- `paperforge inspect` scans text files for patterns that look like
  private keys, AWS access keys, `sk-...`/`ghp_...` tokens, and hardcoded
  password literals, and flags them — it does not transmit or copy them
  anywhere.
- The intake-state persistence design (documented, not yet built — see
  "Remaining limitations" in the release notes) is specified to never
  store secrets; there is currently no intake state file to audit for
  this since the interactive intake wizard has not been implemented.
- `paperforge.utils.subprocess_runner.redact_command` masks
  token/key/secret/password/auth-looking argument values before they
  appear in any logged command string.

## What this document does not cover

This is a statement of current, actual behavior in this codebase, not a
compliance certification (GDPR, HIPAA, or otherwise). If your research
involves regulated personal data, apply your institution's data-handling
policy independently of anything PaperForge does or doesn't do.
