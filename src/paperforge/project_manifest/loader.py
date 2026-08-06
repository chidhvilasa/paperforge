"""Safe YAML loading for project manifests.

This module never uses :func:`yaml.load` with an unsafe loader and never
executes anything found in the document. It layers several defenses on top
of :class:`yaml.SafeLoader`:

- a configurable maximum document byte size, checked before parsing;
- strict UTF-8 decoding (invalid byte sequences are rejected, not replaced);
- rejection of duplicate mapping keys (``SafeLoader`` silently keeps the
  last one by default, which can hide a mistake or an attack);
- a post-parse structural walk that rejects cyclic (self-referential) alias
  structures, excessive nesting depth, oversized collections, and oversized
  scalar strings.

``SafeLoader`` already refuses arbitrary Python object tags
(``!!python/object:...`` and friends) by construction — it only knows how to
build plain ``dict``/``list``/``str``/``int``/``float``/``bool``/``None``/
``date``/``datetime`` — so no extra work is needed for that boundary beyond
using it consistently.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from paperforge.project_manifest.errors import ManifestSecurityError, issue

#: Hard ceiling on manifest document size, in bytes.
DEFAULT_MAX_BYTES = 2_000_000
#: Hard ceiling on nesting depth (mappings/sequences within each other).
DEFAULT_MAX_DEPTH = 40
#: Hard ceiling on the number of items in any single mapping or sequence.
DEFAULT_MAX_COLLECTION_SIZE = 10_000
#: Hard ceiling on the length of any single scalar string.
DEFAULT_MAX_SCALAR_LENGTH = 200_000
#: Hard ceiling on the number of anchors declared in the raw document text,
#: checked cheaply before parsing as an early defense against pathological
#: alias graphs.
DEFAULT_MAX_ANCHORS = 200


class _DuplicateKeySafeLoader(yaml.SafeLoader):
    """A ``SafeLoader`` that raises on duplicate mapping keys instead of
    silently keeping the last value."""


def _construct_mapping_no_dupes(
    loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_DuplicateKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping_no_dupes
)


def _count_anchors(raw_text: str) -> int:
    # Cheap, conservative lexical scan (not YAML-aware) counting anchor
    # declarations. False positives (e.g. an '&' inside a quoted scalar)
    # only make this check *stricter*, never weaker.
    count = 0
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        count += line.count("&")
    return count


def _walk_structure(
    node: Any,
    *,
    depth: int,
    max_depth: int,
    max_collection_size: int,
    max_scalar_length: int,
    seen: set[int],
) -> None:
    if isinstance(node, (dict, list)):
        node_id = id(node)
        if node_id in seen:
            raise ManifestSecurityError(
                [
                    issue(
                        "YAML_RECURSIVE_ALIAS",
                        "Document contains a recursive (self-referential) alias structure.",
                        remediation="Remove circular YAML anchors/aliases from the manifest.",
                        severity="ERROR",
                    )
                ]
            )
        seen = seen | {node_id}

        if depth > max_depth:
            raise ManifestSecurityError(
                [
                    issue(
                        "YAML_EXCESSIVE_NESTING",
                        f"Document nesting exceeds the maximum allowed depth ({max_depth}).",
                        remediation="Flatten the manifest structure.",
                        severity="ERROR",
                    )
                ]
            )

        size = len(node)
        if size > max_collection_size:
            raise ManifestSecurityError(
                [
                    issue(
                        "YAML_EXCESSIVE_COLLECTION_SIZE",
                        f"A mapping or sequence has {size} entries, exceeding the "
                        f"maximum allowed ({max_collection_size}).",
                        remediation="Split large collections into separate referenced files.",
                        severity="ERROR",
                    )
                ]
            )

        values = node.values() if isinstance(node, dict) else node
        for v in values:
            _walk_structure(
                v,
                depth=depth + 1,
                max_depth=max_depth,
                max_collection_size=max_collection_size,
                max_scalar_length=max_scalar_length,
                seen=seen,
            )
    elif isinstance(node, str):
        if len(node) > max_scalar_length:
            raise ManifestSecurityError(
                [
                    issue(
                        "YAML_OVERSIZED_SCALAR",
                        f"A string value has {len(node)} characters, exceeding the "
                        f"maximum allowed ({max_scalar_length}).",
                        remediation="Move large text blocks into a separate referenced file.",
                        severity="ERROR",
                    )
                ]
            )


def load_manifest_text(
    raw_bytes: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_collection_size: int = DEFAULT_MAX_COLLECTION_SIZE,
    max_scalar_length: int = DEFAULT_MAX_SCALAR_LENGTH,
    max_anchors: int = DEFAULT_MAX_ANCHORS,
) -> dict[str, Any]:
    """Safely parse manifest YAML from raw bytes into a plain ``dict``.

    Raises :class:`ManifestSecurityError` for every safety-boundary
    violation described in the module docstring.
    """

    if len(raw_bytes) > max_bytes:
        raise ManifestSecurityError(
            [
                issue(
                    "YAML_OVERSIZED_DOCUMENT",
                    f"Manifest document is {len(raw_bytes)} bytes, exceeding the "
                    f"maximum allowed ({max_bytes}).",
                    remediation="Split the manifest or move large content to referenced files.",
                    severity="ERROR",
                )
            ]
        )

    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ManifestSecurityError(
            [
                issue(
                    "YAML_INVALID_UTF8",
                    f"Manifest is not valid UTF-8: {exc}",
                    remediation="Re-save the manifest file with UTF-8 encoding.",
                    severity="ERROR",
                )
            ]
        ) from exc

    if not text.strip():
        raise ManifestSecurityError(
            [
                issue(
                    "YAML_EMPTY_DOCUMENT",
                    "Manifest document is empty.",
                    remediation="Provide a manifest with at least a `schema_version` field.",
                    severity="ERROR",
                )
            ]
        )

    anchor_count = _count_anchors(text)
    if anchor_count > max_anchors:
        raise ManifestSecurityError(
            [
                issue(
                    "YAML_EXCESSIVE_ALIASES",
                    f"Document appears to declare {anchor_count} YAML anchors, "
                    f"exceeding the maximum allowed ({max_anchors}).",
                    remediation="Remove unnecessary YAML anchors/aliases.",
                    severity="ERROR",
                )
            ]
        )

    try:
        data = yaml.load(text, Loader=_DuplicateKeySafeLoader)
    except yaml.constructor.ConstructorError as exc:
        msg = str(exc)
        if "duplicate key" in msg:
            raise ManifestSecurityError(
                [
                    issue(
                        "YAML_DUPLICATE_KEY",
                        f"Manifest contains a duplicate mapping key: {exc}",
                        remediation="Remove the duplicate key from the manifest.",
                        severity="ERROR",
                    )
                ]
            ) from exc
        if "recursive" in msg.lower():
            raise ManifestSecurityError(
                [
                    issue(
                        "YAML_RECURSIVE_ALIAS",
                        "Document contains a recursive (self-referential) alias structure.",
                        remediation="Remove circular YAML anchors/aliases from the manifest.",
                        severity="ERROR",
                    )
                ]
            ) from exc
        raise ManifestSecurityError(
            [
                issue(
                    "YAML_UNSAFE_CONSTRUCT",
                    f"Manifest contains a value PaperForge will not construct: {exc}",
                    remediation="Remove custom YAML tags from the manifest.",
                    severity="ERROR",
                )
            ]
        ) from exc
    except yaml.YAMLError as exc:
        raise ManifestSecurityError(
            [
                issue(
                    "YAML_PARSE_ERROR",
                    f"Manifest is not valid YAML: {exc}",
                    remediation="Fix the YAML syntax error.",
                    severity="ERROR",
                )
            ]
        ) from exc

    if data is None:
        raise ManifestSecurityError(
            [
                issue(
                    "YAML_EMPTY_DOCUMENT",
                    "Manifest document is empty.",
                    remediation="Provide a manifest with at least a `schema_version` field.",
                    severity="ERROR",
                )
            ]
        )

    if not isinstance(data, dict):
        raise ManifestSecurityError(
            [
                issue(
                    "YAML_NON_MAPPING_ROOT",
                    f"Manifest root must be a mapping, got {type(data).__name__}.",
                    remediation="Ensure the manifest's top level is `key: value` pairs.",
                    severity="ERROR",
                )
            ]
        )

    _walk_structure(
        data,
        depth=0,
        max_depth=max_depth,
        max_collection_size=max_collection_size,
        max_scalar_length=max_scalar_length,
        seen=set(),
    )

    return data


def load_manifest_file(
    path: Path,
    **kwargs: Any,
) -> dict[str, Any]:
    """Safely load and parse a manifest YAML file from disk."""

    raw_bytes = Path(path).read_bytes()
    return load_manifest_text(raw_bytes, **kwargs)


__all__ = [
    "DEFAULT_MAX_ANCHORS",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_COLLECTION_SIZE",
    "DEFAULT_MAX_DEPTH",
    "DEFAULT_MAX_SCALAR_LENGTH",
    "load_manifest_file",
    "load_manifest_text",
]
