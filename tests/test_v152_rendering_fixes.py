"""Regression tests for the v1.5.2 rendering/validation correction:

1. Portable figure asset resolution (project-root-relative source, package-
   relative LaTeX path, submission-mode blocking on unresolved assets).
2. IEEE Access first-section heading policy (no unconditional
   \\IEEEraisesectionheading -> no Index Terms overlap).
3. Output rotation isolation (candidate output directories never share or
   clobber each other's archive).
4. Domain-independent PVALUE_AMBIGUOUS classification (no false positives
   on hyphenated/labeled identifiers).

All fixtures are synthetic and use fictional data only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from paperforge.commands import build, init
from paperforge.commands.build import _rotate_output, resolve_figure_asset
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject, ProjectConfig
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment
from paperforge.models.figure import Figure
from paperforge.venues.ieee import IEEEPlugin
from paperforge.venues.ieee_access import IEEEAccessPlugin


def _mock_project(
    figures=None, claims=None, root: Path = Path(".")
) -> PaperForgeProject:
    config = ProjectConfig(
        version="0.1",
        title="Example Paper",
        authors=["Alex Example"],
        venue="ieee",
        status="draft",
        sections=[],
        build_output_dir=".",
        latex_template="ieee",
    )
    return PaperForgeProject(
        root=root,
        config=config,
        claims=claims or [],
        experiments=[],
        figures=figures or [],
    )


def _init_project(tmp_path: Path) -> None:
    init.run(tmp_path)


# --- Issue 1: portable figure asset resolution ---------------------------


def test_resolve_figure_asset_finds_nested_source(tmp_path: Path) -> None:
    asset = tmp_path / "assets" / "plots" / "figure-01.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF-fake")
    fig = Figure(id="fig_01", caption="Cap", path="assets/plots/figure-01.pdf")

    resolved = resolve_figure_asset(fig, tmp_path)
    assert resolved == "assets/plots/figure-01.pdf"


def test_resolve_figure_asset_copies_into_output_dir(tmp_path: Path) -> None:
    asset = tmp_path / "figures" / "result.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"fake-png")
    output_dir = tmp_path / "paper_generated" / "current"
    output_dir.mkdir(parents=True)

    fig = Figure(id="fig_01", caption="Cap", path="figures/result.png")
    resolved = resolve_figure_asset(fig, tmp_path, output_dir)

    assert resolved == "figures/result.png"
    assert (output_dir / "figures" / "result.png").is_file()
    assert (output_dir / "figures" / "result.png").read_bytes() == b"fake-png"


def test_resolve_figure_asset_rejects_absolute_and_parent_escape(
    tmp_path: Path,
) -> None:
    fig_abs = Figure(id="fig_01", caption="Cap", path="/etc/passwd")
    fig_win_abs = Figure(id="fig_02", caption="Cap", path="C:\\secrets\\figure.png")
    fig_escape = Figure(id="fig_03", caption="Cap", path="../../outside/figure.png")

    assert resolve_figure_asset(fig_abs, tmp_path) is None
    assert resolve_figure_asset(fig_win_abs, tmp_path) is None
    assert resolve_figure_asset(fig_escape, tmp_path) is None


def test_resolve_figure_asset_missing_source_returns_none(tmp_path: Path) -> None:
    fig = Figure(id="fig_01", caption="Cap", path="assets/missing.png")
    assert resolve_figure_asset(fig, tmp_path) is None


def test_figure_collision_preserves_directory_structure(tmp_path: Path) -> None:
    (tmp_path / "section-a").mkdir()
    (tmp_path / "section-b").mkdir()
    (tmp_path / "section-a" / "plot.png").write_bytes(b"AAAA")
    (tmp_path / "section-b" / "plot.png").write_bytes(b"BBBB")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    fig_a = Figure(id="fig_a", caption="A", path="section-a/plot.png")
    fig_b = Figure(id="fig_b", caption="B", path="section-b/plot.png")

    resolved_a = resolve_figure_asset(fig_a, tmp_path, output_dir)
    resolved_b = resolve_figure_asset(fig_b, tmp_path, output_dir)

    assert resolved_a == "section-a/plot.png"
    assert resolved_b == "section-b/plot.png"
    assert (output_dir / "section-a" / "plot.png").read_bytes() == b"AAAA"
    assert (output_dir / "section-b" / "plot.png").read_bytes() == b"BBBB"


def test_generated_latex_uses_package_relative_path_not_project_root(
    tmp_path: Path,
) -> None:
    """Reproduces the reported bug: figure exists, but the generated LaTeX
    path must resolve the same way relative to the *output* directory as
    it does relative to project_root -- never silently drop to a
    placeholder when the asset is genuinely present.
    """
    from paperforge.commands.build import _generate_sections

    asset = tmp_path / "assets" / "figure.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF-fake")
    output_dir = tmp_path / "paper_generated" / "current"
    output_dir.mkdir(parents=True)

    fig = Figure(id="fig_01", caption="Cap", path="assets/figure.pdf")
    claim = Claim(
        id="c1",
        text="Text",
        sections=["introduction"],
        figures=["fig_01"],
        experiment="",
    )
    project = _mock_project(figures=[fig], claims=[claim], root=tmp_path)

    latex = _generate_sections(["introduction"], project, output_dir)

    assert "Figure placeholder" not in latex
    assert "\\includegraphics[width=\\columnwidth]{assets/figure.pdf}" in latex
    assert (output_dir / "assets" / "figure.pdf").is_file()


def test_no_absolute_paths_in_generated_latex(tmp_path: Path) -> None:
    from paperforge.commands.build import _generate_sections

    asset = tmp_path / "figures" / "fig.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"x")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    fig = Figure(id="fig_01", caption="Cap", path="figures/fig.png")
    claim = Claim(
        id="c1",
        text="Text",
        sections=["introduction"],
        figures=["fig_01"],
        experiment="",
    )
    project = _mock_project(figures=[fig], claims=[claim], root=tmp_path)

    latex = _generate_sections(["introduction"], project, output_dir)
    assert str(tmp_path) not in latex


def test_draft_mode_missing_figure_allows_build_with_warning(
    tmp_path: Path, capsys
) -> None:
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    exp = Experiment(id="exp_01", metrics={"score": 1.0})
    (pf / "experiments" / "exp_01.yaml").write_text(
        yaml.dump(exp.to_yaml()), encoding="utf-8"
    )
    claim = Claim(
        id="claim_01",
        text="This model performs well.",
        experiment="exp_01",
        sections=["results"],
        status="verified",
        figures=["fig_missing"],
    )
    (pf / "claims" / "claim_01.yaml").write_text(
        yaml.dump(claim.to_yaml()), encoding="utf-8"
    )
    fig = Figure(
        id="fig_missing", caption="Missing asset", path="figures/does_not_exist.png"
    )
    (pf / "figures" / "fig_missing.yaml").write_text(
        yaml.dump(fig.to_yaml()), encoding="utf-8"
    )

    # Draft mode must not raise even though the figure asset is missing.
    build.run(tmp_path, mode="draft")

    tex_path = tmp_path / "paper_generated" / "current" / "paper.tex"
    assert "Figure placeholder" in tex_path.read_text(encoding="utf-8")


def test_submission_mode_blocks_on_missing_figure_asset(tmp_path: Path) -> None:
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    paper_yaml = pf / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8")) or {}
    data["authors"] = [
        {"given_name": "Alex", "family_name": "Example", "display_name": "Alex Example"}
    ]
    data["title"] = "Example Paper"
    paper_yaml.write_text(yaml.dump(data), encoding="utf-8")

    exp = Experiment(id="exp_01", metrics={"score": 1.0})
    (pf / "experiments" / "exp_01.yaml").write_text(
        yaml.dump(exp.to_yaml()), encoding="utf-8"
    )
    claim = Claim(
        id="claim_01",
        text="This model performs well.",
        experiment="exp_01",
        sections=["results"],
        status="verified",
    )
    (pf / "claims" / "claim_01.yaml").write_text(
        yaml.dump(claim.to_yaml()), encoding="utf-8"
    )
    fig = Figure(
        id="fig_missing", caption="Missing asset", path="figures/does_not_exist.png"
    )
    (pf / "figures" / "fig_missing.yaml").write_text(
        yaml.dump(fig.to_yaml()), encoding="utf-8"
    )

    with pytest.raises(SystemExit) as exc:
        build.run(tmp_path, mode="submission")
    assert exc.value.code == 1

    # Submission mode must never have silently written a placeholder PDF/tex.
    tex_path = tmp_path / "paper_generated" / "current" / "paper.tex"
    assert not tex_path.exists() or "Figure placeholder" not in tex_path.read_text(
        encoding="utf-8"
    )


# --- Issue 2: IEEE Access first-section heading policy --------------------


def test_ieee_access_policy_is_normal_section() -> None:
    plugin = IEEEAccessPlugin()
    assert plugin.first_section_heading_policy == "normal_section"


def test_generic_ieee_journal_policy_is_raised_section() -> None:
    plugin = IEEEPlugin(mode="journal", name="ieee-journal")
    assert plugin.first_section_heading_policy == "raised_section"


def test_ieee_access_build_has_no_raised_heading(tmp_path: Path) -> None:
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    exp = Experiment(id="exp_01", metrics={"score": 1.0})
    (pf / "experiments" / "exp_01.yaml").write_text(
        yaml.dump(exp.to_yaml()), encoding="utf-8"
    )
    claim = Claim(
        id="claim_01",
        text="This model performs well.",
        experiment="exp_01",
        sections=["introduction", "results"],
        status="verified",
    )
    (pf / "claims" / "claim_01.yaml").write_text(
        yaml.dump(claim.to_yaml()), encoding="utf-8"
    )

    build.run(tmp_path, target="ieee-access")
    tex = (tmp_path / "paper_generated" / "current" / "paper.tex").read_text(
        encoding="utf-8"
    )
    assert "\\IEEEraisesectionheading" not in tex
    assert "\\section{Introduction}\\label{sec:introduction}" in tex


def test_ieee_journal_build_still_has_raised_heading(tmp_path: Path) -> None:
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    exp = Experiment(id="exp_01", metrics={"score": 1.0})
    (pf / "experiments" / "exp_01.yaml").write_text(
        yaml.dump(exp.to_yaml()), encoding="utf-8"
    )
    claim = Claim(
        id="claim_01",
        text="This model performs well.",
        experiment="exp_01",
        sections=["introduction", "results"],
        status="verified",
    )
    (pf / "claims" / "claim_01.yaml").write_text(
        yaml.dump(claim.to_yaml()), encoding="utf-8"
    )

    build.run(tmp_path, target="ieee-journal")
    tex = (tmp_path / "paper_generated" / "current" / "paper.tex").read_text(
        encoding="utf-8"
    )
    assert "\\IEEEraisesectionheading" in tex


# --- Issue 3: output rotation isolation -----------------------------------


def test_candidate_rotation_does_not_touch_current_or_previous(tmp_path: Path) -> None:
    current_dir = tmp_path / "output" / "current"
    previous_dir = tmp_path / "output" / "previous"
    candidate_dir = tmp_path / "output" / "candidate-a"
    current_dir.mkdir(parents=True)
    previous_dir.mkdir(parents=True)
    candidate_dir.mkdir(parents=True)
    (current_dir / "paper.pdf").write_bytes(b"CURRENT")
    (previous_dir / "paper.pdf").write_bytes(b"PREVIOUS")
    (candidate_dir / "paper.pdf").write_bytes(b"OLD-CANDIDATE")

    _rotate_output(tmp_path, candidate_dir, policy="preserve_previous")

    assert (current_dir / "paper.pdf").read_bytes() == b"CURRENT"
    assert (previous_dir / "paper.pdf").read_bytes() == b"PREVIOUS"
    # Candidate's own archive is scoped to its own name, not the shared "previous".
    candidate_archive = tmp_path / "output" / "candidate-a.previous"
    assert candidate_archive.is_dir()
    assert (candidate_archive / "paper.pdf").read_bytes() == b"OLD-CANDIDATE"


def test_two_candidate_builds_do_not_clobber_each_other(tmp_path: Path) -> None:
    cand_a = tmp_path / "output" / "candidate-a"
    cand_b = tmp_path / "output" / "candidate-b"
    cand_a.mkdir(parents=True)
    cand_b.mkdir(parents=True)
    (cand_a / "paper.pdf").write_bytes(b"A")
    (cand_b / "paper.pdf").write_bytes(b"B")

    _rotate_output(tmp_path, cand_a, policy="preserve_previous")
    _rotate_output(tmp_path, cand_b, policy="preserve_previous")

    archive_a = tmp_path / "output" / "candidate-a.previous"
    archive_b = tmp_path / "output" / "candidate-b.previous"
    assert archive_a.is_dir() and (archive_a / "paper.pdf").read_bytes() == b"A"
    assert archive_b.is_dir() and (archive_b / "paper.pdf").read_bytes() == b"B"


def test_rotation_disabled_policy_does_nothing(tmp_path: Path) -> None:
    out_dir = tmp_path / "output" / "current"
    out_dir.mkdir(parents=True)
    (out_dir / "paper.pdf").write_bytes(b"X")

    _rotate_output(tmp_path, out_dir, policy="disabled")

    assert not (tmp_path / "output" / "previous").exists()


def test_rotation_timestamped_policy_creates_unique_archive(tmp_path: Path) -> None:
    out_dir = tmp_path / "output" / "current"
    out_dir.mkdir(parents=True)
    (out_dir / "paper.pdf").write_bytes(b"X")

    _rotate_output(tmp_path, out_dir, policy="timestamped")

    archives = list((tmp_path / "output").glob("current_archive_*"))
    assert len(archives) == 1
    assert (archives[0] / "paper.pdf").read_bytes() == b"X"


def test_rotation_rejects_archive_equal_to_output(tmp_path: Path) -> None:
    out_dir = tmp_path / "output" / "current"
    out_dir.mkdir(parents=True)
    (out_dir / "paper.pdf").write_bytes(b"X")

    # Explicit archive_dir identical to output_dir must be a safe no-op,
    # never a self-referential copy.
    _rotate_output(tmp_path, out_dir, archive_dir=out_dir)
    assert (out_dir / "paper.pdf").read_bytes() == b"X"


def test_rotation_rejects_archive_nested_inside_output(tmp_path: Path) -> None:
    out_dir = tmp_path / "output" / "current"
    out_dir.mkdir(parents=True)
    (out_dir / "paper.pdf").write_bytes(b"X")
    nested_archive = out_dir / "archive"

    _rotate_output(tmp_path, out_dir, archive_dir=nested_archive)
    # Must not have recursively created/copied into itself.
    assert not nested_archive.exists()


def test_build_output_rotation_default_current_previous_unchanged(
    tmp_path: Path,
) -> None:
    """Backward-compatibility: default 'current' -> sibling 'previous' pairing
    must keep working exactly as before this fix."""
    _init_project(tmp_path)
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


# --- Issue 4: PVALUE_AMBIGUOUS classifier ----------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "The improvement was 73.6% and the reduction was 5% (p=0.002).",
        "Accuracy rose to 91.2% while error fell to 3.1% (p < .01).",
        "Score A was 12.5 and score B was 7.3, p-value of .03.",
    ],
)
def test_pvalue_ambiguous_true_positive(tmp_path: Path, text: str) -> None:
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    claim = Claim(id="c_pv", text=text, experiment="exp_01", sections=["results"])
    (pf / "claims" / "c_pv.yaml").write_text(
        yaml.dump(claim.to_yaml()), encoding="utf-8"
    )

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "PVALUE_AMBIGUOUS" for i in issues)


@pytest.mark.parametrize(
    "text",
    [
        "Results for batch-50 and model-7 show p = .05.",
        "Using protocol-v2 and version 2 configurations, p < .01.",
        "In experiment 5 with sample 10, p-value of .03 was observed.",
        "See Section 3 and Figure 4 for details (p=0.04).",
        "The system achieved 91.2% accuracy (p=0.002).",
    ],
)
def test_pvalue_ambiguous_negative_fixture(tmp_path: Path, text: str) -> None:
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    claim = Claim(id="c_pv", text=text, experiment="exp_01", sections=["results"])
    (pf / "claims" / "c_pv.yaml").write_text(
        yaml.dump(claim.to_yaml()), encoding="utf-8"
    )

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert not any(i.code == "PVALUE_AMBIGUOUS" for i in issues)
