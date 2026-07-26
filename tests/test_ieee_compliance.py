"""Tests for IEEE Compliance Overhaul."""

from pathlib import Path

import yaml

from paperforge.commands import build, init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject


def _read_tex(tmp_path: Path) -> str:
    p = tmp_path / "paper" / "paper.tex"
    return p.read_text(encoding="utf-8")


def test_funding_field_in_config(tmp_path: Path) -> None:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["funding"] = "This work was supported by X."
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    assert project.config.funding == "This work was supported by X."


def test_funding_appears_in_thanks_block(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    paper_yaml = pf_dir / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "Valid IEEE Title"
    data["authors"] = ["Alice Smith"]
    data["email"] = "alice@example.com"
    data["funding"] = "This work was supported by NSF"
    data["conflict_of_interest"] = "None."
    data["data_availability"] = "Available on request."
    data["keywords"] = ["alpha", "beta", "gamma", "delta"]
    data["sections"] = ["abstract", "introduction", "results", "conclusion"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: 'Results paragraph.'\nexperiment: exp_01\nsections: [results]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_intro.yaml").write_text(
        "id: claim_intro\ntext: 'Motivation text.'\nexperiment: exp_01\nsections: [introduction]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_conc.yaml").write_text(
        "id: claim_conc\ntext: 'Conclusion text.'\nexperiment: exp_01\nsections: [conclusion]\nstatus: verified\n",
        encoding="utf-8",
    )

    build.run(tmp_path, target="ieee-access", no_reveal=True)
    content = _read_tex(tmp_path)
    assert "This work was supported by NSF" in content


def test_email_in_author_block(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    paper_yaml = pf_dir / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "Valid Title"
    data["authors"] = ["Bob Jones"]
    data["email"] = "test@vit.ac.in"
    data["affiliations"] = [{"name": "CSE", "institution": "VIT", "city": "Vellore", "country": "India"}]
    data["conflict_of_interest"] = "None."
    data["data_availability"] = "Available."
    data["keywords"] = ["a", "b", "c", "d"]
    data["sections"] = ["abstract", "introduction", "results", "conclusion"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: 'Res.'\nexperiment: exp_01\nsections: [results]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_intro.yaml").write_text(
        "id: claim_intro\ntext: 'Intro.'\nexperiment: exp_01\nsections: [introduction]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_conc.yaml").write_text(
        "id: claim_conc\ntext: 'Conc.'\nexperiment: exp_01\nsections: [conclusion]\nstatus: verified\n",
        encoding="utf-8",
    )

    build.run(tmp_path, target="ieee-access", no_reveal=True)
    content = _read_tex(tmp_path)
    assert "test@vit.ac.in" in content


def test_conflict_of_interest_emitted(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    paper_yaml = pf_dir / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "Title"
    data["authors"] = ["A. Author"]
    data["email"] = "a@example.com"
    data["conflict_of_interest"] = "No conflicts."
    data["data_availability"] = "Public."
    data["keywords"] = ["a", "b", "c", "d"]
    data["sections"] = ["abstract", "introduction", "results", "conclusion"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: 'Res.'\nexperiment: exp_01\nsections: [results]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_intro.yaml").write_text(
        "id: claim_intro\ntext: 'Intro.'\nexperiment: exp_01\nsections: [introduction]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_conc.yaml").write_text(
        "id: claim_conc\ntext: 'Conc.'\nexperiment: exp_01\nsections: [conclusion]\nstatus: verified\n",
        encoding="utf-8",
    )

    build.run(tmp_path, target="ieee-access", no_reveal=True)
    content = _read_tex(tmp_path)
    assert "Conflict of Interest" in content
    assert "No conflicts." in content


def test_missing_coi_fires_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "MISSING_COI" and i.severity == "WARNING" for i in issues)


def test_missing_data_availability_fires_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "MISSING_DATA_AVAILABILITY" and i.severity == "WARNING" for i in issues)


def test_abstract_has_citation_fires_error(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: 'Abstract claim.'\nexperiment: exp_01\nsections: [abstract]\ncitations: [smith2024]\nstatus: verified\n",
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    matching = [i for i in issues if i.code == "ABSTRACT_HAS_CITATION"]
    assert matching
    assert matching[0].severity == "ERROR"


def test_keywords_alphabetical_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["keywords"] = ["zebra", "apple", "mango"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "KEYWORDS_NOT_ALPHABETICAL" for i in issues)


def test_keywords_alphabetical_no_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["keywords"] = ["apple", "mango", "zebra"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "KEYWORDS_NOT_ALPHABETICAL" for i in issues)


def test_too_few_keywords_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["keywords"] = ["one", "two"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "TOO_FEW_KEYWORDS" for i in issues)


def test_too_many_keywords_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["keywords"] = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "TOO_MANY_KEYWORDS" for i in issues)


def test_table_notes_internal_ref_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    tbl_path = tmp_path / ".paperforge" / "tables" / "tbl_01.yaml"
    tbl_path.write_text(
        "id: tbl_01\ncaption: Cap\ncolumns: [A]\nrows: [[1]]\nnotes: 'See results/tables/data.json for details.'\n",
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "TABLE_NOTES_INTERNAL_REF" for i in issues)


def test_table_notes_clean_no_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    tbl_path = tmp_path / ".paperforge" / "tables" / "tbl_01.yaml"
    tbl_path.write_text(
        "id: tbl_01\ncaption: Cap\ncolumns: [A]\nrows: [[1]]\nnotes: 'n.s. = not significant at alpha=0.05.'\n",
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "TABLE_NOTES_INTERNAL_REF" for i in issues)


def test_abstract_intro_overlap_error(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: 'Shared text.'\nexperiment: exp_01\nsections: [abstract, introduction]\nstatus: verified\n",
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    matching = [i for i in issues if i.code == "ABSTRACT_INTRO_OVERLAP"]
    assert matching
    assert matching[0].severity == "ERROR"


def test_duplicate_citation_key_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: 'Dup cit.'\nexperiment: exp_01\nsections: [results]\ncitations: [smith2024, smith2024]\nstatus: verified\n",
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "DUPLICATE_CITATION_KEY" for i in issues)


def test_title_ends_with_period_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "My Paper Title."
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "TITLE_ENDS_WITH_PERIOD" for i in issues)


