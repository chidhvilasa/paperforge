from pathlib import Path

import yaml

from paperforge.commands import init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject


def test_table_no_caption_is_error(tmp_path: Path) -> None:
    init.run(tmp_path)
    tables_dir = tmp_path / ".paperforge" / "tables"
    (tables_dir / "tbl_01.yaml").write_text(
        yaml.dump({"id": "tbl_01", "caption": ""}), encoding="utf-8"
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    issue = next(i for i in issues if i.code == "TABLE_NO_CAPTION")
    assert issue.severity == "ERROR"


def test_table_with_caption_no_caption_error(tmp_path: Path) -> None:
    init.run(tmp_path)
    tables_dir = tmp_path / ".paperforge" / "tables"
    (tables_dir / "tbl_01.yaml").write_text(
        yaml.dump({"id": "tbl_01", "caption": "Comparison Results"}), encoding="utf-8"
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "TABLE_NO_CAPTION" for i in issues)


def test_table_no_columns_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    tables_dir = tmp_path / ".paperforge" / "tables"
    (tables_dir / "tbl_01.yaml").write_text(
        yaml.dump({"id": "tbl_01", "caption": "Results", "columns": []}),
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "TABLE_NO_COLUMNS" for i in issues)


def test_table_referenced_but_no_yaml(tmp_path: Path) -> None:
    init.run(tmp_path)
    claims_dir = tmp_path / ".paperforge" / "claims"
    (claims_dir / "claim_02.yaml").write_text(
        yaml.dump(
            {
                "id": "claim_02",
                "text": "Claim text",
                "experiment": "exp_01",
                "tables": ["tbl_99"],
            }
        ),
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "TABLE_REFERENCED_BUT_NO_YAML" for i in issues)


def test_table_yaml_but_no_claim(tmp_path: Path) -> None:
    init.run(tmp_path)
    tables_dir = tmp_path / ".paperforge" / "tables"
    (tables_dir / "tbl_01.yaml").write_text(
        yaml.dump({"id": "tbl_01", "caption": "Results"}), encoding="utf-8"
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "TABLE_YAML_BUT_NO_CLAIM" for i in issues)


def test_table_yaml_referenced_in_claim_no_orphan(tmp_path: Path) -> None:
    init.run(tmp_path)
    tables_dir = tmp_path / ".paperforge" / "tables"
    (tables_dir / "tbl_01.yaml").write_text(
        yaml.dump({"id": "tbl_01", "caption": "Results"}), encoding="utf-8"
    )
    claims_dir = tmp_path / ".paperforge" / "claims"
    (claims_dir / "claim_02.yaml").write_text(
        yaml.dump(
            {
                "id": "claim_02",
                "text": "Claim text",
                "experiment": "exp_01",
                "tables": ["tbl_01"],
            }
        ),
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "TABLE_YAML_BUT_NO_CLAIM" for i in issues)


def test_table_row_column_mismatch(tmp_path: Path) -> None:
    init.run(tmp_path)
    tables_dir = tmp_path / ".paperforge" / "tables"
    (tables_dir / "tbl_01.yaml").write_text(
        yaml.dump(
            {
                "id": "tbl_01",
                "caption": "R",
                "columns": ["A", "B", "C"],
                "rows": [["x", "y"]],
            }
        ),
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "TABLE_ROW_COLUMN_MISMATCH" for i in issues)


def test_table_row_column_match_no_issue(tmp_path: Path) -> None:
    init.run(tmp_path)
    tables_dir = tmp_path / ".paperforge" / "tables"
    (tables_dir / "tbl_01.yaml").write_text(
        yaml.dump(
            {
                "id": "tbl_01",
                "caption": "R",
                "columns": ["A", "B"],
                "rows": [["x", "y"], ["p", "q"]],
            }
        ),
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "TABLE_ROW_COLUMN_MISMATCH" for i in issues)
