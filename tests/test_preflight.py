"""Tests for Phase 36 Rendered PDF preflight, template fingerprinting, visual overlap, and structural integrity."""

from pathlib import Path

import yaml

from paperforge.commands import init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.services.reference_verifier import verify_references
from paperforge.services.structural_integrity import (
    check_structural_integrity,
    resolve_symbolic_references,
)
from paperforge.services.template_fingerprint import verify_template_fingerprint


def _init_project(tmp_path: Path) -> None:
    init.run(tmp_path)


def test_template_fingerprint_ieee_access_pass() -> None:
    tex = (
        "\\documentclass[journal,access]{IEEEtran}\n"
        "\\journalid{10.1109/ACCESS.2024.123456}\n"
        "\\title{Sample IEEE Access Paper}\n"
        "\\author{Alice Smith}\n"
        "\\begin{document}\n"
        "\\begin{abstract}Abstract text\\end{abstract}\n"
        "\\begin{keywords}keyword1, keyword2\\end{keywords}\n"
        "\\end{document}\n"
    )
    fp = verify_template_fingerprint(tex, "ieee-access")
    assert fp.passed
    assert fp.status == "VERIFIED"


def test_template_fingerprint_mismatch_detected() -> None:
    tex = (
        "\\documentclass{acmart}\n"
        "\\title{Sample ACM Paper}\n"
        "\\author{Alice Smith}\n"
    )
    fp = verify_template_fingerprint(tex, "ieee-access")
    assert not fp.passed
    assert fp.status == "MISMATCH"
    assert any("documentclass" in m for m in fp.mismatched_files)


def test_raw_latex_escape_corruption_detected(tmp_path: Path) -> None:
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    claim = Claim(
        id="c_raw",
        text="The system achieves extbf{Low} latency.",
        experiment="exp_01",
        sections=["results"],
    )
    (pf / "claims" / "c_raw.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project)
    assert any(i.code == "RAW_LATEX_ESCAPE_CORRUPTION" for i in issues)


def test_symbolic_references_resolution(tmp_path: Path) -> None:
    _init_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    prose = "As discussed in {{section:introduction}} and shown in {{figure:fig_01}} and {{table:tbl_01}}."
    resolved = resolve_symbolic_references(prose, project)
    assert "Section I" in resolved or "Section 1" in resolved


def test_section_roadmap_mismatch_detected(tmp_path: Path) -> None:
    _init_project(tmp_path)
    pf = tmp_path / ".paperforge"
    claim = Claim(
        id="c_road",
        text="Section IV describes introduction and background.",
        experiment="exp_01",
        sections=["results"],
    )
    (pf / "claims" / "c_road.yaml").write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project, mode="submission")
    assert any(i.code == "SECTION_ROADMAP_MISMATCH" for i in issues)


def test_duplicate_latex_label_detected(tmp_path: Path) -> None:
    _init_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    tex = "\\label{fig_01}\n\\label{fig_01}\n"
    res = check_structural_integrity(project, tmp_path, mode="submission", tex_content=tex)
    assert not res.passed
    assert any(i["code"] == "DUPLICATE_OR_CONFLICTING_LABEL" for i in res.issues)


def test_unresolved_cross_reference_detected(tmp_path: Path) -> None:
    _init_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    tex = "As seen in [?] and ??."
    res = check_structural_integrity(project, tmp_path, mode="submission", tex_content=tex)
    assert any(i["code"] == "UNRESOLVED_CROSS_REFERENCE" for i in res.issues)


def test_reference_verification_offline_pass(tmp_path: Path) -> None:
    _init_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    rep = verify_references(project, tmp_path, online=False)
    assert rep.passed
