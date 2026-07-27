"""Tests for configurable paths, import parsing, and build output structure."""

from pathlib import Path

import pytest

from paperforge.commands import import_content, init
from paperforge.core.project import PaperForgeProject, ProjectConfig


def test_project_config_custom_paths() -> None:
    data = {
        "version": "0.1",
        "title": "Test",
        "authors": ["A"],
        "venue": "IEEE",
        "status": "draft",
        "sections": ["intro"],
        "build": {
            "output_dir": "custom_out/current",
            "paper_information_dir": "custom_info",
            "base_dir": "custom_base",
            "theorem_packages": False,
        },
    }
    cfg = ProjectConfig.from_yaml(data)
    assert cfg.build_output_dir == "custom_out/current"
    assert cfg.paper_information_dir == "custom_info"
    assert cfg.base_dir == "custom_base"
    assert cfg.theorem_packages is False


def test_init_creates_configured_paths(tmp_path: Path) -> None:
    init.run(tmp_path)
    assert (tmp_path / ".paperforge").exists()
    assert (tmp_path / "paper_information").exists()
    assert (tmp_path / "paper_generated" / "current").exists()


def test_import_from_custom_info_dir(tmp_path: Path) -> None:
    import yaml

    init.run(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data.setdefault("build", {})["paper_information_dir"] = "paper_information"
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    import_content.run(tmp_path)
    claims = list((tmp_path / ".paperforge" / "claims").glob("*.yaml"))
    assert len(claims) >= 1


def test_import_subsection_and_citations(tmp_path: Path) -> None:
    init.run(tmp_path)

    # Create citation YAML
    cit_dir = tmp_path / ".paperforge" / "citations"
    cit_dir.mkdir(exist_ok=True)
    (cit_dir / "smith2024.yaml").write_text("key: smith2024\ntitle: Paper\nauthors: [Smith]\nyear: 2024\n")

    # Create section content with subsection and citation
    intro_md = tmp_path / "paper_information" / "content" / "introduction.md"
    intro_md.write_text(
        "# Introduction\n\n## Background Subsection\n\nThis is a claim citing [smith2024] in background.\n"
    )

    import_content.run(tmp_path, force=True)

    proj = PaperForgeProject.load(tmp_path)
    found_claim = next((c for c in proj.claims if "background" in (c.text or "").lower() or "smith2024" in c.citations or c.subsection == "Background Subsection"), None)
    assert found_claim is not None
    assert found_claim.subsection == "Background Subsection"
    assert "smith2024" in found_claim.citations
    assert "[smith2024]" not in found_claim.text


def test_build_output_rotation(tmp_path: Path) -> None:
    from paperforge.commands import build

    init.run(tmp_path)
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: Test claim.\nexperiment: exp_01\nsections: [results]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        "id: exp_01\ndescription: Test exp\nhardware: CPU\ndataset: D\nseed: 1\nmetrics: {acc: 90.0}\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "paper_generated" / "current"
    prev_dir = tmp_path / "paper_generated" / "previous"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "paper.tex").write_text("old tex", encoding="utf-8")

    build.run(tmp_path, force=True)

    assert (prev_dir / "paper.tex").exists()
    assert (prev_dir / "paper.tex").read_text(encoding="utf-8") == "old tex"


def test_export_overleaf_zip_path_and_missing_tex(tmp_path: Path) -> None:
    from paperforge.commands import export

    init.run(tmp_path)

    # Overleaf export fails cleanly if paper.tex missing
    with pytest.raises(SystemExit):
        export.run(tmp_path, fmt="overleaf", output=None)
