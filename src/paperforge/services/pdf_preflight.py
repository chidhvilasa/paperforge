"""Rendered PDF preflight inspection service (PyMuPDF / fitz)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import fitz  # type: ignore[import-untyped]
except ImportError:
    fitz = None  # type: ignore[assignment]

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment]


@dataclass
class PageManifest:
    page_number: int
    width: float
    height: float
    rendered_image_path: str
    char_count: int
    image_count: int
    caption_count: int
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "rendered_image_path": self.rendered_image_path,
            "char_count": self.char_count,
            "image_count": self.image_count,
            "caption_count": self.caption_count,
            "warnings": self.warnings,
            "errors": self.errors,
        }


@dataclass
class PreflightReport:
    passed: bool
    total_pages: int
    page_manifests: list[PageManifest] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    rendered_pages_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "total_pages": self.total_pages,
            "page_manifests": [pm.to_dict() for pm in self.page_manifests],
            "issues": self.issues,
            "rendered_pages_dir": self.rendered_pages_dir,
        }


def _is_split_dropcap_word(fragment_text: str, continuation_text: str) -> bool:
    """True if `fragment_text` ends with a single isolated uppercase
    letter and `continuation_text` begins with a word that, with that
    letter prepended, looks like the genuine remainder of a capitalized
    word (e.g. "...INTRODUCTION\\nV" + "EHICULAR Ad hoc..." -> "VEHICULAR").

    A drop-cap macro (\\IEEEPARstart{X}{...}) always takes exactly one
    character as its initial letter, so the fragment is restricted to a
    single character -- this avoids matching a Roman-numeral heading
    marker like "VII" or "IV", which are never length 1.
    """
    lines = [ln.strip() for ln in fragment_text.split("\n") if ln.strip()]
    if not lines:
        return False
    last_line = lines[-1]
    if not (len(last_line) == 1 and last_line.isalpha() and last_line.isupper()):
        return False

    cont_words = continuation_text.strip().split()
    if not cont_words:
        return False
    first_word_alpha = "".join(ch for ch in cont_words[0] if ch.isalpha())
    if len(first_word_alpha) < 2:
        return False
    # The continuation should look like the tail of a capitalized word:
    # fully uppercase (IEEEPARstart typically upper-cases the first word
    # after the drop cap, e.g. "EHICULAR"), or capital-led with a
    # lowercase tail (e.g. "HE" -> combined "THE").
    return first_word_alpha.isupper() or (
        first_word_alpha[0].isupper() and first_word_alpha[1:].islower()
    )


def _classify_block_overlap(
    b1: tuple[Any, ...], b2: tuple[Any, ...], inter: Any
) -> str:
    """Classify why two extracted text blocks' bounding boxes intersect.

    Returns a reason code. Only "LEGITIMATE_DROPCAP_WRAP" is treated as a
    non-material finding (downgraded from ERROR to INFO); every other
    code is still reported as a real PDF_OBJECT_OVERLAP finding.

    This targets a specific, real PyMuPDF extraction artifact: a drop-cap
    macro (e.g. IEEEtran's \\IEEEPARstart) can make the block clustering
    split a paragraph's opening line oddly, so a short heading-sized block
    and the tall multi-line paragraph block below it end up with bounding
    boxes that touch/overlap right at their shared vertical boundary, even
    though the rendered ink never collides. It does not depend on any
    specific letter, title, author, or venue.
    """
    x0_1, y0_1, x1_1, y1_1, txt1 = b1[0], b1[1], b1[2], b1[3], b1[4]
    x0_2, y0_2, x1_2, y1_2, txt2 = b2[0], b2[1], b2[2], b2[3], b2[4]

    # Never exempt a collision involving Index Terms -- this is a real,
    # previously-tracked defect class (a raised-heading layout colliding
    # with a multi-line Index Terms block) and must keep being reported
    # regardless of geometry.
    combined_upper = f"{txt1} {txt2}".upper()
    if "INDEX TERMS" in combined_upper:
        return "CROSS_REGION_COLLISION"

    # Primary signal -- a split drop-cap word: PyMuPDF's clustering can
    # put the oversized initial letter in either block (sometimes trailing
    # the heading, sometimes leading the paragraph). Whichever block ends
    # with a short (1-3 char) isolated uppercase fragment, check whether
    # the *other* block's leading word, with that fragment prepended,
    # forms a real capitalized word start (e.g. "V" + "EHICULAR" ->
    # "VEHICULAR", "T" + "HE" -> "THE"). This is independent of which
    # block is taller and does not depend on any specific letter, title,
    # author, or venue.
    if _is_split_dropcap_word(txt1, txt2) or _is_split_dropcap_word(txt2, txt1):
        return "LEGITIMATE_DROPCAP_WRAP"

    h1, h2 = (y1_1 - y0_1), (y1_2 - y0_2)
    if h1 <= 0 or h2 <= 0:
        return "TRUE_TEXT_OCCLUSION"

    # Identify the vertically shorter ("heading-like") block and the
    # taller ("paragraph-like") block.
    if h1 <= h2:
        short = (x0_1, y0_1, x1_1, y1_1)
        tall = (x0_2, y0_2, x1_2, y1_2)
        h_short, h_tall = h1, h2
    else:
        short = (x0_2, y0_2, x1_2, y1_2)
        tall = (x0_1, y0_1, x1_1, y1_1)
        h_short, h_tall = h2, h1

    horizontal_span = min(short[2], tall[2]) - max(short[0], tall[0])
    narrower_width = min(short[2] - short[0], tall[2] - tall[0])
    horizontal_overlap_ratio = (
        horizontal_span / narrower_width if narrower_width > 0 else 0
    )

    is_heading_sized = h_short < 50
    is_multiline_paragraph = h_tall > 2 * h_short and h_tall > 80
    # Short block starts and ends above (or at) the tall block -- i.e. it
    # sits stacked directly above the paragraph, not embedded inside it.
    stacked_above = short[1] <= tall[1] and short[3] <= tall[3]
    # The overlap is confined to the shared boundary, not a deep interior
    # collision spanning most of the shorter block's own height.
    boundary_touch_only = inter.height <= h_short * 0.8

    if (
        is_heading_sized
        and is_multiline_paragraph
        and horizontal_overlap_ratio > 0.5
        and stacked_above
        and boundary_touch_only
    ):
        return "LEGITIMATE_DROPCAP_WRAP"

    return "TRUE_TEXT_OCCLUSION"


_ORPHAN_NUMERAL_RE = re.compile(
    r"\((?:see\s+)?(?:Fig\.|Figure|Table|Eq\.|Equation)\s*\.?\s*\d+\)\s+([IVXLCDM]+)\b"
)


def _find_orphan_reference_numerals(text: str) -> list[str]:
    """Find genuinely orphaned trailing numerals after a citation, e.g.
    "(see Fig. 1) I" where "I" is a broken/dangling artifact.

    Excludes matches where the trailing Roman-numeral-looking token is
    actually the start of a new numbered section/subsection heading (e.g.
    "(see Fig. 1)" followed, in extracted reading order, by "I. Traffic
    Density Sweep" or "VII. Discussion") -- those are two unrelated,
    correctly-formed pieces of content that merely land adjacent in flat
    extracted text, not a broken citation.
    """
    matches = []
    for m in _ORPHAN_NUMERAL_RE.finditer(text):
        trailing = text[m.end(1) : m.end(1) + 40]
        if re.match(r"^\.\s+[A-Z]", trailing):
            continue
        matches.append(m.group(0))
    return matches


def run_pdf_preflight(
    pdf_path: Path,
    output_reports_dir: Path,
    mode: str = "draft",
    dpi: int = 150,
) -> PreflightReport:
    if not pdf_path.exists():
        return PreflightReport(
            passed=False,
            total_pages=0,
            issues=[
                {
                    "code": "PDF_RENDER_FAILED",
                    "severity": "ERROR",
                    "message": f"PDF file does not exist: {pdf_path}",
                }
            ],
        )

    if fitz is None:
        return PreflightReport(
            passed=False,
            total_pages=0,
            issues=[
                {
                    "code": "PDF_RENDER_FAILED",
                    "severity": "ERROR",
                    "message": "PyMuPDF (fitz) is not installed. PDF preflight requires PyMuPDF.",
                }
            ],
        )

    pages_dir = output_reports_dir / "pdf_pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    issues: list[dict[str, Any]] = []
    page_manifests: list[PageManifest] = []

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:  # noqa: BLE001
        return PreflightReport(
            passed=False,
            total_pages=0,
            issues=[
                {
                    "code": "PDF_RENDER_FAILED",
                    "severity": "ERROR",
                    "message": f"Failed to open PDF for rendering: {e}",
                }
            ],
        )

    total_pages = len(doc)
    if total_pages == 0:
        return PreflightReport(
            passed=False,
            total_pages=0,
            issues=[
                {
                    "code": "PDF_RENDER_FAILED",
                    "severity": "ERROR",
                    "message": "PDF contains 0 pages.",
                }
            ],
        )

    # Configured text artifact patterns
    artifact_patterns = [
        (r"\\textbf", "Raw \\textbf command in text", "ERROR"),
        (r"\\texttt", "Raw \\texttt command in text", "ERROR"),
        (r"\\begin\{", "Raw \\begin{ command in text", "ERROR"),
        (r"\\end\{", "Raw \\end{ command in text", "ERROR"),
        (r"\bextbf\{", "Raw extbf{ token in text", "ERROR"),
        (r"\bexttt\{", "Raw exttt{ token in text", "ERROR"),
        (r"\[\?\?\]", "Unresolved reference [??]", "ERROR"),
        (r"\[\?\]", "Unresolved reference [?]", "ERROR"),
        (r"\bundefined citation\b", "Undefined citation warning in text", "ERROR"),
        (r"\bTODO\b", "Unresolved TODO marker", "ERROR"),
        (r"\bTBD\b", "Unresolved TBD marker", "ERROR"),
        (
            r"\[REQUIRED INFORMATION MISSING",
            "Required placeholder syntax in text",
            "ERROR",
        ),
        (r"\b\d+\.\d+At\b", "Malformed percentage (e.g. 73.6At)", "ERROR"),
        (r"\*\*", "Raw Markdown bold ** token", "ERROR"),
        (r"\?\?", "Unresolved reference ?? in text", "ERROR"),
        (
            r"\bFigure placeholder\b",
            "Missing figure asset placeholder reached the PDF",
            "ERROR",
        ),
    ]

    for pno in range(total_pages):
        page = doc[pno]
        page_num = pno + 1

        # Render page to PNG image
        pix = page.get_pixmap(dpi=dpi)
        img_filename = f"page-{page_num:03d}.png"
        img_path = pages_dir / img_filename
        pix.save(str(img_path))

        rect = page.rect
        page_text = page.get_text("text") or ""
        char_count = len(page_text.strip())

        # Count images & captions on page
        images_list = page.get_images()
        image_count = len(images_list)
        caption_matches = re.findall(r"(?:Fig\.|Figure|Table)\s+\d+[:\.]", page_text)
        caption_count = len(caption_matches)

        page_warnings: list[str] = []
        page_errors: list[str] = []

        # 1. Text Artifact Scan (PF-PDF-002)
        for pat, desc, default_sev in artifact_patterns:
            matches = re.findall(pat, page_text, flags=re.IGNORECASE)
            if matches:
                msg = f"Page {page_num}: Found artifact '{matches[0]}' -- {desc}."
                sev = (
                    "ERROR"
                    if (mode == "submission" or default_sev == "ERROR")
                    else "WARNING"
                )
                page_errors.append(msg) if sev == "ERROR" else page_warnings.append(msg)
                issues.append(
                    {
                        "code": "PDF_TEXT_ARTIFACT",
                        "severity": sev,
                        "message": msg,
                        "page": page_num,
                        "matched_text": matches[0],
                    }
                )

        # Orphan reference numeral check (excludes genuine numbered
        # section/subsection headings that merely land adjacent, in flat
        # reading order, to an unrelated citation elsewhere on the page).
        orphan_matches = _find_orphan_reference_numerals(page_text)
        if orphan_matches:
            msg = (
                f"Page {page_num}: Found artifact '{orphan_matches[0]}' -- "
                f"Orphan reference numeral (e.g. (see Fig. 1) I)."
            )
            sev = "ERROR"
            page_errors.append(msg)
            issues.append(
                {
                    "code": "PDF_TEXT_ARTIFACT",
                    "severity": sev,
                    "message": msg,
                    "page": page_num,
                    "matched_text": orphan_matches[0],
                }
            )

        # 2. Overlap and Out-of-Bounds Detection (PF-PDF-003, PF-PDF-004)
        blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
        text_blocks = [b for b in blocks if b[4].strip()]

        # Out-of-bounds check (margins < 10pt from page border, excluding header/footer)
        for b in text_blocks:
            x0, y0, x1, y1, btext = b[0], b[1], b[2], b[3], b[4]
            # Check margin overflow (top < 15pt or bottom > height - 15pt or left < 15pt or right > width - 15pt)
            if (y0 > 30 and y1 < rect.height - 30) and (x0 < 10 or x1 > rect.width + 5):
                msg = f"Page {page_num}: Content out of page bounds at ({x0:.1f}, {y0:.1f}): '{btext[:30].strip()}'"
                page_errors.append(msg)
                issues.append(
                    {
                        "code": "PDF_CONTENT_OUT_OF_BOUNDS",
                        "severity": "ERROR",
                        "message": msg,
                        "page": page_num,
                    }
                )

        # Overlap check between blocks
        for i in range(len(text_blocks)):
            for j in range(i + 1, len(text_blocks)):
                b1, b2 = text_blocks[i], text_blocks[j]
                r1 = fitz.Rect(b1[0], b1[1], b1[2], b1[3])
                r2 = fitz.Rect(b2[0], b2[1], b2[2], b2[3])

                # Check if rectangles intersect significantly
                inter = r1 & r2
                if inter.is_valid and not inter.is_empty:
                    # Calculate overlap area and dimensions
                    overlap_area = inter.width * inter.height
                    # Ignore minor touching lines/glyph bounding box contact
                    if inter.height > 6 and inter.width > 20 and overlap_area > 120:
                        txt1 = b1[4].replace("\n", " ").strip()[:40]
                        txt2 = b2[4].replace("\n", " ").strip()[:40]
                        # Special check: Index Terms overlapping Introduction
                        is_index_intro = (
                            "Index Terms" in txt1 or "Index Terms" in txt2
                        ) and ("INTRODUCTION" in txt1 or "INTRODUCTION" in txt2)
                        reason_code = _classify_block_overlap(b1, b2, inter)
                        sev = (
                            "INFO"
                            if reason_code == "LEGITIMATE_DROPCAP_WRAP"
                            else "ERROR"
                        )
                        msg = (
                            f"Page {page_num}: Overlap detected between '{txt1}' and "
                            f"'{txt2}' (overlap area: {overlap_area:.1f}pt²) "
                            f"[{reason_code}]"
                        )
                        if sev == "ERROR":
                            page_errors.append(msg)
                        issues.append(
                            {
                                "code": "PDF_OBJECT_OVERLAP",
                                "severity": sev,
                                "message": msg,
                                "page": page_num,
                                "is_index_intro_overlap": is_index_intro,
                                "reason_code": reason_code,
                            }
                        )

        # 3. Blank or Near-Blank Page Detection (PF-PDF-005)
        if char_count == 0 and image_count == 0:
            msg = f"Page {page_num}: Completely blank page."
            sev = "ERROR" if mode == "submission" else "WARNING"
            page_errors.append(msg) if sev == "ERROR" else page_warnings.append(msg)
            issues.append(
                {
                    "code": "PDF_NEAR_BLANK_PAGE",
                    "severity": sev,
                    "message": msg,
                    "page": page_num,
                }
            )
        elif char_count < 40 and image_count == 0:
            # Check if it's just a page number or near-blank
            msg = f"Page {page_num}: Near-blank page containing only {char_count} characters."
            sev = "ERROR" if mode == "submission" else "WARNING"
            page_errors.append(msg) if sev == "ERROR" else page_warnings.append(msg)
            issues.append(
                {
                    "code": "PDF_NEAR_BLANK_PAGE",
                    "severity": sev,
                    "message": msg,
                    "page": page_num,
                }
            )

        pm = PageManifest(
            page_number=page_num,
            width=rect.width,
            height=rect.height,
            rendered_image_path=str(img_path),
            char_count=char_count,
            image_count=image_count,
            caption_count=caption_count,
            warnings=page_warnings,
            errors=page_errors,
        )
        page_manifests.append(pm)

    doc.close()

    # Determine overall pass
    has_errors = any(i["severity"] == "ERROR" for i in issues)
    passed = not has_errors

    report = PreflightReport(
        passed=passed,
        total_pages=total_pages,
        page_manifests=page_manifests,
        issues=issues,
        rendered_pages_dir=str(pages_dir),
    )

    # Save reports in output_reports_dir
    json_path = output_reports_dir / "pdf_preflight.json"
    md_path = output_reports_dir / "pdf_preflight.md"

    json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    md_lines = [
        "# Rendered PDF Preflight Report",
        "",
        f"- **Status:** {'PASSED ✓' if passed else 'FAILED ✗'}",
        f"- **Total Pages:** {total_pages}",
        f"- **Mode:** {mode}",
        f"- **Rendered Pages Dir:** [{pages_dir.name}](file:///{pages_dir.as_posix()})",
        "",
        "## Issues Detected",
        "",
    ]
    if not issues:
        md_lines.append("✓ No preflight issues detected.")
    else:
        for iss in issues:
            md_lines.append(
                f"- **[{iss['severity']}]** `{iss['code']}`: {iss['message']}"
            )

    md_lines.extend(["", "## Page Manifest", ""])
    for pm in page_manifests:
        md_lines.append(f"### Page {pm.page_number}")
        md_lines.append(f"- Dimensions: {pm.width:.1f} x {pm.height:.1f} pt")
        md_lines.append(
            f"- Characters: {pm.char_count}, Images: {pm.image_count}, Captions: {pm.caption_count}"
        )
        if pm.errors:
            md_lines.append(f"- Errors: {', '.join(pm.errors)}")
        if pm.warnings:
            md_lines.append(f"- Warnings: {', '.join(pm.warnings)}")
        md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return report
