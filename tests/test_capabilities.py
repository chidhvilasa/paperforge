"""Tests for Phase 33 capabilities: merge import, sync, biography, AI disclosure,
validate, doctor improvements."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from paperforge.commands import init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import Biography, PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _init_project(tmp_path: Path) -> None:
    """Initialize a minimal paperforge project."""
    init.run(tmp_path)


def _fix_errors(tmp_path: Path) -> None:
    """Fix blocking errors by adding result claim + experiment."""
    pf = tmp_path / ".paperforge"
    # Create a minimal experiment
    exp = Experiment(
        id="exp_01",
        metrics={"accuracy": 98.4},
        dataset="test",
        seed=42,
    )
    _write_yaml(pf / "experiments" / "exp_01.yaml", exp.to_yaml())
    # Create a results claim
    claim = Claim(
        id="claim_results",
        text="System achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results"],
        status="verified",
    )
    _write_yaml(pf / "claims" / "claim_results.yaml", claim.to_yaml())


# ---------------------------------------------------------------------------
# CAPABILITY 1 — Import merge mode
# ---------------------------------------------------------------------------

def test_import_merge_does_not_duplicate(tmp_path: Path) -> None:
    """Running import twice on same content should not create duplicate claims."""
    from paperforge.commands.import_content import run as import_run

    _init_project(tmp_path)
    _write_md(
        tmp_path / "paper_information" / "content" / "abstract.md",
        "This paper presents a novel approach to vehicular networking.\n",
    )

    import_run(project_root=tmp_path, section=None, force=False)
    claims_after_first = list((tmp_path / ".paperforge" / "claims").glob("*.yaml"))
    n_first = len(claims_after_first)

    import_run(project_root=tmp_path, section=None, force=False)
    claims_after_second = list((tmp_path / ".paperforge" / "claims").glob("*.yaml"))
    n_second = len(claims_after_second)

    assert n_second == n_first, (
        f"Duplicate claims created: {n_first} after first import, {n_second} after second"
    )


def test_import_hash_set_on_new_claims(tmp_path: Path) -> None:
    """New claims created by import should have a non-empty import_hash."""
    from paperforge.commands.import_content import run as import_run

    _init_project(tmp_path)
    _write_md(
        tmp_path / "paper_information" / "content" / "abstract.md",
        "Autonomous vehicles require robust communication protocols.\n",
    )

    import_run(project_root=tmp_path, section=None, force=False)
    project = PaperForgeProject.load(tmp_path)
    abstract_claims = [c for c in project.claims if "abstract" in c.sections]
    assert abstract_claims, "No abstract claims were created"
    claim = abstract_claims[0]
    assert claim.import_hash != "", f"import_hash is empty on {claim.id}"


def test_import_force_updates_not_appends(tmp_path: Path) -> None:
    """import --force should update existing claims (same hash) rather than creating duplicates.

    Force updates a claim only when its hash matches (same paragraph identity).
    In this test we verify that re-importing identical content with --force
    does not increase the number of claims.
    """
    from paperforge.commands.import_content import run as import_run

    _init_project(tmp_path)
    md_path = tmp_path / "paper_information" / "content" / "abstract.md"
    # Use content that is well-known
    _write_md(md_path, "This paper presents a novel routing protocol for VANET.\n")

    import_run(project_root=tmp_path, section=None, force=False)
    claims_after_first = list((tmp_path / ".paperforge" / "claims").glob("*.yaml"))
    n_first = len(claims_after_first)

    # Run import --force on identical content — should not create more claims
    import_run(project_root=tmp_path, section=None, force=True)
    claims_after_force = list((tmp_path / ".paperforge" / "claims").glob("*.yaml"))
    n_force = len(claims_after_force)

    assert n_force == n_first, (
        f"--force created new claims with identical content: {n_first} → {n_force}"
    )



# ---------------------------------------------------------------------------
# CAPABILITY 2 — Sync command
# ---------------------------------------------------------------------------

def test_sync_to_md_writes_sections(tmp_path: Path) -> None:
    """sync --direction to-md should write .md files from claims."""
    from paperforge.commands.sync import run as sync_run

    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    claim = Claim(
        id="claim_01",
        text="Test result claim.",
        experiment="",
        sections=["results"],
        status="unverified",
    )
    _write_yaml(pf / "claims" / "claim_01.yaml", claim.to_yaml())

    sync_run(project_root=tmp_path, direction="to-md", force=True)

    results_md = tmp_path / "paper_information" / "content" / "results.md"
    assert results_md.exists(), "results.md was not created by sync to-md"
    content = results_md.read_text(encoding="utf-8")
    assert "Test result claim." in content, "Claim text not found in results.md"


def test_sync_status_shows_divergence(tmp_path: Path) -> None:
    """sync --direction status should not crash."""
    from paperforge.commands.sync import run as sync_run

    _init_project(tmp_path)
    # Should complete without raising
    sync_run(project_root=tmp_path, direction="status", force=False)


# ---------------------------------------------------------------------------
# CAPABILITY 3 — Biography support
# ---------------------------------------------------------------------------

def test_biography_in_paper_yaml(tmp_path: Path) -> None:
    """Biographies set in paper.yaml should be loaded into ProjectConfig."""
    _init_project(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["biographies"] = [
        {"author": "A. Author", "text": "A. Author received the Ph.D. degree.", "photo_path": ""}
    ]
    paper_yaml.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    assert len(project.config.biographies) == 1
    assert project.config.biographies[0].author == "A. Author"


def test_biography_emits_ieeebio_nophoto(tmp_path: Path) -> None:
    """Build should emit IEEEbiographynophoto when photo_path is empty."""
    from paperforge.commands.build import run as build_run

    _init_project(tmp_path)
    _fix_errors(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["biographies"] = [
        {"author": "A. Author", "text": "Brief biography here.", "photo_path": ""}
    ]
    paper_yaml.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    build_run(project_root=tmp_path, force_anyway=True, no_reveal=True)
    output_dir = tmp_path / ".paperforge" / "output"
    # Find the generated paper.tex in any output directory
    tex_files = list(tmp_path.rglob("paper.tex"))
    assert tex_files, "paper.tex not generated"
    content = tex_files[0].read_text(encoding="utf-8")
    assert "IEEEbiographynophoto" in content, "IEEEbiographynophoto not found in paper.tex"


def test_biography_emits_ieeebio_with_photo(tmp_path: Path) -> None:
    """Build should emit IEEEbiography with photo path when photo_path is set."""
    from paperforge.commands.build import run as build_run

    _init_project(tmp_path)
    _fix_errors(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["biographies"] = [
        {
            "author": "A. Author",
            "text": "Brief biography here.",
            "photo_path": "figures/photo.jpg",
        }
    ]
    paper_yaml.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    build_run(project_root=tmp_path, force_anyway=True, no_reveal=True)
    tex_files = list(tmp_path.rglob("paper.tex"))
    assert tex_files, "paper.tex not generated"
    content = tex_files[0].read_text(encoding="utf-8")
    assert "IEEEbiography" in content
    assert "figures/photo.jpg" in content


# ---------------------------------------------------------------------------
# CAPABILITY 4 — AI disclosure
# ---------------------------------------------------------------------------

def test_ai_disclosure_emitted(tmp_path: Path) -> None:
    """Build should emit AI disclosure section when ai_disclosure is set."""
    from paperforge.commands.build import run as build_run

    _init_project(tmp_path)
    _fix_errors(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["ai_disclosure"] = "No AI tools were used in this work."
    paper_yaml.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    build_run(project_root=tmp_path, force_anyway=True, no_reveal=True)
    tex_files = list(tmp_path.rglob("paper.tex"))
    assert tex_files, "paper.tex not generated"
    content = tex_files[0].read_text(encoding="utf-8")
    assert "Artificial Intelligence" in content
    assert "No AI tools were used in this work." in content


def test_ai_disclosure_empty_no_section(tmp_path: Path) -> None:
    """Build should NOT emit AI disclosure section when ai_disclosure is empty."""
    from paperforge.commands.build import run as build_run

    _init_project(tmp_path)
    _fix_errors(tmp_path)
    # ai_disclosure defaults to "" — do not set it
    build_run(project_root=tmp_path, force_anyway=True, no_reveal=True)
    tex_files = list(tmp_path.rglob("paper.tex"))
    assert tex_files, "paper.tex not generated"
    content = tex_files[0].read_text(encoding="utf-8")
    assert "Artificial Intelligence" not in content


# ---------------------------------------------------------------------------
# CAPABILITY 5 — Validate command
# ---------------------------------------------------------------------------

def test_validate_command_runs(tmp_path: Path) -> None:
    """validate.run() should complete without crashing."""
    from paperforge.commands.validate import run as validate_run

    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    exp = Experiment(id="exp_01", metrics={"accuracy": 98.4}, dataset="test", seed=42)
    _write_yaml(pf / "experiments" / "exp_01.yaml", exp.to_yaml())
    claim = Claim(
        id="claim_01",
        text="System achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results"],
        status="unverified",
    )
    _write_yaml(pf / "claims" / "claim_01.yaml", claim.to_yaml())

    validate_run(project_root=tmp_path, output=None)


def test_validate_writes_log(tmp_path: Path) -> None:
    """validate should write VALIDATION_LOG.md to paper_information/."""
    from paperforge.commands.validate import run as validate_run

    _init_project(tmp_path)
    _fix_errors(tmp_path)
    validate_run(project_root=tmp_path, output=None)

    log = tmp_path / "paper_information" / "VALIDATION_LOG.md"
    assert log.exists(), "VALIDATION_LOG.md was not created"


# ---------------------------------------------------------------------------
# CAPABILITY 7 — Doctor output improvements
# ---------------------------------------------------------------------------

def test_doctor_json_output(tmp_path: Path) -> None:
    """collect_issues() should return list of Issue objects with required attributes."""
    _init_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert isinstance(issues, list)
    assert all(hasattr(i, "code") for i in issues)
    assert all(hasattr(i, "severity") for i in issues)
    assert all(hasattr(i, "message") for i in issues)


def test_missing_biography_warning(tmp_path: Path) -> None:
    """MISSING_BIOGRAPHY warning should fire when authors set but no biographies."""
    _init_project(tmp_path)
    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["authors"] = ["A. Author"]
    data.pop("biographies", None)  # ensure not set
    paper_yaml.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "MISSING_BIOGRAPHY" for i in issues), (
        "MISSING_BIOGRAPHY not raised when authors set but biographies empty"
    )


def test_missing_ai_disclosure_info(tmp_path: Path) -> None:
    """MISSING_AI_DISCLOSURE info should always fire (no ai_disclosure set)."""
    _init_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "MISSING_AI_DISCLOSURE" for i in issues), (
        "MISSING_AI_DISCLOSURE info not raised"
    )
