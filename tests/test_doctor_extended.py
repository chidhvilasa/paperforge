"""Tests for doctor checks 11-20 (number consistency and metadata checks)."""

from __future__ import annotations

from pathlib import Path

import yaml

from paperforge.commands import init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _write_claim(tmp_path: Path, claim: Claim, claim_id: str | None = None) -> None:
    cid = claim_id or claim.id
    path = tmp_path / ".paperforge" / "claims" / f"{cid}.yaml"
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


def _load_project(tmp_path: Path) -> PaperForgeProject:
    return PaperForgeProject.load(tmp_path)


# --- Check 11: METRIC_CLAIM_MISMATCH ---


def test_metric_claim_mismatch_detected(tmp_path: Path) -> None:
    """METRIC_CLAIM_MISMATCH is raised when claim % != experiment metric."""
    init.run(tmp_path)
    _write_experiment(
        tmp_path, Experiment(id="exp_01", metrics={"accuracy": 98.4})
    )
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="This model achieves 97.0% accuracy.",
            experiment="exp_01",
            status="unverified",
        ),
    )
    project = _load_project(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "METRIC_CLAIM_MISMATCH" for i in issues)


def test_metric_claim_no_mismatch_when_matches(tmp_path: Path) -> None:
    """METRIC_CLAIM_MISMATCH is NOT raised when claim % matches metric."""
    init.run(tmp_path)
    _write_experiment(
        tmp_path, Experiment(id="exp_01", metrics={"accuracy": 98.4})
    )
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="This model achieves 98.4% accuracy.",
            experiment="exp_01",
            status="unverified",
        ),
    )
    project = _load_project(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "METRIC_CLAIM_MISMATCH" for i in issues)


def test_metric_claim_skipped_when_no_percentages(tmp_path: Path) -> None:
    """METRIC_CLAIM_MISMATCH is NOT raised when claim has no percentage numbers."""
    init.run(tmp_path)
    _write_experiment(
        tmp_path, Experiment(id="exp_01", metrics={"accuracy": 98.4})
    )
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="We collected 500 samples.",
            experiment="exp_01",
            status="unverified",
        ),
    )
    project = _load_project(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "METRIC_CLAIM_MISMATCH" for i in issues)


# --- Check 12: DUPLICATE_CLAIM_TEXT ---


def test_duplicate_claim_text_detected(tmp_path: Path) -> None:
    """DUPLICATE_CLAIM_TEXT is raised when two claims share identical text."""
    init.run(tmp_path)
    for cid in ("claim_01", "claim_02"):
        _write_claim(
            tmp_path,
            Claim(id=cid, text="Same text here.", experiment="exp_01", status="unverified"),
            claim_id=cid,
        )
    project = _load_project(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "DUPLICATE_CLAIM_TEXT" for i in issues)


# --- Check 13: CLAIM_IN_NO_SECTION ---


def test_claim_in_no_section_detected(tmp_path: Path) -> None:
    """CLAIM_IN_NO_SECTION is raised when claim.sections is empty."""
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="A claim with no sections.",
            experiment="exp_01",
            sections=[],
            status="unverified",
        ),
    )
    project = _load_project(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "CLAIM_IN_NO_SECTION" for i in issues)


# --- Check 15: EXPERIMENT_NO_HARDWARE ---


def test_experiment_no_hardware_detected(tmp_path: Path) -> None:
    """EXPERIMENT_NO_HARDWARE is raised when hardware is None."""
    init.run(tmp_path)
    # exp_01 from init has hardware=None by default
    project = _load_project(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "EXPERIMENT_NO_HARDWARE" for i in issues)


# --- Check 17: EXPERIMENT_NO_SEED ---


def test_experiment_no_seed_detected(tmp_path: Path) -> None:
    """EXPERIMENT_NO_SEED is raised when seed is None."""
    init.run(tmp_path)
    # exp_01 from init has seed=None by default
    project = _load_project(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "EXPERIMENT_NO_SEED" for i in issues)


# --- Check 18: UNCLAIMED_EXPERIMENT ---


def test_unclaimed_experiment_detected(tmp_path: Path) -> None:
    """UNCLAIMED_EXPERIMENT is raised when no claim references an experiment."""
    init.run(tmp_path)
    # claim_01 from init has experiment="" — does not reference exp_01
    project = _load_project(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "UNCLAIMED_EXPERIMENT" for i in issues)


# --- Check 19: INVALID_FIGURE_ID ---


def test_invalid_figure_id_detected(tmp_path: Path) -> None:
    """INVALID_FIGURE_ID is raised when figure ID doesn't start with fig_."""
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="A claim.",
            experiment="exp_01",
            figures=["figure_1"],  # wrong convention
            status="unverified",
        ),
    )
    project = _load_project(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "INVALID_FIGURE_ID" for i in issues)


def test_valid_figure_id_no_issue(tmp_path: Path) -> None:
    """INVALID_FIGURE_ID is NOT raised when figure ID starts with fig_."""
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="A claim.",
            experiment="exp_01",
            figures=["fig_01"],  # correct convention
            status="unverified",
        ),
    )
    project = _load_project(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "INVALID_FIGURE_ID" for i in issues)
