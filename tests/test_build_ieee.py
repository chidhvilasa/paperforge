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
    p = tmp_path / "paper" / "paper.tex"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return (tmp_path / ".paperforge" / "output" / "paper.tex").read_text(
        encoding="utf-8"
    )


def test_build_journal_creates_tex(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    assert (tmp_path / "paper" / "paper.tex").exists()


def test_build_journal_documentclass(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    assert content.splitlines()[0] == "\\documentclass[journal]{IEEEtran}"


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
    bib_path = tmp_path / "paper" / "references.bib"
    assert bib_path.exists()
    content = bib_path.read_text(encoding="utf-8")
    assert "smith2024" in content


def test_build_ieee_journal_target_alias(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-trans")
    content = _read_tex(tmp_path)
    assert "journal" in content


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


def test_build_author_not_double_wrapped(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    author_count = content.count("\\author{")
    assert author_count == 1, f"Expected \\author{{}} exactly once, found {author_count} times"
    assert "\\author{\\author" not in content


def test_build_table_label_appears_once(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    claim3_path = pf_dir / "claims" / "claim_03.yaml"
    claim3 = Claim(
        id="claim_03",
        text="The system maintains 98.4% accuracy across runs.",
        experiment="exp_01",
        figures=[],
        tables=["tbl_01"],
        citations=[],
        sections=["discussion"],
        status="verified",
    )
    claim3_path.write_text(
        yaml.dump(claim3.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    tbl_path = pf_dir / "tables" / "tbl_01.yaml"
    tbl_path.write_text(
        yaml.dump(
            {
                "id": "tbl_01",
                "caption": "Performance Comparison",
                "columns": ["Method", "Accuracy"],
                "rows": [["B2", "91.2%"], ["Ours", "98.4%"]],
                "notes": "",
                "first_mentioned_in": "results",
                "source_experiment": "exp_01",
            },
            default_flow_style=False,
        ),
        encoding="utf-8",
    )

    claim2_path = pf_dir / "claims" / "claim_02.yaml"
    claim2_data = yaml.safe_load(claim2_path.read_text(encoding="utf-8"))
    claim2_data["tables"] = ["tbl_01"]
    claim2_path.write_text(yaml.dump(claim2_data, default_flow_style=False), encoding="utf-8")

    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    label_count = content.count("\\label{tab:tbl_01}")
    assert label_count == 1, f"Expected \\label{{tab:tbl_01}} exactly once, found {label_count}"
    begin_table_count = content.count("\\begin{table}")
    assert begin_table_count == 1, f"Expected \\begin{{table}} exactly once, found {begin_table_count}"


def test_build_figure_label_appears_once(tmp_path: Path) -> None:
    write_journal_project(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    fig_path = pf_dir / "figures" / "fig_01.yaml"
    fig_path.write_text(
        yaml.dump(
            {
                "id": "fig_01",
                "caption": "System Architecture",
                "path": "figures/fig_01.png",
                "format": "png",
                "width_inches": 3.5,
                "resolution_dpi": 300,
                "first_mentioned_in": "results",
            },
            default_flow_style=False,
        ),
        encoding="utf-8",
    )

    claim2_path = pf_dir / "claims" / "claim_02.yaml"
    claim2_data = yaml.safe_load(claim2_path.read_text(encoding="utf-8"))
    claim2_data["figures"] = ["fig_01"]
    claim2_path.write_text(yaml.dump(claim2_data, default_flow_style=False), encoding="utf-8")

    claim3_path = pf_dir / "claims" / "claim_03.yaml"
    claim3 = Claim(
        id="claim_03",
        text="As shown above, latency decreases under high load.",
        experiment="exp_01",
        figures=["fig_01"],
        tables=[],
        citations=[],
        sections=["discussion"],
        status="verified",
    )
    claim3_path.write_text(
        yaml.dump(claim3.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    build.run(tmp_path, target="ieee-journal")
    content = _read_tex(tmp_path)
    label_count = content.count("\\label{fig:fig_01}")
    assert label_count == 1, f"Expected \\label{{fig:fig_01}} exactly once, found {label_count}"
    begin_figure_count = content.count("\\begin{figure}")
    assert begin_figure_count == 1, f"Expected \\begin{{figure}} exactly once, found {begin_figure_count}"


def test_build_conference_author_not_double_wrapped(tmp_path: Path) -> None:
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
    author_count = content.count("\\author{")
    assert author_count == 1
    assert "\\author{\\author" not in content


def test_build_preserves_real_references_bib(tmp_path: Path) -> None:
    write_journal_project(tmp_path)

    build.run(tmp_path, target="ieee-journal")

    bib_path = tmp_path / "paper" / "references.bib"
    bib_path.write_text(
        "@article{smith2024,\n"
        "  author = {Smith, A.},\n"
        "  title = {Real Title},\n"
        "  journal = {IEEE Access},\n"
        "  year = {2024}\n"
        "}\n",
        encoding="utf-8",
    )

    build.run(tmp_path, target="ieee-journal")

    content = bib_path.read_text(encoding="utf-8")
    assert "Real Title" in content
    assert "TODO" not in content


def test_build_overwrites_stub_references_bib(tmp_path: Path) -> None:
    write_journal_project(tmp_path)

    build.run(tmp_path, target="ieee-journal")
    build.run(tmp_path, target="ieee-journal")

    bib_path = tmp_path / "paper" / "references.bib"
    content = bib_path.read_text(encoding="utf-8")
    assert "@article" in content
