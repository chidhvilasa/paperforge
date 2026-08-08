# Repository cleanup audit

Performed as part of the v1.7.0 product-completion pass. Records what was
inspected, what was removed, and what was deliberately kept.

## Inspected

`audit_output/`, `backups/`, `dist/`, `build/`, virtual environments,
caches, coverage artifacts, temporary clean-install projects, stale
fixtures, duplicate tests, dead code, obsolete modules, unused templates,
stale docs, hardcoded absolute paths, secrets, version drift, dependency
drift, generated schemas, large Git objects.

## Findings and actions

| Finding | Action |
|---|---|
| `release_notes.txt`, `tag_msg.txt` at repo root — one-time scratch text for the v0.4.0 release (dated Jul 25), stale for 15+ subsequent versions, referenced nowhere in code/docs/config (grep-verified) | **Removed** (`git rm`) |
| Stale local `dist/*.whl`/`*.tar.gz` (versions 1.4.0 through 1.5.3) | **Removed** (untracked, regenerable local build artifacts; a fresh build is produced as part of this pass's own quality gates) |
| `pyproject.toml` declared `pillow>=10.0.0`, and the installed 10.4.0 had 24 known advisories (see [SECURITY_AUDIT.md](SECURITY_AUDIT.md)) | **Fixed**: bumped to `pillow>=12.3.0`, upgraded the installed package, re-audited clean |
| In-repo `backups/` directory (from earlier, pre-this-pass sessions, containing pre-v1.5.1 through pre-v1.5.3 snapshots) | **Kept** (backups are never deleted per this pass's explicit constraints) but confirmed **not tracked** by git (`git check-ignore` confirms `/backups/` in `.gitignore` already covers it — nothing inside it was ever at risk of being committed). Noted here as a candidate to relocate outside the repository in a future pass, matching this pass's own convention of writing backups to `../backups/` (one level above the repo). |
| `docs/PHASE_36_BASELINE_AUDIT.md` — a dated (2026-07-30), clearly historical point-in-time audit referencing the then-current v1.4.0 baseline | **Kept** — legitimate historical record, clearly dated and scoped, not presented as current documentation, causes no confusion; deleting project history for its own sake is not a goal of this audit |
| Repo-wide grep for hardcoded personal absolute paths (`C:\Users\<name>`, `/home/<name>`) or the operator's personal email in tracked files | **Clean** — no matches outside this document's own description of the finding process |
| `uv.lock` vs `pyproject.toml` dependency consistency | **Verified clean** (`uv lock --check`: no drift) after the Pillow bump |
| Large Git objects | **Not a concern** — `git count-objects -vH` at Milestone 0 baseline showed 1030 objects, 3.87 MiB, no packs, no garbage; this pass added source/doc files only, no binaries |
| `audit_output/` | Untracked, `.gitignore`'d, contains only this pass's own local report (`BASELINE_AUDIT.md`) and the final completion marker — never committed, per repository policy on local audit data |
| Duplicate tests / dead code from this pass's own additions | None found — every new module has a corresponding, non-overlapping test file; no function was written and left uncalled (all new public functions are exercised by at least one test or one CLI command) |

## `.gitignore` updates made this pass

```
audit_output/
/backups/
examples/*/.paperforge/
examples/*/paper_generated/
```

(The Coverage section (`.coverage`, `htmlcov/`) pre-existed this pass.)

## Not done in this pass

A full dead-code analysis (e.g. with `vulture` or coverage-based
unreachable-code detection) across the pre-existing ~60 source files from
before this pass was not performed — this audit focused on artifacts
newly discovered or newly introduced during this pass, not a from-scratch
audit of the entire pre-existing codebase.
