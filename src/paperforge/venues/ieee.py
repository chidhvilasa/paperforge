"""IEEE (generic) venue plugin."""

from __future__ import annotations

from typing import ClassVar

from paperforge.core.project import PaperForgeProject
from paperforge.venues.base import VenueIssue, VenuePlugin


class IEEEPlugin(VenuePlugin):
    name = "ieee"
    display_name = "IEEE (Generic)"
    latex_documentclass = "\\documentclass[conference]{IEEEtran}"
    required_sections: ClassVar[list[str]] = ["abstract", "introduction", "conclusion"]
    max_pages = 8

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
                            f"IEEE requires section '{section}' "
                            "to have at least one claim"
                        ),
                    )
                )
        for claim in project.claims:
            if not claim.citations and claim.text:
                issues.append(
                    VenueIssue(
                        code="UNCITED_CLAIM",
                        severity="WARNING",
                        message=(
                            f"{claim.id} has no citations — IEEE expects "
                            "citations for all claims"
                        ),
                    )
                )
        return issues

    def generate_preamble(self) -> str:
        return (
            "\\IEEEoverridecommandlockouts\n"
            "\\usepackage{cite}\n"
            "\\usepackage{amsmath,amssymb,amsfonts}\n"
            "\\usepackage{graphicx}\n"
            "\\usepackage{textcomp}\n"
            "\\usepackage{xcolor}\n"
            "\\usepackage{hyperref}"
        )

    def generate_author_block(self, authors: list[str]) -> str:
        if not authors:
            return "\\author{Author(s) TBD}"
        return "\\author{" + " \\and ".join(authors) + "}"
