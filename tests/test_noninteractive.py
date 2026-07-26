import zipfile
from pathlib import Path

import pytest
import yaml

from paperforge.commands.add_citation import run as run_add_citation
from paperforge.commands.add_claim import run as run_add_claim
from paperforge.commands.add_figure import run as run_add_figure
from paperforge.commands.add_table import run as run_add_table
from paperforge.commands.build import run as run_build
from paperforge.commands.export import run as run_export
from paperforge.commands.init import run as run_init
from paperforge.graph.dependency import ResearchGraph
from paperforge.models.citation import Citation
from paperforge.models.claim import Claim
from paperforge.models.figure import Figure
from paperforge.models.table import Table


def test_add_claim_noninteractive_basic(tmp_path: Path) -> None:
    run_init(tmp_path)
    run_add_claim(
        tmp_path,
        text="Test claim.",
        experiment="exp_01",
        sections="results,abstract",
        figures=None,
        tables=None,
        citations=None,
        status=None,
    )
    claim_path = tmp_path / ".paperforge" / "claims" / "claim_02.yaml"
    assert claim_path.exists()
    content = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert content["text"] == "Test claim."
    assert content["sections"] == ["results", "abstract"]
    assert content["experiment"] == "exp_01"


def test_add_claim_noninteractive_with_citations(tmp_path: Path) -> None:
    run_init(tmp_path)
    run_add_claim(
        tmp_path,
        text="Cited claim.",
        citations="smith2024,jones2023",
    )
    claim_path = tmp_path / ".paperforge" / "claims" / "claim_02.yaml"
    content = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert content["citations"] == ["smith2024", "jones2023"]


def test_add_claim_noninteractive_status_verified(tmp_path: Path) -> None:
    run_init(tmp_path)
    run_add_claim(
        tmp_path,
        text="Verified claim.",
        status="verified",
    )
    claim_path = tmp_path / ".paperforge" / "claims" / "claim_02.yaml"
    content = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert content["status"] == "verified"


def test_add_figure_noninteractive(tmp_path: Path) -> None:
    run_init(tmp_path)
    run_add_figure(
        tmp_path,
        caption="Test fig.",
        path="figures/fig_01.png",
        format="png",
        width=3.5,
        dpi=300,
        section="results",
        notes="",
        wide=False,
    )
    fig_path = tmp_path / ".paperforge" / "figures" / "fig_01.yaml"
    assert fig_path.exists()
    fig = Figure.from_yaml(yaml.safe_load(fig_path.read_text(encoding="utf-8")))
    assert fig.caption == "Test fig."
    assert fig.width_inches == 3.5
    assert fig.resolution_dpi == 300


def test_add_table_noninteractive(tmp_path: Path) -> None:
    run_init(tmp_path)
    run_add_table(
        tmp_path,
        caption="Results Table",
        experiment="exp_01",
        columns="A,B,C",
        section="results",
        notes="",
        wide=False,
    )
    tbl_path = tmp_path / ".paperforge" / "tables" / "tbl_01.yaml"
    assert tbl_path.exists()
    tbl = Table.from_yaml(yaml.safe_load(tbl_path.read_text(encoding="utf-8")))
    assert tbl.caption == "Results Table"
    assert tbl.columns == ["A", "B", "C"]


def test_add_citation_noninteractive(tmp_path: Path) -> None:
    run_init(tmp_path)
    run_add_citation(
        tmp_path,
        key="smith2024",
        type_str="article",
        authors="Smith, A.; Jones, B.",
        title="Test Paper",
        year=2024,
        venue="IEEE Access",
        volume="",
        number="",
        pages="",
        doi="10.1109/x",
        notes="",
    )
    cit_path = tmp_path / ".paperforge" / "citations" / "smith2024.yaml"
    assert cit_path.exists()
    cit = Citation.from_yaml(yaml.safe_load(cit_path.read_text(encoding="utf-8")))
    assert cit.title == "Test Paper"
    assert cit.doi == "10.1109/x"
    assert cit.authors == ["Smith, A.", "Jones, B."]


