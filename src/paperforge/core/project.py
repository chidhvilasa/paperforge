"""Project core."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from paperforge.graph.dependency import ResearchGraph
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


@dataclass
class ProjectConfig:
    version: str
    title: str
    authors: list[str]
    venue: str
    status: str
    sections: list[str]
    build_output_dir: str
    latex_template: str
    paper_type: str = "conference"
    keywords: list[str] = field(default_factory=list)

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
            latex_template=build.get("latex_template", "ieee"),
            paper_type=data.get("paper_type", "conference"),
            keywords=data.get("keywords", []),
        )


class PaperForgeProject:
    PAPERFORGE_DIR = ".paperforge"

    def __init__(
        self,
        root: Path,
        config: ProjectConfig,
        claims: list[Claim],
        experiments: list[Experiment],
    ) -> None:
        self.root = root
        self.config = config
        self.claims = claims
        self.experiments = experiments

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
        with open(paper_yaml) as f:
            config_data = yaml.safe_load(f)
        config = ProjectConfig.from_yaml(config_data)

        claims: list[Claim] = []
        claims_dir = pf_dir / "claims"
        if claims_dir.exists():
            for claim_file in sorted(claims_dir.glob("*.yaml")):
                with open(claim_file) as f:
                    claims.append(Claim.from_yaml(yaml.safe_load(f)))

        experiments: list[Experiment] = []
        experiments_dir = pf_dir / "experiments"
        if experiments_dir.exists():
            for exp_file in sorted(experiments_dir.glob("*.yaml")):
                with open(exp_file) as f:
                    experiments.append(Experiment.from_yaml(yaml.safe_load(f)))

        return cls(root=path, config=config, claims=claims, experiments=experiments)

    def get_graph(self) -> ResearchGraph:
        graph = ResearchGraph()
        for claim in self.claims:
            graph.add_claim(claim)
        for experiment in self.experiments:
            graph.add_experiment(experiment)
        return graph

    @property
    def paperforge_dir(self) -> Path:
        return self.root / self.PAPERFORGE_DIR
