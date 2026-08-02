"""Regression test fixture for VANET 2026-07 failed build issues."""

from pathlib import Path

import pytest
import yaml

from paperforge.commands import build, init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.models.citation import Citation
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _init_project(tmp_path: Path) -> None:
    init.run(tmp_path)


def test_regression_author_identity_inconsistent(tmp_path: Path) -> None:
    """Detect author identity inconsistency between metadata family_name and biography."""
    _init_project(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["authors"] = [
        {
            "given_name": "Alex",
            "family_name": "Example",
            "display_name": "Alex Example",
            "biography": "Alex Sample received the B.Tech degree.",
        }
    ]
    paper_yaml.write_text(yaml.dump(data), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "AUTHOR_IDENTITY_INCONSISTENT" for i in issues)


def test_regression_isolated_i_artifact(tmp_path: Path) -> None:
    """Detect isolated 'I' artifact in claim text."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    claim = Claim(
        id="c_art",
        text="The system I described in section II.",
        experiment="exp_01",
        sections=["results"],
    )
    (pf / "claims" / "c_art.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "LATEX_ARTIFACT_IN_CLAIM" for i in issues)


def test_regression_citation_internal_note(tmp_path: Path) -> None:
    """Detect internal research commentary in citation notes."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    cit = Citation(
        key="smith2024",
        title="Sample Paper",
        authors=["Smith, A."],
        year=2024,
        notes="not a precise source - unconfirmed values",
    )
    (pf / "citations" / "smith2024.yaml").write_text(yaml.dump(cit.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "CITATION_HAS_INTERNAL_NOTE" for i in issues)


def test_regression_pvalue_ambiguous(tmp_path: Path) -> None:
    """Detect single p-value attached to multiple metrics in a claim."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    claim = Claim(
        id="c_pv",
        text="The latency improved 73.6% and PDR by 5% (p=0.002).",
        experiment="exp_01",
        sections=["results"],
    )
    (pf / "claims" / "c_pv.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "PVALUE_AMBIGUOUS" for i in issues)


def test_regression_claim_constraint_violated(tmp_path: Path) -> None:
    """Detect claim constraint violation against experiment metrics."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    exp = Experiment(id="exp_01", metrics={"adaptive_pdr": 0.43})
    (pf / "experiments" / "exp_01.yaml").write_text(yaml.dump(exp.to_yaml()), encoding="utf-8")

    claim = Claim(
        id="c_con",
        text="Adaptive PDR satisfies target threshold.",
        experiment="exp_01",
        sections=["results"],
        permitted_only_if=["adaptive_pdr >= 0.95"],
    )
    (pf / "claims" / "c_con.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "CLAIM_CONSTRAINT_VIOLATED" for i in issues)


def test_regression_significance_mismatch(tmp_path: Path) -> None:
    """Detect non-significance language framed as positive improvement."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    claim = Claim(
        id="c_sig",
        text="The improvement is statistically indistinguishable but better than baseline.",
        experiment="exp_01",
        sections=["results"],
    )
    (pf / "claims" / "c_sig.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "SIGNIFICANCE_LANGUAGE_MISMATCH" for i in issues)


def test_regression_required_placeholder(tmp_path: Path) -> None:
    """Detect [REQUIRED INFORMATION MISSING: ...] placeholder in claim text."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    claim = Claim(
        id="c_req",
        text="Batch timeout is [REQUIRED INFORMATION MISSING: batch timeout].",
        experiment="exp_01",
        sections=["results"],
    )
    (pf / "claims" / "c_req.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "REQUIRED_PLACEHOLDER_IN_CLAIM" for i in issues)


def test_regression_build_blocked_submission_mode(tmp_path: Path) -> None:
    """Submission mode blocks build when AUTHOR_NAME_INCOMPLETE error is present."""
    _init_project(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["authors"] = [{"given_name": "", "family_name": "", "display_name": ""}]
    paper_yaml.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        build.run(tmp_path, mode="submission")
    assert exc.value.code == 1


def test_regression_draft_mode_allows_warnings(tmp_path: Path, monkeypatch) -> None:
    """Draft mode allows build when only WARNING issues exist."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    exp = Experiment(id="exp_01", metrics={"accuracy": 98.4})
    (pf / "experiments" / "exp_01.yaml").write_text(yaml.dump(exp.to_yaml()), encoding="utf-8")
    claim = Claim(
        id="claim_01",
        text="System achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results"],
        status="verified",
    )
    (pf / "claims" / "claim_01.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    monkeypatch.setattr("shutil.which", lambda name: None)
    # Draft mode should not raise
    build.run(tmp_path, mode="draft")


def test_regression_submission_mode_blocks_more(tmp_path: Path, monkeypatch) -> None:
    """Submission mode blocks on issues like METRIC_CLAIM_MISMATCH that draft mode allows."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    exp = Experiment(id="exp_01", metrics={"accuracy": 50.0})
    (pf / "experiments" / "exp_01.yaml").write_text(yaml.dump(exp.to_yaml()), encoding="utf-8")
    claim = Claim(
        id="claim_01",
        text="System achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results"],
        status="verified",
    )
    (pf / "claims" / "claim_01.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    monkeypatch.setattr("shutil.which", lambda name: None)

    # Draft mode does NOT raise on METRIC_CLAIM_MISMATCH (it is warning in draft)
    build.run(tmp_path, mode="draft")

    # Submission mode DOES raise on METRIC_CLAIM_MISMATCH
    with pytest.raises(SystemExit) as exc:
        build.run(tmp_path, mode="submission")
    assert exc.value.code == 1


def test_regression_raw_latex_escape_corruption(tmp_path: Path) -> None:
    """Detect malformed control sequences like extbf{Low} in claim text."""
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    claim = Claim(
        id="c_bad_esc",
        text="The latency is extbf{Low} under high load.",
        experiment="exp_01",
        sections=["results"],
    )
    (pf / "claims" / "c_bad_esc.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "RAW_LATEX_ESCAPE_CORRUPTION" for i in issues)


def test_regression_venue_template_mismatch(tmp_path: Path) -> None:
    """Detect template fingerprint mismatch when wrong template class is generated."""
    _init_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    # Default initialized project is ieee-access but generated tex may lack IEEE Access specific markers
    assert any(i.code in ("VENUE_TEMPLATE_MISMATCH", "VENUE_TEMPLATE_UNVERIFIED") for i in issues)
