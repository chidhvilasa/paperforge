# Output lifecycle: current, previous, promote, rollback

Build output lives in `paper_generated/current/` (and, once a second build
runs, `paper_generated/previous/`, populated automatically by `build`'s
existing rotation logic before it overwrites `current`).

## Commands

```bash
paperforge outputs list [--json]
paperforge outputs verify [--target current|previous] [--json]
paperforge promote [--json]
paperforge rollback [--json]
```

## `outputs verify`

Checks artifact *completeness*, independent of `doctor`/`preflight`
content checks:

- `paper.pdf` exists and is larger than a trivial-size floor
- `paper.pdf` starts with a valid PDF header (`%PDF-`)
- SHA-256 hashes of every present artifact (`paper.pdf`, `paper.tex`,
  `references.bib`, `paper_overleaf.zip`, `paper.docx`,
  `traceability.tex`) are recorded so a later comparison (e.g. after
  `rollback`) can detect a hand-edit or corruption.

## `promote`

Verifies `paper_generated/current/`. If it passes, writes
`.paperforge/output_manifest.json` (hashes + timestamp) recording it as
the reviewed, confirmed submission candidate. **If verification fails,
`current` and `previous` are left completely untouched** and the specific
issues are reported — nothing is silently promoted.

## `rollback`

Atomically swaps `current` and `previous` via a 3-step rename sequence
(`current → tmp`, `previous → current`, `tmp → previous`), writing a
resumable marker file (`.paperforge/.rollback_in_progress.json`) before
each step. If the process is interrupted mid-swap, the *next* `rollback`
call detects the marker and resumes from the exact next step rather than
restarting or leaving a half-swapped state. Refuses (reporting why) when
there is no non-empty `previous` to roll back to.

## Known scope limitation

This does not yet implement building into an isolated `.staging-<id>`
directory *before* `current` is touched at all — `promote` validates
`current` as already produced by `build` (which already writes the *old*
current into `previous` first via its existing rotation logic), rather
than orchestrating an independently staged build that only replaces
`current` after full validation. `rollback`, `outputs list`, and `outputs
verify` are fully real and unaffected by this limitation.
