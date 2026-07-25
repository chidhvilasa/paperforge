"""Tests for doctor checks 21-30 and INFO severity."""

from pathlib import Path

import yaml

from paperforge.commands import doctor, init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
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


def _set_paper_title_and_authors(tmp_path: Path) -> None:
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "A Great Paper"
    data["authors"] = ["Jane Doe"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def test_undefined_acronym_detected(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="VANET performance is tested.",
            experiment="exp_01",
            sections=["results"],
        ),
    )
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert any(i.code == "UNDEFINED_ACRONYM" for i in issues)


def test_defined_acronym_no_issue(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="Vehicular Ad Hoc Network (VANET) performance is tested.",
            experiment="exp_01",
            sections=["results"],
        ),
    )
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert not any(i.code == "UNDEFINED_ACRONYM" for i in issues)


def test_common_acronym_excluded(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="IEEE standards require compliance.",
            experiment="exp_01",
            sections=["results"],
        ),
    )
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert not any(i.code == "UNDEFINED_ACRONYM" for i in issues)


def test_abstract_too_long(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text=" ".join(["word"] * 260),
            experiment="exp_01",
            sections=["abstract", "results"],
        ),
    )
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert any(i.code == "ABSTRACT_TOO_LONG" for i in issues)


def test_abstract_too_short(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="Short abstract.",
            experiment="exp_01",
            sections=["abstract", "results"],
        ),
    )
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert any(i.code == "ABSTRACT_TOO_SHORT" for i in issues)


def test_no_conclusion_claims(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="A verified claim.",
            experiment="exp_01",
            sections=["results"],
        ),
    )
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert any(i.code == "NO_CONCLUSION_CLAIMS" for i in issues)


def test_results_section_empty_is_error(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="A verified claim.",
            experiment="exp_01",
            sections=["introduction"],
        ),
    )
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert any(i.code == "RESULTS_SECTION_EMPTY" for i in issues)
    assert (
        next(i for i in issues if i.code == "RESULTS_SECTION_EMPTY").severity
        == "ERROR"
    )


def test_evidence_coverage_info_always_present(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert any(i.code == "EVIDENCE_COVERAGE" for i in issues)
    info = next(i for i in issues if i.code == "EVIDENCE_COVERAGE")
    assert info.severity == "INFO"


def test_info_severity_does_not_affect_exit_code(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="A verified claim.",
            experiment="exp_01",
            sections=["results", "conclusion", "introduction"],
            status="verified",
        ),
    )
    _write_experiment(
        tmp_path,
        Experiment(id="exp_01", metrics={"accuracy": 98.4}),
    )
    _set_paper_title_and_authors(tmp_path)

    doctor.run(project_root=tmp_path, fix=False)


def test_claim_excessive_length(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text=" ".join(["word"] * 90),
            experiment="exp_01",
            sections=["results"],
        ),
    )
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert any(i.code == "CLAIM_EXCESSIVE_LENGTH" for i in issues)
