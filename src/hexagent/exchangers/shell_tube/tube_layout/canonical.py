"""Deterministic canonicalization helpers for TASK-021 Slice A."""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from typing import Any

DECIMAL_PRECISION = 50
COORDINATE_QUANTUM = Decimal("0.000000000001")
SQRT_3 = Decimal("1.7320508075688772935274463415058723669428052538104")
UUID_NAMESPACE_URL = uuid.NAMESPACE_URL
POSITION_URN_PREFIX = "urn:hxforge:task021:tube-position:v1:"
LAYOUT_URN_PREFIX = "urn:hxforge:task021:tube-layout:v1:"
_DECIMAL_RE = __import__("re").compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


class CanonicalizationError(ValueError):
    """Raised when a value is outside the TASK-021 canonical JSON domain."""


def parse_decimal(value: str, *, positive: bool | None = None) -> Decimal:
    """Parse one canonical decimal string under the frozen Decimal context."""

    if not isinstance(value, str) or not _DECIMAL_RE.fullmatch(value):
        raise CanonicalizationError("decimal lexical form is invalid")
    if value.startswith("+") or value != value.strip() or "e" in value.lower():
        raise CanonicalizationError("decimal lexical form is invalid")
    try:
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            result = Decimal(value)
    except InvalidOperation as exc:  # pragma: no cover - Decimal is defensive
        raise CanonicalizationError("decimal lexical form is invalid") from exc
    if not result.is_finite():
        raise CanonicalizationError("decimal must be finite")
    if result == 0:
        result = Decimal(0)
    if positive is True and result <= 0:
        raise CanonicalizationError("decimal must be positive")
    if positive is False and result < 0:
        raise CanonicalizationError("decimal must be non-negative")
    return result


def decimal_string(value: Decimal) -> str:
    """Return a non-exponent canonical decimal string."""

    if not value.is_finite():
        raise CanonicalizationError("decimal must be finite")
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def quantized_decimal_string(value: Decimal) -> str:
    """Quantize a coordinate using the frozen quantum and rounding mode."""

    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        return decimal_string(value.quantize(COORDINATE_QUANTUM))


def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, float):
        raise CanonicalizationError("binary floating-point values are forbidden")
    if isinstance(value, Decimal):
        raise CanonicalizationError(
            "Decimal objects are forbidden at serialization boundary"
        )
    if dataclasses.is_dataclass(value):
        return _canonical_value(dataclass_to_mapping(value))
    if isinstance(value, tuple | set | frozenset):
        raise CanonicalizationError("implicit array types are forbidden")
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("canonical object keys must be strings")
            normalized[key] = _canonical_value(item)
        return {key: normalized[key] for key in sorted(normalized)}
    raise CanonicalizationError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize a value under the TASK-021 canonical JSON rules."""

    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_hex(value: Any) -> str:
    """Return SHA-256 over canonical JSON bytes."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def dataclass_to_mapping(value: Any) -> dict[str, Any]:
    """Convert dataclasses and enums to JSON-compatible mappings preserving tuples as lists."""

    if not dataclasses.is_dataclass(value):
        raise TypeError("value must be a dataclass instance")
    result: dict[str, Any] = {}
    for field in dataclasses.fields(value):
        raw = getattr(value, field.name)
        result[field.name] = to_primitive(raw)
    return result


def to_primitive(value: Any) -> Any:
    """Convert package dataclasses to ordinary JSON-compatible Python values."""

    if dataclasses.is_dataclass(value):
        return dataclass_to_mapping(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, tuple):
        return [to_primitive(item) for item in value]
    if isinstance(value, list):
        return [to_primitive(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): to_primitive(item) for key, item in value.items()}
    return value


def sorted_unique_strings(
    values: Sequence[str], *, allow_empty: bool = True
) -> tuple[str, ...]:
    """Validate and sort a duplicate-free string array."""

    if not isinstance(values, list | tuple):
        raise TypeError("expected an array")
    if not allow_empty and not values:
        raise ValueError("array must be non-empty")
    if any(not isinstance(item, str) or not item for item in values):
        raise TypeError("array items must be non-empty strings")
    if len(set(values)) != len(values):
        raise ValueError("duplicate array item")
    return tuple(sorted(values))


def message_sort_key(entry: Any) -> tuple[str, str, str, str, str]:
    """Return the frozen warning/blocker composite ordering key."""

    details = getattr(entry, "details", None)
    evidence_refs = list(getattr(entry, "evidence_refs", ()))
    return (
        str(getattr(entry, "code")),
        "" if getattr(entry, "field_path", None) is None else str(entry.field_path),
        str(getattr(entry, "message_key")),
        sha256_hex(details),
        sha256_hex(evidence_refs),
    )


def sort_messages(entries: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(entries, key=message_sort_key))


def position_id(request_hash: str, u: int, v: int) -> str:
    return str(
        uuid.uuid5(UUID_NAMESPACE_URL, f"{POSITION_URN_PREFIX}{request_hash}:{u}:{v}")
    )


def layout_id(layout_hash: str) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE_URL, LAYOUT_URN_PREFIX + layout_hash))


__all__ = [
    "COORDINATE_QUANTUM",
    "DECIMAL_PRECISION",
    "LAYOUT_URN_PREFIX",
    "POSITION_URN_PREFIX",
    "SQRT_3",
    "UUID_NAMESPACE_URL",
    "CanonicalizationError",
    "canonical_json",
    "dataclass_to_mapping",
    "decimal_string",
    "layout_id",
    "message_sort_key",
    "parse_decimal",
    "position_id",
    "quantized_decimal_string",
    "sha256_hex",
    "sort_messages",
    "sorted_unique_strings",
    "to_primitive",
]
