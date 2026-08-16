"""TASK-029 closed raw value encoder and raw projection capture.

I04 scope only: ``canonicalize_raw_value`` and ``encode_raw_projection``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    _u32_be,
    _u64_be,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    FrozenTask029RawProjection,
)

RAW_NONE = b"RAW_NONE"
RAW_BOOL = b"RAW_BOOL"
RAW_INTEGER = b"RAW_INTEGER"
RAW_STRING = b"RAW_STRING"
RAW_DECIMAL = b"RAW_DECIMAL"
RAW_DICT = b"RAW_DICT"
RAW_LIST = b"RAW_LIST"
RAW_TUPLE = b"RAW_TUPLE"
RAW_UNSUPPORTED = b"RAW_UNSUPPORTED"


def _raw_frame(tag: bytes, payload: bytes) -> bytes:
    """Raw projection frame: U32(tag_len) + tag + U64(payload_len) + payload."""
    return _u32_be(len(tag)) + tag + _u64_be(len(payload)) + payload


def _unsupported_type_identity(value: object) -> bytes:
    value_type = type(value)
    identity = f"{value_type.__module__}.{value_type.__qualname__}"
    return identity.encode("utf-8")


def canonicalize_raw_value(value: Any) -> bytes:
    """§12.1 — Recursive closed raw-value canonicalization."""
    if value is None:
        return _raw_frame(RAW_NONE, b"")
    if type(value) is bool:
        return _raw_frame(RAW_BOOL, b"true" if value else b"false")
    if type(value) is int:
        return _raw_frame(RAW_INTEGER, str(value).encode("ascii"))
    if type(value) is str:
        return _raw_frame(RAW_STRING, value.encode("utf-8"))
    if type(value) is Decimal:
        return _raw_frame(RAW_DECIMAL, str(value).encode("utf-8"))
    if type(value) is dict:
        payload = _u32_be(len(value))
        for key, item in value.items():
            key_frame = canonicalize_raw_value(key)
            value_frame = canonicalize_raw_value(item)
            payload += _u64_be(len(key_frame)) + key_frame + _u64_be(len(value_frame)) + value_frame
        return _raw_frame(RAW_DICT, payload)
    if type(value) is list:
        payload = _u32_be(len(value))
        for item in value:
            item_frame = canonicalize_raw_value(item)
            payload += _u64_be(len(item_frame)) + item_frame
        return _raw_frame(RAW_LIST, payload)
    if type(value) is tuple:
        payload = _u32_be(len(value))
        for item in value:
            item_frame = canonicalize_raw_value(item)
            payload += _u64_be(len(item_frame)) + item_frame
        return _raw_frame(RAW_TUPLE, payload)
    return _raw_frame(RAW_UNSUPPORTED, _unsupported_type_identity(value))


def encode_raw_projection(projection_kind: str, raw_input: Any) -> FrozenTask029RawProjection:
    """Encode raw input into a frozen raw projection with lowercase hex bytes."""
    canonical_bytes = canonicalize_raw_value(raw_input)
    return FrozenTask029RawProjection(
        projection_kind=projection_kind,
        canonical_bytes_hex=canonical_bytes.hex(),
    )


__all__ = [
    "FrozenTask029RawProjection",
    "canonicalize_raw_value",
    "encode_raw_projection",
    "RAW_NONE",
    "RAW_BOOL",
    "RAW_INTEGER",
    "RAW_STRING",
    "RAW_DECIMAL",
    "RAW_DICT",
    "RAW_LIST",
    "RAW_TUPLE",
    "RAW_UNSUPPORTED",
]
