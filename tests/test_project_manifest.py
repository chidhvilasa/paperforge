"""Tests for paperforge.project_manifest: models, safe YAML, path safety,
validator, schema export, and migrations."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from paperforge.project_manifest.errors import ManifestSecurityError
from paperforge.project_manifest.loader import (
    load_manifest_file,
    load_manifest_text,
)
from paperforge.project_manifest.migrations import (
    detect_version,
    is_future_version,
    migrate,
    migrate_file,
    needs_migration,
)
from paperforge.project_manifest.models import EVIDENCE_CLASSES, ProjectManifest
from paperforge.project_manifest.path_safety import (
    check_project_path,
    enforce_project_path,
)
from paperforge.project_manifest.schema import export_json_schema
from paperforge.project_manifest.validator import validate_manifest_dict

MINIMAL_VALID = """
schema_version: "1.0"
project:
  title: "Example Research Project"
  research_domain: "Computer Science"
  study_type: "Experimental"
  language: "English"
authors:
  - id: "author_1"
    name: "Alex Morgan"
research:
  primary_question: "What effect does the evaluated method have?"
manuscript:
  generation_policy: "validation_only"
  required_sections:
    - abstract
    - introduction
    - methodology
    - results
    - discussion
    - conclusion
"""


# ---------------------------------------------------------------------------
# Models: round-trip
# ---------------------------------------------------------------------------


def test_minimal_manifest_round_trips_through_yaml_and_json() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    manifest = ProjectManifest.from_dict(raw)
    assert manifest.project.title == "Example Research Project"
    assert manifest.authors[0].id == "author_1"
    assert manifest.research.primary_question.startswith("What effect")

    yaml_text = manifest.to_yaml_text()
    round_tripped = ProjectManifest.from_dict(yaml.safe_load(yaml_text))
    assert round_tripped == manifest

    json_text = manifest.to_json_text()
    import json as json_module

    assert (
        json_module.loads(json_text)["project"]["title"] == "Example Research Project"
    )


def test_to_dict_uses_stable_top_level_order() -> None:
    manifest = ProjectManifest.from_dict(yaml.safe_load(MINIMAL_VALID))
    keys = list(manifest.to_dict().keys())
    assert keys == list(ProjectManifest.TOP_LEVEL_ORDER)


def test_extensions_field_round_trips_arbitrary_user_data() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    raw["extensions"] = {"lab_internal_id": "XYZ-42", "nested": {"a": [1, 2, 3]}}
    manifest = ProjectManifest.from_dict(raw)
    assert manifest.extensions["lab_internal_id"] == "XYZ-42"
    assert manifest.to_dict()["extensions"]["nested"]["a"] == [1, 2, 3]


def test_evidence_classes_match_claim_taxonomy() -> None:
    from paperforge.models.claim import EVIDENCE_CLASSES as CLAIM_EVIDENCE_CLASSES

    assert EVIDENCE_CLASSES == CLAIM_EVIDENCE_CLASSES


# ---------------------------------------------------------------------------
# Safe YAML loading
# ---------------------------------------------------------------------------


def test_load_manifest_text_accepts_minimal_valid() -> None:
    data = load_manifest_text(MINIMAL_VALID.encode("utf-8"))
    assert data["project"]["title"] == "Example Research Project"


def test_rejects_arbitrary_python_object_tags() -> None:
    malicious = "project: !!python/object/apply:os.system ['echo pwned']\n"
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(malicious.encode("utf-8"))
    assert excinfo.value.issues[0].code in {"YAML_UNSAFE_CONSTRUCT", "YAML_PARSE_ERROR"}


def test_rejects_duplicate_keys() -> None:
    dup = 'schema_version: "1.0"\nproject:\n  title: "A"\n  title: "B"\n'
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(dup.encode("utf-8"))
    assert excinfo.value.issues[0].code == "YAML_DUPLICATE_KEY"


def test_rejects_invalid_utf8() -> None:
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(b"\xff\xfe\x00schema_version: 1")
    assert excinfo.value.issues[0].code == "YAML_INVALID_UTF8"


def test_rejects_empty_document() -> None:
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(b"   \n\n  ")
    assert excinfo.value.issues[0].code == "YAML_EMPTY_DOCUMENT"


def test_rejects_non_mapping_root() -> None:
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(b"- a\n- b\n- c\n")
    assert excinfo.value.issues[0].code == "YAML_NON_MAPPING_ROOT"


def test_rejects_oversized_document() -> None:
    huge = b"schema_version: '1.0'\nproject:\n  title: '" + b"x" * 100 + b"'\n"
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(huge, max_bytes=50)
    assert excinfo.value.issues[0].code == "YAML_OVERSIZED_DOCUMENT"


def test_rejects_excessive_nesting() -> None:
    depth = 60
    text = (
        "root:\n"
        + "".join(f"{'  ' * (i + 1)}n:\n" for i in range(depth))
        + f"{'  ' * (depth + 1)}leaf: 1\n"
    )
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(text.encode("utf-8"), max_depth=10)
    assert excinfo.value.issues[0].code == "YAML_EXCESSIVE_NESTING"


def test_rejects_excessive_collection_size() -> None:
    items = "\n".join(f"  - item{i}" for i in range(50))
    text = f"schema_version: '1.0'\nbig:\n{items}\n"
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(text.encode("utf-8"), max_collection_size=10)
    assert excinfo.value.issues[0].code == "YAML_EXCESSIVE_COLLECTION_SIZE"


def test_rejects_oversized_scalar_string() -> None:
    text = "schema_version: '1.0'\nproject:\n  title: '" + ("a" * 500) + "'\n"
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(text.encode("utf-8"), max_scalar_length=100)
    assert excinfo.value.issues[0].code == "YAML_OVERSIZED_SCALAR"


def test_rejects_recursive_alias_structure_in_mapping() -> None:
    """A self-referential mapping is refused by PyYAML's own eager
    (non-generator) construction under our duplicate-key-checking loader."""
    recursive = "root: &a\n  self: *a\n"
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(recursive.encode("utf-8"))
    assert excinfo.value.issues[0].code == "YAML_RECURSIVE_ALIAS"


def test_rejects_recursive_alias_structure_in_sequence() -> None:
    """A self-referential *sequence* is constructible by PyYAML itself
    (generator-based), so this exercises our own post-parse cycle-detecting
    structural walk rather than PyYAML's constructor guard."""
    recursive = "schema_version: '1.0'\nroot: &a\n- *a\n"
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(recursive.encode("utf-8"))
    assert excinfo.value.issues[0].code == "YAML_RECURSIVE_ALIAS"


