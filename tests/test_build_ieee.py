"""Tests for the IEEE Transactions / journal LaTeX build template."""

from pathlib import Path

import yaml

from paperforge.commands import build, init
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def write_journal_project(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    (pf_dir / "claims" / "claim_01.yaml").unlink()

    paper_yaml = pf_dir / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "Test Paper"
    data["authors"] = ["A. Author"]
    data["paper_type"] = "journal"
    data["keywords"] = ["security", "IoT"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    exp_path = pf_dir / "experiments" / "exp_01.yaml"
    experiment = Experiment(
        id="exp_01",
        description="Test experiment",
        metrics={"accuracy": 98.4},
        hardware="RTX 4070",
        dataset="TestSet",
        seed=42,
    )
    exp_path.write_text(
        yaml.dump(experiment.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    claim_path = pf_dir / "claims" / "claim_02.yaml"
    claim = Claim(
        id="claim_02",
        text="The system achieves 98.4% accuracy.",
        experiment="exp_01",
        citations=["smith2024"],
        sections=["abstract", "results", "introduction"],
        status="verified",
    )
    claim_path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _read_tex(tmp_path: Path) -> str:
    return (tmp_path / ".paperforge" / "output" / "paper.tex").read_text(
        encoding="utf-8"
    )


def test_build_journal_creates_tex(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    assert (tmp_path / ".paperforge" / "output" / "paper.tex").exists()


def test_build_journal_documentclass(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    assert "journal,compsoc" in content


def test_build_journal_abstract_in_titleabstractindextext(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    assert "IEEEtitleabstractindextext" in content
    assert "begin{abstract}" in content


def test_build_journal_ieeeraisesectionheading(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    assert "IEEEraisesectionheading" in content


def test_build_journal_ieeeparstart(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    assert "IEEEPARstart" in content


def test_build_journal_ieeedisplaynontitleabstractindextext(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    assert "IEEEdisplaynontitleabstractindextext" in content


def test_build_journal_keywords(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    assert "IEEEkeywords" in content
    assert "security" in content


def test_build_journal_acknowledgment(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    assert "Acknowledgments" in content
    assert "ifCLASSOPTIONcompsoc" in content


def test_build_journal_bibliography_stub(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    bib_path = tmp_path / ".paperforge" / "output" / "references.bib"
    assert bib_path.exists()
    content = bib_path.read_text(encoding="utf-8")
    assert "smith2024" in content


def test_build_ieee_journal_target_alias(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-trans")
    content = _read_tex(tmp_path)
    assert "journal,compsoc" in content


def test_build_conference_unchanged(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    claim_path = pf_dir / "claims" / "claim_01.yaml"
    claim = Claim(
        id="claim_01",
        text="This model achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results"],
        status="verified",
    )
    claim_path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    exp_path = pf_dir / "experiments" / "exp_01.yaml"
    experiment = Experiment(id="exp_01", metrics={"accuracy": 98.4})
    exp_path.write_text(
        yaml.dump(experiment.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    paper_yaml = pf_dir / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "Test Paper Title"
    data["authors"] = ["Test Author"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    build.run(tmp_path, target="ieee")

    content = _read_tex(tmp_path)
    assert "conference" in content
    assert "IEEEtitleabstractindextext" not in content


def test_build_paper_type_journal_auto_selects_journal_template(
    tmp_path: Path,
) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
