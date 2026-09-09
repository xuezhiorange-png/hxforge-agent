"""Bounded, total raw-admission projection for TASK-168.

Only built-in containers/scalars and dataclasses from the trusted ``hexagent``
package are admitted.  Unsupported objects are reported structurally; their
``repr``/``str``/``id``/``hash`` and object state are never inspected.
"""

from __future__ import annotations

import dataclasses
import enum
import uuid
from collections.abc import Mapping
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from .canonical import canonical_bytes
from .errors import BlockerCode
from .models import RAW_MAX_DEPTH, RAW_MAX_NODES, RAW_MAX_SCALAR_BYTES


class RawProjectionFailure(ValueError):
    """A deterministic raw-boundary failure with no user-controlled text."""

    def __init__(self, code: BlockerCode, field_path: str = "") -> None:
        self.code = code
        self.field_path = field_path
        super().__init__(code.value)


class _Budget:
    def __init__(self) -> None:
        self.nodes = 0

    def visit(self, depth: int, path: str) -> None:
        if depth > RAW_MAX_DEPTH:
            raise RawProjectionFailure(BlockerCode.RAW_DEPTH_LIMIT_EXCEEDED, path)
        self.nodes += 1
        if self.nodes > RAW_MAX_NODES:
            raise RawProjectionFailure(BlockerCode.RAW_NODE_LIMIT_EXCEEDED, path)


def _trusted_dataclass(value: Any) -> bool:
    if not dataclasses.is_dataclass(value) or isinstance(value, type):
        return False
    module = type(value).__module__
    return type(module) is str and module.startswith("hexagent.")


def _trusted_enum(value: Any) -> bool:
    if not isinstance(value, enum.Enum):
        return False
    module = type(value).__module__
    return type(module) is str and module.startswith("hexagent.")


def _scalar(value: Any, path: str) -> dict[str, Any] | None:
    if value is None:
        return {"kind": "NONE"}
    if type(value) is bool:
        return {"kind": "BOOLEAN", "value": value}
    if type(value) is int:
        return {"kind": "INTEGER", "value": value}
    if type(value) is str:
        try:
            encoded = value.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise RawProjectionFailure(BlockerCode.RAW_UNICODE_ENCODING_FAILURE, path) from exc
        if len(encoded) > RAW_MAX_SCALAR_BYTES:
            raise RawProjectionFailure(BlockerCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED, path)
        return {"kind": "STRING", "value": value}
    if type(value) is Decimal:
        if not value.is_finite():
            raise RawProjectionFailure(BlockerCode.UNSUPPORTED_RAW_VALUE, path)
        encoded = str(value).encode("ascii", "strict")
        if len(encoded) > RAW_MAX_SCALAR_BYTES:
            raise RawProjectionFailure(BlockerCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED, path)
        return {"kind": "DECIMAL", "value": str(value)}
    if type(value) is bytes:
        if len(value) > RAW_MAX_SCALAR_BYTES:
            raise RawProjectionFailure(BlockerCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED, path)
        return {"kind": "BYTES", "value": value.hex()}
    if type(value) is uuid.UUID:
        return {"kind": "UUID", "value": str(value).lower()}
    return None


def _walk(value: Any, *, depth: int, path: str, budget: _Budget) -> dict[str, Any]:
    budget.visit(depth, path)
    scalar = _scalar(value, path)
    if scalar is not None:
        return scalar
    if _trusted_enum(value):
        return {
            "kind": "ENUM_LITERAL",
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "value": _walk(value.value, depth=depth + 1, path=f"{path}.value", budget=budget),
        }
    if isinstance(value, MappingProxyType) or type(value) is dict:
        if not isinstance(value, Mapping):
            raise RawProjectionFailure(BlockerCode.UNSUPPORTED_RAW_VALUE, path)
        entries: list[tuple[bytes, str, dict[str, Any]]] = []
        for key, item in value.items():
            if type(key) is not str:
                raise RawProjectionFailure(BlockerCode.UNSUPPORTED_RAW_VALUE, f"{path}.<key>")
            try:
                key_bytes = key.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise RawProjectionFailure(BlockerCode.RAW_UNICODE_ENCODING_FAILURE, path) from exc
            entries.append(
                (
                    key_bytes,
                    key,
                    _walk(item, depth=depth + 1, path=f"{path}.{key}", budget=budget),
                )
            )
        return {
            "kind": "MAPPING",
            "items": [[key, item] for _, key, item in sorted(entries, key=lambda row: row[0])],
        }
    if type(value) in (tuple, list):
        return {
            "kind": "SEQUENCE",
            "items": [
                _walk(item, depth=depth + 1, path=f"{path}[{index}]", budget=budget)
                for index, item in enumerate(value)
            ],
        }
    if _trusted_dataclass(value):
        items = []
        for field in dataclasses.fields(value):
            items.append(
                [
                    field.name,
                    _walk(
                        getattr(value, field.name),
                        depth=depth + 1,
                        path=f"{path}.{field.name}",
                        budget=budget,
                    ),
                ]
            )
        return {
            "kind": "RECORD",
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "fields": items,
        }
    raise RawProjectionFailure(BlockerCode.UNSUPPORTED_RAW_VALUE, path)


def project_raw(value: object) -> dict[str, Any]:
    """Return a bounded structural projection or raise a typed failure."""

    return _walk(value, depth=0, path="$", budget=_Budget())


def raw_projection_hash(value: object) -> str:
    """Hash a raw value through its bounded projection."""

    import hashlib

    return hashlib.sha256(canonical_bytes(project_raw(value))).hexdigest()


def raw_projection_hash_from_projection(value: dict[str, Any]) -> str:
    """Hash an already-admitted projection without walking it again."""

    import hashlib

    return hashlib.sha256(canonical_bytes(value)).hexdigest()


__all__ = [
    "RawProjectionFailure",
    "project_raw",
    "raw_projection_hash",
    "raw_projection_hash_from_projection",
]
