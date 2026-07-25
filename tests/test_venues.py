"""Tests for the venue plugin architecture."""

from pathlib import Path

import pytest
import yaml

from paperforge.commands import build, init
from paperforge.core.project import PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment
from paperforge.venues.registry import get_plugin, list_plugins


def _write_claim(tmp_path: Path, claim: Claim) -> None:
    path = tmp_path / ".paperforge" / "claims" / f"{claim.id}.yaml"
    path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _write_experiment(tmp_path: Path, experiment: Experiment) -> None:
    path = tmp_path / ".paperforge" / "experiments" / f"{experiment.id}.yaml"
    path.write_text(
        yaml.dump(experiment.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _set_paper_title_and_authors(tmp_path: Path) -> None:
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "Test Paper"
    data["authors"] = ["Test Author"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def _make_valid_project(tmp_path: Path, sections: list[str] | None = None) -> None:
    init.run(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="claim_01",
            text="This model achieves 98.4% accuracy.",
            experiment="exp_01",
            sections=sections if sections is not None else ["results"],
            status="verified",
        ),
    )
    _write_experiment(
        tmp_path,
        Experiment(id="exp_01", metrics={"accuracy": 98.4}, seed=42, dataset="MNIST"),
    )
    _set_paper_title_and_authors(tmp_path)


def test_registry_lists_three_plugins() -> None:
    assert list_plugins() == ["acm", "ieee", "neurips"]


def test_get_plugin_ieee() -> None:
    plugin = get_plugin("ieee")
    assert plugin.name == "ieee"
    assert "IEEEtran" in plugin.latex_documentclass


def test_get_plugin_acm() -> None:
    plugin = get_plugin("acm")
    assert plugin.name == "acm"
    assert "acmart" in plugin.latex_documentclass


def test_get_plugin_neurips() -> None:
    plugin = get_plugin("neurips")
    assert plugin.name == "neurips"
    assert plugin.max_pages == 9


def test_get_plugin_unknown_raises() -> None:
    with pytest.raises(ValueError):
        get_plugin("springer")


def test_ieee_validate_missing_required_section(tmp_path: Path) -> None:
    _make_valid_project(tmp_path, sections=["results"])
    project = PaperForgeProject.load(tmp_path)
    plugin = get_plugin("ieee")

    issues = plugin.validate(project)

    assert any(
        issue.code == "MISSING_REQUIRED_SECTION" and "introduction" in issue.message
        for issue in issues
    )


def test_ieee_validate_uncited_claim(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)

    issues = get_plugin("ieee").validate(project)

    assert any(issue.code == "UNCITED_CLAIM" for issue in issues)


def test_neurips_validate_missing_seed(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_experiment(tmp_path, Experiment(id="exp_01", seed=None))
    project = PaperForgeProject.load(tmp_path)

    issues = get_plugin("neurips").validate(project)

    assert any(issue.code == "MISSING_SEED" for issue in issues)


def test_neurips_validate_missing_dataset(tmp_path: Path) -> None:
    init.run(tmp_path)
    _write_experiment(tmp_path, Experiment(id="exp_01", dataset=None))
    project = PaperForgeProject.load(tmp_path)

    issues = get_plugin("neurips").validate(project)

    assert any(issue.code == "MISSING_DATASET" for issue in issues)


def test_acm_validate_missing_related_work(tmp_path: Path) -> None:
    _make_valid_project(tmp_path, sections=["results"])
    project = PaperForgeProject.load(tmp_path)

    issues = get_plugin("acm").validate(project)

    assert any(issue.code == "MISSING_RELATED_WORK" for issue in issues)


def test_build_uses_venue_documentclass(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)

    build.run(tmp_path, target="acm")

    content = (tmp_path / ".paperforge" / "output" / "paper.tex").read_text(
        encoding="utf-8"
    )
    assert "acmart" in content


def test_build_unknown_venue_exits(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        build.run(tmp_path, target="springer")
    assert exc_info.value.code == 1
