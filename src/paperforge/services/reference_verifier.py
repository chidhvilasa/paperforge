"""Reference verification service (local BibTeX + optional Crossref API)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge import __version__
from paperforge.core.project import PaperForgeProject


@dataclass
class ReferenceVerificationReport:
    passed: bool
    total_citations: int
    online_verified_count: int
    issues: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "total_citations": self.total_citations,
            "online_verified_count": self.online_verified_count,
            "issues": self.issues,
        }


def verify_references(
    project: PaperForgeProject,
    output_reports_dir: Path,
    online: bool = False,
) -> ReferenceVerificationReport:
    issues: list[dict[str, Any]] = []
    total_citations = len(project.citations)
    online_verified_count = 0

    cache_dir = project.project_root / ".paperforge" / "cache"
    cache_file = cache_dir / "crossref_cache.json"
    cache: dict[str, Any] = {}
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache = {}

    for cit in project.citations:
        # Local deterministic checks
        if not cit.title or cit.title.startswith("TODO"):
            issues.append(
                {
                    "code": "CITATION_NO_TITLE",
                    "severity": "ERROR",
                    "message": f"Citation '{cit.key}' has missing or TODO title.",
                    "citation_key": cit.key,
                }
            )

        if cit.notes:
            internal_pats = ["not a precise source", "approximate", "unconfirmed", "todo", "need to find"]
            if any(p in cit.notes.lower() for p in internal_pats):
                issues.append(
                    {
                        "code": "CITATION_HAS_INTERNAL_NOTE",
                        "severity": "ERROR",
                        "message": f"Citation '{cit.key}' notes contain internal research commentary.",
                        "citation_key": cit.key,
                    }
                )

        # Online Crossref API verification if enabled and DOI present
        if online and cit.doi:
            clean_doi = cit.doi.strip()
            if clean_doi in cache:
                cross_data = cache[clean_doi]
                online_verified_count += 1
            else:
                try:
                    url = f"https://api.crossref.org/works/{urllib.parse.quote(clean_doi)}"
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": f"PaperForge/{__version__} (mailto:academic@paperforge.org)"},
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode("utf-8"))
                            cross_data = data.get("message", {})
                            cache[clean_doi] = cross_data
                            online_verified_count += 1
                except Exception:  # noqa: BLE001
                    cross_data = None  # Graceful fallback when offline

            if cross_data:
                # Compare title similarity
                cr_titles = cross_data.get("title", [])
                if cr_titles and cit.title:
                    cr_title = cr_titles[0].lower()
                    local_title = cit.title.lower()
                    if len(set(cr_title.split()) & set(local_title.split())) < 2:
                        issues.append(
                            {
                                "code": "REFERENCE_METADATA_MISMATCH",
                                "severity": "WARNING",
                                "message": f"Citation '{cit.key}' title mismatch with Crossref DOI metadata. Local: '{cit.title}', Crossref: '{cr_titles[0]}'.",
                                "citation_key": cit.key,
                            }
                        )

    # Save cache if online ran
    if online and cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        except OSError:
            pass

    has_errors = any(i["severity"] == "ERROR" for i in issues)
    passed = not has_errors

    report = ReferenceVerificationReport(
        passed=passed,
        total_citations=total_citations,
        online_verified_count=online_verified_count,
        issues=issues,
    )

    # Save report markdown
    md_path = output_reports_dir / "reference_verification.md"
    md_lines = [
        "# Reference Verification Report",
        "",
        f"- **Status:** {'PASSED ✓' if passed else 'FAILED ✗'}",
        f"- **Total Citations:** {total_citations}",
        f"- **Online Verified (Crossref):** {online_verified_count} (Mode: {'online' if online else 'offline'})",
        "",
        "## Issues Detected",
        "",
    ]
    if not issues:
        md_lines.append("✓ All citation entries validated with no issues.")
    else:
        for iss in issues:
            md_lines.append(f"- **[{iss['severity']}]** `{iss['code']}`: {iss['message']}")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return report
