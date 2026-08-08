"""Artifact-completeness verification for a build output directory.

Distinct from `doctor`/`preflight`, which check manuscript *content*
correctness -- this only checks that the expected output *files* exist,
are non-trivially sized, and (for the PDF) start with a valid PDF header.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from paperforge.outputs.models import ArtifactInfo, OutputVerification

REQUIRED_ARTIFACTS = ("paper.pdf",)
OPTIONAL_ARTIFACTS = (
    "paper.tex",
    "references.bib",
    "paper_overleaf.zip",
    "paper.docx",
    "traceability.tex",
)
_MIN_PLAUSIBLE_SIZE_BYTES = 100


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_output_dir(path: Path) -> OutputVerification:
    issues: list[str] = []
    artifacts: list[ArtifactInfo] = []

    if not path.exists():
        return OutputVerification(
            target=path.name,
            path=str(path),
            ok=False,
            artifacts=[],
            issues=[f"Output directory does not exist: {path}"],
        )

    for name in (*REQUIRED_ARTIFACTS, *OPTIONAL_ARTIFACTS):
        p = path / name
        exists = p.is_file()
        size = p.stat().st_size if exists else 0
        digest = _sha256_of(p) if exists else ""
        artifacts.append(
            ArtifactInfo(name=name, exists=exists, size_bytes=size, sha256=digest)
        )

    by_name = {a.name: a for a in artifacts}
    for req in REQUIRED_ARTIFACTS:
        info = by_name[req]
        if not info.exists:
            issues.append(f"Missing required artifact: {req}")
        elif info.size_bytes < _MIN_PLAUSIBLE_SIZE_BYTES:
            issues.append(
                f"{req} exists but is suspiciously small ({info.size_bytes} bytes)"
            )

    pdf_path = path / "paper.pdf"
    if pdf_path.is_file():
        try:
            head = pdf_path.read_bytes()[:5]
        except OSError:
            head = b""
        if head != b"%PDF-":
            issues.append("paper.pdf does not start with a valid PDF header (%PDF-)")

    return OutputVerification(
        target=path.name,
        path=str(path),
        ok=not issues,
        artifacts=artifacts,
        issues=issues,
    )


__all__ = ["OPTIONAL_ARTIFACTS", "REQUIRED_ARTIFACTS", "verify_output_dir"]
