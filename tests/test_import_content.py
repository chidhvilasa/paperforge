"""Tests for paper_information/ input layer and import command."""

from pathlib import Path

import yaml

from paperforge.commands import build, import_content, init
from paperforge.core.project import PaperForgeProject


def setup_valid_project(tmp_path: Path) -> None:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    pdata = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    pdata["title"] = "Valid Test Title"
    pdata["authors"] = ["Author One"]
    pdata["email"] = "author@example.com"
    pdata["sections_overview"] = "Related Work in Section II."
    paper_yaml.write_text(yaml.dump(pdata), encoding="utf-8")

    exp_yaml = tmp_path / ".paperforge" / "experiments" / "exp_01.yaml"
    edata = yaml.safe_load(exp_yaml.read_text(encoding="utf-8"))
    edata["description"] = "Reproducible test experiment."
    edata["metrics"] = {"accuracy": 98.4}
    exp_yaml.write_text(yaml.dump(edata), encoding="utf-8")

    claim_yaml = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    cdata = yaml.safe_load(claim_yaml.read_text(encoding="utf-8"))
    cdata["text"] = "Primary results claim text."
    cdata["experiment"] = "exp_01"
    cdata["sections"] = ["results"]
    cdata["status"] = "verified"
    claim_yaml.write_text(yaml.dump(cdata), encoding="utf-8")


def test_init_creates_paper_information_dir(tmp_path: Path) -> None:
    init.run(tmp_path)
    assert (tmp_path / "paper_information").is_dir()


def test_init_creates_content_sections(tmp_path: Path) -> None:
    init.run(tmp_path)
    content_dir = tmp_path / "paper_information" / "content"
    expected_files = [
        "abstract.md",
        "introduction.md",
        "related_work.md",
        "methodology.md",
        "experiments.md",
        "results.md",
        "discussion.md",
        "conclusion.md",
    ]
    for fname in expected_files:
        assert (content_dir / fname).exists()


def test_init_creates_author_yaml(tmp_path: Path) -> None:
    init.run(tmp_path)
    assert (tmp_path / "paper_information" / "author.yaml").exists()


def test_init_creates_metadata_yaml(tmp_path: Path) -> None:
    init.run(tmp_path)
    assert (tmp_path / "paper_information" / "metadata.yaml").exists()


def test_import_metadata_updates_paper_yaml(tmp_path: Path) -> None:
    init.run(tmp_path)
    meta_path = tmp_path / "paper_information" / "metadata.yaml"
    meta_data = {
        "title": "Imported Paper Title",
        "venue": "IEEE Access",
        "keywords": ["example-topic", "security"],
    }
    meta_path.write_text(yaml.dump(meta_data), encoding="utf-8")

    import_content.run(tmp_path, section=None)
    project = PaperForgeProject.load(tmp_path)
    assert project.config.title == "Imported Paper Title"
    assert project.config.venue == "IEEE Access"


def test_import_abstract_creates_claim(tmp_path: Path) -> None:
    init.run(tmp_path)
    abs_md = tmp_path / "paper_information" / "content" / "abstract.md"
    abs_md.write_text("# Abstract\n\nThis is a test abstract paragraph.", encoding="utf-8")

    import_content.run(tmp_path, section="abstract")
    project = PaperForgeProject.load(tmp_path)
    abs_claims = [c for c in project.claims if "abstract" in c.sections]
    assert len(abs_claims) >= 1
    assert "test abstract paragraph" in abs_claims[0].text.lower()


def test_import_does_not_duplicate_existing_claims(tmp_path: Path) -> None:
    init.run(tmp_path)
    abs_md = tmp_path / "paper_information" / "content" / "abstract.md"
    abs_md.write_text("# Abstract\n\nUnique test paragraph for deduplication.", encoding="utf-8")

    import_content.run(tmp_path, section="abstract")
    project1 = PaperForgeProject.load(tmp_path)
    count1 = len(project1.claims)

    import_content.run(tmp_path, section="abstract")
    project2 = PaperForgeProject.load(tmp_path)
    count2 = len(project2.claims)

    assert count1 == count2


def test_import_contribution_claims(tmp_path: Path) -> None:
    init.run(tmp_path)
    intro_md = tmp_path / "paper_information" / "content" / "introduction.md"
    intro_text = (
        "# Introduction\n\n"
        "## Contributions\n"
        "- First contribution here\n"
        "- Second contribution here\n"
    )
    intro_md.write_text(intro_text, encoding="utf-8")

    import_content.run(tmp_path, section="introduction")
    project = PaperForgeProject.load(tmp_path)
    contrib = [c for c in project.claims if c.is_contribution]
    assert len(contrib) == 2


def test_import_csv_table(tmp_path: Path) -> None:
    init.run(tmp_path)
    csv_file = tmp_path / "paper_information" / "tables" / "results.csv"
    csv_file.write_text("Method,Accuracy,Latency\nB2,91.2,271.72\nAdaptive,98.4,71.86\n", encoding="utf-8")

    import_content.run(tmp_path, section=None)
    project = PaperForgeProject.load(tmp_path)
    tbl = next((t for t in project.tables if t.id == "results"), None)
    assert tbl is not None
    assert tbl.columns == ["Method", "Accuracy", "Latency"]
    assert len(tbl.rows) == 2


def test_paper_generated_versioned_output(tmp_path: Path) -> None:
    setup_valid_project(tmp_path)
    build.run(tmp_path, target="ieee", force=True, no_reveal=True)

    # Modify claim text
    claim_path = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    cdata = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    cdata["text"] = "Modified claim text for versioning test."
    claim_path.write_text(yaml.dump(cdata), encoding="utf-8")

    build.run(tmp_path, target="ieee", force=True, no_reveal=True)
    assert (tmp_path / "paper_generated" / "previous" / "paper.tex").exists()
    assert (tmp_path / "paper_generated" / "current" / "paper.tex").exists()
