"""Venue plugin interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from paperforge.core.project import PaperForgeProject


@dataclass
class VenueIssue:
    code: str
    severity: str
    message: str


class VenuePlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Short name, e.g. 'ieee', 'acm', 'neurips'."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human name, e.g. 'IEEE Transactions', 'ACM', 'NeurIPS'."""

    @property
    @abstractmethod
    def latex_documentclass(self) -> str:
        """Full documentclass line, e.g. '\\documentclass[conference]{IEEEtran}'."""

    @property
    @abstractmethod
    def required_sections(self) -> list[str]:
        """Sections that must exist and have claims."""

    @property
    @abstractmethod
    def max_pages(self) -> int | None:
        """Page limit, or None if not applicable."""

    @abstractmethod
    def validate(self, project: PaperForgeProject) -> list[VenueIssue]:
        """Run venue-specific validation checks. Return list of issues."""

    @abstractmethod
    def generate_preamble(self) -> str:
        """Return LaTeX preamble lines after documentclass."""

    @abstractmethod
    def generate_author_block(self, authors: list[str]) -> str:
        """Return LaTeX author block formatted for this venue."""
