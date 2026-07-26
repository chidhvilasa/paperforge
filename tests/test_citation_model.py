from pathlib import Path

from paperforge.commands.build import run as run_build
from paperforge.core.project import PaperForgeProject
from paperforge.models.citation import Citation


def test_citation_round_trip_full() -> None:
    cit = Citation(
        key="smith2024",
        type="article",
        authors=["Smith, A.", "Jones, B."],
        title="Adaptive Authentication in VANETs",
        year=2024,
        venue="IEEE Access",
        volume="12",
        number="4",
        pages="12345--12360",
        doi="10.1109/ACCESS.2024.123456",
        url="https://doi.org/10.1109/ACCESS.2024.123456",
        publisher="IEEE",
        institution="VIT",
        notes="Key reference",
    )
    data = cit.to_yaml()
    restored = Citation.from_yaml(data)
    assert restored == cit


def test_citation_round_trip_minimal() -> None:
    cit = Citation(key="smith2024")
    data = cit.to_yaml()
    restored = Citation.from_yaml(data)
    assert restored.key == "smith2024"
    assert restored.type == "article"
    assert restored.authors == []
    assert restored.title == ""
    assert restored.year is None
    assert restored.venue == ""
    assert restored.volume == ""
    assert restored.number == ""
    assert restored.pages == ""
    assert restored.doi == ""
    assert restored.url == ""
    assert restored.publisher == ""
    assert restored.institution == ""
    assert restored.notes == ""


def test_citation_to_bibtex_article() -> None:
    cit = Citation(
        key="s24",
        type="article",
        authors=["Smith, A."],
        title="Test Paper",
        venue="IEEE Access",
        year=2024,
        doi="10.1109/x",
    )
    bib = cit.to_bibtex()
    assert "@article{s24," in bib
    assert "Smith, A." in bib
    assert "IEEE Access" in bib
    assert "10.1109/x" in bib


def test_citation_to_bibtex_inproceedings() -> None:
    cit = Citation(
        key="j23",
        type="inproceedings",
        authors=["Jones, B."],
        title="A Paper",
        venue="Proc. IEEE INFOCOM",
        year=2023,
    )
    bib = cit.to_bibtex()
    assert "@inproceedings{j23," in bib
    assert "booktitle" in bib


def test_citation_to_bibtex_omits_empty_fields() -> None:
    cit = Citation(
        key="x",
        type="article",
        authors=["A, B"],
        title="T",
        year=2024,
    )
    bib = cit.to_bibtex()
    assert "volume" not in bib
    assert "pages" not in bib
    assert "doi" not in bib


def test_project_loads_citations(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    pf_dir.mkdir()
    (pf_dir / "paper.yaml").write_text(
        "title: T\nauthors: []\nsections: [results]\n", encoding="utf-8"
    )
    cit_dir = pf_dir / "citations"
    cit_dir.mkdir()
    (cit_dir / "smith2024.yaml").write_text(
        "key: smith2024\ntitle: Real Title\ntype: article\n", encoding="utf-8"
    )

    project = PaperForgeProject.load(tmp_path)
    assert len(project.citations) == 1
    assert project.citations[0].key == "smith2024"


def test_project_citation_count(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    pf_dir.mkdir()
    (pf_dir / "paper.yaml").write_text(
        "title: T\nauthors: []\nsections: [results]\n", encoding="utf-8"
    )
    cit_dir = pf_dir / "citations"
    cit_dir.mkdir()
    (cit_dir / "smith2024.yaml").write_text(
        "key: smith2024\ntitle: Title 1\n", encoding="utf-8"
    )
    (cit_dir / "jones2023.yaml").write_text(
        "key: jones2023\ntitle: Title 2\n", encoding="utf-8"
    )

    project = PaperForgeProject.load(tmp_path)
    assert project.citation_count == 2


def test_project_citation_map(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    pf_dir.mkdir()
    (pf_dir / "paper.yaml").write_text(
        "title: T\nauthors: []\nsections: [results]\n", encoding="utf-8"
    )
    cit_dir = pf_dir / "citations"
    cit_dir.mkdir()
    (cit_dir / "smith2024.yaml").write_text(
        "key: smith2024\ntitle: Title 1\n", encoding="utf-8"
    )
    (cit_dir / "jones2023.yaml").write_text(
        "key: jones2023\ntitle: Title 2\n", encoding="utf-8"
    )

    project = PaperForgeProject.load(tmp_path)
    cmap = project.citation_map
    assert "smith2024" in cmap
    assert "jones2023" in cmap
    assert cmap["smith2024"].title == "Title 1"


def test_build_uses_citation_yaml_for_bibtex(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims").mkdir(parents=True)
    (pf_dir / "experiments").mkdir(parents=True)
    (pf_dir / "citations").mkdir(parents=True)

    (pf_dir / "paper.yaml").write_text(
        "title: Test\nauthors: [A]\nsections: [results]\nacknowledgment: Thanks\nbuild:\n  output_dir: 'paper'\n",
        encoding="utf-8",
    )
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        "id: exp_01\ndescription: D\nmetrics: {acc: 90}\nhardware: H\ndataset: D\nseed: 42\nresults_file: r.json\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: Claim 90% acc\nexperiment: exp_01\nsections: [results]\ncitations: [smith2024]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "citations" / "smith2024.yaml").write_text(
        "key: smith2024\ntitle: Real Title Paper\ntype: article\nauthors: [Smith, A.]\nyear: 2024\n",
        encoding="utf-8",
    )

    run_build(tmp_path, no_reveal=True)
    bib_content = (tmp_path / "paper" / "references.bib").read_text(encoding="utf-8")
    assert "TODO" not in bib_content
    assert "Real Title Paper" in bib_content


def test_build_stubs_for_keys_without_yaml(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims").mkdir(parents=True)
    (pf_dir / "experiments").mkdir(parents=True)

    (pf_dir / "paper.yaml").write_text(
        "title: Test\nauthors: [A]\nsections: [results]\nacknowledgment: Thanks\nbuild:\n  output_dir: 'paper'\n",
        encoding="utf-8",
    )
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        "id: exp_01\ndescription: D\nmetrics: {acc: 90}\nhardware: H\ndataset: D\nseed: 42\nresults_file: r.json\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: Claim 90% acc\nexperiment: exp_01\nsections: [results]\ncitations: [unknown2099]\nstatus: verified\n",
        encoding="utf-8",
    )

    run_build(tmp_path, no_reveal=True)
    bib_content = (tmp_path / "paper" / "references.bib").read_text(encoding="utf-8")
    assert "unknown2099" in bib_content
    assert "TODO" in bib_content
