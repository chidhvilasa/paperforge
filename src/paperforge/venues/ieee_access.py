"""IEEE Access venue plugin."""

from __future__ import annotations

from typing import ClassVar

from paperforge.core.project import PaperForgeProject
from paperforge.venues.base import VenueIssue, VenuePlugin


class IEEEAccessPlugin(VenuePlugin):
    name = "ieee-access"
    display_name = "IEEE Access"
    latex_documentclass = "\\documentclass[journal]{IEEEtran}"
    required_sections: ClassVar[list[str]] = ["abstract", "introduction", "conclusion"]
    max_pages: int | None = None  # IEEE Access has no page limit

    @property
    def first_section_heading_policy(self) -> str:
        # IEEE Access papers commonly carry longer Index Terms lists than
        # a plain IEEEtran journal assumes. \IEEEraisesectionheading raises
        # the first section heading by a fixed amount that only clears the
        # Index Terms block when it fits on a single line; with a longer
        # (multi-line) Index Terms block the raised heading and drop cap
        # collide with the tail of Index Terms. A plain section heading
        # has no such length-dependent collision, so it is used
        # unconditionally for this venue rather than only "sometimes".
        return "normal_section"

    def validate(self, project: PaperForgeProject) -> list[VenueIssue]:
        issues = []
        section_names = {c for claim in project.claims for c in claim.sections}
        for section in self.required_sections:
            if section not in section_names:
                issues.append(
                    VenueIssue(
                        code="MISSING_REQUIRED_SECTION",
                        severity="WARNING",
                        message=(
                            f"IEEE Access requires section "
                            f"'{section}' to have at least one claim"
                        ),
                    )
                )
        return issues

    def generate_preamble(self) -> str:
        return (
            "\\usepackage[T1]{fontenc}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage{cite}\n"
            "\\usepackage{amsmath,amssymb,amsfonts}\n"
            "\\usepackage{algorithmic}\n"
            "\\usepackage{array}\n"
            "\\usepackage{textcomp}\n"
            "\\usepackage{xcolor}\n"
            "\\usepackage{graphicx}\n"
            "\\usepackage{booktabs}\n"
            "\\usepackage{microtype}\n"
            "\\usepackage[hidelinks]{hyperref}"
        )

    def generate_author_block(self, authors: list[str]) -> str:
        if not authors:
            return "\\author{Author(s) TBD}"
        return "\\author{" + " \\and ".join(authors) + "}"
