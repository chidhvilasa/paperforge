"""Author-review approval workflow.

Tracks explicit author decisions (approve/reject/reset) over the objects
PaperForge generates or records automatically: generated provenance
sentences, manifest claims, and direct/derived/statistical evidence
records. Every decision is written to an append-only ledger
(``.paperforge/approvals.json``) alongside a content hash of the object at
decision time, so a later edit to that object is detected as a *stale*
approval rather than silently staying "approved".
"""

from __future__ import annotations

__all__: list[str] = []
