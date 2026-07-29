"""Structural integrity & canonical document outline service."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge.core.project import PaperForgeProject


@dataclass
class SectionNode:
    id: str
    number: str
    title: str
    order: int
    claims: list[str] = field(default_factory=list)


@dataclass
class StructuralReport:
    passed: bool
    sections: list[dict[str, Any]] = field(default_factory=list)
    resolved_references: dict[str, str] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "sections": self.sections,
            "resolved_references": self.resolved_references,
            "issues": self.issues,
        }


def check_structural_integrity(
    project: PaperForgeProject,
    output_reports_dir: Path,
    mode: str = "draft",
    tex_content: str = "",
) -> StructuralReport:
    issues: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    resolved_refs: dict[str, str] = {}

    # Standard section numbering order
    roman_numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    sec_names = project.config.sections
    sec_nodes: list[SectionNode] = []

    for idx, sname in enumerate(sec_names):
        num = roman_numerals[idx] if idx < len(roman_numerals) else str(idx + 1)
        node = SectionNode(id=sname.lower(), number=num, title=sname.title(), order=idx + 1)
        sec_nodes.append(node)
        sections.append({"id": node.id, "number": node.number, "title": node.title, "order": node.order})
        resolved_refs[f"section:{node.id}"] = f"Section {node.number}"

    # Map claims and check section roadmaps
    sec_order_map = {n.id: n.order for n in sec_nodes}
    for claim in project.claims:
        if not claim.text:
            continue
        # Look for hardcoded section references like "Section IV describes..." or "Section 4"
        matches = re.findall(r"Section\s+([I|V|X\d]+)\s+(?:describes|presents|details|covers|evaluates)\s+([a-zA-Z_\s]+)", claim.text, flags=re.IGNORECASE)
        for num_str, topic in matches:
            topic_clean = topic.strip().lower()
            matching_sec = next((s for s in sec_nodes if s.id in topic_clean or topic_clean in s.id), None)
            if matching_sec and matching_sec.number != num_str:
                msg = f"Section roadmap mismatch in {claim.id}: prose references Section {num_str} for '{topic_clean}', but '{matching_sec.title}' is Section {matching_sec.number}."
                sev = "ERROR" if mode == "submission" else "WARNING"
                issues.append(
                    {
                        "code": "SECTION_ROADMAP_MISMATCH",
                        "severity": sev,
                        "message": msg,
                        "claim_id": claim.id,
                    }
                )

    # 2. FLOAT_AFTER_CONCLUSION (PF-STRUCT-002)
    conclusion_order = sec_order_map.get("conclusion", 999)

    # Check figures and tables placement
    for fig in project.figures:
        first_sec = (fig.first_mentioned_in or "").lower()
        if first_sec in sec_order_map and sec_order_map[first_sec] < conclusion_order and tex_content and ("\\section{Conclusion}" in tex_content or "\\section{VI. Conclusion}" in tex_content or "Conclusion" in tex_content):
            concl_pos = tex_content.find("Conclusion")
            fig_pos = tex_content.find(f"\\label{{{fig.id}}}")
            if fig_pos != -1 and concl_pos != -1 and fig_pos > concl_pos:
                msg = f"Float placement defect: Figure '{fig.id}' (first mentioned in '{first_sec}') is placed after Conclusion section."
                sev = "ERROR" if mode == "submission" else "WARNING"
                issues.append(
                    {
                        "code": "FLOAT_AFTER_CONCLUSION",
                        "severity": sev,
                        "message": msg,
                        "fig_id": fig.id,
                    }
                )

    for tbl in project.tables:
        first_sec = (tbl.first_mentioned_in or "").lower()
        if first_sec in sec_order_map and sec_order_map[first_sec] < conclusion_order and tex_content and "Conclusion" in tex_content:
            concl_pos = tex_content.find("Conclusion")
            tbl_pos = tex_content.find(f"\\label{{{tbl.id}}}")
            if tbl_pos != -1 and concl_pos != -1 and tbl_pos > concl_pos:
                msg = f"Float placement defect: Table '{tbl.id}' (first mentioned in '{first_sec}') is placed after Conclusion section."
                sev = "ERROR" if mode == "submission" else "WARNING"
                issues.append(
                    {
                        "code": "FLOAT_AFTER_CONCLUSION",
                        "severity": sev,
                        "message": msg,
                        "tbl_id": tbl.id,
                    }
                )

    # 3. DUPLICATE_OR_CONFLICTING_LABEL (PF-STRUCT-003)
    if tex_content:
        labels = re.findall(r"\\label\{([^}]+)\}", tex_content)
        seen_labels: set[str] = set()
        for lbl in labels:
            if lbl in seen_labels:
                msg = f"Duplicate LaTeX label found: '\\label{{{lbl}}}'."
                issues.append(
                    {
                        "code": "DUPLICATE_OR_CONFLICTING_LABEL",
                        "severity": "ERROR",
                        "message": msg,
                        "label": lbl,
                    }
                )
            seen_labels.add(lbl)

    # 4. UNRESOLVED_CROSS_REFERENCE (PF-STRUCT-004)
    if tex_content and ("[?]" in tex_content or "??" in tex_content):
        msg = "Unresolved cross-reference or citation marker ([?] or ??) in generated LaTeX output."
        issues.append(
            {
                "code": "UNRESOLVED_CROSS_REFERENCE",
                "severity": "ERROR",
                "message": msg,
            }
        )

    has_errors = any(i["severity"] == "ERROR" for i in issues)
    passed = not has_errors

    report = StructuralReport(
        passed=passed,
        sections=sections,
        resolved_references=resolved_refs,
        issues=issues,
    )

    # Save reports
    json_path = output_reports_dir / "structural_integrity.json"
    md_path = output_reports_dir / "structural_integrity.md"

    json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    md_lines = [
        "# Structural Integrity & Canonical Outline Report",
        "",
        f"- **Status:** {'PASSED ✓' if passed else 'FAILED ✗'}",
        f"- **Total Sections:** {len(sections)}",
        "",
        "## Canonical Section Outline",
        "",
    ]
    for s in sections:
        md_lines.append(f"{s['number']}. {s['title']} (`{s['id']}`)")

    md_lines.extend(["", "## Issues Detected", ""])
    if not issues:
        md_lines.append("✓ No structural integrity issues detected.")
    else:
        for iss in issues:
            md_lines.append(f"- **[{iss['severity']}]** `{iss['code']}`: {iss['message']}")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return report


def resolve_symbolic_references(text: str, project: PaperForgeProject) -> str:
    """Resolve {{section:id}}, {{figure:id}}, {{table:id}} placeholders in prose."""
    if not text or "{{" not in text:
        return text

    roman_numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    sec_num_map = {
        sname.lower(): (roman_numerals[idx] if idx < len(roman_numerals) else str(idx + 1))
        for idx, sname in enumerate(project.config.sections)
    }
    fig_num_map = {f.id: idx + 1 for idx, f in enumerate(project.figures)}
    tbl_num_map = {t.id: idx + 1 for idx, t in enumerate(project.tables)}

    def _replace_match(m: re.Match) -> str:
        ref_type, ref_id = m.group(1).lower(), m.group(2).lower()
        if ref_type == "section":
            num_str = sec_num_map.get(ref_id, "??")
            return f"Section {num_str}"
        elif ref_type == "figure":
            num_val = fig_num_map.get(ref_id, "??")
            return f"Fig. {num_val}"
        elif ref_type == "table":
            num_val = tbl_num_map.get(ref_id, "??")
            return f"Table {num_val}"
        return m.group(0)

    return re.sub(r"\{\{(section|figure|table):([a-zA-Z0-9_.-]+)\}\}", _replace_match, text, flags=re.IGNORECASE)
