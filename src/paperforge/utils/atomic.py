"""Atomic, crash-safe file writes.

Used anywhere PaperForge persists state that must never be left half-written
if the process dies mid-write: the project manifest, intake state, migration
output, requirements reports, provenance sidecars, and output-lifecycle
manifests.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` atomically.

    Writes to a temporary file in the same directory as ``path`` (so the
    final ``os.replace`` is guaranteed atomic on the same filesystem/volume)
    and then renames it into place. On any failure, the temporary file is
    removed and the original ``path`` is left untouched.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


__all__ = ["atomic_write_bytes", "atomic_write_text"]
