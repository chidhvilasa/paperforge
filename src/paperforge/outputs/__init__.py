"""Output lifecycle: listing, verifying, promoting, and rolling back the
`paper_generated/current` / `paper_generated/previous` build outputs.

This operates on top of the `current`/`previous` convention already
produced by `paperforge build` (via `_rotate_output`, which copies the old
`current` into `previous` before a new build overwrites `current`). It adds:

- `outputs list` / `outputs verify`: real artifact-completeness checks
  (required files present, non-trivial size, valid PDF header) independent
  of `doctor`/`preflight` content checks.
- `promote`: verifies `current` and, only if it passes, records a
  promotion manifest (hashes + timestamp) confirming it as the reviewed
  submission candidate. Refuses (leaving `current`/`previous` untouched)
  if verification fails.
- `rollback`: atomically swaps `current` and `previous`, using a marker
  file so an interrupted swap can be safely resumed rather than left in a
  half-swapped state.

Known scope limitation (see docs/OUTPUT_LIFECYCLE.md): this does not yet
implement building into an isolated `.staging-<id>` directory before
`current` is touched at all -- `promote` validates the `current` directory
as already produced by `build`, rather than orchestrating an independent
staged build. `rollback` and `outputs verify` are unaffected by this and
are fully real.
"""

from __future__ import annotations

from paperforge.outputs.lifecycle import list_outputs, promote, rollback
from paperforge.outputs.models import (
    ArtifactInfo,
    OutputVerification,
    PromoteResult,
    RollbackResult,
)
from paperforge.outputs.verifier import verify_output_dir

__all__ = [
    "ArtifactInfo",
    "OutputVerification",
    "PromoteResult",
    "RollbackResult",
    "list_outputs",
    "promote",
    "rollback",
    "verify_output_dir",
]
