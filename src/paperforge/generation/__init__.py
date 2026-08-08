"""Deterministic, evidence-safe manuscript generation.

This package never fabricates scientific content. The only text it ever
produces is:

- structural outlines (headings, goals, permitted claim/evidence/citation
  lists, unresolved items) with no prose at all, or
- neutral template sentences that wrap a claim's *author-provided* text
  (``ClaimEntry.text``) in a structural phrase naming its evidence class,
  claim ID, and evidence/citation references -- never inventing new facts,
  numbers, citations, or interpretations.

Every generated sentence is paired with a provenance record
(:mod:`paperforge.generation.provenance`) recording exactly which claim,
evidence, and citations it came from, so nothing generated is untraceable.

Generation works with zero AI providers configured (:class:`NoAIProvider`)
and ships a second, fully deterministic :class:`FixtureProvider` for tests.
No test in this repository requires a real API key.
"""

from __future__ import annotations

from paperforge.generation.no_ai import (
    GeneratedSection,
    GeneratedSentence,
    generate_outline,
    generate_section,
)
from paperforge.generation.provenance import ProvenanceRecord, validate_provenance
from paperforge.generation.providers import (
    FixtureProvider,
    GenerationProvider,
    NoAIProvider,
    ProviderConfig,
    get_provider,
)

__all__ = [
    "FixtureProvider",
    "GeneratedSection",
    "GeneratedSentence",
    "GenerationProvider",
    "NoAIProvider",
    "ProviderConfig",
    "ProvenanceRecord",
    "generate_outline",
    "generate_section",
    "get_provider",
    "validate_provenance",
]
