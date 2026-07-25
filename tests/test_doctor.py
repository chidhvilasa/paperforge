"""Tests for the paperforge doctor command."""

from pathlib import Path

import pytest
import yaml

from paperforge.commands import doctor, init
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _claim_path(tmp_path: Path, claim_id: str = "claim_01") -> Path:
    return tmp_path / ".paperforge" / "claims" / f"{claim_id}.yaml"


def _experiment_path(tmp_path: Path, experiment_id: str = "exp_01") -> Path:
    return tmp_path / ".paperforge" / "experiments" / f"{experiment_id}.yaml"


def _write_claim(path: Path, claim: Claim) -> None:
    path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _write_experiment(path: Path, experiment: Experiment) -> None:
    path.write_text(
        yaml.dump(experiment.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _set_paper_title_and_authors(tmp_path: Path) -> None:
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "A Great Paper"
    data["authors"] = ["Jane Doe"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def test_doctor_passes_clean_project(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_claim(
        _claim_path(tmp_path),
        Claim(
            id="claim_01",
            text="A verified claim.",
            experiment="exp_01",
            status="verified",
        ),
    )
    _write_experiment(
        _experiment_path(tmp_path),
        Experiment(id="exp_01", metrics={"accuracy": 98.4}),
    )
    _set_paper_title_and_authors(tmp_path)

    doctor.run(project_root=tmp_path, fix=False)


def test_doctor_error_orphan_claim(tmp_path: Path) -> None:
    init.run(tmp_path)
    claim_path = _claim_path(tmp_path)
    claim = Claim.from_yaml(yaml.safe_load(claim_path.read_text(encoding="utf-8")))
    claim.experiment = ""
    _write_claim(claim_path, claim)

    with pytest.raises(SystemExit) as exc_info:
        doctor.run(project_root=tmp_path, fix=False)
    assert exc_info.value.code == 1


def test_doctor_error_missing_experiment(tmp_path: Path) -> None:
    init.run(tmp_path)
    claim_path = _claim_path(tmp_path)
    claim = Claim.from_yaml(yaml.safe_load(claim_path.read_text(encoding="utf-8")))
    claim.experiment = "exp_nonexistent"
    _write_claim(claim_path, claim)
    _experiment_path(tmp_path).unlink()

    with pytest.raises(SystemExit) as exc_info:
        doctor.run(project_root=tmp_path, fix=False)
    assert exc_info.value.code == 1


def test_doctor_error_stale_claim(tmp_path: Path) -> None:
    init.run(tmp_path)
    claim_path = _claim_path(tmp_path)
    claim = Claim.from_yaml(yaml.safe_load(claim_path.read_text(encoding="utf-8")))
    claim.status = "stale"
    _write_claim(claim_path, claim)

    with pytest.raises(SystemExit) as exc_info:
        doctor.run(project_root=tmp_path, fix=False)
    assert exc_info.value.code == 1


def test_doctor_error_empty_claim_text(tmp_path: Path) -> None:
    init.run(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        doctor.run(project_root=tmp_path, fix=False)
    assert exc_info.value.code == 1


def test_doctor_warning_unverified_does_not_block(tmp_path: Path) -> None:
    init.run(tmp_path)
    claim_path = _claim_path(tmp_path)
    claim = Claim.from_yaml(yaml.safe_load(claim_path.read_text(encoding="utf-8")))
    claim.text = "A claim awaiting verification."
    claim.experiment = "exp_01"
    _write_claim(claim_path, claim)
    _set_paper_title_and_authors(tmp_path)

    doctor.run(project_root=tmp_path, fix=False)


def test_doctor_warning_empty_metrics(tmp_path: Path) -> None:
    init.run(tmp_path)
    claim_path = _claim_path(tmp_path)
    _write_claim(
        claim_path,
        Claim(
            id="claim_01",
            text="A verified claim.",
            experiment="exp_01",
            status="verified",
        ),
    )
    _set_paper_title_and_authors(tmp_path)

    doctor.run(project_root=tmp_path, fix=False)


def test_doctor_warning_no_claims(tmp_path: Path) -> None:
    init.run(tmp_path)
    _claim_path(tmp_path).unlink()

    doctor.run(project_root=tmp_path, fix=False)


def test_doctor_warning_missing_title(tmp_path: Path) -> None:
    init.run(tmp_path)
    claim_path = _claim_path(tmp_path)
    _write_claim(
        claim_path,
        Claim(
            id="claim_01",
            text="A verified claim.",
            experiment="exp_01",
            status="verified",
        ),
    )
    _write_experiment(
        _experiment_path(tmp_path),
        Experiment(id="exp_01", metrics={"accuracy": 98.4}),
    )

    doctor.run(project_root=tmp_path, fix=False)


def test_doctor_fix_sets_unverified_to_stale(tmp_path: Path) -> None:
    init.run(tmp_path)
    claim_path = _claim_path(tmp_path)
    claim = Claim.from_yaml(yaml.safe_load(claim_path.read_text(encoding="utf-8")))
    claim.text = "A claim awaiting verification."
    claim.experiment = "exp_01"
    claim.sections = ["results"]
    _write_claim(claim_path, claim)

    doctor.run(project_root=tmp_path, fix=True)

    fixed = Claim.from_yaml(yaml.safe_load(claim_path.read_text(encoding="utf-8")))
    assert fixed.status == "stale"


def test_doctor_fails_without_init(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        doctor.run(project_root=tmp_path)
    assert exc_info.value.code == 1


def test_doctor_multiple_errors_all_reported(tmp_path: Path) -> None:
    init.run(tmp_path)
    claims_dir = tmp_path / ".paperforge" / "claims"
    _write_claim(
        claims_dir / "claim_01.yaml",
        Claim(id="claim_01", text="", experiment=""),
    )
    _write_claim(
        claims_dir / "claim_02.yaml",
        Claim(id="claim_02", text="", experiment=""),
    )

    with pytest.raises(SystemExit) as exc_info:
        doctor.run(project_root=tmp_path, fix=False)
    assert exc_info.value.code == 1
