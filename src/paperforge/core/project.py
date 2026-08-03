"""Project core."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from paperforge.graph.dependency import ResearchGraph
from paperforge.models.algorithm import Algorithm
from paperforge.models.citation import Citation
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment
from paperforge.models.figure import Figure
from paperforge.models.table import Table


@dataclass
class Biography:
    author: str = ""
    text: str = ""
    photo_path: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Biography:
        return cls(
            author=data.get("author", ""),
            text=data.get("text", ""),
            photo_path=data.get("photo_path", ""),
        )

    def to_latex(self) -> str:
        from paperforge.utils.latex import escape_latex_safe

        text = escape_latex_safe(self.text)
        author_escaped = escape_latex_safe(self.author)
        if self.photo_path:
            return (
                f"\\begin{{IEEEbiography}}"
                f"[{{\\includegraphics[width=1in,height=1.25in,"
                f"clip,keepaspectratio]{{{self.photo_path}}}}}]"
                f"{{{author_escaped}}}\n"
                f"{text}\n"
                f"\\end{{IEEEbiography}}"
            )
        else:
            return (
                f"\\begin{{IEEEbiographynophoto}}"
                f"{{{author_escaped}}}\n"
                f"{text}\n"
                f"\\end{{IEEEbiographynophoto}}"
            )


@dataclass
class Author:
    given_name: str = ""
    family_name: str = ""
    display_name: str = ""
    citation_name: str = ""
    email: str = ""
    affiliation_ids: list[str] = field(default_factory=list)
    corresponding: bool = False
    ieee_membership_grade: str | None = None
    orcid: str | None = None
    biography: str = ""

    @property
    def full_name(self) -> str:
        if self.display_name:
            return self.display_name
        parts = [self.given_name, self.family_name]
        res = " ".join(p for p in parts if p)
        return res

    @property
    def cite_name(self) -> str:
        if self.citation_name:
            return self.citation_name
        if self.given_name and self.family_name:
            return f"{self.given_name[0]}. {self.family_name}"
        return self.full_name

    def __str__(self) -> str:
        return self.full_name

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> Author:
        if isinstance(data, str):
            return cls(display_name=data)
        aff_ids = data.get("affiliation_ids") or []
        if not aff_ids and data.get("affiliation"):
            aff_ids = [str(data.get("affiliation"))]
        return cls(
            given_name=str(data.get("given_name", "") or ""),
            family_name=str(data.get("family_name", "") or ""),
            display_name=str(
                data.get("display_name", "") or data.get("name", "") or ""
            ),
            citation_name=str(data.get("citation_name", "") or ""),
            email=str(data.get("email", "") or ""),
            affiliation_ids=[str(x) for x in aff_ids],
            corresponding=bool(data.get("corresponding", False)),
            ieee_membership_grade=data.get("ieee_membership_grade")
            or data.get("membership"),
            orcid=data.get("orcid"),
            biography=str(data.get("biography", "") or ""),
        )


@dataclass
class Affiliation:
    id: str = ""
    name: str = ""
    institution: str = ""
    department: str = ""
    city: str = ""
    country: str = ""
    email: str = ""
    membership: str = ""
    shared_with: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str, key: str = "") -> Affiliation:
        if isinstance(data, str):
            return cls(id=key, name=data, institution=data)
        return cls(
            id=key or str(data.get("id", "") or ""),
            name=str(data.get("name", "") or data.get("institution", "") or ""),
            institution=str(data.get("institution", "") or ""),
            department=str(data.get("department", "") or ""),
            city=str(data.get("city", "") or ""),
            country=str(data.get("country", "") or ""),
            email=str(data.get("email", "") or ""),
            membership=str(data.get("membership", "") or ""),
            shared_with=[str(x) for x in (data.get("shared_with") or [])],
        )


@dataclass
class ProjectConfig:
    version: str
    title: str
    authors: list[Author]
    venue: str
    status: str
    sections: list[str]
    build_output_dir: str = "paper_generated/current"
    paper_information_dir: str = "paper_information"
    base_dir: str = ""
    latex_template: str = "ieee"
    paper_type: str = "conference"
    keywords: list[str] = field(default_factory=list)
    affiliations: list[Affiliation] = field(default_factory=list)
    acknowledgment: str = ""
    email: str = ""
    orcid: str = ""
    funding: str = ""
    data_availability: str = ""
    code_availability: str = ""
    conflict_of_interest: str = ""
    manuscript_received: str = ""
    publisher_id: str = ""
    sections_overview: str = ""
    theorem_packages: bool = True
    biographies: list[Biography] = field(default_factory=list)
    ai_disclosure: str = ""
    output_rotation: str = "preserve_previous"
    output_rotation_archive_dir: str = ""

    @classmethod
    def from_yaml(cls, data: dict) -> ProjectConfig:
        build = data.get("build", {})
        raw_authors = data.get("authors", [])
        authors = [Author.from_dict(a) for a in raw_authors]

        raw_affs = data.get("affiliations")
        affiliations: list[Affiliation] = []
        if isinstance(raw_affs, dict):
            affiliations = [
                Affiliation.from_dict(v, key=k) for k, v in raw_affs.items()
            ]
        elif isinstance(raw_affs, list):
            affiliations = [Affiliation.from_dict(a) for a in raw_affs]

        bios = [Biography.from_dict(b) for b in data.get("biographies", [])]
        # Supplement biographies from author biographies if not explicitly listed
        existing_bio_authors = {b.author for b in bios}
        for a in authors:
            if a.biography and a.full_name not in existing_bio_authors:
                bios.append(Biography(author=a.full_name, text=a.biography))

        return cls(
            version=data.get("version", "0.1"),
            title=data.get("title", ""),
            authors=authors,
            venue=data.get("venue", ""),
            status=data.get("status", "draft"),
            sections=data.get("sections", []),
            build_output_dir=build.get("output_dir", ".paperforge/output"),
            paper_information_dir=build.get(
                "paper_information_dir", "paper_information"
            ),
            base_dir=build.get("base_dir", ""),
            latex_template=build.get("latex_template", "ieee"),
            paper_type=data.get("paper_type", "conference"),
            keywords=data.get("keywords", []),
            affiliations=affiliations,
            acknowledgment=data.get("acknowledgment", ""),
            email=data.get("email", ""),
            orcid=data.get("orcid", ""),
            funding=data.get("funding", ""),
            data_availability=data.get("data_availability", ""),
            code_availability=data.get("code_availability", ""),
            conflict_of_interest=data.get("conflict_of_interest", ""),
            manuscript_received=data.get("manuscript_received", ""),
            publisher_id=data.get("publisher_id", ""),
            sections_overview=data.get("sections_overview", ""),
            theorem_packages=bool(build.get("theorem_packages", True)),
            biographies=bios,
            ai_disclosure=data.get("ai_disclosure", ""),
            output_rotation=build.get("rotation", "preserve_previous"),
            output_rotation_archive_dir=build.get("rotation_archive_dir", ""),
        )


class PaperForgeProject:
    PAPERFORGE_DIR = ".paperforge"

    def __init__(
        self,
        root: Path,
        config: ProjectConfig,
        claims: list[Claim],
        experiments: list[Experiment],
        figures: list[Figure],
        tables: list[Table] | None = None,
        citations: list[Citation] | None = None,
        algorithms: list[Algorithm] | None = None,
    ) -> None:
        self.root = root
        self.config = config
        self.claims = claims
        self.experiments = experiments
        self.figures = figures
        self.tables = tables if tables is not None else []
        self.citations = citations if citations is not None else []
        self.algorithms = algorithms if algorithms is not None else []

    @classmethod
    def load(cls, path: Path) -> PaperForgeProject:
        pf_dir = path / cls.PAPERFORGE_DIR
        if not pf_dir.exists():
            raise FileNotFoundError(
                f"No .paperforge/ directory found in {path}. "
                "Run `paperforge init` first."
            )
        paper_yaml = pf_dir / "paper.yaml"
        if not paper_yaml.exists():
            raise FileNotFoundError(f"paper.yaml not found in {pf_dir}.")
        with open(paper_yaml, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        config = ProjectConfig.from_yaml(config_data)

        claims: list[Claim] = []
        claims_dir = pf_dir / "claims"
        if claims_dir.exists():
            for claim_file in sorted(claims_dir.glob("*.yaml")):
                with open(claim_file, encoding="utf-8") as f:
                    claims.append(Claim.from_yaml(yaml.safe_load(f)))

        experiments: list[Experiment] = []
        experiments_dir = pf_dir / "experiments"
        if experiments_dir.exists():
            for exp_file in sorted(experiments_dir.glob("*.yaml")):
                with open(exp_file, encoding="utf-8") as f:
                    experiments.append(Experiment.from_yaml(yaml.safe_load(f)))

        figures: list[Figure] = []
        figures_dir = pf_dir / "figures"
        if figures_dir.exists():
            for fig_file in sorted(figures_dir.glob("*.yaml")):
                with open(fig_file, encoding="utf-8") as f:
                    figures.append(Figure.from_yaml(yaml.safe_load(f)))

        tables: list[Table] = []
        tables_dir = pf_dir / "tables"
        if tables_dir.exists():
            for tbl_file in sorted(tables_dir.glob("*.yaml")):
                with open(tbl_file, encoding="utf-8") as f:
                    tables.append(Table.from_yaml(yaml.safe_load(f)))

        citations: list[Citation] = []
        citations_dir = pf_dir / "citations"
        if citations_dir.exists():
            for cit_file in sorted(citations_dir.glob("*.yaml")):
                with open(cit_file, encoding="utf-8") as f:
                    citations.append(Citation.from_yaml(yaml.safe_load(f)))

        algorithms: list[Algorithm] = []
        algorithms_dir = pf_dir / "algorithms"
        if algorithms_dir.exists():
            for alg_file in sorted(algorithms_dir.glob("*.yaml")):
                with open(alg_file, encoding="utf-8") as f:
                    algorithms.append(Algorithm.from_yaml(yaml.safe_load(f)))

        return cls(
            root=path,
            config=config,
            claims=claims,
            experiments=experiments,
            figures=figures,
            tables=tables,
            citations=citations,
            algorithms=algorithms,
        )

    def get_graph(self) -> ResearchGraph:
        graph = ResearchGraph()
        for claim in self.claims:
            graph.add_claim(claim)
        for experiment in self.experiments:
            graph.add_experiment(experiment)
        for figure in self.figures:
            graph.add_figure(figure)
        for table in self.tables:
            graph.add_table(table)
        return graph

    @property
    def figure_count(self) -> int:
        return len(self.figures)

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def citation_count(self) -> int:
        return len(self.citations)

    @property
    def algorithm_count(self) -> int:
        return len(self.algorithms)

    @property
    def citation_map(self) -> dict[str, Citation]:
        return {c.key: c for c in self.citations}

    @property
    def algorithm_map(self) -> dict[str, Algorithm]:
        return {a.id: a for a in self.algorithms}

    @property
    def paperforge_dir(self) -> Path:
        return self.root / self.PAPERFORGE_DIR

    @property
    def project_root(self) -> Path:
        return self.root

    @property
    def output_dir(self) -> Path:
        return self.root / (self.config.build_output_dir or "paper_generated/current")
