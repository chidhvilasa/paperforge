"""Shared JSON result envelope and stable exit-code groups for agent-facing
PaperForge commands (``manifest``, ``requirements``, ``plan``, ``generate``,
``provenance``, ``outputs``, ``promote``, ``rollback``, and friends).

Every ``--json`` command builds a :class:`ResultEnvelope`, computes its exit
code from severity, prints exactly one JSON object to stdout, and exits with
that code. This is the one place exit-code numbers are defined so they can
never drift between commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from paperforge import __version__

# Exit-code groups (see docs/AGENT_PROTOCOL.md for the authoritative table).
EXIT_SUCCESS = 0
EXIT_CLI_MISUSE = 2
EXIT_INVALID_MANIFEST = 10
EXIT_UNSUPPORTED_SCHEMA_VERSION = 11
EXIT_MIGRATION_REQUIRED = 12
EXIT_MISSING_STRUCTURAL_REQUIREMENT = 20
EXIT_SUBMISSION_BLOCKER = 21
EXIT_UNSAFE_MANIFEST_OR_PATH = 30
EXIT_GENERATION_PROVENANCE_ERROR = 40
EXIT_EVIDENCE_ERROR = 45
EXIT_BUILD_PREFLIGHT_ERROR = 50
EXIT_REFERENCES_ERROR = 60
EXIT_PACKAGING_OUTPUT_ERROR = 70
EXIT_TIMEOUT = 80
EXIT_INTERNAL_ERROR = 90


@dataclass
class ResultEnvelope:
    command: str
    project_root: str = ""
    status: str = "success"  # success | warning | failure
    exit_code: int = EXIT_SUCCESS
    outputs: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "status": self.status,
            "exit_code": self.exit_code,
            "version": __version__,
            "project_root": self.project_root,
            "outputs": self.outputs,
            "summary": {"errors": len(self.errors), "warnings": len(self.warnings)},
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def finalize(self, exit_code_on_error: int) -> ResultEnvelope:
        """Derive ``status``/``exit_code`` from the collected errors/warnings."""

        if self.errors:
            self.status = "failure"
            self.exit_code = exit_code_on_error
        elif self.warnings:
            self.status = "warning"
            self.exit_code = EXIT_SUCCESS
        else:
            self.status = "success"
            self.exit_code = EXIT_SUCCESS
        return self


def print_envelope(env: ResultEnvelope) -> int:
    import json

    import typer

    typer.echo(json.dumps(env.to_dict(), indent=2, ensure_ascii=False, sort_keys=False))
    return env.exit_code


__all__ = [
    "EXIT_BUILD_PREFLIGHT_ERROR",
    "EXIT_CLI_MISUSE",
    "EXIT_EVIDENCE_ERROR",
    "EXIT_GENERATION_PROVENANCE_ERROR",
    "EXIT_INTERNAL_ERROR",
    "EXIT_INVALID_MANIFEST",
    "EXIT_MIGRATION_REQUIRED",
    "EXIT_MISSING_STRUCTURAL_REQUIREMENT",
    "EXIT_PACKAGING_OUTPUT_ERROR",
    "EXIT_REFERENCES_ERROR",
    "EXIT_SUBMISSION_BLOCKER",
    "EXIT_SUCCESS",
    "EXIT_TIMEOUT",
    "EXIT_UNSAFE_MANIFEST_OR_PATH",
    "EXIT_UNSUPPORTED_SCHEMA_VERSION",
    "ResultEnvelope",
    "print_envelope",
]
