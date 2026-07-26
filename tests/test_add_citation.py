from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from paperforge.commands.add_citation import run as run_add_citation
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject


def test_add_citation_creates_yaml(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    pf_dir.mkdir()
    (pf_dir / "paper.yaml").write_text(
        "title: T\nauthors: []\nsections: [results]\n", encoding="utf-8"
    )

    prompts = [
        "article",  # Type
        "Smith, Alice; Jones, Bob",  # Authors
        "Adaptive Auth",  # Title
        "2024",  # Year
        "IEEE Access",  # Venue
        "12",  # Volume
        "1",  # Issue
        "100--110",  # Pages
        "10.1109/x",  # DOI
        "Note",  # Notes
    ]
    with patch("typer.prompt", side_effect=prompts):
        run_add_citation(tmp_path, "smith2024")

    yaml_path = tmp_path / ".paperforge" / "citations" / "smith2024.yaml"
    assert yaml_path.exists()
    content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert content["key"] == "smith2024"
    assert content["authors"] == ["Smith, Alice", "Jones, Bob"]
    assert content["year"] == 2024
    assert content["doi"] == "10.1109/x"


def test_add_citation_parses_authors(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    pf_dir.mkdir()
    (pf_dir / "paper.yaml").write_text(
        "title: T\nauthors: []\nsections: [results]\n", encoding="utf-8"
    )

    prompts = [
        "article",
        "Smith, A.; Jones, B.",
        "Title",
        "2024",
        "Venue",
        "",
        "",
        "",
        "",
        "",
    ]
    with patch("typer.prompt", side_effect=prompts):
        run_add_citation(tmp_path, "s24")

    yaml_path = tmp_path / ".paperforge" / "citations" / "s24.yaml"
    content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert content["authors"] == ["Smith, A.", "Jones, B."]


def test_add_citation_parses_year(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    pf_dir.mkdir()
    (pf_dir / "paper.yaml").write_text(
        "title: T\nauthors: []\nsections: [results]\n", encoding="utf-8"
    )

    prompts = ["article", "", "Title", "2024", "", "", "", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        run_add_citation(tmp_path, "s24")

    yaml_path = tmp_path / ".paperforge" / "citations" / "s24.yaml"
    content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert content["year"] == 2024


def test_add_citation_invalid_year_gives_none(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    pf_dir.mkdir()
    (pf_dir / "paper.yaml").write_text(
        "title: T\nauthors: []\nsections: [results]\n", encoding="utf-8"
    )

    prompts = ["article", "", "Title", "not_a_year", "", "", "", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        run_add_citation(tmp_path, "s24")

    yaml_path = tmp_path / ".paperforge" / "citations" / "s24.yaml"
    content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert content["year"] is None


def test_add_citation_empty_authors_gives_empty_list(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    pf_dir.mkdir()
    (pf_dir / "paper.yaml").write_text(
        "title: T\nauthors: []\nsections: [results]\n", encoding="utf-8"
    )

    prompts = ["article", "", "Title", "2024", "", "", "", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        run_add_citation(tmp_path, "s24")

    yaml_path = tmp_path / ".paperforge" / "citations" / "s24.yaml"
    content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert content["authors"] == []


def test_add_citation_fails_without_init(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run_add_citation(tmp_path, "x")
    assert exc_info.value.code == 1


def test_doctor_cited_key_no_yaml(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims").mkdir(parents=True)
    (pf_dir / "experiments").mkdir(parents=True)
    (pf_dir / "paper.yaml").write_text(
        "title: T\nauthors: [A]\nsections: [results]\n", encoding="utf-8"
    )
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        "id: exp_01\ndescription: D\nmetrics: {acc: 90}\nhardware: H\ndataset: D\nseed: 42\nresults_file: r.json\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: Claim text 90%\nexperiment: exp_01\nsections: [results]\ncitations: [ghost2024]\nstatus: verified\n",
        encoding="utf-8",
    )

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "CITED_KEY_NO_YAML" for i in issues)


def test_doctor_citation_no_title_is_error(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "citations").mkdir(parents=True)
    (pf_dir / "paper.yaml").write_text(
        "title: T\nauthors: [A]\nsections: [results]\n", encoding="utf-8"
    )
    (pf_dir / "citations" / "notitle2024.yaml").write_text(
        "key: notitle2024\ntitle: ''\ntype: article\n", encoding="utf-8"
    )

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    issue = next(i for i in issues if i.code == "CITATION_NO_TITLE")
    assert issue.severity == "ERROR"
