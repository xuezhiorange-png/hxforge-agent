"""Canonical serialization and identity helpers for TASK-022 Slice A."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any

from hexagent.exchangers.shell_tube.tube_layout import canonical as task021_canonical

from .models import MessageEntry

DECIMAL_PRECISION = 50
UUID_NAMESPACE_URL = uuid.NAMESPACE_URL
GEOMETRY_URN_PREFIX = "urn:hxforge:task022:shell-bundle-geometry:v1:"

CanonicalizationError = task021_canonical.CanonicalizationError
PublicCanonicalDomainError = task021_canonical.PublicCanonicalDomainError
FrozenJsonArray = task021_canonical.FrozenJsonArray
FrozenJsonObject = task021_canonical.FrozenJsonObject

parse_decimal = task021_canonical.parse_decimal
decimal_string = task021_canonical.decimal_string
canonical_json = task021_canonical.canonical_json
sha256_hex = task021_canonical.sha256_hex
dataclass_to_mapping = task021_canonical.dataclass_to_mapping
to_primitive = task021_canonical.to_primitive
canonical_raw_json_or_none = task021_canonical.canonical_raw_json_or_none
freeze_known_fragment = task021_canonical.freeze_known_fragment
internal_frozen_to_primitive = task021_canonical.internal_frozen_to_primitive


def geometry_id(geometry_hash: str) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE_URL, GEOMETRY_URN_PREFIX + geometry_hash))


def decimal_sqrt(value: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        return value.sqrt()


def message_to_primitive(entry: MessageEntry) -> dict[str, Any]:
    details = None if entry.details is None else internal_frozen_to_primitive(entry.details)
    return {
        "code": entry.code,
        "field_path": entry.field_path,
        "message_key": entry.message_key,
        "evidence_refs": list(entry.evidence_refs),
        "details": details,
    }


def message_sort_key(
    entry: MessageEntry, stage_rank: int = 0
) -> tuple[int, str, str, str, str, str]:
    details = None if entry.details is None else internal_frozen_to_primitive(entry.details)
    return (
        stage_rank,
        entry.code,
        entry.field_path or "",
        entry.message_key,
        sha256_hex(details),
        sha256_hex(list(entry.evidence_refs)),
    )


def sort_messages(
    entries: Iterable[MessageEntry],
    *,
    stage_by_identity: Mapping[int, int] | None = None,
) -> tuple[MessageEntry, ...]:
    ranks = stage_by_identity or {}
    return tuple(
        sorted(entries, key=lambda entry: message_sort_key(entry, ranks.get(id(entry), 0)))
    )


def canonical_string_array(raw: Any, *, non_empty: bool, field_path: str) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise TypeError(f"{field_path} must be a list")
    if non_empty and not raw:
        raise ValueError(f"{field_path} must be non-empty")
    if any(not isinstance(item, str) or not item for item in raw):
        raise TypeError(f"{field_path} items must be non-empty strings")
    if len(set(raw)) != len(raw):
        raise ValueError(f"{field_path} contains duplicates")
    return tuple(sorted(raw))


__all__ = [
    "CanonicalizationError",
    "DECIMAL_PRECISION",
    "FrozenJsonArray",
    "FrozenJsonObject",
    "PublicCanonicalDomainError",
    "canonical_json",
    "canonical_raw_json_or_none",
    "canonical_string_array",
    "dataclass_to_mapping",
    "decimal_sqrt",
    "decimal_string",
    "freeze_known_fragment",
    "geometry_id",
    "internal_frozen_to_primitive",
    "message_sort_key",
    "message_to_primitive",
    "parse_decimal",
    "sha256_hex",
    "sort_messages",
    "to_primitive",
]
