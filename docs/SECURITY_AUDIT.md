# Security audit log

This is a log of the security review performed as part of the v1.7.0
product-completion pass, not a certification. It records exactly what was
checked, what was found, and what was explicitly out of scope — see
[SECURITY_MODEL.md](SECURITY_MODEL.md) for the resulting design summary.

## Scope of this pass

A targeted spot-check (not an exhaustive, professional security audit)
covering: YAML parsing safety, path-field traversal, subprocess
invocation safety, archive handling, formula/eval injection, template
injection, provider privacy, and direct-dependency known vulnerabilities.

## Method

- Repo-wide `grep` for `eval(`, `exec(`, `yaml.load(` without a safe
  loader, `unsafe_load`, `FullLoader`, `shell=True`, `zipfile` usage, and
  Jinja/templating imports.
- 20 targeted adversarial/boundary unit tests in `tests/test_project_manifest.py`
  (out of 48 in that file total) covering: arbitrary Python object tags,
  duplicate keys, invalid UTF-8, empty documents, non-mapping roots,
  oversized documents, excessive nesting, excessive collection size,
  oversized scalars, recursive alias structures (both mapping- and
  sequence-based), excessive alias counts, `../` traversal, external
  absolute paths, Windows drive-letter escape, UNC escape, empty paths,
  and symlink escape (simulated via monkeypatching rather than requiring
  real OS symlink-creation privilege, which plain Windows accounts
  without Developer Mode do not have).
- 8 tests in `tests/test_subprocess_runner.py` covering hanging-command
  termination, missing-executable handling, and command-string redaction.
- `pip-audit` against this project's exact direct-dependency versions
  (audited as an explicit requirements list rather than the full ambient
  Python environment, which contains unrelated packages from other
  projects on this development machine that are not installable from
  PyPI and would otherwise abort the scan).

## Findings

### 1. Pillow 10.4.0 — 24 known advisories (FIXED)

`pip-audit` found 24 published PYSEC advisories against the installed
Pillow 10.4.0, all fixed in Pillow ≥12.1.1 (12.3.0 recommended, the
version this fix upgrades to). `pyproject.toml` previously declared only
`pillow>=10.0.0`, permitting installation of any vulnerable version back
to 10.0.0.

**Exploitability in this codebase**: low in practice — `PIL.Image` is
imported in exactly one place (`services/pdf_preflight.py`) as an optional
dependency behind a `try/except ImportError` guard, and grep confirms it
is never actually called anywhere in that file (a vestigial import). The
advisories are nonetheless real and the fix is essentially free (no code
depends on old-Pillow-specific behavior), so it was fixed rather than
left as a documented risk.

**Fix**: `pyproject.toml` now pins `pillow>=12.3.0`. Installed environment
upgraded and re-audited clean (`pip-audit`: "No known vulnerabilities
found" against the updated dependency set). `tests/test_preflight.py`,
`tests/test_build_figures.py`, and `tests/test_v152_rendering_fixes.py`
(the tests most likely to touch image handling) re-run and pass
unchanged (55/55) after the upgrade.

### No other findings

No `eval`/`exec` usage, no unsafe YAML loading, no `shell=True`, no ZIP
extraction (only creation), and no templating-engine usage were found
anywhere in `src/paperforge/`.

## Explicitly not audited in this pass

See "What is explicitly not covered by this pass" in
[SECURITY_MODEL.md](SECURITY_MODEL.md) — LaTeX-escaping re-audit, template
f-string input review beyond confirming no templating engine is used,
temp-file permissions, non-manifest oversized-input DoS surfaces, and
network timeout/redirect handling for `--online` reference verification.
These are not claimed secure; they are recorded as unreviewed.
