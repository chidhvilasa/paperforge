"""Tests for Phase 21 critical fixes."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from paperforge.commands import build, capture, init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment
from paperforge.models.table import Table
from paperforge.venues.registry import list_plugins


def _fix_all_errors(
    tmp_path: Path,
    title: str = "Test Paper",
    authors: list[str] | None = None,
) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    claim_path = pf_dir / "claims" / "claim_01.yaml"
    claim = Claim(
        id="claim_01",
        text="This model achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results"],
        status="verified",
    )
    claim_path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    exp_path = pf_dir / "experiments" / "exp_01.yaml"
    experiment = Experiment(id="exp_01", metrics={"accuracy": 98.4}, seed=42)
    exp_path.write_text(
        yaml.dump(experiment.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    paper_yaml = pf_dir / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = title
    data["authors"] = authors if authors is not None else ["Test Author"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def _read_tex(tmp_path: Path) -> str:
    p = tmp_path / "paper" / "paper.tex"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return (tmp_path / ".paperforge" / "output" / "paper.tex").read_text(
        encoding="utf-8"
    )


# --- Fix 1: encoding ---


def test_encoding_project_loads_utf8_text(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    claim = Claim(
        id="claim_02",
        text="Authentication—fast and secure.",
        experiment="exp_01",
    )
    (pf_dir / "claims" / "claim_02.yaml").write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    project = PaperForgeProject.load(tmp_path)

    assert project.claims[1].text == "Authentication—fast and secure."


# --- Fix 2: acknowledgment field ---


def test_acknowledgment_field_in_config(tmp_path: Path) -> None:
    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["acknowledgment"] = "This work was supported by VIT Vellore."
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)

    assert project.config.acknowledgment == "This work was supported by VIT Vellore."


def test_build_uses_acknowledgment_from_config(tmp_path: Path) -> None:
    _fix_all_errors(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["acknowledgment"] = "This work was supported by VIT Vellore."
    data["paper_type"] = "journal"
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    build.run(tmp_path, target="ieee-journal")

    content = _read_tex(tmp_path)
    assert "This work was supported by VIT Vellore." in content


def test_acknowledgment_missing_fires_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert any(i.code == "MISSING_ACKNOWLEDGMENT" for i in issues)


# --- Fix 3/4: compsoc split + ieee-access ---


def test_ieee_journal_non_compsoc_documentclass(tmp_path: Path) -> None:
    _fix_all_errors(tmp_path)
    build.run(tmp_path, target="ieee-journal")

    content = _read_tex(tmp_path)
    assert "\\documentclass[journal]{IEEEtran}" in content
    assert "journal,compsoc" not in content


def test_ieee_compsoc_documentclass(tmp_path: Path) -> None:
    _fix_all_errors(tmp_path)
    build.run(tmp_path, target="ieee-compsoc")

    content = _read_tex(tmp_path)
    assert "compsoc" in content


def test_ieee_access_documentclass(tmp_path: Path) -> None:
    _fix_all_errors(tmp_path)
    build.run(tmp_path, target="ieee-access")

    content = _read_tex(tmp_path)
    assert "\\documentclass[journal]{IEEEtran}" in content
    assert "journal,compsoc" not in content


# --- Fix 5: wide tables ---


def test_wide_table_uses_table_star(tmp_path: Path) -> None:
    _fix_all_errors(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    tbl = Table(
        id="tbl_01",
        caption="Wide Table",
        columns=["A", "B", "C"],
        rows=[["1", "2", "3"]],
        wide=True,
    )
    (pf_dir / "tables" / "tbl_01.yaml").write_text(
        yaml.dump(tbl.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    claim_path = pf_dir / "claims" / "claim_01.yaml"
    claim_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    claim_data["tables"] = ["tbl_01"]
    claim_path.write_text(yaml.dump(claim_data, default_flow_style=False), encoding="utf-8")

    build.run(tmp_path, target="ieee")

    content = _read_tex(tmp_path)
    assert "\\begin{table*}" in content


def test_narrow_table_uses_table(tmp_path: Path) -> None:
    _fix_all_errors(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    tbl = Table(
        id="tbl_01",
        caption="Narrow Table",
        columns=["A", "B"],
        rows=[["1", "2"]],
        wide=False,
    )
    (pf_dir / "tables" / "tbl_01.yaml").write_text(
        yaml.dump(tbl.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    claim_path = pf_dir / "claims" / "claim_01.yaml"
    claim_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    claim_data["tables"] = ["tbl_01"]
    claim_path.write_text(yaml.dump(claim_data, default_flow_style=False), encoding="utf-8")

    build.run(tmp_path, target="ieee")

    content = _read_tex(tmp_path)
    assert "\\begin{table}" in content
    assert "\\begin{table*}" not in content


def test_wide_table_recommended_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    tbl = Table(
        id="tbl_01",
        caption="Big Table",
        columns=["A", "B", "C", "D", "E", "F"],
        rows=[["1", "2", "3", "4", "5", "6"]],
        wide=False,
    )
    (pf_dir / "tables" / "tbl_01.yaml").write_text(
        yaml.dump(tbl.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)

    assert any(i.code == "WIDE_TABLE_RECOMMENDED" for i in issues)


# --- Fix 6: nested JSON metrics ---


def test_capture_flattens_nested_json(tmp_path: Path) -> None:
    init.run(tmp_path)
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps({"b2": {"meanLatencyMs": {"mean": 71.86, "std": 2.1}}}),
        encoding="utf-8",
    )

    capture.run(results=metrics_path, experiment_id="exp_01", project_root=tmp_path)

    exp_path = tmp_path / ".paperforge" / "experiments" / "exp_01.yaml"
    experiment = Experiment.from_yaml(
        yaml.safe_load(exp_path.read_text(encoding="utf-8"))
    )
    assert experiment.metrics != {}
    assert any("meanLatencyMs" in k for k in experiment.metrics)


def test_capture_flat_json_unchanged(tmp_path: Path) -> None:
    init.run(tmp_path)
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps({"accuracy": 98.4}), encoding="utf-8")

    capture.run(results=metrics_path, experiment_id="exp_01", project_root=tmp_path)

    exp_path = tmp_path / ".paperforge" / "experiments" / "exp_01.yaml"
    experiment = Experiment.from_yaml(
        yaml.safe_load(exp_path.read_text(encoding="utf-8"))
    )
    assert experiment.metrics["accuracy"] == 98.4


# --- Fix 8: multi-seed ---


def test_multi_seed_experiment_no_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    exp_path = tmp_path / ".paperforge" / "experiments" / "exp_01.yaml"
    data = yaml.safe_load(exp_path.read_text(encoding="utf-8"))
    data["seeds"] = [0, 1, 2, 3, 4]
    exp_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)

    assert not any(i.code == "EXPERIMENT_NO_SEED" for i in issues)


def test_single_seed_experiment_no_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    exp_path = tmp_path / ".paperforge" / "experiments" / "exp_01.yaml"
    data = yaml.safe_load(exp_path.read_text(encoding="utf-8"))
    data["seed"] = 42
    data["seeds"] = None
    exp_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)

    assert not any(i.code == "EXPERIMENT_NO_SEED" for i in issues)


def test_no_seed_fires_warning(tmp_path: Path) -> None:
    init.run(tmp_path)
    project = PaperForgeProject.load(tmp_path)

    issues = collect_issues(project)

    assert any(i.code == "EXPERIMENT_NO_SEED" for i in issues)


# --- Fix 7: acronym plurals ---


def test_acronym_plural_definition_accepted(tmp_path: Path) -> None:
    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"

    claim1 = Claim(
        id="claim_01",
        text="Vehicular Ad Hoc Networks (VANETs) are tested.",
        experiment="exp_01",
        sections=["results"],
    )
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        yaml.dump(claim1.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    claim2 = Claim(
        id="claim_02",
        text="VANET performance is evaluated.",
        experiment="exp_01",
        sections=["results"],
    )
    (pf_dir / "claims" / "claim_02.yaml").write_text(
        yaml.dump(claim2.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)

    assert not any(
        i.code == "UNDEFINED_ACRONYM" and "VANET" in i.message for i in issues
    )


# --- Fix 4: venue registry ---


def test_venues_include_ieee_access_and_compsoc() -> None:
    plugins = list_plugins()
    assert "ieee-access" in plugins
    assert "ieee-compsoc" in plugins