def test_title_too_long_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = " ".join(["word"] * 16)
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "TITLE_TOO_LONG" for i in issues)


def test_missing_email_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "MISSING_CORRESPONDING_EMAIL" for i in issues)


def test_orcid_info_when_missing(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    matching = [i for i in issues if i.code == "MISSING_ORCID"]
    assert matching
    assert matching[0].severity == "INFO"


def test_bibliography_command_format(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    paper_yaml = pf_dir / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "Valid Title"
    data["authors"] = ["A. Author"]
    data["email"] = "a@example.com"
    data["conflict_of_interest"] = "None."
    data["data_availability"] = "Available."
    data["keywords"] = ["a", "b", "c", "d"]
    data["sections"] = ["abstract", "introduction", "results", "conclusion"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: 'Res.'\nexperiment: exp_01\nsections: [results]\ncitations: [ref1]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_intro.yaml").write_text(
        "id: claim_intro\ntext: 'Intro.'\nexperiment: exp_01\nsections: [introduction]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_conc.yaml").write_text(
        "id: claim_conc\ntext: 'Conc.'\nexperiment: exp_01\nsections: [conclusion]\nstatus: verified\n",
        encoding="utf-8",
    )

    build.run(tmp_path, target="ieee-access", no_reveal=True)
    content = _read_tex(tmp_path)
    assert "\\bibliography{references}" in content
    assert "\\bibliography{paper/references}" not in content
    assert "\\bibliography{references.bib}" not in content
