"""Tests for PaperForgeProject."""

from pathlib import Path

import pytest

from paperforge.commands import init
from paperforge.core.project import PaperForgeProject
from paperforge.graph.dependency import ResearchGraph

CLAIM_02_YAML = """\
id: claim_02
text: "A second claim."
experiment: "exp_01"
figures: []
tables: []
citations: []
sections: []
status: unverified
last_verified: null
"""


def test_project_load_reads_config(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    assert project.config.version == "0.1"
    assert project.config.status == "draft"
    assert len(project.config.sections) == 8


def test_project_load_reads_claims(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    assert len(project.claims) == 1
    assert project.claims[0].id == "claim_01"


def test_project_load_reads_experiments(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    assert len(project.experiments) == 1
    assert project.experiments[0].id == "exp_01"


def test_project_get_graph_returns_research_graph(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    graph = project.get_graph()
    assert isinstance(graph, ResearchGraph)
    assert graph.claim_count == 1
    assert graph.experiment_count == 1


def test_project_load_fails_without_init(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        PaperForgeProject.load(tmp_path)


def test_project_load_multiple_claims(tmp_path: Path) -> None:
    init.run(tmp_path)
    claim_02 = tmp_path / ".paperforge" / "claims" / "claim_02.yaml"
    claim_02.write_text(CLAIM_02_YAML, encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    assert len(project.claims) == 2
