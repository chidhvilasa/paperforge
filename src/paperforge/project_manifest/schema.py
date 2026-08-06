"""JSON Schema export for the canonical project manifest.

The schema is derived directly from the dataclasses in
:mod:`paperforge.project_manifest.models` via introspection, so it can never
drift out of sync with the Python model: add a field there and it appears
here automatically.
"""

from __future__ import annotations

import dataclasses
import types
import typing
from typing import Any, get_args, get_origin

from paperforge.project_manifest.models import CURRENT_SCHEMA_VERSION, ProjectManifest

_SCHEMA_ID = "https://paperforge.dev/schema/paperforge-project.schema.json"


def _py_type_to_schema(
    py_type: Any, *, _seen: set[type] | None = None
) -> dict[str, Any]:
    _seen = _seen or set()

    origin = get_origin(py_type)

    # Optional[X] / X | None
    if origin in (typing.Union, types.UnionType):
        args = [a for a in get_args(py_type) if a is not type(None)]
        if len(args) == 1:
            return _py_type_to_schema(args[0], _seen=_seen)
        return {"anyOf": [_py_type_to_schema(a, _seen=_seen) for a in args]}

    if origin in (list, typing.List):  # noqa: UP006
        (item_type,) = get_args(py_type) or (Any,)
        return {"type": "array", "items": _py_type_to_schema(item_type, _seen=_seen)}

    if origin in (dict, typing.Dict):  # noqa: UP006
        return {"type": "object", "additionalProperties": True}

    if dataclasses.is_dataclass(py_type):
        # py_type here is always a class (never an instance) in this module's
        # own usage; dataclasses.is_dataclass()'s stub widens the type to
        # also cover instances, so narrow it back explicitly.
        assert isinstance(py_type, type)
        return _dataclass_to_schema(py_type, _seen=_seen)

    if py_type is str:
        return {"type": "string"}
    if py_type is bool:
        return {"type": "boolean"}
    if py_type is int:
        return {"type": "integer"}
    if py_type is float:
        return {"type": "number"}
    if py_type is Any or py_type is object:
        return {}

    return {}


def _dataclass_to_schema(
    dc_cls: type, *, _seen: set[type] | None = None
) -> dict[str, Any]:
    _seen = _seen or set()
    if dc_cls in _seen:
        # Should not happen for this schema (no self-referential models),
        # but guard against infinite recursion defensively.
        return {"type": "object"}
    _seen = _seen | {dc_cls}

    hints = typing.get_type_hints(dc_cls)
    properties: dict[str, Any] = {}
    for f in dataclasses.fields(dc_cls):
        if not f.init:
            continue
        properties[f.name] = _py_type_to_schema(hints.get(f.name, str), _seen=_seen)
    return {
        "type": "object",
        "properties": properties,
        "additionalProperties": dc_cls is ProjectManifest,
    }


def export_json_schema() -> dict[str, Any]:
    """Build the full JSON Schema document for ``paperforge.project.yaml``."""

    schema = _dataclass_to_schema(ProjectManifest)
    schema.update(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": _SCHEMA_ID,
            "title": "PaperForge canonical project manifest",
            "description": (
                "Schema for paperforge.project.yaml, version "
                f"{CURRENT_SCHEMA_VERSION}. Only project.title, "
                "project.research_domain, project.study_type, "
                "project.language, at least one author (id + name), "
                "research.primary_question, and manuscript.generation_policy "
                "+ manuscript.required_sections are structurally required; "
                "declarations such as funding/ethics/consent/DOI/ORCID are "
                "conditionally required depending on study type, venue, and "
                "mode (see the requirements engine), not by this schema."
            ),
            "required": ["schema_version"],
        }
    )
    return schema


__all__ = ["export_json_schema"]
