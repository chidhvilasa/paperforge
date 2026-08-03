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
        (
            r"\(see Fig\. \d+\)\s+[I|V|X]+",
            "Orphan reference numeral (e.g. (see Fig. 1) I)",
            "ERROR",
        ),
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
                        msg = f"Page {page_num}: Overlap detected between '{txt1}' and '{txt2}' (overlap area: {overlap_area:.1f}pt²)"
                        page_errors.append(msg)
                        issues.append(
                            {
                                "code": "PDF_OBJECT_OVERLAP",
                                "severity": "ERROR",
                                "message": msg,
                                "page": page_num,
                                "is_index_intro_overlap": is_index_intro,
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
