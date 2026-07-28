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
class Affiliation:
    name: str = ""
    institution: str = ""
    department: str = ""
    city: str = ""
    country: str = ""
    email: str = ""
    membership: str = ""
    shared_with: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Affiliation:
        return cls(
            name=data.get("name", ""),
            institution=data.get("institution", ""),
            department=data.get("department", ""),
            city=data.get("city", ""),
            country=data.get("country", ""),
            email=data.get("email", ""),
            membership=data.get("membership", ""),
            shared_with=data.get("shared_with") or [],
        )


@dataclass
class ProjectConfig:
    version: str
    title: str
    authors: list[str]
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

    @classmethod
    def from_yaml(cls, data: dict) -> ProjectConfig:
        build = data.get("build", {})
        return cls(
            version=data.get("version", "0.1"),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            venue=data.get("venue", ""),
            status=data.get("status", "draft"),
            sections=data.get("sections", []),
            build_output_dir=build.get("output_dir", ".paperforge/output"),
            paper_information_dir=build.get("paper_information_dir", "paper_information"),
            base_dir=build.get("base_dir", ""),
            latex_template=build.get("latex_template", "ieee"),
            paper_type=data.get("paper_type", "conference"),
            keywords=data.get("keywords", []),
            affiliations=[Affiliation.from_dict(a) for a in data.get("affiliations", [])],
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
            biographies=[Biography.from_dict(b) for b in data.get("biographies", [])],
            ai_disclosure=data.get("ai_disclosure", ""),
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
