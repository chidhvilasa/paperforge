"""Tests for ResearchGraph."""

from paperforge.graph.dependency import ResearchGraph
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def test_get_affected_returns_correct_nodes() -> None:
    graph = ResearchGraph()
    graph.add_experiment(Experiment(id="exp_27"))
    graph.add_claim(
        Claim(
            id="claim_07",
            text="x",
            experiment="exp_27",
            sections=["abstract", "results"],
            figures=["fig_03"],
            tables=["tbl_02"],
        )
    )
    graph.add_claim(
        Claim(
            id="claim_12",
            text="y",
            experiment="exp_27",
            sections=["results", "discussion"],
            figures=[],
            tables=["tbl_02"],
        )
    )

    affected = graph.get_affected("exp_27")

    assert affected.claims == ["claim_07", "claim_12"]
    assert "abstract" in affected.sections
    assert "results" in affected.sections
    assert "discussion" in affected.sections
    assert "fig_03" in affected.figures
    assert "tbl_02" in affected.tables
    assert len(affected.tables) == 1


def test_get_affected_unknown_experiment() -> None:
    graph = ResearchGraph()
    affected = graph.get_affected("nonexistent")
    assert affected.claims == []
    assert affected.sections == []
    assert affected.figures == []
    assert affected.tables == []


def test_get_affected_no_matching_claims() -> None:
    graph = ResearchGraph()
    graph.add_experiment(Experiment(id="exp_01"))
    graph.add_experiment(Experiment(id="exp_02"))
    graph.add_claim(Claim(id="claim_01", text="x", experiment="exp_01"))

    affected = graph.get_affected("exp_02")

    assert affected.claims == []


def test_sections_deduplicated() -> None:
    graph = ResearchGraph()
    graph.add_experiment(Experiment(id="exp_01"))
    graph.add_claim(
        Claim(id="claim_01", text="x", experiment="exp_01", sections=["results"])
    )
    graph.add_claim(
        Claim(id="claim_02", text="y", experiment="exp_01", sections=["results"])
    )

    affected = graph.get_affected("exp_01")

    assert affected.sections == ["results"]


def test_claim_count() -> None:
    graph = ResearchGraph()
    graph.add_claim(Claim(id="claim_01", text="a", experiment="exp_01"))
    graph.add_claim(Claim(id="claim_02", text="b", experiment="exp_01"))
    graph.add_claim(Claim(id="claim_03", text="c", experiment="exp_01"))
    assert graph.claim_count == 3


def test_experiment_count() -> None:
    graph = ResearchGraph()
    graph.add_experiment(Experiment(id="exp_01"))
    graph.add_experiment(Experiment(id="exp_02"))
    assert graph.experiment_count == 2
