"""Venue plugin architecture for PaperForge."""

from paperforge.venues.base import VenueIssue, VenuePlugin
from paperforge.venues.registry import get_plugin, list_plugins

__all__ = ["VenueIssue", "VenuePlugin", "get_plugin", "list_plugins"]
