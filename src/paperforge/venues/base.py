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

    # --- Versioning metadata (Phase 13 / gap #9) --------------------------
    #
    # None of these are structurally required (existing plugins predate
    # them), so they default to honest "we don't know" values rather than
    # fabricating currency. A blank `checked_date` is not an error; it is
    # a true statement that this adapter's rules were never verified
    # against a dated, live official source and should be treated as a
    # heuristic default, not a guarantee the venue's actual current
    # requirements match.

    @property
    def adapter_version(self) -> str:
        """This adapter's own revision, not a claim about venue currency."""
        return "1.0"

    @property
    def checked_date(self) -> str:
        """ISO date this adapter's rules were last checked against an
        official source. Empty string means never checked -- callers must
        not present the rules as current when this is empty."""
        return ""

    @property
    def source_url(self) -> str:
        """Where these rules nominally come from (documentation only --
        an empty `checked_date` means this URL's content was not verified
        as part of building this adapter)."""
        return ""

    @property
    def source_description(self) -> str:
        return (
            "Default heuristic settings shipped with PaperForge. Not verified "
            "against a dated official venue source."
        )

    @property
    def first_section_heading_policy(self) -> str:
        """How to render the first ("introduction") section heading.

        - "raised_section": use \\IEEEraisesectionheading (the classic
          IEEEtran two-column drop-cap layout). Only safe when the
          Abstract/Index Terms block is short and predictable.
        - "normal_section": use a plain \\section{...} heading. Safe
          regardless of abstract/keyword length.

        Defaults to "raised_section" for backward compatibility with
        existing IEEEtran-based venues. Venues whose real template layout
        makes the raised heading unsafe (e.g. IEEE Access, where Index
        Terms commonly wraps to multiple lines) should override this.
        """
        return "raised_section"
