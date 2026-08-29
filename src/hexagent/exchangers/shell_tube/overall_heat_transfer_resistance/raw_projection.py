"""Non-executing raw-boundary projections for TASK-037.

The S00 branch is entered before any typed attribute access.  Arbitrary
objects, subclasses of accepted containers, and hostile values are represented
only by exact built-in type tokens.  No ``repr``, property lookup, custom
iteration, equality, or user-defined method is invoked.
"""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side.provenance import FrozenRawProjection

from .canonical import frame_value

RAW_PROJECTION_KIND = "task037.raw-boundary.v1"


def _type_token(value: object) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _safe_payload(value: object, active: set[int]) -> bytes:
    value_type = type(value)
    if value is None:
        return frame_value(b"NONE", b"")
    if value_type is bool:
        return frame_value(b"BOOL_TRUE" if value else b"BOOL_FALSE", b"")
    if value_type is int:
        return frame_value(b"INT", str(value).encode("ascii"))
    if value_type is str:
        encoded = value.encode("utf-8")
        return frame_value(b"STRING", encoded)
    if value_type is Decimal:
        encoded = str(value).encode("ascii")
        return frame_value(b"DECIMAL", encoded)
    if value_type is bytes:
        return frame_value(b"BYTES", value)
    if value_type in (tuple, list):
        object_id = id(value)
        if object_id in active:
            return frame_value(b"RAW_PROJECTION", b"CYCLIC_EXACT_SEQUENCE")
        active.add(object_id)
        try:
            payload = bytearray(len(value).to_bytes(4, "big", signed=False))
            for item in value:
                child = _safe_payload(item, active)
                payload.extend(len(child).to_bytes(8, "big", signed=False))
                payload.extend(child)
            return frame_value(b"TUPLE", bytes(payload))
        finally:
            active.remove(object_id)
    if value_type is dict:
        object_id = id(value)
        if object_id in active:
            return frame_value(b"RAW_PROJECTION", b"CYCLIC_EXACT_DICT")
        active.add(object_id)
        try:
            payload = bytearray(len(value).to_bytes(4, "big", signed=False))
            for key, item in value.items():
                if type(key) is str:
                    key_bytes = key.encode("utf-8")
                    payload.extend(len(key_bytes).to_bytes(4, "big", signed=False))
                    payload.extend(key_bytes)
                else:
                    key_token = _type_token(key).encode("utf-8")
                    payload.extend(len(key_token).to_bytes(4, "big", signed=False))
                    payload.extend(key_token)
                child = _safe_payload(item, active)
                payload.extend(len(child).to_bytes(8, "big", signed=False))
                payload.extend(child)
            return frame_value(b"FROZEN_JSON_OBJECT", bytes(payload))
        finally:
            active.remove(object_id)
    # Only type metadata is read for an arbitrary object.  In particular this
    # branch never invokes the object's __repr__, properties, or iterators.
    return frame_value(b"RAW_PROJECTION", _type_token(value).encode("utf-8"))


def project_raw_value(value: object) -> FrozenRawProjection:
    payload = _safe_payload(value, set())
    return FrozenRawProjection(
        projection_kind=RAW_PROJECTION_KIND,
        canonical_bytes_hex=payload.hex(),
    )


def project_raw_request(value: object) -> FrozenRawProjection:
    return project_raw_value(value)


def raw_projection_hex(value: object) -> str:
    return project_raw_value(value).canonical_bytes_hex


def unsafe_object_signal(value: object) -> str:
    return _type_token(value)


__all__ = [
    "RAW_PROJECTION_KIND",
    "project_raw_request",
    "project_raw_value",
    "raw_projection_hex",
    "unsafe_object_signal",
]
