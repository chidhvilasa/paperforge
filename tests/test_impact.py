"""Tests for the paperforge impact command."""

from pathlib import Path

import pytest
import yaml

from paperforge.commands import impact, init
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _write_claim(tmp_path: Path, claim: Claim) -> None:
    path = tmp_path / ".paperforge" / "claims" / f"{claim.id}.yaml"
    path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _write_experiment(tmp_path: Path, experiment: Experiment) -> None:
    path = tmp_path / ".paperforge" / "experiments" / f"{experiment.id}.yaml"
    path.write_text(
        yaml.dump(experiment.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def test_impact_shows_affected_claims(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_experiment(tmp_path, Experiment(id="exp_01", metrics={"accuracy": 98.4}))
    _write_claim(
        tmp_path,
        Claim(
            id="claim_02",
            text="Model achieves 98.4% accuracy.",
            experiment="exp_01",
            sections=["results"],
            status="verified",
        ),
    )

    impact.run("exp_01", tmp_path)


def test_impact_no_claims_linked(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_experiment(tmp_path, Experiment(id="exp_01"))

    impact.run("exp_01", tmp_path)


def test_impact_unknown_experiment(tmp_path: Path) -> None:
    init.run(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        impact.run("exp_nonexistent", tmp_path)
    assert exc_info.value.code == 1


def test_impact_fails_without_init(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        impact.run("exp_01", tmp_path)
    assert exc_info.value.code == 1


def test_impact_deduplicates_sections(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_experiment(tmp_path, Experiment(id="exp_01"))
    _write_claim(
        tmp_path,
        Claim(id="claim_a", text="A", experiment="exp_01", sections=["results"]),
    )
    _write_claim(
        tmp_path,
        Claim(id="claim_b", text="B", experiment="exp_01", sections=["results"]),
    )

    impact.run("exp_01", tmp_path)


def test_impact_shows_multiple_claims(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_experiment(tmp_path, Experiment(id="exp_01"))
    for name in ("claim_a", "claim_b", "claim_c"):
        _write_claim(
            tmp_path,
            Claim(id=name, text=f"Text for {name}.", experiment="exp_01"),
        )

    impact.run("exp_01", tmp_path)


def test_impact_verification_status_unverified(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_experiment(tmp_path, Experiment(id="exp_01"))
    _write_claim(
        tmp_path,
        Claim(
            id="claim_a",
            text="An unverified claim.",
            experiment="exp_01",
            status="unverified",
        ),
    )

    impact.run("exp_01", tmp_path)


def test_impact_empty_text_displays_placeholder(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_experiment(tmp_path, Experiment(id="exp_01"))
    _write_claim(
        tmp_path,
        Claim(id="claim_a", text="", experiment="exp_01"),
    )

    impact.run("exp_01", tmp_path)


def test_impact_sorted_sections(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_experiment(tmp_path, Experiment(id="exp_01"))
    _write_claim(
        tmp_path,
        Claim(
            id="claim_a",
            text="Text",
            experiment="exp_01",
            sections=["results", "abstract", "discussion"],
        ),
    )

    impact.run("exp_01", tmp_path)


def test_impact_figures_and_tables_reported(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_experiment(tmp_path, Experiment(id="exp_01"))
    _write_claim(
        tmp_path,
        Claim(
            id="claim_a",
            text="Text",
            experiment="exp_01",
            figures=["fig_03"],
            tables=["tbl_02"],
        ),
    )

    impact.run("exp_01", tmp_path)
