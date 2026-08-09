"""Evidence-first result architecture.

Three explicit evidence kinds back every DIRECT_RESULT / DERIVED_RESULT /
STATISTICAL_RESULT claim:

- :class:`~paperforge.evidence.models.DirectEvidence` -- a value read
  verbatim from a source file (CSV/JSON/YAML) or manually recorded by an
  author, with a content hash so later changes to the source are detected.
- :class:`~paperforge.evidence.models.DerivedEvidence` -- a value computed
  from other evidence via a formula evaluated by the sandboxed AST
  evaluator in :mod:`paperforge.evidence.formula` (never Python ``eval``).
- :class:`~paperforge.evidence.models.StatisticalEvidence` -- an explicitly
  recorded statistical result (test name, statistic, p-value, effect size,
  interval, ...), never computed automatically from prose.

:mod:`paperforge.evidence.graph` links these to manifest claims and detects
cycles and staleness. :mod:`paperforge.evidence.store` persists everything
under ``.paperforge/evidence/`` with atomic writes.
"""

from __future__ import annotations

__all__: list[str] = []
