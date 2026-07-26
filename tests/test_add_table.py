from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from paperforge.commands import add_table, init
from paperforge.models.table import Table


def test_add_table_creates_yaml(tmp_path: Path) -> None:
    init.run(tmp_path)
    prompts = [
        "Test caption",  # Caption
        "exp_01",        # Experiment
        "Method,Accuracy", # Columns
        "B2,91.2%",      # Row 1
        "done",          # Row end
        "results",       # Section
        "",              # Notes
        "",              # Wide?
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_table.run(tmp_path)

    out_file = tmp_path / ".paperforge" / "tables" / "tbl_01.yaml"
    assert out_file.exists()


def test_add_table_parses_columns(tmp_path: Path) -> None:
    init.run(tmp_path)
    prompts = [
        "Test caption",
        "exp_01",
        "Method,Accuracy,F1",
        "done",
        "results",
        "",
        "",
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_table.run(tmp_path)

    out_file = tmp_path / ".paperforge" / "tables" / "tbl_01.yaml"
    data = yaml.safe_load(out_file.read_text(encoding="utf-8"))
    assert data["columns"] == ["Method", "Accuracy", "F1"]


def test_add_table_parses_rows(tmp_path: Path) -> None:
    init.run(tmp_path)
    prompts = [
        "Test caption",
        "exp_01",
        "Method,Accuracy,F1",
        "B2,91.2%,90.8%",
        "done",
        "results",
        "",
        "",
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_table.run(tmp_path)

    out_file = tmp_path / ".paperforge" / "tables" / "tbl_01.yaml"
    data = yaml.safe_load(out_file.read_text(encoding="utf-8"))
    assert data["rows"] == [["B2", "91.2%", "90.8%"]]


def test_add_table_empty_columns_gives_empty_list(tmp_path: Path) -> None:
    init.run(tmp_path)
    prompts = [
        "Test caption",
        "exp_01",
        "",  # Empty columns
        "done",
        "results",
        "",
        "",
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_table.run(tmp_path)

    out_file = tmp_path / ".paperforge" / "tables" / "tbl_01.yaml"
    data = yaml.safe_load(out_file.read_text(encoding="utf-8"))
    assert data["columns"] == []


def test_add_table_increments_id(tmp_path: Path) -> None:
    init.run(tmp_path)
    tables_dir = tmp_path / ".paperforge" / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    (tables_dir / "tbl_01.yaml").write_text(yaml.dump({"id": "tbl_01"}), encoding="utf-8")
    (tables_dir / "tbl_02.yaml").write_text(yaml.dump({"id": "tbl_02"}), encoding="utf-8")

    prompts = ["Caption", "", "", "done", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        add_table.run(tmp_path)

    out_file = tables_dir / "tbl_03.yaml"
    assert out_file.exists()


def test_add_table_first_table_is_tbl_01(tmp_path: Path) -> None:
    init.run(tmp_path)
    prompts = ["Caption", "", "", "done", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        add_table.run(tmp_path)

    out_file = tmp_path / ".paperforge" / "tables" / "tbl_01.yaml"
    assert out_file.exists()


def test_add_table_empty_source_experiment_gives_none(tmp_path: Path) -> None:
    init.run(tmp_path)
    prompts = ["Caption", "", "", "done", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        add_table.run(tmp_path)

    out_file = tmp_path / ".paperforge" / "tables" / "tbl_01.yaml"
    tbl = Table.from_yaml(yaml.safe_load(out_file.read_text(encoding="utf-8")))
    assert tbl.source_experiment is None


def test_add_table_fails_without_init(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        add_table.run(tmp_path)
    assert exc_info.value.code == 1
