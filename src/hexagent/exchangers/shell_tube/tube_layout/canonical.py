"""Deterministic canonicalization helpers for TASK-021 Slice A."""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from types import MappingProxyType
from typing import Any

DECIMAL_PRECISION = 50
COORDINATE_QUANTUM = Decimal("0.000000000001")
SQRT_3 = Decimal("1.7320508075688772935274463415058723669428052538104")
UUID_NAMESPACE_URL = uuid.NAMESPACE_URL
POSITION_URN_PREFIX = "urn:hxforge:task021:tube-position:v1:"
LAYOUT_URN_PREFIX = "urn:hxforge:task021:tube-layout:v1:"
_DECIMAL_RE = __import__("re").compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


# Frozen-fragment types produced by `strict_public_json_snapshot`. Only these may
# be passed into `frozen_fragment_to_primitive` or any internal primitive-
# reduction path. Anything else (Decimal, bytes, float, set, frozenset, tuple,
# arbitrary object, non-string mapping key) MUST be rejected before it ever
# crosses the public/internal boundary.
FrozenMapping = MappingProxyType
FrozenSequence = tuple[Any, ...]
_FROZEN_ATOM_TYPES = (bool, int, str, type(None))


class CanonicalizationError(ValueError):
    """Raised when a value is outside the TASK-021 canonical JSON domain."""


class PublicCanonicalDomainError(CanonicalizationError):
    """Raised when a value intended for the public canonical boundary is invalid.

    This is the only signal `strict_public_json_snapshot` and
    `frozen_fragment_to_primitive` use to reject a value. Callers that want
    fail-closed semantics (`canonical_raw_json_or_none`) MUST catch this.
    """


class NonCanonicalFragmentError(CanonicalizationError):
    """Raised when a frozen fragment is asked to be reduced to a primitive form.

    The only acceptable inputs are `MappingProxyType` (frozen mapping) or
    `tuple` (frozen sequence). Anything else has bypassed
    `strict_public_json_snapshot` and is rejected.
    """


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


# --------------------------------------------------------------------------- #
# Public canonical boundary (round 3 P1-1)
# --------------------------------------------------------------------------- #
#
# `strict_public_json_snapshot` accepts ONLY the §6.1 canonical JSON domain:
#   - None
#   - bool, int, str
#   - list (recursively)
#   - dict whose keys are all str
#
# It MUST REJECT:
#   - float (binary floating-point)
#   - Decimal (not representable in canonical JSON; canonical decimal strings only)
#   - bytes, bytearray, memoryview
#   - tuple, set, frozenset, namedtuple
#   - arbitrary objects, dataclasses, enums
#   - dict with non-string keys
#   - any nested instance that crosses the boundary
#
# Output is a recursive deep-frozen structure: dict→MappingProxyType,
# list→tuple, leaves preserved. The frozen structure cannot be mutated after
# capture and is safe to canonically serialize.


def strict_public_json_snapshot(value: Any) -> Any:
    """Validate ``value`` and return a recursive deep-frozen canonical shape.

    Raises ``PublicCanonicalDomainError`` on any out-of-domain input. The
    returned structure uses ``MappingProxyType`` for mappings and ``tuple`` for
    sequences and may be safely passed to ``frozen_fragment_to_primitive`` or
    used as a public canonical value (e.g. for ``license_evidence``,
    ``MessageEntry.details``, ``case_authority``, ``provenance`` fragments).
    """

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return tuple(strict_public_json_snapshot(item) for item in value)
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise PublicCanonicalDomainError(
                    "mapping keys must be strings at the public canonical boundary"
                )
        frozen_items = {key: strict_public_json_snapshot(item) for key, item in value.items()}
        return MappingProxyType({key: frozen_items[key] for key in sorted(frozen_items)})
    raise PublicCanonicalDomainError(
        f"value of type {type(value).__name__} is outside the public canonical domain"
    )


def frozen_fragment_to_primitive(value: Any) -> Any:
    """Convert a frozen-fragment snapshot back to a JSON-compatible primitive.

    Accepts ONLY the recursive deep-frozen shape produced by
    ``strict_public_json_snapshot``. Anything else is rejected with
    ``NonCanonicalFragmentError`` so internal code never silently accepts a
    raw callable / Decimal / arbitrary-object that bypassed the snapshot
    boundary.
    """

    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, MappingProxyType):
        # sorted-key ordering for canonical JSON stability.
        return {key: frozen_fragment_to_primitive(item) for key, item in sorted(value.items())}
    if isinstance(value, tuple):
        return [frozen_fragment_to_primitive(item) for item in value]
    raise NonCanonicalFragmentError(
        f"frozen fragment value of type {type(value).__name__} is not a canonical atom"
    )


