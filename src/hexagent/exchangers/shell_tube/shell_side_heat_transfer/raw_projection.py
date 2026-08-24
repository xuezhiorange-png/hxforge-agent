"""Bounded raw-boundary projection with no repr or recursive dumping."""

from __future__ import annotations

from typing import Any

RAW_PROJECTION_FIELDS: tuple[str, ...] = (
    "top_level_type",
    "sorted_top_level_keys",
    "schema_version_projection",
    "profile_id_projection",
    "task032_flow_state_type",
    "task032_request_evidence_type",
    "evidence_refs_projection",
)
RAW_PROJECTION_FIELD_COUNT = 7


def _lexical(value: Any) -> str | None:
    return value if type(value) is str else None


def project_raw_request(raw_request: Any) -> tuple[Any, ...]:
    is_dict = type(raw_request) is dict
    keys = tuple(sorted(key for key in raw_request if type(key) is str)) if is_dict else ()
    return (
        "builtin.dict" if is_dict else type(raw_request).__name__,
        keys,
        _lexical(raw_request.get("schema_version")) if is_dict else None,
        _lexical(raw_request.get("profile_id")) if is_dict else None,
        "builtin.dict"
        if is_dict and type(raw_request.get("task032_flow_state")) is dict
        else (None if not is_dict else type(raw_request.get("task032_flow_state")).__name__),
        "builtin.dict"
        if is_dict and type(raw_request.get("task032_request_evidence")) is dict
        else (None if not is_dict else type(raw_request.get("task032_request_evidence")).__name__),
        tuple(
            item
            for item in (raw_request.get("evidence_refs", []) if is_dict else [])
            if type(item) is str
        ),
    )


__all__ = ["RAW_PROJECTION_FIELD_COUNT", "RAW_PROJECTION_FIELDS", "project_raw_request"]
