from unittest.mock import patch

import pytest
import yaml

from paperforge.commands.add_figure import run as add_figure_run
from paperforge.commands.init import run as init_run


def test_add_figure_creates_yaml(tmp_path):
    init_run(tmp_path)
    prompts = [
        "Test caption",
        "figures/fig_01.png",
        "png",
        "3.5",
        "300",
        "results",
        "",
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_figure_run(tmp_path)

    fig_file = tmp_path / ".paperforge" / "figures" / "fig_01.yaml"
    assert fig_file.exists()
    
    with open(fig_file) as f:
        data = yaml.safe_load(f)
    assert data["caption"] == "Test caption"


def test_add_figure_parses_float_width(tmp_path):
    init_run(tmp_path)
    prompts = ["Test caption", "", "", "3.5", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        add_figure_run(tmp_path)

    fig_file = tmp_path / ".paperforge" / "figures" / "fig_01.yaml"
    with open(fig_file) as f:
        data = yaml.safe_load(f)
    assert data["width_inches"] == 3.5


def test_add_figure_parses_int_dpi(tmp_path):
    init_run(tmp_path)
    prompts = ["Test caption", "", "", "", "300", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        add_figure_run(tmp_path)

    fig_file = tmp_path / ".paperforge" / "figures" / "fig_01.yaml"
    with open(fig_file) as f:
        data = yaml.safe_load(f)
    assert data["resolution_dpi"] == 300


def test_add_figure_empty_path_gives_none(tmp_path):
    init_run(tmp_path)
    prompts = ["Test caption", "", "", "", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        add_figure_run(tmp_path)

    fig_file = tmp_path / ".paperforge" / "figures" / "fig_01.yaml"
    with open(fig_file) as f:
        data = yaml.safe_load(f)
    assert data["path"] is None


def test_add_figure_increments_id(tmp_path):
    init_run(tmp_path)
    fig_dir = tmp_path / ".paperforge" / "figures"
    (fig_dir / "fig_01.yaml").write_text("id: fig_01")
    (fig_dir / "fig_02.yaml").write_text("id: fig_02")

    prompts = ["Test caption", "", "", "", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        add_figure_run(tmp_path)

    assert (fig_dir / "fig_03.yaml").exists()


def test_add_figure_invalid_width_gives_none(tmp_path):
    init_run(tmp_path)
    prompts = ["Test caption", "", "", "not_a_number", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        add_figure_run(tmp_path)

    fig_file = tmp_path / ".paperforge" / "figures" / "fig_01.yaml"
    with open(fig_file) as f:
        data = yaml.safe_load(f)
    assert data["width_inches"] is None


def test_add_figure_fails_without_init(tmp_path):
    # No init run
    prompts = ["Test caption", "", "", "", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        with pytest.raises(SystemExit) as exc_info:
            add_figure_run(tmp_path)
        assert exc_info.value.code == 1


def test_add_figure_first_figure_is_fig_01(tmp_path):
    init_run(tmp_path)
    prompts = ["Test caption", "", "", "", "", "", ""]
    with patch("typer.prompt", side_effect=prompts):
        add_figure_run(tmp_path)

    fig_file = tmp_path / ".paperforge" / "figures" / "fig_01.yaml"
    assert fig_file.exists()
