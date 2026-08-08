# Troubleshooting

## `paperforge generate` refuses with `GENERATION_PLAN_NOT_APPROVED`

You ran `paperforge generate` in its default (validated) mode without an
approved plan. Either run:

```bash
paperforge plan --approve --mode submission --non-interactive
```

first, or use a mode that doesn't require approval:

```bash
paperforge generate --outline-only
paperforge generate --draft-with-placeholders
```

## `paperforge generate` refuses with `GENERATION_PLAN_APPROVAL_STALE`

Something changed since you last approved the plan — the manifest, its
evidence, its claims, the venue, or the plan's own structure. Re-run:

```bash
paperforge plan --approve --mode submission
```

The `--json` output's `outputs.approval_stale_reasons` (or the console
output) tells you exactly what changed.

## `paperforge manifest validate` reports `YAML_*` errors

These are safe-YAML boundary rejections (see
[SECURITY_MODEL.md](SECURITY_MODEL.md)), not ordinary YAML syntax errors —
they mean the document was parseable but violated a safety rule (oversized,
too deeply nested, a duplicate key, a recursive alias, etc). The error
message states which rule and why; fix the manifest accordingly. This is
not a bug report situation unless the *safety rule itself* is wrong for
your legitimate use case (e.g. a manifest that legitimately needs to
exceed the default 2 MB size limit) — in that case, the size/depth/
collection/scalar limits are keyword arguments to
`paperforge.project_manifest.loader.load_manifest_text`/`load_manifest_file`,
not currently exposed as CLI flags (a known gap).

## `paperforge manifest validate` reports `MANIFEST_MIGRATION_REQUIRED`

Run `paperforge manifest migrate --input <path>` first (see
[MIGRATION.md](MIGRATION.md)), then re-validate.

## `paperforge rollback` reports "Nothing to roll back to"

There is no non-empty `paper_generated/previous/` directory yet — this is
expected after a project's very first build (there's nothing to have
rotated into `previous` yet). Build again to populate `previous`, or
this message is correct and there's nothing to fix.

## A build seems to hang

As of this pass, every `latexmk`/`pdflatex`/`bibtex` invocation inside
`paperforge build` has a 300-second timeout with full process-tree
cleanup (see [`src/paperforge/utils/subprocess_runner.py`](../src/paperforge/utils/subprocess_runner.py)).
If a build still appears stuck for longer than that, it is not this
timeout mechanism working as intended — check for a MiKTeX "check for
updates"/package-installation prompt blocking the *first* pass before the
timeout would even fire (a real, previously observed environmental issue
with some MiKTeX installations), and consider disabling MiKTeX's
auto-update prompt in your TeX distribution's settings.

## `paperforge doctor`/`preflight` findings conflict with `paperforge requirements`

They check different things and are intentionally independent (see
[REQUIREMENTS_ENGINE.md](REQUIREMENTS_ENGINE.md#relationship-to-doctor)).
`doctor`/`preflight` check the `.paperforge/paper.yaml` + `build` LaTeX
pipeline's content; `requirements` checks the separate, optional
`paperforge.project.yaml` canonical manifest. A project using only one of
the two workflows will only see meaningful output from the corresponding
tool.

## Where do I report a bug or security issue?

Functional bugs: open a GitHub issue. Security issues: see
[SECURITY.md](../SECURITY.md) — do not open a public issue for those.
