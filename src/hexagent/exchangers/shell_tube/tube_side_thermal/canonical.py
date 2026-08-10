"""TASK-026 canonical encoding helpers.

R8 implementation. Reuses TASK-025 canonical framing primitives
(frame_value, frame_record, frame_tuple, sha256_hex_from_framed_bytes)
verbatim per R6-R7 §11.1. Adds TASK-026-specific hash_kind literal
constants and per-record payload helpers used only by the 25 in-scope
TASK-026 hash-field tuples.

Frozen source: A2 manifest (e152c80345...), T1-R2 (b763b1a4768...),
H1-R1 (f9dbe86b...). This module contains no engineering computation.
"""

from __future__ import annotations

import struct
from collections.abc import Sequence
from decimal import Decimal
from typing import Any, Final

from hexagent.exchangers.shell_tube.tube_side.canonical import (
    frame_record as _t025_frame_record,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    frame_tuple as _t025_frame_tuple,
)

# Reuse TASK-025 canonical framing primitives verbatim.
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    frame_value as _t025_frame_value,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    sha256_hex_from_framed_bytes as _t025_sha256_hex,
)

# KIND_TAG literals (ASCII, frozen). These are the byte sequences used
# inside frame_value() calls. The TASK-026 hash-field tuples reference
# these tags by name (e.g. KIND_DECIMAL, KIND_ENUM, KIND_TUPLE,
# KIND_RECORD, KIND_RAW_PROJECTION). See R6-R7 §9.2-§9.7 for the
# exact per-field tag mapping.
KIND_NONE: Final[bytes] = b"NONE"
KIND_INT: Final[bytes] = b"INT"
KIND_STRING: Final[bytes] = b"STRING"
KIND_BYTES: Final[bytes] = b"BYTES"
KIND_DECIMAL: Final[bytes] = b"DECIMAL"
KIND_ENUM: Final[bytes] = b"ENUM"
KIND_TUPLE: Final[bytes] = b"TUPLE"
KIND_RECORD: Final[bytes] = b"RECORD"
KIND_RAW_PROJECTION: Final[bytes] = b"RAW_PROJECTION"


# U32_BE / U64_BE helpers (re-exposed for orchard-style direct use by
# stage_pipeline / test files). These are byte-equivalent to the TASK-025
# internal helpers and intentionally re-exported here so that the R8
# module signature text is self-contained.
def _u32_be(n: int) -> bytes:
    if n < 0 or n > 0xFFFFFFFF:
        raise ValueError("u32_be out of range")
    return struct.pack(">I", n)


def _u64_be(n: int) -> bytes:
    if n < 0 or n > 0xFFFFFFFFFFFFFFFF:
        raise ValueError("u64_be out of range")
    return struct.pack(">Q", n)


# Re-export the framing primitives under the names used by the R8 callers.
# Each helper preserves the TASK-025 byte contract; the R8 wrappers exist
# only to give the TASK-026 hash-field tuples a single canonical
# import path.
def frame_value(kind: bytes, payload: bytes) -> bytes:
    """R6-R7 §11.3 — FRAME(kind, payload) using TASK-025 helper."""
    return _t025_frame_value(kind, payload)


def frame_tuple(item_payloads: Sequence[bytes]) -> bytes:
    """R6-R7 §11.3 — TUPLE_PAYLOAD using TASK-025 helper.

    TUPLE_PAYLOAD = U32_BE(item_count) || FRAME(\"ITEM\", item_n_payload)
    The outer KIND_TUPLE frame is applied by the caller.
    """
    return _t025_frame_tuple(item_payloads)


def frame_record(namespace: str, fields: Sequence[tuple[str, bytes, bytes]]) -> bytes:
    """R6-R7 §11.3 — frame_record using TASK-025 helper.

    Each field is (name_utf8, kind_tag_ascii, payload_bytes). The
    frame_record helper applies the field frame exactly once per field
    and embeds the namespace.
    """
    return _t025_frame_record(namespace, fields)


def sha256_hex_from_framed_bytes(framed: bytes) -> str:
    """R6-R7 §9.9 — SHA-256 of canonical framed bytes, 64-lowercase-hex."""
    return _t025_sha256_hex(framed)


# ---------------------------------------------------------------------------
# Per-kind payload helpers (R6-R7 §11.2 per-kind atom table).
# ---------------------------------------------------------------------------


def decimal_payload(value: Decimal) -> bytes:
    """R6-R7 §11.2 — KIND_DECIMAL payload = str(value).encode('ascii')."""
    return str(value).encode("ascii")


def int_payload(value: int) -> bytes:
    """R6-R7 §11.2 — KIND_INT payload = str(value).encode('ascii')."""
    return str(value).encode("ascii")


def string_payload(value: str) -> bytes:
    """R6-R7 §11.2 — KIND_STRING payload = value.encode('utf-8')."""
    return value.encode("utf-8")


def bytes_payload(value: bytes) -> bytes:
    """R6-R7 §11.2 — KIND_BYTES payload = bytes(value)."""
    return bytes(value)


def enum_payload(value: Any) -> bytes:
    """R6-R7 §11.2 — KIND_ENUM payload = enum.value.encode('ascii')."""
    encoded: bytes = value.value.encode("ascii")
    return encoded


def none_payload() -> bytes:
    """R6-R7 §11.2 — KIND_NONE payload is empty bytes."""
    return b""


def composite_hash(record_namespace: str, fields: Sequence[tuple[str, bytes, bytes]]) -> str:
    """Convenience: hash a record frame as sha256_hex_from_framed_bytes."""
    return sha256_hex_from_framed_bytes(frame_record(record_namespace, fields))


# ---------------------------------------------------------------------------
# Absent optional projection (R6-R7 §9.5 raw_projection_field_closure).
# ---------------------------------------------------------------------------


ABSENT_OPTIONAL_KIND: Final[bytes] = KIND_NONE
ABSENT_OPTIONAL_PAYLOAD: Final[bytes] = b""


__all__ = [
    "KIND_NONE",
    "KIND_INT",
    "KIND_STRING",
    "KIND_BYTES",
    "KIND_DECIMAL",
    "KIND_ENUM",
    "KIND_TUPLE",
    "KIND_RECORD",
    "KIND_RAW_PROJECTION",
    "ABSENT_OPTIONAL_KIND",
    "ABSENT_OPTIONAL_PAYLOAD",
    "frame_value",
    "frame_tuple",
    "frame_record",
    "sha256_hex_from_framed_bytes",
    "decimal_payload",
    "int_payload",
    "string_payload",
    "bytes_payload",
    "enum_payload",
    "none_payload",
    "composite_hash",
]
