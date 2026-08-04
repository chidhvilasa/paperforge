"""Tests for Phase 36 Rendered PDF preflight, template fingerprinting, visual overlap, and structural integrity."""

from pathlib import Path

import fitz
import yaml

from paperforge.commands import init
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.services.pdf_preflight import (
    _classify_block_overlap,
    _find_orphan_reference_numerals,
)
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
    tex = "\\documentclass{acmart}\n\\title{Sample ACM Paper}\n\\author{Alice Smith}\n"
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
    (pf / "claims" / "c_raw.yaml").write_text(
        yaml.dump(claim.to_yaml()), encoding="utf-8"
    )

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
    (pf / "claims" / "c_road.yaml").write_text(
        yaml.dump(claim.to_yaml()), encoding="utf-8"
    )

    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project, mode="submission")
    assert any(i.code == "SECTION_ROADMAP_MISMATCH" for i in issues)


def test_duplicate_latex_label_detected(tmp_path: Path) -> None:
    _init_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    tex = "\\label{fig_01}\n\\label{fig_01}\n"
    res = check_structural_integrity(
        project, tmp_path, mode="submission", tex_content=tex
    )
    assert not res.passed
    assert any(i["code"] == "DUPLICATE_OR_CONFLICTING_LABEL" for i in res.issues)


def test_unresolved_cross_reference_detected(tmp_path: Path) -> None:
    _init_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    tex = "As seen in [?] and ??."
    res = check_structural_integrity(
        project, tmp_path, mode="submission", tex_content=tex
    )
    assert any(i["code"] == "UNRESOLVED_CROSS_REFERENCE" for i in res.issues)


def test_reference_verification_offline_pass(tmp_path: Path) -> None:
    _init_project(tmp_path)
    project = PaperForgeProject.load(tmp_path)
    rep = verify_references(project, tmp_path, online=False)
    assert rep.passed


# --- v1.5.3: drop-cap-aware overlap classification ---------------------


def _overlap_block(x0: float, y0: float, x1: float, y1: float, text: str) -> tuple:
    return (x0, y0, x1, y1, text, 0, 0)


def test_classify_overlap_legitimate_dropcap_wrap() -> None:
    """Real-world evidence from an external integration report: a short
    heading-sized block sitting directly above a much taller multi-line
    paragraph block, overlapping only at their shared boundary -- the
    classic IEEEPARstart drop-cap block-clustering artifact.
    """
    heading = _overlap_block(50.0, 469.9, 250.0, 512.8, "I. INTRODUCTION V")
    paragraph = _overlap_block(
        50.0, 485.4, 350.0, 615.0, "EHICULAR Ad hoc Networks require secure..."
    )
    inter = fitz.Rect(heading[0], heading[1], heading[2], heading[3]) & fitz.Rect(
        paragraph[0], paragraph[1], paragraph[2], paragraph[3]
    )
    assert (
        _classify_block_overlap(heading, paragraph, inter) == "LEGITIMATE_DROPCAP_WRAP"
    )
    # Order-independence: same result regardless of argument order.
    assert (
        _classify_block_overlap(paragraph, heading, inter) == "LEGITIMATE_DROPCAP_WRAP"
    )


def test_classify_overlap_dropcap_in_heading_block_short_paragraph() -> None:
    """Variant actually reproduced against a short neutral fixture: the
    drop-cap glyph lands in the *heading* block's own trailing line
    ("I. INTRODUCTION\\nT") while the paragraph block is short (a couple
    of lines), so the heading block is *taller* than the paragraph --
    the inverse of the primary evidence case. Geometry-only heuristics
    based on "heading is the short block" would miss this; the
    split-word text signal catches it independent of block height.
    """
    heading = _overlap_block(48.96, 204.17, 213.38, 246.59, "I. INTRODUCTION\nT\n")
    paragraph = _overlap_block(
        69.47,
        219.24,
        300.02,
        241.18,
        "HE example system achieves strong performance across\nall evaluated conditions.\n",
    )
    inter = fitz.Rect(heading[0], heading[1], heading[2], heading[3]) & fitz.Rect(
        paragraph[0], paragraph[1], paragraph[2], paragraph[3]
    )
    assert (
        _classify_block_overlap(heading, paragraph, inter) == "LEGITIMATE_DROPCAP_WRAP"
    )


