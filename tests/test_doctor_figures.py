import yaml

from paperforge.commands.doctor import collect_issues
from paperforge.commands.init import run as init_run
from paperforge.core.project import PaperForgeProject


def _write_figure(tmp_path, fig_id, data):
    fig_file = tmp_path / ".paperforge" / "figures" / f"{fig_id}.yaml"
    data["id"] = fig_id
    with open(fig_file, "w") as f:
        yaml.dump(data, f)


def _update_claim_figures(tmp_path, figures):
    claim_file = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    with open(claim_file) as f:
        data = yaml.safe_load(f)
    data["figures"] = figures
    with open(claim_file, "w") as f:
        yaml.dump(data, f)


def test_figure_no_caption_detected(tmp_path):
    init_run(tmp_path)
    _write_figure(tmp_path, "fig_01", {"caption": ""})
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "FIGURE_NO_CAPTION" for i in issues)


def test_figure_with_caption_no_issue(tmp_path):
    init_run(tmp_path)
    _write_figure(tmp_path, "fig_01", {"caption": "System architecture diagram."})
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "FIGURE_NO_CAPTION" for i in issues)


def test_figure_no_first_mention_detected(tmp_path):
    init_run(tmp_path)
    _write_figure(tmp_path, "fig_01", {"first_mentioned_in": None})
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "FIGURE_NO_FIRST_MENTION" for i in issues)


def test_figure_referenced_but_no_yaml(tmp_path):
    init_run(tmp_path)
    _update_claim_figures(tmp_path, ["fig_99"])
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "FIGURE_REFERENCED_BUT_NO_YAML" for i in issues)


def test_figure_yaml_but_no_claim(tmp_path):
    init_run(tmp_path)
    _write_figure(tmp_path, "fig_01", {})
    # claim_01 has figures=[] by default
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "FIGURE_YAML_BUT_NO_CLAIM" for i in issues)


def test_figure_yaml_referenced_in_claim_no_orphan_issue(tmp_path):
    init_run(tmp_path)
    _write_figure(tmp_path, "fig_01", {})
    _update_claim_figures(tmp_path, ["fig_01"])
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "FIGURE_YAML_BUT_NO_CLAIM" for i in issues)


def test_low_resolution_figure_detected(tmp_path):
    init_run(tmp_path)
    _write_figure(tmp_path, "fig_01", {"resolution_dpi": 150, "format": "png"})
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "LOW_RESOLUTION_FIGURE" for i in issues)


def test_adequate_resolution_no_issue(tmp_path):
    init_run(tmp_path)
    _write_figure(tmp_path, "fig_01", {"resolution_dpi": 300, "format": "png"})
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "LOW_RESOLUTION_FIGURE" for i in issues)
