"""ACM venue plugin."""

from __future__ import annotations

from typing import ClassVar

from paperforge.core.project import PaperForgeProject
from paperforge.venues.base import VenueIssue, VenuePlugin


class ACMPlugin(VenuePlugin):
    name = "acm"
    display_name = "ACM"
    latex_documentclass = "\\documentclass[sigconf]{acmart}"
    required_sections: ClassVar[list[str]] = ["abstract", "introduction", "conclusion"]
    max_pages = 12

    @property
    def source_url(self) -> str:
        return "https://www.acm.org/publications/proceedings-template"

    @property
    def source_description(self) -> str:
        return (
            "acmart 'sigconf' class conventions. Page limits and section "
            "requirements are PaperForge heuristic defaults; specific ACM "
            "venues/CFPs vary and are not individually verified here."
        )

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
                            f"ACM requires section '{section}' "
                            "to have at least one claim"
                        ),
                    )
                )
        if "related_work" not in section_names:
            issues.append(
                VenueIssue(
                    code="MISSING_RELATED_WORK",
                    severity="WARNING",
                    message="ACM submissions typically require a Related Work section",
                )
            )
        return issues

    def generate_preamble(self) -> str:
        return (
            "\\usepackage{booktabs}\n"
            "\\usepackage{graphicx}\n"
            "\\usepackage{hyperref}"
        )

    def generate_author_block(self, authors: list[str]) -> str:
        if not authors:
            return "\\author{Author TBD}\n\\affiliation{\\institution{Institution}}"
        blocks = []
        for author in authors:
            blocks.append(
                f"\\author{{{author}}}\n"
                f"\\affiliation{{\\institution{{Institution TBD}}}}"
            )
        return "\n".join(blocks)
