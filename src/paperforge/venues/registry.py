"""Venue plugin registry."""

from __future__ import annotations

from paperforge.venues.acm import ACMPlugin
from paperforge.venues.base import VenuePlugin
from paperforge.venues.ieee import IEEEPlugin
from paperforge.venues.neurips import NeurIPSPlugin

_REGISTRY: dict[str, VenuePlugin] = {
    "ieee": IEEEPlugin(mode="conference", name="ieee"),
    "ieee-journal": IEEEPlugin(mode="journal", name="ieee-journal"),
    "ieee-trans": IEEEPlugin(mode="journal", name="ieee-trans"),
    "acm": ACMPlugin(),
    "neurips": NeurIPSPlugin(),
}


def get_plugin(name: str) -> VenuePlugin:
    key = name.lower().strip()
    if key not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(f"Unknown venue '{name}'. Available: {available}")
    return _REGISTRY[key]


def list_plugins() -> list[str]:
    return sorted(_REGISTRY.keys())
