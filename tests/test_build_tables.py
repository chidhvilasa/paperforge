from pathlib import Path

import yaml

from paperforge.commands import build, init


def write_project_with_table(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    paper_yaml = pf_dir / "paper.yaml"
    paper_data = {
        "version": "0.1",
        "title": "Paper Title",
        "authors": ["Author One"],
        "paper_type": "journal",
        "sections": ["abstract", "introduction", "results", "conclusion"],
    }
    paper_yaml.write_text(yaml.dump(paper_data), encoding="utf-8")

    exp_data = {
        "id": "exp_01",
        "description": "Experiment 1",
        "metrics": {"accuracy": 98.4},
        "seed": 42,
    }
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        yaml.dump(exp_data), encoding="utf-8"
    )

    tbl_data = {
        "id": "tbl_01",
        "caption": "Performance Comparison",
        "columns": ["Method", "Accuracy", "F1"],
        "rows": [["B2", "91.2%", "90.8%"], ["Adaptive", "98.4%", "97.9%"]],
        "first_mentioned_in": "results",
        "source_experiment": "exp_01",
    }
    (pf_dir / "tables" / "tbl_01.yaml").write_text(
        yaml.dump(tbl_data), encoding="utf-8"
    )

    claim_data = {
        "id": "claim_02",
        "text": "System achieves 98.4% accuracy.",
        "experiment": "exp_01",
        "sections": ["results", "abstract"],
        "tables": ["tbl_01"],
        "citations": ["smith2024"],
        "status": "verified",
    }
    (pf_dir / "claims" / "claim_02.yaml").write_text(
        yaml.dump(claim_data), encoding="utf-8"
    )
    # Remove default empty claim_01 if present
    c1 = pf_dir / "claims" / "claim_01.yaml"
    if c1.exists():
        c1.unlink()


def test_build_emits_table_environment(tmp_path: Path) -> None:
    write_project_with_table(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    tex_content = (tmp_path / ".paperforge" / "output" / "paper.tex").read_text(
        encoding="utf-8"
    )
    assert "\\begin{table}" in tex_content


def test_build_caption_before_tabular(tmp_path: Path) -> None:
    write_project_with_table(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    tex_content = (tmp_path / ".paperforge" / "output" / "paper.tex").read_text(
        encoding="utf-8"
    )
    caption_pos = tex_content.index("\\caption{Performance Comparison}")
    tabular_pos = tex_content.index("\\begin{tabular}")
    assert caption_pos < tabular_pos


def test_build_table_label(tmp_path: Path) -> None:
    write_project_with_table(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    tex_content = (tmp_path / ".paperforge" / "output" / "paper.tex").read_text(
        encoding="utf-8"
    )
    assert "\\label{tab:tbl_01}" in tex_content


def test_build_table_column_headers(tmp_path: Path) -> None:
    write_project_with_table(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    tex_content = (tmp_path / ".paperforge" / "output" / "paper.tex").read_text(
        encoding="utf-8"
    )
    assert "Method" in tex_content
    assert "Accuracy" in tex_content


def test_build_table_data_rows(tmp_path: Path) -> None:
    write_project_with_table(tmp_path)
    build.run(tmp_path, target="ieee-journal")
    tex_content = (tmp_path / ".paperforge" / "output" / "paper.tex").read_text(
        encoding="utf-8"
    )
    assert "98.4%" in tex_content or "98.4\\%" in tex_content
    assert "Adaptive" in tex_content


def test_build_bare_table_reference_emits_comment(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    paper_data = {
        "version": "0.1",
        "title": "Paper Title",
        "authors": ["Author"],
        "sections": ["abstract", "results"],
    }
    (pf_dir / "paper.yaml").write_text(yaml.dump(paper_data), encoding="utf-8")
    exp_data = {"id": "exp_01", "description": "exp", "metrics": {"acc": 90.0}}
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        yaml.dump(exp_data), encoding="utf-8"
    )
    claim_data = {
        "id": "claim_02",
        "text": "Achieves 90.0% accuracy.",
        "experiment": "exp_01",
        "sections": ["results"],
        "tables": ["tbl_99"],
        "status": "verified",
    }
    (pf_dir / "claims" / "claim_02.yaml").write_text(
        yaml.dump(claim_data), encoding="utf-8"
    )
    c1 = pf_dir / "claims" / "claim_01.yaml"
    if c1.exists():
        c1.unlink()

    build.run(tmp_path, target="ieee")
    tex_content = (tmp_path / ".paperforge" / "output" / "paper.tex").read_text(
        encoding="utf-8"
    )
    assert "% Table reference: tbl_99" in tex_content
