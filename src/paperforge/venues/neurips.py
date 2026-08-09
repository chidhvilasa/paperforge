"""NeurIPS venue plugin."""

from __future__ import annotations

from typing import ClassVar

from paperforge.core.project import PaperForgeProject
from paperforge.venues.base import VenueIssue, VenuePlugin


class NeurIPSPlugin(VenuePlugin):
    name = "neurips"
    display_name = "NeurIPS"
    latex_documentclass = "\\documentclass{article}"
    required_sections: ClassVar[list[str]] = ["abstract", "introduction", "conclusion"]
    max_pages = 9

    @property
    def source_url(self) -> str:
        return "https://neurips.cc/Conferences/2024/PaperInformation/StyleFiles"

    @property
    def source_description(self) -> str:
        return (
            "neurips_2024 style file conventions (preprint mode). NeurIPS "
            "publishes a fresh style package most years; this adapter is "
            "not re-verified against each year's package automatically."
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
                            f"NeurIPS requires section '{section}' "
                            "to have at least one claim"
                        ),
                    )
                )
        for exp in project.experiments:
            if exp.seed is None:
                issues.append(
                    VenueIssue(
                        code="MISSING_SEED",
                        severity="WARNING",
                        message=(
                            f"{exp.id} has no random seed — NeurIPS reviewers "
                            "expect reproducibility"
                        ),
                    )
                )
        for exp in project.experiments:
            if exp.dataset is None:
                issues.append(
                    VenueIssue(
                        code="MISSING_DATASET",
                        severity="WARNING",
                        message=(
                            f"{exp.id} has no dataset specified — required "
                            "for NeurIPS reproducibility"
                        ),
                    )
                )
        return issues

    def generate_preamble(self) -> str:
        return (
            "\\usepackage[preprint]{neurips_2024}\n"
            "\\usepackage{amsfonts}\n"
            "\\usepackage{amsmath}\n"
            "\\usepackage{graphicx}\n"
            "\\usepackage{hyperref}\n"
            "\\usepackage{microtype}"
        )

    def generate_author_block(self, authors: list[str]) -> str:
        if not authors:
            return "\\author{Author TBD \\\\ Institution TBD}"
        return "\\author{" + " \\\\[0.5em] ".join(authors) + "}"
