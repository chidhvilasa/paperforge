# Release checklist

The actual sequence used for every release from v1.5.1 onward, including
this one. Not automated end-to-end; run manually in order.

## 1. Safety

- [ ] `git status` clean (or only expected untracked local files)
- [ ] External backup: `git bundle create <dir>/paperforge.bundle --all`,
      then `git bundle verify`
- [ ] Local safety branch: `git branch backup/pre-<name>-<timestamp> HEAD`
- [ ] Baseline `python -m pytest -q` passes before making any change

## 2. Implementation

- [ ] Each logical unit of work committed separately, with a descriptive
      message and an accurate, verified test count
- [ ] Targeted tests for the change pass before moving to the next unit

## 3. Quality gates (run at the end, after all changes)

```bash
python -m pytest -q
ruff check .
ruff format --check .          # on changed files only if a repo-wide
                                # reformat isn't wanted for this release
mypy src/paperforge
python -m build
twine check dist/*
pip-audit --strict -r <(exact direct-dependency versions)
```

All must pass with zero failures/errors before proceeding. Do not report
a release complete with any of these red.

## 4. Clean-install acceptance

- [ ] Build wheel + sdist
- [ ] Install the **wheel** into a fresh virtual environment *outside* the
      repository
- [ ] `python -c "import paperforge; print(paperforge.__file__)"` resolves
      inside that clean environment, not the dev tree
- [ ] `paperforge --version` matches the release version
- [ ] `paperforge --help` and each major subcommand's `--help` work
- [ ] At least one real end-to-end fixture exercised from the installed
      wheel (not just from source)
- [ ] Extract the sdist separately, build a wheel from it, and confirm it
      installs and behaves the same

## 5. Version and changelog

- [ ] Semantic version bump reasoned explicitly (patch vs. minor vs.
      major) and recorded (see `docs/VERSION_DECISION.md` when one exists
      for a given release)
- [ ] Version updated consistently in `pyproject.toml`,
      `src/paperforge/__init__.py`, and `uv.lock`
- [ ] `CHANGELOG.md` updated with an honest Added/Fixed/Known-limitations
      section — no feature listed as shipped unless it was actually
      verified working in step 4

## 6. Git

- [ ] `git log --oneline origin/main..HEAD` / `HEAD..origin/main` both
      checked for remote parity before and after push
- [ ] Push to `origin/main` (never force-push)
- [ ] **Do not** create or move a Git tag automatically
- [ ] **Do not** create a GitHub release automatically

Tagging and publishing a GitHub release remain deliberate, manual,
human-triggered steps after this checklist completes.
