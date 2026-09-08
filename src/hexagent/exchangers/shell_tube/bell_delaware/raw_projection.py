"""Total bounded raw ingress for TASK-166.

Only exact built-in containers and registered TASK-166 dataclasses are
traversed.  Unsupported objects are represented without invoking ``repr``,
``str``, ``id``, ``hash`` or user code.
"""

from __future__ import annotations

import dataclasses
import enum
from decimal import Decimal
from typing import Any

from .authority import RAW_MAX_DEPTH, RAW_MAX_NODES, RAW_MAX_SCALAR_BYTES


class RawProjectionFailure(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


_REGISTERED_TYPES: dict[type[Any], tuple[str, ...]] = {}


def register_dataclass_type(value_type: type[Any], field_names: tuple[str, ...]) -> None:
    _REGISTERED_TYPES[value_type] = field_names


class _Budget:
    def __init__(self) -> None:
        self.nodes = 0

    def node(self) -> None:
        self.nodes += 1
        if self.nodes > RAW_MAX_NODES:
            raise RawProjectionFailure("RAW_NODE_LIMIT_EXCEEDED", "raw node budget exceeded")


def _string(value: str) -> dict[str, Any]:
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise RawProjectionFailure("RAW_UNICODE_ENCODING_FAILURE", "invalid UTF-8 scalar") from exc
    if len(encoded) > RAW_MAX_SCALAR_BYTES:
        raise RawProjectionFailure("RAW_SCALAR_BYTE_LIMIT_EXCEEDED", "raw scalar budget exceeded")
    return {"kind": "STRING", "value": value}


def _bounded_ascii_length(value: str) -> None:
    if len(value.encode("ascii", "strict")) > RAW_MAX_SCALAR_BYTES:
        raise RawProjectionFailure("RAW_SCALAR_BYTE_LIMIT_EXCEEDED", "raw scalar budget exceeded")


def _walk(value: Any, *, depth: int, budget: _Budget) -> dict[str, Any]:
    if depth > RAW_MAX_DEPTH:
        raise RawProjectionFailure("RAW_DEPTH_LIMIT_EXCEEDED", "raw depth budget exceeded")
    if value is None:
        budget.node()
        return {"kind": "NONE"}
    if type(value) is bool:
        budget.node()
        _bounded_ascii_length("true" if value else "false")
        return {"kind": "BOOL", "value": value}
    if type(value) is int:
        budget.node()
        try:
            _bounded_ascii_length(str(value))
        except ValueError as exc:
            raise RawProjectionFailure(
                "RAW_SCALAR_BYTE_LIMIT_EXCEEDED", "integer too large"
            ) from exc
        return {"kind": "INTEGER", "value": value}
    if type(value) is str:
        budget.node()
        return _string(value)
    if type(value) is Decimal:
        budget.node()
        if not value.is_finite():
            raise RawProjectionFailure("UNSUPPORTED_RAW_VALUE", "non-finite Decimal")
        _bounded_ascii_length(str(value))
        return {"kind": "DECIMAL", "value": str(value)}
    if isinstance(value, enum.Enum):
        budget.node()
        # No access to .value or textual hooks for unregistered/custom enums.
        raise RawProjectionFailure("UNSUPPORTED_RAW_VALUE", "custom Enum is unsupported")
    value_type = type(value)
    if value_type is dict:
        budget.node()
        if depth == RAW_MAX_DEPTH:
            raise RawProjectionFailure(
                "RAW_DEPTH_LIMIT_EXCEEDED", "mapping child would exceed depth"
            )
        keys: list[tuple[bytes, str]] = []
        for key in value:
            if type(key) is not str:
                raise RawProjectionFailure(
                    "UNSUPPORTED_RAW_VALUE", "mapping key is not an exact string"
                )
            try:
                keys.append((key.encode("utf-8", "strict"), key))
            except UnicodeEncodeError as exc:
                raise RawProjectionFailure(
                    "RAW_UNICODE_ENCODING_FAILURE", "invalid UTF-8 key"
                ) from exc
        keys.sort(key=lambda item: item[0])
        return {
            "kind": "RECORD",
            "fields": [[key, _walk(value[key], depth=depth + 1, budget=budget)] for _, key in keys],
        }
    if value_type is list or value_type is tuple:
        budget.node()
        if depth == RAW_MAX_DEPTH:
            raise RawProjectionFailure(
                "RAW_DEPTH_LIMIT_EXCEEDED", "sequence child would exceed depth"
            )
        return {
            "kind": "SEQUENCE",
            "items": [_walk(item, depth=depth + 1, budget=budget) for item in value],
        }
    fields = _REGISTERED_TYPES.get(value_type)
    if fields is not None and dataclasses.is_dataclass(value):
        budget.node()
        if depth == RAW_MAX_DEPTH:
            raise RawProjectionFailure(
                "RAW_DEPTH_LIMIT_EXCEEDED", "dataclass child would exceed depth"
            )
        return {
            "kind": value_type.__name__,
            "fields": [
                [field_name, _walk(getattr(value, field_name), depth=depth + 1, budget=budget)]
                for field_name in fields
            ],
        }
    raise RawProjectionFailure("UNSUPPORTED_RAW_VALUE", "unsupported raw value")


def project_raw(value: Any) -> dict[str, Any]:
    """Project a raw value or raise a classified bounded failure."""
    try:
        return _walk(value, depth=0, budget=_Budget())
    except RawProjectionFailure:
        raise
    except BaseException as exc:  # total boundary, including hostile hooks
        raise RawProjectionFailure("UNSUPPORTED_RAW_VALUE", "raw projection failed closed") from exc


def projection_bytes(value: Any) -> bytes:
    from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_json

    return canonical_json(project_raw(value)).encode("utf-8")


__all__ = [
    "RawProjectionFailure",
    "project_raw",
    "projection_bytes",
    "register_dataclass_type",
]
