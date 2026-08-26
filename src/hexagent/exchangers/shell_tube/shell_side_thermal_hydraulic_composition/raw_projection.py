"""Deterministic, bounded projection for the raw TASK-035 boundary."""

from __future__ import annotations

import json
from decimal import Decimal
from enum import Enum
from typing import Any

RAW_PROJECTION_NAMESPACE = "task035.raw-projection.v1"
RAW_MAX_DEPTH = 8
RAW_MAX_MAPPING_ITEMS = 64
RAW_MAX_SEQUENCE_ITEMS = 64
RAW_TRUNCATION_TOKEN = "__task035_truncated__"
RAW_FLOAT_TOKEN = "__task035_float__"
RAW_UNSUPPORTED_TOKEN = "__task035_unsupported__"

RAW_PROJECTION_FIELDS: tuple[str, ...] = (
    "projection_kind",
    "projection",
)
RAW_PROJECTION_FIELD_COUNT = len(RAW_PROJECTION_FIELDS)


def _type_name(value: Any) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _truncated(value: Any, count: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"type": _type_name(value)}
    if count is not None:
        result["count"] = count
    return {RAW_TRUNCATION_TOKEN: result}


def _project(value: Any, *, depth: int, active: set[int] | None = None) -> Any:
    if depth > RAW_MAX_DEPTH:
        return _truncated(value)
    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, float):
        return {RAW_FLOAT_TOKEN: type(value).__name__}
    if isinstance(value, Enum):
        return {RAW_UNSUPPORTED_TOKEN: _type_name(value)}
    if isinstance(value, bytes | bytearray | memoryview):
        return {RAW_UNSUPPORTED_TOKEN: _type_name(value)}
    if isinstance(value, (set, frozenset)):
        return {
            RAW_UNSUPPORTED_TOKEN: _type_name(value),
            "count": len(value),
        }

    if active is None:
        active = set()
    if type(value) is dict or type(value) is list or type(value) is tuple:
        identity = id(value)
        if identity in active:
            return {RAW_UNSUPPORTED_TOKEN: "cycle"}
        active.add(identity)
        try:
            if type(value) is dict:
                # Project every item before truncating.  Sorting first is part
                # of the raw contract: insertion order cannot select which
                # entries survive the bounded projection.
                sortable_items: list[tuple[tuple[Any, ...], str, Any]] = []
                for key, item in value.items():
                    if type(key) is str:
                        normalized_key = key
                        sort_key: tuple[Any, ...] = (0, key)
                    else:
                        normalized_key = f"{RAW_UNSUPPORTED_TOKEN}:key:{_type_name(key)}"
                        sort_key = (
                            1,
                            _type_name(key),
                            json.dumps(
                                _project(item, depth=depth + 1, active=active),
                                ensure_ascii=False,
                                separators=(",", ":"),
                                sort_keys=True,
                            ),
                        )
                    sortable_items.append(
                        (sort_key, normalized_key, _project(item, depth=depth + 1, active=active))
                    )
                sortable_items.sort(key=lambda item: item[0])
                items = sortable_items[:RAW_MAX_MAPPING_ITEMS]
                projected: dict[str, Any] = {}
                for _sort_key, normalized_key, projected_item in items:
                    if normalized_key in projected:
                        existing = projected[normalized_key]
                        if isinstance(existing, list):
                            existing.append(projected_item)
                        else:
                            projected[normalized_key] = [existing, projected_item]
                    else:
                        projected[normalized_key] = projected_item
                if len(sortable_items) > RAW_MAX_MAPPING_ITEMS:
                    projected[RAW_TRUNCATION_TOKEN] = {"count": len(value)}
                return {key: projected[key] for key in sorted(projected)}

            items = list(value)
            result = [
                _project(item, depth=depth + 1, active=active)
                for item in items[:RAW_MAX_SEQUENCE_ITEMS]
            ]
            if len(items) > RAW_MAX_SEQUENCE_ITEMS:
                result.append({RAW_TRUNCATION_TOKEN: {"count": len(items)}})
            return result
        finally:
            active.remove(identity)
    return {RAW_UNSUPPORTED_TOKEN: _type_name(value)}


def project_raw_request(raw_request: Any) -> dict[str, Any]:
    """Return a bounded projection without invoking ``repr`` or object hooks."""

    projected = _project(raw_request, depth=0, active=set())
    if isinstance(projected, dict):
        return {
            "projection_kind": "TASK035_RAW_REQUEST",
            "projection": projected,
        }
    return {
        "projection_kind": "TASK035_RAW_REQUEST",
        "projection": projected,
    }


def projection_primitive(value: Any) -> Any:
    """Return the already-sanitized projection for canonical hashing."""

    return _project(value, depth=0, active=set())


__all__ = [
    "RAW_FLOAT_TOKEN",
    "RAW_MAX_DEPTH",
    "RAW_MAX_MAPPING_ITEMS",
    "RAW_MAX_SEQUENCE_ITEMS",
    "RAW_PROJECTION_FIELD_COUNT",
    "RAW_PROJECTION_FIELDS",
    "RAW_PROJECTION_NAMESPACE",
    "RAW_TRUNCATION_TOKEN",
    "RAW_UNSUPPORTED_TOKEN",
    "project_raw_request",
    "projection_primitive",
]