def snapshot_then_to_primitive(value: Any) -> Any:
    """Public-boundary pass for callers that hold an ordinary canonical value.

    Accepts a value in the §6.1 canonical JSON domain (null/bool/int/str/list/
    string-keyed dict) and returns the canonical-primitive form. Used for
    MessageEntry.details and other fragments that may still be ordinary
    dicts on internal data flows. The recursive snapshot guarantees
    immutability during the conversion.
    """

    frozen = strict_public_json_snapshot(value)
    return frozen_fragment_to_primitive(frozen)


def canonical_raw_json_or_none(value: Any) -> Any | None:
    """Return a detached primitive snapshot of ``value`` or ``None``.

    Implements §12.8 semantics: ``raw_failing_field`` is the canonical raw JSON
    for a failing field that could not be normalized, IF such canonical raw
    JSON exists. If the field is a float / Decimal / bytes / non-string-keyed
    mapping / arbitrary object / tuple / set / frozenset, return ``None``
    (no canonical raw JSON exists for that value at the public boundary).

    Never raises for unsupported inputs; always fail-closed.
    """

    if value is None:
        return None
    try:
        snapshot = strict_public_json_snapshot(value)
    except PublicCanonicalDomainError:
        return None
    try:
        return frozen_fragment_to_primitive(snapshot)
    except NonCanonicalFragmentError:
        return None


# --------------------------------------------------------------------------- #
# Internal canonical primitive reduction (round 3 P0-3 / P1-1)
# --------------------------------------------------------------------------- #
#
# `canonical_json` is the ONLY public JSON serialization boundary. It accepts
# only atoms that satisfy the canonical JSON domain; exceptions are strictly
# fail-closed.


def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, float):
        raise CanonicalizationError("binary floating-point values are forbidden")
    if isinstance(value, Decimal):
        raise CanonicalizationError("Decimal objects are forbidden at serialization boundary")
    if isinstance(value, (tuple, frozenset)):
        raise CanonicalizationError(
            f"sequence type {type(value).__name__} is forbidden at serialization boundary; "
            "use a list of canonical primitives instead"
        )
    if isinstance(value, set):
        raise CanonicalizationError(
            "set is forbidden at serialization boundary; iteration order is not canonical"
        )
    if dataclasses.is_dataclass(value):
        return _canonical_value(dataclass_to_mapping(value))
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
    if isinstance(value, bytes | bytearray | memoryview):
        raise CanonicalizationError("byte strings are forbidden at serialization boundary")
    if isinstance(value, float):
        raise CanonicalizationError("binary floating-point values are forbidden")
    if isinstance(value, Decimal):
        raise CanonicalizationError("Decimal objects must be expressed as canonical strings")
    if isinstance(value, tuple):
        return [to_primitive(item) for item in value]
    if isinstance(value, list):
        return [to_primitive(item) for item in value]
    if isinstance(value, Mapping):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalizationError("canonical mapping keys must be strings")
        return {key: to_primitive(item) for key, item in value.items()}
    if value is None or isinstance(value, (bool, int, str)):
        return value
    raise CanonicalizationError(f"unsupported canonical value: {type(value).__name__}")


# --------------------------------------------------------------------------- #
# Frozen fragment derivation (round 3 P1-1)
# --------------------------------------------------------------------------- #
#
# `freeze_deeply` produced an internal frozen shape previously. The round-3
# contract makes a strict distinction:
#
#  1. Public-boundary inputs MUST already be in §6.1 canonical JSON domain
#     (null / bool / int / str / list / string-keyed dict).
#     Call `strict_public_json_snapshot(value)` first.
#  2. After the boundary, the resulting frozen shape is the only form that is
#     permitted to flow into hash computation. Reduction back to a primitive
#     uses `frozen_fragment_to_primitive`.