def test_rejects_excessive_alias_count() -> None:
    lines = ["schema_version: '1.0'"]
    for i in range(20):
        lines.append(f"a{i}: &anchor{i} value{i}")
    text = "\n".join(lines) + "\n"
    with pytest.raises(ManifestSecurityError) as excinfo:
        load_manifest_text(text.encode("utf-8"), max_anchors=5)
    assert excinfo.value.issues[0].code == "YAML_EXCESSIVE_ALIASES"


def test_load_manifest_file_reads_from_disk(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    p.write_text(MINIMAL_VALID, encoding="utf-8")
    data = load_manifest_file(p)
    assert data["project"]["title"] == "Example Research Project"


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


def test_path_safety_accepts_project_local_path(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "results.csv").write_text("a,b\n1,2\n")
    result = check_project_path(tmp_path, "data/results.csv")
    assert result.ok
    assert result.resolved == (tmp_path / "data" / "results.csv").resolve()


def test_path_safety_rejects_dotdot_traversal(tmp_path: Path) -> None:
    result = check_project_path(tmp_path, "../../etc/passwd")
    assert not result.ok
    assert result.code == "PATH_TRAVERSAL_ESCAPE"


def test_path_safety_rejects_external_absolute_path(tmp_path: Path) -> None:
    result = check_project_path(tmp_path, "/etc/passwd")
    assert not result.ok
    assert result.code in {"PATH_EXTERNAL_ABSOLUTE", "PATH_TRAVERSAL_ESCAPE"}


def test_path_safety_rejects_windows_drive_escape(tmp_path: Path) -> None:
    result = check_project_path(tmp_path, r"C:\Windows\System32\config")
    assert not result.ok
    assert result.code == "PATH_DRIVE_ESCAPE"


def test_path_safety_rejects_unc_escape(tmp_path: Path) -> None:
    result = check_project_path(tmp_path, r"\\evil-server\share\file.txt")
    assert not result.ok
    assert result.code == "PATH_UNC_ESCAPE"


def test_path_safety_rejects_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulates a symlink that resolves outside the project root without
    requiring real OS symlink-creation privileges (which plain Windows
    accounts without Developer Mode do not have), by monkeypatching the
    filesystem probes `_find_symlink_escape` relies on."""
    import os as os_module

    project_root = tmp_path / "project"
    project_root.mkdir()
    link_path = project_root / "escape_link"
    outside_real = str((tmp_path.parent / f"{tmp_path.name}_outside_target").resolve())

    real_exists = Path.exists
    real_is_symlink = Path.is_symlink
    real_realpath = os_module.path.realpath

    def fake_exists(self: Path) -> bool:
        if self == link_path:
            return True
        return real_exists(self)

    def fake_is_symlink(self: Path) -> bool:
        if self == link_path:
            return True
        return real_is_symlink(self)

    def fake_realpath(p: str, *args: object, **kwargs: object) -> str:
        if Path(p) == link_path:
            return outside_real
        return real_realpath(p, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    monkeypatch.setattr(os_module.path, "realpath", fake_realpath)

    result = check_project_path(project_root, "escape_link/secret.txt")
    assert not result.ok
    assert result.code == "PATH_SYMLINK_ESCAPE"


def test_path_safety_rejects_empty_path(tmp_path: Path) -> None:
    result = check_project_path(tmp_path, "")
    assert not result.ok
    assert result.code == "PATH_EMPTY"


def test_enforce_project_path_raises_on_violation(tmp_path: Path) -> None:
    with pytest.raises(ManifestSecurityError):
        enforce_project_path(tmp_path, "../outside.txt")


# ---------------------------------------------------------------------------
# Validator: structural requirements
# ---------------------------------------------------------------------------


def test_validate_minimal_manifest_passes_draft_and_submission() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    for mode in ("draft", "review", "submission"):
        result = validate_manifest_dict(raw, mode=mode)
        assert result.ok, f"unexpected errors in {mode}: {result.errors}"


def test_validate_missing_title_is_error() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    del raw["project"]["title"]
    result = validate_manifest_dict(raw, mode="draft")
    assert any(e.code == "MISSING_TITLE" for e in result.errors)


def test_validate_missing_author_is_error() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    raw["authors"] = []
    result = validate_manifest_dict(raw, mode="draft")
    assert any(e.code == "MISSING_AUTHORS" for e in result.errors)


def test_validate_missing_research_basis_is_error() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    del raw["research"]["primary_question"]
    result = validate_manifest_dict(raw, mode="draft")
    assert any(e.code == "MISSING_PRIMARY_QUESTION" for e in result.errors)


def test_validate_does_not_require_funding_ethics_consent_doi_orcid() -> None:
    """Funding/ethics/consent/DOI/ORCID must never be universally mandatory
    at the manifest-validation layer -- only the requirements engine may
    make them conditionally required."""

    raw = yaml.safe_load(MINIMAL_VALID)
    result = validate_manifest_dict(raw, mode="submission")
    codes = {e.code for e in result.errors}
    forbidden = {
        "MISSING_FUNDING",
        "MISSING_ETHICS",
        "MISSING_CONSENT",
        "MISSING_DOI",
        "MISSING_ORCID",
        "MISSING_STATISTICS",
        "MISSING_DATASETS",
        "MISSING_FIGURES",
        "MISSING_CODE_AVAILABILITY",
    }
    assert not (codes & forbidden)


def test_validate_unknown_extension_field_allowed_under_extensions() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    raw["extensions"] = {"internal_tracking_id": "abc"}
    result = validate_manifest_dict(raw, mode="submission")
    assert result.ok


def test_validate_unknown_critical_field_rejected_in_submission() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    raw["totally_made_up_field"] = "x"
    result = validate_manifest_dict(raw, mode="submission")
    assert any(e.code == "UNKNOWN_FIELD_SUBMISSION" for e in result.errors)


def test_validate_unknown_field_is_warning_in_draft() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    raw["totally_made_up_field"] = "x"
    result = validate_manifest_dict(raw, mode="draft")
    assert not result.errors
    assert any(w.code == "UNKNOWN_FIELD" for w in result.warnings)


@pytest.mark.parametrize(
    ("typo", "correct"),
    [
        ("autors", "authors"),
        ("target_vanue", "target_venue"),
    ],
)
def test_validate_detects_likely_misspellings(typo: str, correct: str) -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    if typo == "autors":
        raw["autors"] = raw.pop("authors")
    else:
        raw["project"][typo] = "ieee"
    result_draft = validate_manifest_dict(raw, mode="draft")
    assert any(
        e.code == "LIKELY_MISSPELLED_FIELD" and correct in e.remediation
        for e in result_draft.errors
    )
    result_submission = validate_manifest_dict(raw, mode="submission")
    assert any(e.code == "LIKELY_MISSPELLED_FIELD" for e in result_submission.errors)


def test_validate_invalid_evidence_class_is_warning() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    raw["claims"] = [{"id": "c1", "text": "x", "evidence_class": "NOT_A_REAL_CLASS"}]
    result = validate_manifest_dict(raw, mode="draft")
    assert any(w.code == "INVALID_EVIDENCE_CLASS" for w in result.warnings)
    assert not result.errors


# ---------------------------------------------------------------------------
# JSON Schema export
# ---------------------------------------------------------------------------


def test_export_json_schema_has_expected_top_level_properties() -> None:
    schema = export_json_schema()
    assert schema["type"] == "object"
    for key in (
        "schema_version",
        "project",
        "authors",
        "research",
        "methodology",
        "evidence",
        "literature",
        "claims",
        "manuscript",
        "declarations",
        "submission",
        "extensions",
    ):
        assert key in schema["properties"], key
    assert schema["properties"]["authors"]["type"] == "array"
    assert schema["properties"]["project"]["type"] == "object"
    assert "title" in schema["properties"]["project"]["properties"]


def test_export_json_schema_is_json_serializable() -> None:
    import json as json_module

    schema = export_json_schema()
    text = json_module.dumps(schema)
    assert json_module.loads(text)["title"] == "PaperForge canonical project manifest"


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------


LEGACY_0_1 = """
schema_version: "0.1"
title: "A Legacy-Format Study"
research_domain: "Biology"
study_type: "Observational"
author_name: "Sam Rivera"
author_email: "sam@example.org"
venue: "generic"
primary_question: "Does the intervention change the outcome?"
"""


def test_detect_version_defaults_to_legacy_when_absent() -> None:
    assert detect_version({}) == "0.1"


def test_needs_migration_true_for_legacy() -> None:
    raw = yaml.safe_load(LEGACY_0_1)
    assert needs_migration(raw)


def test_needs_migration_false_for_current() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    assert not needs_migration(raw)


def test_is_future_version_detects_unsupported_future_schema() -> None:
    raw = {"schema_version": "9.9"}
    assert is_future_version(raw)


def test_migrate_future_version_raises() -> None:
    from paperforge.project_manifest.errors import UnsupportedSchemaVersionError

    with pytest.raises(UnsupportedSchemaVersionError):
        migrate({"schema_version": "9.9"})


def test_migrate_legacy_0_1_to_1_0_produces_valid_manifest() -> None:
    raw = yaml.safe_load(LEGACY_0_1)
    migrated, report = migrate(raw)
    assert migrated["schema_version"] == "1.0"
    assert migrated["project"]["title"] == "A Legacy-Format Study"
    assert migrated["authors"][0]["name"] == "Sam Rivera"
    assert migrated["research"]["primary_question"].startswith("Does the intervention")
    assert report.source_version == "0.1"
    assert report.target_version == "1.0"
    assert report.applied_steps == ["0.1 -> 1.0"]
    assert report.changed
    assert report.source_hash != report.output_hash

    result = validate_manifest_dict(migrated, mode="draft")
    assert result.ok, result.errors


def test_migrate_current_version_is_a_no_op() -> None:
    raw = yaml.safe_load(MINIMAL_VALID)
    _migrated, report = migrate(raw)
    assert not report.changed
    assert report.applied_steps == []


def test_migrate_file_dry_run_does_not_write(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    p.write_text(LEGACY_0_1, encoding="utf-8")
    original_bytes = p.read_bytes()
    report = migrate_file(p, dry_run=True)
    assert report.changed
    assert p.read_bytes() == original_bytes


def test_migrate_file_writes_atomically_and_backs_up(tmp_path: Path) -> None:
    p = tmp_path / "paperforge.project.yaml"
    p.write_text(LEGACY_0_1, encoding="utf-8")
    report = migrate_file(p, dry_run=False, make_backup=True)
    assert report.changed
    migrated = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert migrated["schema_version"] == "1.0"
    backup = p.with_suffix(p.suffix + ".bak")
    assert backup.exists()
    assert yaml.safe_load(backup.read_text(encoding="utf-8"))["schema_version"] == "0.1"


def test_migrate_file_to_separate_output_path_preserves_source(tmp_path: Path) -> None:
    src = tmp_path / "old.yaml"
    src.write_text(LEGACY_0_1, encoding="utf-8")
    dst = tmp_path / "new.yaml"
    report = migrate_file(src, dst, dry_run=False)
    assert report.changed
    assert yaml.safe_load(src.read_text(encoding="utf-8"))["schema_version"] == "0.1"
    assert yaml.safe_load(dst.read_text(encoding="utf-8"))["schema_version"] == "1.0"
