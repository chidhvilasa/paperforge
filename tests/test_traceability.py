from pathlib import Path

import pytest
import yaml

from paperforge.commands import export, init
from paperforge.commands.export import _escape_latex


def test_export_traceability_creates_three_files(tmp_path: Path) -> None:
    init.run(tmp_path)
    export.run(tmp_path, fmt="traceability", output=None)
    out_dir = tmp_path / ".paperforge" / "output"
    assert (out_dir / "traceability.md").exists()
    assert (out_dir / "traceability.csv").exists()
    assert (out_dir / "traceability.tex").exists()


def test_export_traceability_custom_output_dir(tmp_path: Path) -> None:
    init.run(tmp_path)
    custom_dir = tmp_path / "custom"
    export.run(tmp_path, fmt="traceability", output=custom_dir)
    assert (custom_dir / "traceability.md").exists()
    assert (custom_dir / "traceability.csv").exists()
    assert (custom_dir / "traceability.tex").exists()


def test_export_traceability_md_summary_block(tmp_path: Path) -> None:
    init.run(tmp_path)
    export.run(tmp_path, fmt="traceability", output=None)
    content = (tmp_path / ".paperforge" / "output" / "traceability.md").read_text(encoding="utf-8")
    assert "# Claim Traceability Matrix" in content
    assert "**Evidence Coverage:**" in content


def test_export_traceability_md_status_emojis(tmp_path: Path) -> None:
    init.run(tmp_path)
    claims_dir = tmp_path / ".paperforge" / "claims"
    (claims_dir / "claim_01.yaml").write_text(
        yaml.dump({"id": "claim_01", "text": "c1", "status": "verified", "experiment": "exp_01"}),
        encoding="utf-8",
    )
    (claims_dir / "claim_02.yaml").write_text(
        yaml.dump({"id": "claim_02", "text": "c2", "status": "unverified"}),
        encoding="utf-8",
    )
    (claims_dir / "claim_03.yaml").write_text(
        yaml.dump({"id": "claim_03", "text": "c3", "status": "stale"}),
        encoding="utf-8",
    )
    export.run(tmp_path, fmt="traceability", output=None)
    content = (tmp_path / ".paperforge" / "output" / "traceability.md").read_text(encoding="utf-8")
    assert "✅ verified" in content
    assert "⚠️ unverified" in content
    assert "❌ stale" in content


def test_export_traceability_md_sorted_claims(tmp_path: Path) -> None:
    init.run(tmp_path)
    claims_dir = tmp_path / ".paperforge" / "claims"
    (claims_dir / "claim_02.yaml").write_text(
        yaml.dump({"id": "claim_02", "text": "Second claim"}), encoding="utf-8"
    )
    (claims_dir / "claim_01.yaml").write_text(
        yaml.dump({"id": "claim_01", "text": "First claim"}), encoding="utf-8"
    )
    export.run(tmp_path, fmt="traceability", output=None)
    content = (tmp_path / ".paperforge" / "output" / "traceability.md").read_text(encoding="utf-8")
    pos1 = content.index("claim_01")
    pos2 = content.index("claim_02")
    assert pos1 < pos2


def test_export_traceability_md_key_metric(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        yaml.dump({"id": "exp_01", "metrics": {"accuracy": 98.4, "f1": 97.1}}),
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        yaml.dump({"id": "claim_01", "text": "Test claim", "experiment": "exp_01"}),
        encoding="utf-8",
    )
    export.run(tmp_path, fmt="traceability", output=None)
    content = (tmp_path / ".paperforge" / "output" / "traceability.md").read_text(encoding="utf-8")
    assert "accuracy: 98.4" in content


def test_export_traceability_csv_header(tmp_path: Path) -> None:
    init.run(tmp_path)
    export.run(tmp_path, fmt="traceability", output=None)
    content = (tmp_path / ".paperforge" / "output" / "traceability.csv").read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    assert lines[0] == "Claim ID,Text,Status,Experiment,Key Metric,Figures,Tables,Citations,Sections,Verified"