def test_classify_overlap_never_exempts_index_terms_collision() -> None:
    """Same drop-cap-shaped geometry, but one block is genuinely Index
    Terms -- this is the real, previously-tracked defect class and must
    never be exempted regardless of geometry.
    """
    heading = _overlap_block(50.0, 469.9, 250.0, 512.8, "I. INTRODUCTION")
    index_terms = _overlap_block(
        50.0, 485.4, 350.0, 615.0, "Index Terms\u2014security, authentication, networks"
    )
    inter = fitz.Rect(heading[0], heading[1], heading[2], heading[3]) & fitz.Rect(
        index_terms[0], index_terms[1], index_terms[2], index_terms[3]
    )
    assert (
        _classify_block_overlap(heading, index_terms, inter) == "CROSS_REGION_COLLISION"
    )


def test_classify_overlap_real_body_text_collision_not_exempted() -> None:
    """Two ordinary paragraph-sized blocks deeply overlapping each other
    (neither is heading-sized) -- a genuine collision, must not be
    exempted."""
    b1 = _overlap_block(50.0, 200.0, 300.0, 260.0, "First unrelated paragraph of text.")
    b2 = _overlap_block(
        60.0, 210.0, 310.0, 270.0, "Second unrelated paragraph of text."
    )
    inter = fitz.Rect(b1[0], b1[1], b1[2], b1[3]) & fitz.Rect(
        b2[0], b2[1], b2[2], b2[3]
    )
    assert _classify_block_overlap(b1, b2, inter) == "TRUE_TEXT_OCCLUSION"


def test_classify_overlap_glyph_embedded_inside_paragraph_not_exempted() -> None:
    """A short block positioned *inside* (not stacked above) a tall block
    -- an oversized glyph in the middle of a paragraph rather than a
    leading drop cap -- must not be exempted."""
    tall = _overlap_block(
        50.0, 100.0, 350.0, 300.0, "A long multi-line paragraph of body text."
    )
    short = _overlap_block(150.0, 180.0, 200.0, 220.0, "X")
    inter = fitz.Rect(tall[0], tall[1], tall[2], tall[3]) & fitz.Rect(
        short[0], short[1], short[2], short[3]
    )
    assert _classify_block_overlap(tall, short, inter) == "TRUE_TEXT_OCCLUSION"


def test_classify_overlap_low_horizontal_overlap_not_exempted() -> None:
    """A short block and a tall block that barely share any horizontal
    span (different columns) must not be exempted as a drop cap."""
    heading = _overlap_block(50.0, 469.9, 100.0, 512.8, "I.")
    paragraph = _overlap_block(
        320.0, 485.4, 560.0, 615.0, "Unrelated second-column text."
    )
    inter = fitz.Rect(heading[0], heading[1], heading[2], heading[3]) & fitz.Rect(
        paragraph[0], paragraph[1], paragraph[2], paragraph[3]
    )
    # No geometric intersection at all in this case -- but if extraction
    # noise ever produced a technically-touching rect, it must still not
    # be classified as a legitimate drop cap given near-zero column overlap.
    if inter.is_valid and not inter.is_empty:
        assert (
            _classify_block_overlap(heading, paragraph, inter)
            != "LEGITIMATE_DROPCAP_WRAP"
        )


# --- v1.5.3: orphan reference numeral (Roman heading adjacency) --------


def test_orphan_numeral_true_positive_still_detected() -> None:
    text = "The system improves security (see Fig. 1) I have shown."
    matches = _find_orphan_reference_numerals(text)
    assert matches == ["(see Fig. 1) I"]


def test_orphan_numeral_not_flagged_before_roman_heading_single_letter() -> None:
    text = "...secure broadcast (see Fig. 1)\nI. Traffic Density Sweep\nWe now..."
    assert _find_orphan_reference_numerals(text) == []


def test_orphan_numeral_not_flagged_before_roman_heading_multi_letter() -> None:
    text = "...latency budget (see Fig. 1)\nVII. Discussion\nThis section..."
    assert _find_orphan_reference_numerals(text) == []


def test_orphan_numeral_not_flagged_for_table_citation_heading() -> None:
    text = "...as shown (see Table 2)\nIV. Results\nWe report..."
    assert _find_orphan_reference_numerals(text) == []


def test_orphan_numeral_flagged_with_no_trailing_heading() -> None:
    text = "A broken citation artifact (see Fig. 1) I"
    assert _find_orphan_reference_numerals(text) == ["(see Fig. 1) I"]
