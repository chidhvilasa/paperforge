"""Canonical PaperForge project manifest (``paperforge.project.yaml``).

This package defines the typed, versioned schema for the canonical project
manifest, safe loading/validation of manifest files, path-security checks for
project-local path fields, JSON Schema export, and a migration registry for
upgrading older manifest documents to the current schema version.

Nothing in this package executes user-supplied code, notebooks, shell
scripts, templates, or configuration hooks. Loading a manifest only ever
performs a size-bounded, alias-safe YAML parse followed by structural
validation.
"""

from __future__ import annotations

from paperforge.project_manifest.errors import (
    ManifestIssue,
    ManifestSecurityError,
    ManifestValidationError,
    MigrationRequiredError,
    UnsupportedSchemaVersionError,
)
from paperforge.project_manifest.loader import load_manifest_file, load_manifest_text
from paperforge.project_manifest.migrations import (
    MigrationReport,
    detect_version,
    is_future_version,
    migrate,
    migrate_file,
    needs_migration,
)
from paperforge.project_manifest.models import (
    CURRENT_SCHEMA_VERSION,
    AuthorEntry,
    ClaimEntry,
    Declarations,
    EvidenceInventory,
    Literature,
    ManuscriptPlanConfig,
    Methodology,
    ProjectIdentity,
    ProjectManifest,
    ResearchBasis,
    SubmissionPackaging,
)
from paperforge.project_manifest.path_safety import (
    PathCheckResult,
    check_project_path,
    enforce_project_path,
)
from paperforge.project_manifest.schema import export_json_schema
from paperforge.project_manifest.validator import (
    ValidationResult,
    validate_manifest,
    validate_manifest_dict,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "AuthorEntry",
    "ClaimEntry",
    "Declarations",
    "EvidenceInventory",
    "Literature",
    "ManifestIssue",
    "ManifestSecurityError",
    "ManifestValidationError",
    "ManuscriptPlanConfig",
    "Methodology",
    "MigrationReport",
    "MigrationRequiredError",
    "PathCheckResult",
    "ProjectIdentity",
    "ProjectManifest",
    "ResearchBasis",
    "SubmissionPackaging",
    "UnsupportedSchemaVersionError",
    "ValidationResult",
    "check_project_path",
    "detect_version",
    "enforce_project_path",
    "export_json_schema",
    "is_future_version",
    "load_manifest_file",
    "load_manifest_text",
    "migrate",
    "migrate_file",
    "needs_migration",
    "validate_manifest",
    "validate_manifest_dict",
]
