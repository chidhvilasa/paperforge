"""Tests for versioned venue adapter metadata and custom venue loading."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from paperforge.cli import app
from paperforge.venues.custom import CustomVenueError, load_custom_venue
from paperforge.venues.registry import get_plugin, list_plugins

runner = CliRunner()


def test_every_builtin_venue_has_version_metadata() -> None:
    for name in list_plugins():
        plugin = get_plugin(name)
        assert plugin.adapter_version
        assert isinstance(plugin.checked_date, str)
        assert isinstance(plugin.source_url, str)
        assert plugin.source_description


def test_builtin_venues_are_honestly_unverified() -> None:
    # None of the shipped adapters were checked against a live, dated
    # source in this pass -- checked_date must stay empty rather than
    # fabricate currency.
    for name in list_plugins():
        assert get_plugin(name).checked_date == ""


def test_venue_show_cli_reports_unverified_warning(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["venue", "show", "--target", "ieee", "--json", "--path", str(tmp_path)]
    )
    data = json.loads(result.output)
    assert data["outputs"]["venue"]["source_verified"] is False
    assert data["status"] == "warning"
    assert result.exit_code == 0


def test_venue_show_unknown_target(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "venue",
            "show",
            "--target",
            "not-a-real-venue",
            "--json",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0


def test_custom_venue_missing_id_warns(tmp_path: Path) -> None:
    (tmp_path / "custom_venue.yaml").write_text(
        "display_name: My Venue\n", encoding="utf-8"
    )
    result = runner.invoke(
        app,
        [
            "venue",
            "validate",
            "--custom-file",
            "custom_venue.yaml",
            "--json",
            "--path",
            str(tmp_path),
        ],
    )
    data = json.loads(result.output)
    assert result.exit_code != 0
    assert any(e["code"] == "CUSTOM_VENUE_MISSING_ID" for e in data["errors"])


def test_custom_venue_loads_full_fields(tmp_path: Path) -> None:
    (tmp_path / "custom_venue.yaml").write_text(
        "venue_id: my_venue\n"
        "display_name: My Venue\n"
        "adapter_version: '1.0'\n"
        "checked_date: '2026-01-01'\n"
        "source_url: https://example.org/cfp\n"
        "max_pages: 10\n",
        encoding="utf-8",
    )
    cfg = load_custom_venue(tmp_path, "custom_venue.yaml")
    assert cfg.venue_id == "my_venue"
    assert cfg.checked_date == "2026-01-01"
    assert cfg.max_pages == 10


def test_custom_venue_path_traversal_rejected(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(CustomVenueError, match="outside the project root"):
        load_custom_venue(tmp_path, "../../etc/passwd")


def test_custom_venue_cli_rejects_traversal(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "venue",
            "show",
            "--custom-file",
            "../../outside.yaml",
            "--json",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert any("outside the project root" in e["message"] for e in data["errors"])


def test_venue_yaml_safety_no_arbitrary_python_tags(tmp_path: Path) -> None:
    # yaml.safe_load must refuse to construct arbitrary Python objects.
    malicious = tmp_path / "evil.yaml"
    malicious.write_text(
        "venue_id: !!python/object/apply:os.system ['echo pwned']\n", encoding="utf-8"
    )
    import pytest
    import yaml

    with pytest.raises((yaml.YAMLError, CustomVenueError)):
        load_custom_venue(tmp_path, "evil.yaml")