def freeze_deeply(value: Any) -> Any:
    """Internal: deep-freeze a value IF it is already in the canonical domain.

    For the public boundary, prefer `strict_public_json_snapshot`. This helper
    remains exported because internal pipeline code uses it after upstream code
    has guaranteed the input is already a canonical primitive mapping or list
    of canonical primitives. It rejects out-of-domain types aggressively and
    never silently coerces.

    ``tuple`` and ``frozenset`` are accepted as atoms (already immutable);
    ``set`` is rejected because its iteration order is implementation-defined
    and would break canonical reproducibility.
    """

    if value is None or isinstance(value, _FROZEN_ATOM_TYPES):
        return value
    if isinstance(value, (tuple, frozenset)):
        return tuple(freeze_deeply(item) for item in value)
    if isinstance(value, bytes | bytearray | memoryview):
        raise PublicCanonicalDomainError(
            "byte strings are forbidden at the frozen-fragment boundary"
        )
    if isinstance(value, float):
        raise PublicCanonicalDomainError(
            "binary floating-point values are forbidden at the frozen-fragment boundary"
        )
    if isinstance(value, Decimal):
        raise PublicCanonicalDomainError(
            "Decimal objects must be expressed as canonical strings at the frozen-fragment boundary"
        )
    if isinstance(value, set):
        raise PublicCanonicalDomainError("set values are forbidden at the frozen-fragment boundary")
    if dataclasses.is_dataclass(value):
        return freeze_deeply(dataclass_to_mapping(value))
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, list):
        return tuple(freeze_deeply(item) for item in value)
    if isinstance(value, Mapping):
        for key in value:
            if not isinstance(key, str):
                raise PublicCanonicalDomainError("canonical fragment keys must be strings")
        frozen_items = {key: freeze_deeply(item) for key, item in value.items()}
        return MappingProxyType(frozen_items)
    raise PublicCanonicalDomainError(
        f"unsupported canonical fragment value: {type(value).__name__}"
    )


def fragment_canonical(value: Any) -> Any:
    """Canonicalize a frozen fragment to its sorted-key primitive form."""

    return _canonical_value(freeze_deeply(value))


def fragment_canonical_json(value: Any) -> str:
    """Return canonical JSON of a public-boundary frozen fragment.

    Callers must have already reduced the input through
    `strict_public_json_snapshot` (or fed in a dataclass that is intended for
    capture under a §12.6/§12.7 slot).
    """

    frozen = freeze_deeply(value)
    reduced = frozen_fragment_to_primitive(frozen)
    return canonical_json(reduced)


def frozen_mapping_to_mapping(value: MappingProxyType[Any, Any]) -> dict[str, Any]:
    """Convert a frozen mapping back to a JSON-compatible dict.

    The contract requires this conversion for hash computation. Calling code
    must ensure the input was produced by `strict_public_json_snapshot` and
    not by some other path that bypassed the boundary.
    """

    return {key: frozen_fragment_to_primitive(item) for key, item in sorted(value.items())}


def frozen_sequence_to_list(value: tuple[Any, ...]) -> list[Any]:
    """Convert a frozen tuple back to a JSON-compatible list."""

    return [frozen_fragment_to_primitive(item) for item in value]


def sorted_unique_strings(values: Sequence[str], *, allow_empty: bool = True) -> tuple[str, ...]:
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
        str(entry.code),
        "" if getattr(entry, "field_path", None) is None else str(entry.field_path),
        str(entry.message_key),
        sha256_hex(details),
        sha256_hex(evidence_refs),
    )


def sort_messages(entries: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(entries, key=message_sort_key))


def position_id(request_hash: str, u: int, v: int) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE_URL, f"{POSITION_URN_PREFIX}{request_hash}:{u}:{v}"))


def layout_id(layout_hash: str) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE_URL, LAYOUT_URN_PREFIX + layout_hash))


__all__ = [
    "COORDINATE_QUANTUM",
    "DECIMAL_PRECISION",
    "LAYOUT_URN_PREFIX",
    "NonCanonicalFragmentError",
    "POSITION_URN_PREFIX",
    "PublicCanonicalDomainError",
    "SQRT_3",
    "UUID_NAMESPACE_URL",
    "CanonicalizationError",
    "canonical_json",
    "canonical_raw_json_or_none",
    "dataclass_to_mapping",
    "decimal_string",
    "fragment_canonical",
    "fragment_canonical_json",
    "freeze_deeply",
    "frozen_fragment_to_primitive",
    "frozen_mapping_to_mapping",
    "frozen_sequence_to_list",
    "layout_id",
    "message_sort_key",
    "parse_decimal",
    "position_id",
    "quantized_decimal_string",
    "sha256_hex",
    "snapshot_then_to_primitive",
    "sort_messages",
    "sorted_unique_strings",
    "strict_public_json_snapshot",
    "to_primitive",
]
