"""Venue template fingerprinting service."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@dataclass
class FingerprintResult:
    passed: bool
    requested_venue: str
    detected_template: str
    manifest_version: str
    status: str  # VERIFIED | MISMATCH | UNVERIFIED
    mismatched_files: list[str] = field(default_factory=list)
    missing_markers: list[str] = field(default_factory=list)
    unexpected_modifications: list[str] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "requested_venue": self.requested_venue,
            "detected_template": self.detected_template,
            "manifest_version": self.manifest_version,
            "status": self.status,
            "mismatched_files": self.mismatched_files,
            "missing_markers": self.missing_markers,
            "unexpected_modifications": self.unexpected_modifications,
            "issues": self.issues,
        }


def load_manifest(venue_id: str) -> dict[str, Any] | None:
    # Map venue aliases to directory names
    canonical = venue_id.lower().replace("_", "-")
    if canonical in ("ieee-access",):
        dir_name = "ieee_access"
    elif canonical.startswith("ieee"):
        dir_name = "ieee"
    elif canonical.startswith("acm"):
        dir_name = "acm"
    elif canonical.startswith("neurips"):
        dir_name = "neurips"
    else:
        dir_name = canonical

    manifest_file = TEMPLATES_DIR / dir_name / "template_manifest.json"
    if not manifest_file.exists():
        # Fallback check
        dir_name_sub = canonical.replace("-", "_")
        manifest_file = TEMPLATES_DIR / dir_name_sub / "template_manifest.json"
        if not manifest_file.exists():
            return None

    try:
        return json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def verify_template_fingerprint(
    tex_content: str,
    requested_venue: str,
    build_dir: Path | None = None,
) -> FingerprintResult:
    if not tex_content or not tex_content.strip():
        return FingerprintResult(
            passed=True,
            status="UNVERIFIED",
            requested_venue=requested_venue,
            detected_template="unknown",
            manifest_version="N/A",
            mismatched_files=[],
            issues=[
                {
                    "code": "VENUE_TEMPLATE_UNVERIFIED",
                    "severity": "INFO",
                    "message": f"LaTeX source not generated yet. Template fingerprint for venue '{requested_venue}' is unverified until build.",
                }
            ],
        )

    manifest = load_manifest(requested_venue)
    if not manifest:
        return FingerprintResult(
            passed=False,
            requested_venue=requested_venue,
            detected_template="Unknown / Unregistered",
            manifest_version="N/A",
            status="UNVERIFIED",
            issues=[
                {
                    "code": "VENUE_TEMPLATE_UNVERIFIED",
                    "severity": "WARNING",
                    "message": f"No template manifest available for venue '{requested_venue}'.",
                }
            ],
        )

    detected_template = manifest.get("template_name", "Unknown Template")
    manifest_version = manifest.get("template_version", "1.0.0")
    expected_doc_class = manifest.get("expected_documentclass")
    required_markers = manifest.get("required_markers", [])
    forbidden_markers = manifest.get("forbidden_markers", [])

    mismatched_files: list[str] = []
    missing_markers: list[str] = []
    unexpected_modifications: list[str] = []
    issues: list[dict[str, Any]] = []

    # Check document class
    doc_class_match = re.search(r"\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}", tex_content)
    if doc_class_match:
        actual_class = doc_class_match.group(1).strip()
        if expected_doc_class and actual_class != expected_doc_class:
            mismatched_files.append(f"documentclass mismatch: expected '{expected_doc_class}', got '{actual_class}'")
            issues.append(
                {
                    "code": "VENUE_TEMPLATE_MISMATCH",
                    "severity": "ERROR",
                    "message": f"Requested venue '{requested_venue}' expects documentclass '{expected_doc_class}', but got '{actual_class}'.",
                }
            )

    # Check forbidden markers
    for forb in forbidden_markers:
        if forb in tex_content:
            unexpected_modifications.append(f"Forbidden marker present: '{forb}'")
            issues.append(
                {
                    "code": "VENUE_TEMPLATE_MISMATCH",
                    "severity": "ERROR",
                    "message": f"LaTeX output contains forbidden marker '{forb}' for venue '{requested_venue}'.",
                }
            )

    # Check required markers
    for req in required_markers:
        if req not in tex_content:
            missing_markers.append(req)
            issues.append(
                {
                    "code": "VENUE_TEMPLATE_MISMATCH",
                    "severity": "ERROR",
                    "message": f"Required venue marker '{req}' missing from LaTeX output for venue '{requested_venue}'.",
                }
            )

    is_mismatch = bool(mismatched_files or missing_markers or unexpected_modifications or any(i["code"] == "VENUE_TEMPLATE_MISMATCH" for i in issues))
    status = "MISMATCH" if is_mismatch else "VERIFIED"
    passed = not is_mismatch

    return FingerprintResult(
        passed=passed,
        requested_venue=requested_venue,
        detected_template=detected_template,
        manifest_version=manifest_version,
        status=status,
        mismatched_files=mismatched_files,
        missing_markers=missing_markers,
        unexpected_modifications=unexpected_modifications,
        issues=issues,
    )
