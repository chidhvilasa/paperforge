"""Structured error and issue types for the project manifest subsystem.

Every diagnostic produced anywhere in :mod:`paperforge.project_manifest`
(loading, safe-YAML parsing, path-security checks, structural validation,
migrations) is represented as a :class:`ManifestIssue` so that CLI, JSON
envelopes, and human console output can all render the same information:
a stable machine code, the field path it applies to, a human message, a
remediation suggestion, and a severity.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ManifestIssue:
    """A single structured diagnostic about a manifest document.

    Attributes:
        code: Stable machine-readable identifier, e.g. ``"UNKNOWN_FIELD"``.
        field_path: Dotted path into the document, e.g. ``"authors[0].name"``.
            Empty string for document-level issues.
        message: Human-readable description of the problem.
        remediation: A concrete suggestion for how to fix it.
        severity: One of ``"ERROR"``, ``"WARNING"``, ``"INFO"``.
        line: 1-indexed source line, if known (``None`` otherwise).
        column: 1-indexed source column, if known (``None`` otherwise).
    """

    code: str
    message: str
    remediation: str = ""
    field_path: str = ""
    severity: str = "ERROR"
    line: int | None = None
    column: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "field_path": self.field_path,
            "message": self.message,
            "remediation": self.remediation,
            "severity": self.severity,
            "line": self.line,
            "column": self.column,
        }

    def __str__(self) -> str:
        loc = f" ({self.field_path})" if self.field_path else ""
        pos = ""
        if self.line is not None:
            pos = f" [line {self.line}" + (
                f", col {self.column}]" if self.column else "]"
            )
        return f"[{self.severity}] {self.code}{loc}{pos}: {self.message}"


class ManifestError(Exception):
    """Base class for all project-manifest exceptions."""

    def __init__(
        self, issues: list[ManifestIssue] | None = None, message: str = ""
    ) -> None:
        self.issues: list[ManifestIssue] = list(issues or [])
        if not message and self.issues:
            message = "; ".join(str(i) for i in self.issues)
        super().__init__(message or self.__class__.__name__)


class ManifestValidationError(ManifestError):
    """Raised when a manifest document fails structural validation."""


class ManifestSecurityError(ManifestError):
    """Raised when a manifest document (or a path field inside it) violates
    a safety boundary: unsafe YAML content, an oversized document, or a
    path field that attempts to escape the project root.
    """


class UnsupportedSchemaVersionError(ManifestError):
    """Raised when a manifest declares a schema version newer than the
    version this installation of PaperForge understands.
    """


class MigrationRequiredError(ManifestError):
    """Raised when a manifest declares a schema version older than current
    and must be migrated before it can be validated or used.
    """

    def __init__(
        self,
        found_version: str,
        target_version: str,
        issues: list[ManifestIssue] | None = None,
    ) -> None:
        self.found_version = found_version
        self.target_version = target_version
        message = (
            f"Manifest schema version {found_version!r} is older than "
            f"{target_version!r}. Run `paperforge manifest migrate` first."
        )
        super().__init__(issues, message)


def issue(
    code: str,
    message: str,
    *,
    remediation: str = "",
    field_path: str = "",
    severity: str = "ERROR",
    line: int | None = None,
    column: int | None = None,
) -> ManifestIssue:
    """Convenience constructor mirroring :class:`ManifestIssue` field order."""

    return ManifestIssue(
        code=code,
        message=message,
        remediation=remediation,
        field_path=field_path,
        severity=severity,
        line=line,
        column=column,
    )


__all__ = [
    "ManifestError",
    "ManifestIssue",
    "ManifestSecurityError",
    "ManifestValidationError",
    "MigrationRequiredError",
    "UnsupportedSchemaVersionError",
    "issue",
]