def test_add_claim_from_yaml(tmp_path: Path) -> None:
    run_init(tmp_path)
    tmpl = tmp_path / "claim_tmpl.yaml"
    tmpl.write_text(
        "text: 'System achieves 98.4% accuracy.'\n"
        "experiment: exp_01\n"
        "sections: [abstract, results]\n"
        "status: verified\n",
        encoding="utf-8",
    )
    run_add_claim(tmp_path, from_yaml=tmpl)
    claim_path = tmp_path / ".paperforge" / "claims" / "claim_02.yaml"
    assert claim_path.exists()
    content = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert content["text"] == "System achieves 98.4% accuracy."
    assert content["status"] == "verified"


def test_add_citation_from_yaml_uses_key_from_file(tmp_path: Path) -> None:
    run_init(tmp_path)
    tmpl = tmp_path / "smith_tmpl.yaml"
    tmpl.write_text(
        "key: smith2024\n"
        "type: article\n"
        "title: 'Real Title'\n"
        "authors: ['Smith, A.']\n"
        "year: 2024\n",
        encoding="utf-8",
    )
    run_add_citation(tmp_path, from_yaml=tmpl)
    cit_path = tmp_path / ".paperforge" / "citations" / "smith2024.yaml"
    assert cit_path.exists()
    cit = Citation.from_yaml(yaml.safe_load(cit_path.read_text(encoding="utf-8")))
    assert cit.key == "smith2024"
    assert cit.title == "Real Title"


def test_claim_multiple_experiments_round_trip() -> None:
    c = Claim(
        id="c1",
        text="x",
        experiment="exp_01",
        experiments=["exp_02", "exp_03"],
    )
    data = c.to_yaml()
    restored = Claim.from_yaml(data)
    assert restored.experiments == ["exp_02", "exp_03"]


def test_get_affected_includes_additional_experiments() -> None:
    graph = ResearchGraph()
    graph.add_claim(
        Claim(id="c1", text="x", experiment="exp_01", experiments=["exp_02"])
    )
    affected = graph.get_affected("exp_02")
    assert "c1" in affected.claims


def test_get_affected_primary_still_works() -> None:
    graph = ResearchGraph()
    graph.add_claim(
        Claim(id="c1", text="x", experiment="exp_01", experiments=["exp_02"])
    )
    affected = graph.get_affected("exp_01")
    assert "c1" in affected.claims


def test_overleaf_export_creates_zip(tmp_path: Path) -> None:
    run_init(tmp_path)
    # Fix placeholder claim text so build succeeds
    (tmp_path / ".paperforge" / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: 'Valid claim text.'\nexperiment: exp_01\nsections: [results]\nstatus: verified\n",
        encoding="utf-8",
    )
    run_build(tmp_path, no_reveal=True)
    run_export(tmp_path, fmt="overleaf", output=None)
    assert (tmp_path / "paper_overleaf.zip").exists()


def test_overleaf_zip_contains_paper_tex(tmp_path: Path) -> None:
    run_init(tmp_path)
    (tmp_path / ".paperforge" / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: 'Valid claim text.'\nexperiment: exp_01\nsections: [results]\nstatus: verified\n",
        encoding="utf-8",
    )
    run_build(tmp_path, no_reveal=True)
    run_export(tmp_path, fmt="overleaf", output=None)
    with zipfile.ZipFile(tmp_path / "paper_overleaf.zip") as z:
        assert "paper.tex" in z.namelist()


def test_overleaf_zip_contains_readme(tmp_path: Path) -> None:
    run_init(tmp_path)
    (tmp_path / ".paperforge" / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: 'Valid claim text.'\nexperiment: exp_01\nsections: [results]\nstatus: verified\n",
        encoding="utf-8",
    )
    run_build(tmp_path, no_reveal=True)
    run_export(tmp_path, fmt="overleaf", output=None)
    with zipfile.ZipFile(tmp_path / "paper_overleaf.zip") as z:
        assert "README.txt" in z.namelist()


def test_overleaf_fails_without_build(tmp_path: Path) -> None:
    run_init(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        run_export(tmp_path, fmt="overleaf", output=None)
    assert exc_info.value.code == 1
