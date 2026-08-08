"""Data model for output-lifecycle verification/promotion/rollback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ArtifactInfo:
    name: str
    exists: bool
    size_bytes: int = 0
    sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass
class OutputVerification:
    target: str
    path: str
    ok: bool
    artifacts: list[ArtifactInfo] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "path": self.path,
            "ok": self.ok,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "issues": list(self.issues),
        }


@dataclass
class PromoteResult:
    ok: bool
    current_path: str
    verification: OutputVerification
    manifest_path: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "current_path": self.current_path,
            "verification": self.verification.to_dict(),
            "manifest_path": self.manifest_path,
            "message": self.message,
        }


@dataclass
class RollbackResult:
    ok: bool
    current_path: str
    previous_path: str
    resumed_interrupted: bool = False
    verification_after: OutputVerification | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "current_path": self.current_path,
            "previous_path": self.previous_path,
            "resumed_interrupted": self.resumed_interrupted,
            "verification_after": self.verification_after.to_dict()
            if self.verification_after
            else None,
            "message": self.message,
        }


__all__ = ["ArtifactInfo", "OutputVerification", "PromoteResult", "RollbackResult"]
