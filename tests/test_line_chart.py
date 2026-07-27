"""Tests for multi-series line chart generation and multi-experiment claim metric matching."""

from pathlib import Path

from paperforge.commands import generate_figures, init
from paperforge.core.project import PaperForgeProject
from paperforge.models.figure import Figure


def test_figure_line_chart_model_fields() -> None:
    fig = Figure.from_yaml({
        "id": "fig_line",
        "caption": "Line Chart",
        "chart_type": "line",
        "line_experiments": ["exp_01", "exp_02"],
        "x_values": [1.0, 2.0, 3.0],
    })
    assert fig.chart_type == "line"
    assert fig.line_experiments == ["exp_01", "exp_02"]
    assert fig.x_values == [1.0, 2.0, 3.0]
    dumped = fig.to_yaml()
    assert dumped["line_experiments"] == ["exp_01", "exp_02"]
    assert dumped["x_values"] == [1.0, 2.0, 3.0]


def test_generate_line_chart_multi_experiment(tmp_path: Path) -> None:
    from paperforge.commands.generate_figures import _generate_line_chart

    fig = Figure.from_yaml({
        "id": "fig_multi_line",
        "caption": "Multi Line",
        "chart_type": "line",
        "metric_keys": ["accuracy"],
        "x_values": [1.0, 2.0],
        "x_labels": ["Step 1", "Step 2"],
    })
    experiments = [
        ("exp_01", {"accuracy": 85.0}),
        ("exp_02", {"accuracy": 92.5}),
    ]
    out_file = tmp_path / "figures" / "fig_multi_line.png"
    _generate_line_chart(fig, experiments, out_file)
    assert out_file.exists()
    assert out_file.stat().st_size > 0


def test_generate_figures_line_chart_cli(tmp_path: Path) -> None:
    init.run(tmp_path)

    # Setup 2 experiments
    exp_dir = tmp_path / ".paperforge" / "experiments"
    (exp_dir / "exp_01.yaml").write_text("id: exp_01\nmetrics:\n  acc: 80.0\n")
    (exp_dir / "exp_02.yaml").write_text("id: exp_02\nmetrics:\n  acc: 90.0\n")

    # Setup line chart figure
    fig_dir = tmp_path / ".paperforge" / "figures"
    fig_dir.mkdir(exist_ok=True)
    (fig_dir / "fig_line.yaml").write_text(
        "id: fig_line\ncaption: Line Chart\nchart_type: line\nsource_experiment: exp_01\nline_experiments: [exp_02]\nmetric_keys: [acc]\n"
    )

    generate_figures.run(tmp_path, figure_id="fig_line")
    png_path = tmp_path / "figures" / "fig_line.png"
    assert png_path.exists()


def test_metric_claim_mismatch_multi_experiment(tmp_path: Path) -> None:
    from paperforge.commands.doctor import collect_issues

    pf = tmp_path / ".paperforge"
    pf.mkdir()
    (pf / "paper.yaml").write_text("version: '0.1'\ntitle: T\nauthors: [A]\nvenue: IEEE\nstatus: draft\nsections: []\n")
    (pf / "claims").mkdir()
    (pf / "experiments").mkdir()

    (pf / "experiments" / "exp_01.yaml").write_text("id: exp_01\nmetrics:\n  acc: 75.0\n")
    (pf / "experiments" / "exp_02.yaml").write_text("id: exp_02\nmetrics:\n  pdr: 95.0\n")

    # Claim links exp_01 as primary and exp_02 in experiments list, text mentions 95.0%
    (pf / "claims" / "c1.yaml").write_text(
        "id: c1\ntext: Method achieves 95.0% PDR.\nexperiment: exp_01\nexperiments: [exp_02]\n"
    )

    proj = PaperForgeProject.load(tmp_path)
    issues = collect_issues(proj)
    mismatches = [i for i in issues if i.code == "METRIC_CLAIM_MISMATCH"]
    assert len(mismatches) == 0
