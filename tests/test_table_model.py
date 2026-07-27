from pathlib import Path

import yaml

from paperforge.commands import init
from paperforge.core.project import PaperForgeProject
from paperforge.graph.dependency import ResearchGraph
from paperforge.models.table import Table


def test_table_round_trip_full() -> None:
    tbl = Table(
        id="tbl_01",
        caption="Performance Comparison",
        columns=["Method", "Accuracy", "F1"],
        rows=[["B2", "91.2%", "90.8%"], ["Adaptive", "98.4%", "97.9%"]],
        notes="Evaluated on test set",
        first_mentioned_in="results",
        source_experiment="exp_01",
    )
    data = tbl.to_yaml()
    reconstructed = Table.from_yaml(data)
    assert reconstructed.id == tbl.id
    assert reconstructed.caption == tbl.caption
    assert reconstructed.columns == tbl.columns
    assert reconstructed.rows == tbl.rows
    assert reconstructed.notes == tbl.notes
    assert reconstructed.first_mentioned_in == tbl.first_mentioned_in
    assert reconstructed.source_experiment == tbl.source_experiment


def test_table_round_trip_minimal() -> None:
    tbl = Table(id="tbl_01")
    data = tbl.to_yaml()
    reconstructed = Table.from_yaml(data)
    assert reconstructed.id == "tbl_01"
    assert reconstructed.caption == ""
    assert reconstructed.columns == []
    assert reconstructed.rows == []
    assert reconstructed.notes == ""
    assert reconstructed.first_mentioned_in is None
    assert reconstructed.source_experiment is None


def test_table_from_yaml_missing_optional_fields() -> None:
    data = {"id": "tbl_01"}
    tbl = Table.from_yaml(data)
    assert tbl.caption == ""
    assert tbl.columns == []
    assert tbl.rows == []
    assert tbl.notes == ""
    assert tbl.first_mentioned_in is None
    assert tbl.source_experiment is None


def test_table_to_yaml_keys() -> None:
    tbl = Table(id="tbl_01", caption="Results")
    data = tbl.to_yaml()
    assert set(data.keys()) == {
        "id",
        "caption",
        "columns",
        "rows",
        "notes",
        "first_mentioned_in",
        "source_experiment",
        "wide",
        "auto_rows_from_experiment",
        "is_math",
        "raw_latex_rows",
    }


def test_project_loads_tables(tmp_path: Path) -> None:
    init.run(tmp_path)
    tables_dir = tmp_path / ".paperforge" / "tables"
    tbl_yaml = tables_dir / "tbl_01.yaml"
    tbl_data = {
        "id": "tbl_01",
        "caption": "Results Table",
        "columns": ["A", "B"],
        "rows": [["1", "2"]],
    }
    tbl_yaml.write_text(yaml.dump(tbl_data), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    assert len(project.tables) == 1
    assert project.tables[0].id == "tbl_01"


def test_project_table_count(tmp_path: Path) -> None:
    init.run(tmp_path)
    tables_dir = tmp_path / ".paperforge" / "tables"
    (tables_dir / "tbl_01.yaml").write_text(
        yaml.dump({"id": "tbl_01", "caption": "T1"}), encoding="utf-8"
    )
    (tables_dir / "tbl_02.yaml").write_text(
        yaml.dump({"id": "tbl_02", "caption": "T2"}), encoding="utf-8"
    )

    project = PaperForgeProject.load(tmp_path)
    assert project.table_count == 2


def test_graph_add_table() -> None:
    graph = ResearchGraph()
    graph.add_table(Table(id="tbl_01", caption="Results"))
    assert graph.table_count == 1
    tbl = graph.get_table("tbl_01")
    assert tbl is not None
    assert tbl.caption == "Results"


def test_graph_get_table_unknown() -> None:
    graph = ResearchGraph()
    assert graph.get_table("tbl_99") is None
