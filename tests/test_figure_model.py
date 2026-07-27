from paperforge.core.project import PaperForgeProject
from paperforge.graph.dependency import ResearchGraph
from paperforge.models.figure import Figure


def test_figure_round_trip_full():
    fig = Figure(
        id="fig_01",
        caption="Full caption",
        path="figures/fig_01.png",
        format="png",
        width_inches=3.5,
        resolution_dpi=300,
        first_mentioned_in="results",
        notes="A note",
    )
    data = fig.to_yaml()
    loaded = Figure.from_yaml(data)
    assert loaded == fig


def test_figure_round_trip_minimal():
    fig = Figure(id="fig_01")
    data = fig.to_yaml()
    loaded = Figure.from_yaml(data)
    assert loaded.id == "fig_01"
    assert loaded.caption == ""
    assert loaded.path is None
    assert loaded.format is None
    assert loaded.width_inches is None
    assert loaded.resolution_dpi is None
    assert loaded.first_mentioned_in is None
    assert loaded.notes == ""


def test_figure_from_yaml_missing_optional_fields():
    data = {"id": "fig_01"}
    fig = Figure.from_yaml(data)
    assert fig.caption == ""
    assert fig.path is None
    assert fig.resolution_dpi is None


def test_figure_to_yaml_keys():
    fig = Figure(id="fig_01", caption="Test caption")
    data = fig.to_yaml()
    assert set(data.keys()) == {
        "id",
        "caption",
        "path",
        "format",
        "width_inches",
        "resolution_dpi",
        "first_mentioned_in",
        "notes",
        "wide",
        "source_experiment",
        "chart_type",
        "x_label",
        "y_label",
        "chart_title",
        "metric_keys",
        "x_labels",
    }


def test_project_loads_figures(tmp_path):
    # init basic layout so project can load
    from paperforge.commands.init import run as init_run
    init_run(tmp_path)
    
    import yaml
    fig_yaml = tmp_path / ".paperforge" / "figures" / "fig_01.yaml"
    with open(fig_yaml, "w") as f:
        yaml.dump({"id": "fig_01", "caption": "Test caption"}, f)

    project = PaperForgeProject.load(tmp_path)
    assert len(project.figures) == 1
    assert project.figures[0].id == "fig_01"


def test_project_figure_count(tmp_path):
    from paperforge.commands.init import run as init_run
    init_run(tmp_path)
    
    import yaml
    for i in range(1, 3):
        fig_yaml = tmp_path / ".paperforge" / "figures" / f"fig_{i:02d}.yaml"
        with open(fig_yaml, "w") as f:
            yaml.dump({"id": f"fig_{i:02d}"}, f)

    project = PaperForgeProject.load(tmp_path)
    assert project.figure_count == 2


def test_graph_add_figure():
    graph = ResearchGraph()
    graph.add_figure(Figure(id="fig_01", caption="Test"))
    assert graph.figure_count == 1
    assert graph.get_figure("fig_01").caption == "Test"


def test_graph_get_figure_unknown():
    graph = ResearchGraph()
    assert graph.get_figure("fig_99") is None
