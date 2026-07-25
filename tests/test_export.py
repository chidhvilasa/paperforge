"""Tests for paperforge export command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from paperforge.commands import export, init
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def write_valid_project(tmp_path: Path) -> None:
    """Initialize project and add a complete experiment and verified claim."""
    init.run(tmp_path)
    pf = tmp_path / ".paperforge"

    # Update exp_01 with real metrics
    exp = Experiment(
        id="exp_01",
        metrics={"accuracy": 98.4},
        dataset="CICDDoS2019",
        seed=42,
    )
    _write_yaml(
        pf / "experiments" / "exp_01.yaml",
        exp.to_yaml(),
    )

    # Write claim_02 (verified, with citations and sections)
    claim = Claim(
        id="claim_02",
        text="Model achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results"],
        citations=["smith2024", "jones2023"],
        status="verified",
    )
    _write_yaml(pf / "claims" / "claim_02.yaml", claim.to_yaml())


def _json_output(tmp_path: Path) -> Path:
    return tmp_path / ".paperforge" / "output" / "research_graph.json"


# --- Tests ---


def test_export_json_creates_file(tmp_path: Path) -> None:
    write_valid_project(tmp_path)
    export.run(tmp_path, "json", None)
    assert _json_output(tmp_path).exists()


def test_export_json_schema(tmp_path: Path) -> None:
    write_valid_project(tmp_path)
    export.run(tmp_path, "json", None)
    data = json.loads(_json_output(tmp_path).read_text(encoding="utf-8"))
    assert "paperforge_version" in data
    assert "project" in data
    assert "claims" in data
    assert "experiments" in data
    assert "graph" in data
    assert data["graph"]["claim_count"] == 2
    assert len(data["claims"]) == 2


def test_export_json_claim_fields(tmp_path: Path) -> None:
    write_valid_project(tmp_path)
    export.run(tmp_path, "json", None)
    data = json.loads(_json_output(tmp_path).read_text(encoding="utf-8"))
    claim_02 = next(c for c in data["claims"] if c["id"] == "claim_02")
    for field in ("id", "text", "experiment", "figures", "tables",
                  "citations", "sections", "status", "last_verified"):
        assert field in claim_02, f"Missing field: {field}"


def test_export_bibtex_creates_file(tmp_path: Path) -> None:
    write_valid_project(tmp_path)
    export.run(tmp_path, "bibtex", None)
    bib = tmp_path / ".paperforge" / "output" / "references.bib"
    assert bib.exists()


def test_export_bibtex_contains_citation_keys(tmp_path: Path) -> None:
    write_valid_project(tmp_path)
    export.run(tmp_path, "bibtex", None)
    content = (tmp_path / ".paperforge" / "output" / "references.bib").read_text(
        encoding="utf-8"
    )
    assert "smith2024" in content
    assert "jones2023" in content


def test_export_bibtex_no_citations(tmp_path: Path) -> None:
    """When no citations exist, the .bib is comment-only."""
    init.run(tmp_path)
    export.run(tmp_path, "bibtex", None)
    content = (tmp_path / ".paperforge" / "output" / "references.bib").read_text(
        encoding="utf-8"
    )
    assert content.startswith("%")


def test_export_markdown_creates_file(tmp_path: Path) -> None:
    write_valid_project(tmp_path)
    export.run(tmp_path, "markdown", None)
    md = tmp_path / ".paperforge" / "output" / "summary.md"
    assert md.exists()


def test_export_markdown_contains_title(tmp_path: Path) -> None:
    write_valid_project(tmp_path)
    # Set a title in paper.yaml
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "My Amazing Paper"
    _write_yaml(paper_yaml, data)
    export.run(tmp_path, "markdown", None)
    content = (tmp_path / ".paperforge" / "output" / "summary.md").read_text(
        encoding="utf-8"
    )
    assert "My Amazing Paper" in content


def test_export_custom_output_path(tmp_path: Path) -> None:
    write_valid_project(tmp_path)
    custom = tmp_path / "my_export.json"
    export.run(tmp_path, "json", custom)
    assert custom.exists()


def test_export_unknown_format_exits(tmp_path: Path) -> None:
    write_valid_project(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        export.run(tmp_path, "latex", None)
    assert exc_info.value.code == 1
