"""Safe raw-boundary projection; never serializes repr or object addresses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .canonical import primitive

RAW_PROJECTION_FIELDS: tuple[str, ...] = (
    "top_level_type",
    "sorted_top_level_keys",
    "schema_version_projection",
    "profile_id_projection",
    "task033_upstream_evidence_type",
    "task031_request_evidence_type",
    "shell_type_authority_presence_and_value_projection",
    "wall_property_fields_projection",
    "evidence_refs_projection",
)
RAW_PROJECTION_FIELD_COUNT = 9


def _type_token(value: Any) -> str:
    return type(value).__name__


def project_raw_request(raw_request: Any) -> tuple[Any, ...]:
    if type(raw_request) is not dict:
        keys: tuple[str, ...] = ()
        schema = None
        profile = None
    else:
        keys = tuple(sorted(str(key) for key in raw_request if type(key) is str))
        schema = raw_request.get("schema_version")
        profile = raw_request.get("profile_id")
    upstream = (
        None if type(raw_request) is not dict else raw_request.get("task033_upstream_evidence")
    )
    task031 = None if type(raw_request) is not dict else raw_request.get("task031_request_evidence")
    if type(raw_request) is not dict or "shell_type_authority" not in raw_request:
        shell_type_authority = ("MISSING", None)
    else:
        shell_type_authority = (
            "PRESENT",
            projection_primitive(raw_request.get("shell_type_authority")),
        )
    wall = (
        None
        if type(raw_request) is not dict
        else (
            raw_request.get("shell_side_wall_dynamic_viscosity_pa_s"),
            raw_request.get("wall_property_schema_version"),
            raw_request.get("wall_property_source_id"),
            raw_request.get("wall_property_source_version"),
            raw_request.get("wall_property_evidence_refs"),
            raw_request.get("wall_property_snapshot_hash"),
            raw_request.get("wall_property_authority_hash"),
        )
    )
    refs = None if type(raw_request) is not dict else raw_request.get("evidence_refs")
    return (
        "dict" if type(raw_request) is dict else _type_token(raw_request),
        keys,
        schema,
        profile,
        _type_token(upstream),
        _type_token(task031),
        shell_type_authority,
        wall,
        refs,
    )


def projection_primitive(value: Any) -> Any:
    try:
        return primitive(value)
    except Exception:
        if isinstance(value, (tuple, list)):
            return [projection_primitive(item) for item in value]
        if isinstance(value, Mapping):
            return {str(key): projection_primitive(item) for key, item in value.items()}
        if value is None or isinstance(value, (bool, int, str)):
            return value
        return _type_token(value)


__all__ = ["project_raw_request", "projection_primitive"]
