"""paperforge preflight command — PDF visual & structural preflight suite."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from paperforge.core.project import PaperForgeProject
from paperforge.services.pdf_preflight import run_pdf_preflight
from paperforge.services.reference_verifier import verify_references
from paperforge.services.structural_integrity import check_structural_integrity
from paperforge.services.template_fingerprint import verify_template_fingerprint

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def run(
    project_root: Path,
    mode: str = "draft",
    pdf_path: Path | None = None,
    json_output: bool = False,
    open_renders: bool = False,
    online_references: bool = False,
) -> None:
    project = PaperForgeProject.load(project_root)
    reports_dir = (
        project.output_dir.parent.parent / "reports"
        if project.output_dir.parent.name == "paper_generated"
        else project.output_dir / "reports"
    )
    reports_dir.mkdir(parents=True, exist_ok=True)

    target_pdf = pdf_path or (project.output_dir / "paper.pdf")
    tex_file = project.output_dir / "paper.tex"
    tex_text = tex_file.read_text(encoding="utf-8") if tex_file.exists() else ""

    # 1. Template Fingerprint
    fp_res = verify_template_fingerprint(tex_text, project.config.venue or "ieee", project.output_dir)

    # 2. Structural Integrity
    struct_res = check_structural_integrity(project, reports_dir, mode=mode, tex_content=tex_text)

    # 3. Reference Verification
    ref_res = verify_references(project, reports_dir, online=online_references)

    # 4. Rendered PDF Preflight
    pdf_res = run_pdf_preflight(target_pdf, reports_dir, mode=mode)

    all_issues: list[dict[str, Any]] = []
    all_issues.extend(fp_res.issues)
    all_issues.extend(struct_res.issues)
    all_issues.extend(ref_res.issues)
    all_issues.extend(pdf_res.issues)

    has_errors = any(i.get("severity") == "ERROR" for i in all_issues)
    passed = not has_errors

    # Write combined reports
    fp_json = reports_dir / "venue_fingerprint.json"
    fp_md = reports_dir / "venue_fingerprint.md"
    fp_json.write_text(json.dumps(fp_res.to_dict(), indent=2), encoding="utf-8")
    fp_md.write_text(
        f"# Venue Fingerprint Report\n\n- Status: {fp_res.status}\n- Requested: {fp_res.requested_venue}\n- Detected: {fp_res.detected_template}\n",
        encoding="utf-8",
    )

    if json_output:
        result_data = {
            "passed": passed,
            "venue_fingerprint": fp_res.to_dict(),
            "structural_integrity": struct_res.to_dict(),
            "reference_verification": ref_res.to_dict(),
            "pdf_preflight": pdf_res.to_dict(),
            "all_issues": all_issues,
        }
        print(json.dumps(result_data, indent=2))
        if has_errors and mode == "submission":
            sys.exit(1)
        return

    # Rich Panel Output
    title = f"PaperForge Preflight Summary [{mode.upper()} mode]"
    status_style = "bold green" if passed else "bold red"
    status_text = "PASSED ✓" if passed else "FAILED / BLOCKED ✗"

    lines = [
        f"Overall Status: [{status_style}]{status_text}[/{status_style}]",
        f"Target PDF: {target_pdf}",
        "",
        "Component Readiness:",
        f"  Venue Fingerprint:        [{'green' if fp_res.passed else 'red'}]{'PASSED' if fp_res.passed else 'MISMATCH'}[/]",
        f"  PDF Page Rendering:       [{'green' if pdf_res.passed else 'red'}]{'PASSED (' + str(pdf_res.total_pages) + ' pages)' if pdf_res.passed else 'FAILED'}[/]",
        f"  Visual Overlap Scan:      [{'green' if not any(i.get('code')=='PDF_OBJECT_OVERLAP' for i in pdf_res.issues) else 'red'}]{'PASSED' if not any(i.get('code')=='PDF_OBJECT_OVERLAP' for i in pdf_res.issues) else 'FAILED'}[/]",
        f"  Text Artifact Scan:       [{'green' if not any(i.get('code')=='PDF_TEXT_ARTIFACT' for i in pdf_res.issues) else 'red'}]{'PASSED' if not any(i.get('code')=='PDF_TEXT_ARTIFACT' for i in pdf_res.issues) else 'FAILED'}[/]",
        f"  Structural Integrity:     [{'green' if struct_res.passed else 'red'}]{'PASSED' if struct_res.passed else 'FAILED'}[/]",
        f"  Reference Verification:   [{'green' if ref_res.passed else 'red'}]{'PASSED (' + str(ref_res.total_citations) + ' references)' if ref_res.passed else 'FAILED'}[/]",
        "",
        f"Reports generated in: {reports_dir}",
    ]

    if all_issues:
        lines.append("\nPreflight Issues:")
        for iss in all_issues:
            code = iss.get("code", "ISSUE")
            sev = iss.get("severity", "WARNING")
            msg = iss.get("message", "")
            s_color = "red" if sev == "ERROR" else "yellow"
            lines.append(f"  [{s_color}][{sev}][/{s_color}] [{code}] {msg}")

    console.print(Panel(Text.from_markup("\n".join(lines)), title=title, border_style="green" if passed else "red"))

    if open_renders and pdf_res.rendered_pages_dir:
        import subprocess
        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", pdf_res.rendered_pages_dir], check=False)
        except (OSError, subprocess.SubprocessError):
            pass

    if has_errors and mode == "submission":
        sys.exit(1)
