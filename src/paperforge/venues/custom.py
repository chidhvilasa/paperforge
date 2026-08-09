"""Loading a local, author-supplied venue configuration file.

A custom venue is a plain YAML document (parsed with ``yaml.safe_load``,
never ``yaml.load``) describing a venue PaperForge doesn't ship a plugin
for. It is read-only metadata for `paperforge venue show|validate` in this
pass -- it does not (yet) plug into `--target` for `build`/`doctor`.

The file path is resolved through the same
:mod:`paperforge.project_manifest.path_safety` traversal guard used for
manifest-referenced paths, so a malicious or mistaken ``../../etc`` style
path is rejected before anything is read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge.project_manifest.path_safety import check_project_path

MAX_CUSTOM_VENUE_FILE_SIZE = 1_000_000


class CustomVenueError(ValueError):
    pass


@dataclass
class CustomVenueConfig:
    venue_id: str = ""
    display_name: str = ""
    adapter_version: str = ""
    checked_date: str = ""
    source_url: str = ""
    source_description: str = ""
    template_version: str = ""
    compiler: str = ""
    abstract_requirements: str = ""
    keyword_requirements: str = ""
    anonymous_review_rules: str = ""
    author_formatting: str = ""
    biography_requirement: str = ""
    max_pages: int | None = None
    max_words: int | None = None
    declaration_requirements: list[str] = field(default_factory=list)
    graphical_abstract_rules: str = ""
    highlights_rules: str = ""
    source_package_rules: str = ""
    supplementary_rules: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue_id": self.venue_id,
            "display_name": self.display_name,
            "adapter_version": self.adapter_version,
            "checked_date": self.checked_date,
            "source_url": self.source_url,
            "source_description": self.source_description,
            "template_version": self.template_version,
            "compiler": self.compiler,
            "abstract_requirements": self.abstract_requirements,
            "keyword_requirements": self.keyword_requirements,
            "anonymous_review_rules": self.anonymous_review_rules,
            "author_formatting": self.author_formatting,
            "biography_requirement": self.biography_requirement,
            "max_pages": self.max_pages,
            "max_words": self.max_words,
            "declaration_requirements": list(self.declaration_requirements),
            "graphical_abstract_rules": self.graphical_abstract_rules,
            "highlights_rules": self.highlights_rules,
            "source_package_rules": self.source_package_rules,
            "supplementary_rules": self.supplementary_rules,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomVenueConfig:
        field_names = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in field_names}
        return cls(**kwargs)


def load_custom_venue(project_root: Path, raw_path: str) -> CustomVenueConfig:
    check = check_project_path(project_root, raw_path, field_path="venue.custom_file")
    if not check.ok or check.resolved is None:
        raise CustomVenueError(
            check.reason or f"Invalid custom venue path '{raw_path}'."
        )

    path = check.resolved
    if not path.exists():
        raise CustomVenueError(f"Custom venue file not found: {raw_path}")
    if not path.is_file():
        raise CustomVenueError(f"Custom venue path is not a regular file: {raw_path}")
    size = path.stat().st_size
    if size > MAX_CUSTOM_VENUE_FILE_SIZE:
        raise CustomVenueError(
            f"Custom venue file '{raw_path}' is {size} bytes, exceeding the "
            f"{MAX_CUSTOM_VENUE_FILE_SIZE}-byte limit."
        )

    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise CustomVenueError(f"Could not parse custom venue YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise CustomVenueError("Custom venue file must contain a YAML mapping.")

    return CustomVenueConfig.from_dict(data)


__all__ = [
    "MAX_CUSTOM_VENUE_FILE_SIZE",
    "CustomVenueConfig",
    "CustomVenueError",
    "load_custom_venue",
]
