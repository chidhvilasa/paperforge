"""Tests for the Claim and Experiment data models."""

from datetime import date

from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def test_claim_round_trip() -> None:
    claim = Claim(
        id="claim_07",
        text="EXAMINA achieved 98.4% accuracy.",
        experiment="exp_27",
        figures=["fig_03"],
        tables=["tbl_02"],
        citations=["cite_01"],
        sections=["abstract", "results"],
        status="verified",
        last_verified=date(2026, 7, 25),
    )
    reconstructed = Claim.from_yaml(claim.to_yaml())
    assert reconstructed == claim


def test_claim_round_trip_nulls() -> None:
    claim = Claim(id="claim_01", text="x", experiment="exp_01")
    reconstructed = Claim.from_yaml(claim.to_yaml())
    assert reconstructed == claim


def test_experiment_round_trip() -> None:
    experiment = Experiment(
        id="exp_27",
        description="Accuracy benchmark",
        results_file="results/exp_27.json",
        metrics={"accuracy": 98.4},
        hardware="A100",
        dataset="EXAMINA",
        seed=42,
        ran_at=date(2026, 7, 25),
    )
    reconstructed = Experiment.from_yaml(experiment.to_yaml())
    assert reconstructed == experiment


def test_experiment_round_trip_nulls() -> None:
    experiment = Experiment(id="exp_01")
    reconstructed = Experiment.from_yaml(experiment.to_yaml())
    assert reconstructed == experiment


def test_claim_status_default() -> None:
    claim = Claim(id="c1", text="x", experiment="e1")
    assert claim.status == "unverified"


def test_experiment_metrics_default() -> None:
    experiment = Experiment(id="e1")
    assert experiment.metrics == {}
