"""TASK-028 raw projection value object and recursive raw-value canonicalization.

§15 — Raw projection, §24 — Raw encoding.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast

from hexagent.exchangers.shell_tube.tube_side.canonical import (
    _u32_be,
    _u64_be,
)

# §11.1 — Raw projection kind tags
RAW_NONE = b"RAW_NONE"
RAW_BOOL = b"RAW_BOOL"
RAW_INTEGER = b"RAW_INTEGER"
RAW_STRING = b"RAW_STRING"
RAW_DECIMAL = b"RAW_DECIMAL"
RAW_MAPPING = b"RAW_MAPPING"
RAW_SEQUENCE = b"RAW_SEQUENCE"
RAW_UNSUPPORTED = b"RAW_UNSUPPORTED_VALUE"


@dataclass(frozen=True)
class Task028RawProjection:
    """§11.1 — TASK-028 raw projection. Namespace: task028.raw-projection.v1."""

    projection_kind: str  # "REQUEST" | "TASK025_RESULT" | "TASK026_RESULT"
    canonical_bytes_hex: str


def _raw_frame(tag: bytes, payload: bytes) -> bytes:
    """Raw projection frame: U32(tag_len) + tag + U64(payload_len) + payload."""
    return _u32_be(len(tag)) + tag + _u64_be(len(payload)) + payload


def _raw_decimal_payload(value: Decimal) -> bytes:
    """Encode Decimal as lexical bytes for raw projection (evidence-preserving, no quantization)."""
    if value.is_snan():
        return b"sNaN"
    if value.is_nan():
        return b"-NaN" if value.is_signed() else b"NaN"
    if value.is_infinite():
        return b"-Infinity" if value.is_signed() else b"Infinity"
    sign, digits, exponent = value.as_tuple()
    finite_exponent = cast(int, exponent)
    digits_ascii = "".join(str(d) for d in digits)
    if digits_ascii == "":
        digits_ascii = "0"
    if finite_exponent >= 0:
        integer_part = digits_ascii + ("0" * finite_exponent)
        fractional_part = ""
    else:
        fractional_digits = -finite_exponent
        if len(digits_ascii) <= fractional_digits:
            integer_part = "0"
            fractional_part = ("0" * (fractional_digits - len(digits_ascii))) + digits_ascii
        else:
            split = len(digits_ascii) - fractional_digits
            integer_part = digits_ascii[:split]
            fractional_part = digits_ascii[split:]
    lexical = integer_part + ("." + fractional_part if fractional_part else "")
    if sign:
        lexical = "-" + lexical
    return lexical.encode("ascii")


def canonicalize_raw_value(value: Any) -> bytes:
    """§11.2 — Recursive raw-value canonicalization."""
    if value is None:
        return _raw_frame(RAW_NONE, b"")
    if type(value) is bool:
        return _raw_frame(RAW_BOOL, b"true" if value else b"false")
    if type(value) is int:
        return _raw_frame(RAW_INTEGER, str(value).encode("ascii"))
    if type(value) is str:
        return _raw_frame(RAW_STRING, value.encode("utf-8"))
    if type(value) is Decimal:
        return _raw_frame(RAW_DECIMAL, _raw_decimal_payload(value))
    if type(value) is dict:
        for key in value:
            if type(key) is not str:
                return _raw_frame(RAW_UNSUPPORTED, b"")
        sorted_keys = sorted(value.keys(), key=lambda k: k.encode("utf-8"))
        payload = _u32_be(len(sorted_keys))
        for key in sorted_keys:
            key_frame = _raw_frame(RAW_STRING, key.encode("utf-8"))
            value_frame = canonicalize_raw_value(value[key])
            payload += _u64_be(len(key_frame)) + key_frame + _u64_be(len(value_frame)) + value_frame
        return _raw_frame(RAW_MAPPING, payload)
    if type(value) is list or type(value) is tuple:
        payload = _u32_be(len(value))
        for item in value:
            item_frame = canonicalize_raw_value(item)
            payload += _u64_be(len(item_frame)) + item_frame
        return _raw_frame(RAW_SEQUENCE, payload)
    return _raw_frame(RAW_UNSUPPORTED, b"")


def encode_raw_projection(projection_kind: str, raw_input: Any) -> Task028RawProjection:
    """Encode a raw input into a Task028RawProjection."""
    canonical_bytes = canonicalize_raw_value(raw_input)
    canonical_bytes_hex = hashlib.sha256(canonical_bytes).hexdigest()
    return Task028RawProjection(
        projection_kind=projection_kind,
        canonical_bytes_hex=canonical_bytes_hex,
    )


__all__ = [
    "Task028RawProjection",
    "canonicalize_raw_value",
    "encode_raw_projection",
    "RAW_NONE",
    "RAW_BOOL",
    "RAW_INTEGER",
    "RAW_STRING",
    "RAW_DECIMAL",
    "RAW_MAPPING",
    "RAW_SEQUENCE",
    "RAW_UNSUPPORTED",
    "_raw_frame",
    "_raw_decimal_payload",
]