def test_export_traceability_csv_pipe_separator(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        yaml.dump({
            "id": "claim_01",
            "text": "Multi-ref claim",
            "figures": ["fig_01", "fig_02"],
            "tables": ["tbl_01", "tbl_02"],
            "citations": ["ref1", "ref2"],
            "sections": ["results", "abstract"],
        }),
        encoding="utf-8",
    )
    export.run(tmp_path, fmt="traceability", output=None)
    content = (tmp_path / ".paperforge" / "output" / "traceability.csv").read_text(encoding="utf-8")
    assert "fig_01|fig_02" in content
    assert "tbl_01|tbl_02" in content
    assert "ref1|ref2" in content
    assert "results|abstract" in content


def test_export_traceability_csv_full_text(tmp_path: Path) -> None:
    init.run(tmp_path)
    long_text = "This is a very long claim text that exceeds sixty characters and should remain full in the CSV output."
    (tmp_path / ".paperforge" / "claims" / "claim_01.yaml").write_text(
        yaml.dump({"id": "claim_01", "text": long_text}), encoding="utf-8"
    )
    export.run(tmp_path, fmt="traceability", output=None)
    content = (tmp_path / ".paperforge" / "output" / "traceability.csv").read_text(encoding="utf-8")
    assert long_text in content


def test_export_traceability_tex_longtable(tmp_path: Path) -> None:
    init.run(tmp_path)
    export.run(tmp_path, fmt="traceability", output=None)
    content = (tmp_path / ".paperforge" / "output" / "traceability.tex").read_text(encoding="utf-8")
    assert "\\begin{longtable}" in content
    assert "\\end{longtable}" in content


def test_export_traceability_tex_label(tmp_path: Path) -> None:
    init.run(tmp_path)
    export.run(tmp_path, fmt="traceability", output=None)
    content = (tmp_path / ".paperforge" / "output" / "traceability.tex").read_text(encoding="utf-8")
    assert "\\label{tab:traceability}" in content


def test_export_traceability_tex_headers(tmp_path: Path) -> None:
    init.run(tmp_path)
    export.run(tmp_path, fmt="traceability", output=None)
    content = (tmp_path / ".paperforge" / "output" / "traceability.tex").read_text(encoding="utf-8")
    assert "\\endfirsthead" in content
    assert "\\endhead" in content


def test_escape_latex_special_characters() -> None:
    input_str = "\\ % $ & # _ { } ~ ^"
    escaped = _escape_latex(input_str)
    assert "\\textbackslash{}" in escaped
    assert "\\%" in escaped
    assert "\\$" in escaped
    assert "\\&" in escaped
    assert "\\#" in escaped
    assert "\\_" in escaped
    assert "\\{" in escaped
    assert "\\}" in escaped
    assert "\\textasciitilde{}" in escaped
    assert "\\textasciicircum{}" in escaped


def test_escape_latex_backslash_order() -> None:
    # Test that replacing \ first doesn't double-escape newly created backslashes
    escaped = _escape_latex("100% \\ precision")
    assert "100\\%" in escaped
    assert "\\textbackslash{}" in escaped
    assert "\\textbackslash{}\\%" not in escaped


def test_export_unknown_format_exits_1(tmp_path: Path) -> None:
    init.run(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        export.run(tmp_path, fmt="invalid_format", output=None)
    assert exc_info.value.code == 1


def test_export_traceability_empty_project(tmp_path: Path) -> None:
    init.run(tmp_path)
    (tmp_path / ".paperforge" / "claims" / "claim_01.yaml").unlink(missing_ok=True)
    (tmp_path / ".paperforge" / "experiments" / "exp_01.yaml").unlink(missing_ok=True)
    export.run(tmp_path, fmt="traceability", output=None)
    out_dir = tmp_path / ".paperforge" / "output"
    assert (out_dir / "traceability.md").exists()
    assert (out_dir / "traceability.csv").exists()
    assert (out_dir / "traceability.tex").exists()
