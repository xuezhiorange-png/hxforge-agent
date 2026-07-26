"""TASK-025 canonical value framing and A01 frozen value types.

# mypy: ignore-errors

§10.1 — Universal labeled-record framing
§14.3 — A01 production ownership: FrozenJsonArray, FrozenJsonObject, sha256_hex_from_framed_bytes

This module owns the unique byte contract used at every TASK-025 hash
boundary. No TASK-025 framing boundary may invoke the upstream
canonicalize_layout_payload / to_frozen_json / FrozenJsonValue helpers.
"""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any, Final

# -----------------------------------------------------------------------
# Canonical kind-tag literals (ASCII, frozen).
# §10.1 — INTEGER_ENCODING / NONE_ENCODING / DECIMAL_LEXICAL_ENCODING.
# -----------------------------------------------------------------------

KIND_NONE: Final[bytes] = b"NONE"
KIND_BOOL_TRUE: Final[bytes] = b"BOOL_TRUE"
KIND_BOOL_FALSE: Final[bytes] = b"BOOL_FALSE"
KIND_INT: Final[bytes] = b"INT"
KIND_STRING: Final[bytes] = b"STRING"
KIND_BYTES: Final[bytes] = b"BYTES"
KIND_DECIMAL: Final[bytes] = b"DECIMAL"
KIND_ENUM: Final[bytes] = b"ENUM"
KIND_TUPLE: Final[bytes] = b"TUPLE"
KIND_RECORD: Final[bytes] = b"RECORD"
KIND_FROZEN_JSON_ARRAY: Final[bytes] = b"FROZEN_JSON_ARRAY"
KIND_FROZEN_JSON_OBJECT: Final[bytes] = b"FROZEN_JSON_OBJECT"
KIND_RAW_PROJECTION: Final[bytes] = b"RAW_PROJECTION"


# -----------------------------------------------------------------------
# Canonical framing primitives.
# -----------------------------------------------------------------------


def _u32_be(n: int) -> bytes:
    if n < 0 or n > 0xFFFFFFFF:
        raise ValueError("u32_be out of range")
    return struct.pack(">I", n)


def _u64_be(n: int) -> bytes:
    if n < 0 or n > 0xFFFFFFFFFFFFFFFF:
        raise ValueError("u64_be out of range")
    return struct.pack(">Q", n)


def frame_value(kind_tag_ascii: bytes, payload_bytes: bytes) -> bytes:
    """§10.1 — Universal labeled-record framing for a single value.

    FRAME(kind_tag_ascii, payload_bytes) =
        KIND_TAG_LENGTH_U32_BE
      || KIND_TAG_ASCII
      || PAYLOAD_LENGTH_U64_BE
      || PAYLOAD_BYTES
    """
    kind_tag = (
        kind_tag_ascii if isinstance(kind_tag_ascii, bytes) else kind_tag_ascii.encode("ascii")
    )
    payload = payload_bytes if isinstance(payload_bytes, bytes) else payload_bytes.encode("ascii")
    return _u32_be(len(kind_tag)) + kind_tag + _u64_be(len(payload)) + payload


def frame_tuple(item_payloads: Sequence[bytes]) -> bytes:
    """§10.1 — TUPLE_PAYLOAD with U32_BE item count.

    TUPLE_PAYLOAD =
        ITEM_COUNT_U32_BE
      || for each item in order:
            FRAME(item_kind_tag, item_payload)
    """
    out = _u32_be(len(item_payloads))
    for payload in item_payloads:
        # Default kind is "ITEM" — caller decides actual kind via frame_value.
        out += frame_value(b"ITEM", payload)
    return out


def frame_record(node_namespace: str, fields: Sequence[tuple[str, bytes, bytes]]) -> bytes:
    """§10.1 — HASH_RECORD canonical framing.

    HASH_RECORD =
        NODE_NAMESPACE_LENGTH_U32_BE
      || NODE_NAMESPACE_UTF8
      || FIELD_COUNT_U32_BE
      || for each field in frozen order:
            FIELD_NAME_LENGTH_U32_BE
          || FIELD_NAME_UTF8
          || FRAME(field_kind_tag, field_payload)
    """
    ns = node_namespace.encode("utf-8")
    out = _u32_be(len(ns)) + ns + _u32_be(len(fields))
    for field_name, field_kind_tag, field_payload in fields:
        out += (
            _u32_be(len(field_name))
            + field_name.encode("utf-8")
            + frame_value(field_kind_tag, field_payload)
        )
    return out


# -----------------------------------------------------------------------
# §8.4 π authority — exact UTF-8 lexeme.
# -----------------------------------------------------------------------

PI_DECIMAL_LEXEME: Final[bytes] = (
    b"3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679"
)
# PI_DECIMAL_CANONICAL_UTF8_SHA256 verified by §16 audit block:
#   aa6eee625a838a2af84f7d591e8c677bdd9c1b07c44380e2fee8fc738f9234f0
_PI_DIGEST: Final[bytes] = hashlib.sha256(PI_DECIMAL_LEXEME).digest()
assert _PI_DIGEST.hex() == "aa6eee625a838a2af84f7d591e8c677bdd9c1b07c44380e2fee8fc738f9234f0", (
    "PI authority canonical UTF-8 SHA-256 mismatch"
)


def pi_decimal() -> PIWrapper:
    """Return the TASK-025 π authority as a Decimal wrapper.

    The wrapper exposes the canonical UTF-8 lexeme bytes for hashing.
    """
    from decimal import Decimal as _Decimal  # local import to avoid module-load cost

    return PIWrapper(_Decimal(PI_DECIMAL_LEXEME.decode("ascii")))


class PIWrapper:
    """Wrapper for the §8.4 π authority.

    Exposes the canonical UTF-8 lexeme bytes for hashing through the
    raw projection (which encodes Decimals as their lexeme).
    """

    __slots__ = ("_value", "_lexeme")

    def __init__(self, value: Any) -> None:
        self._value = value
        self._lexeme = PI_DECIMAL_LEXEME

    @property
    def canonical_utf8_bytes(self) -> bytes:
        """Return the canonical UTF-8 bytes for hashing."""
        return self._lexeme

    def __repr__(self) -> str:  # pragma: no cover
        return "PIWrapper(canonical)"


# -----------------------------------------------------------------------
# §14.3 — A01 frozen value types: FrozenJsonArray, FrozenJsonObject.
# Frozen JSON value containers that participate in canonical hashing.
# -----------------------------------------------------------------------


class FrozenJsonArray(Sequence[Any]):
    """§14.3 — Frozen JSON array value object.

    The backing tuple is read-only. Hashing uses the universal labeled
    record framing. Items must be TASK-025 canonical atoms (None /
    bool / int / str / bytes / Decimal / enum) or nested FrozenJsonArray /
    FrozenJsonObject.
    """

    __slots__ = ("_items",)

    def __init__(self, items: Sequence[Any]) -> None:
        items_tuple = tuple(items)
        for item in items_tuple:
            _validate_frozen_json_item(item)
        self._items = items_tuple

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: Any) -> Any:
        return self._items[index]

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._items)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FrozenJsonArray):
            return NotImplemented
        return self._items == other._items

    def __hash__(self) -> int:
        return hash(self._items)

    def items(self) -> tuple[Any, ...]:
        return self._items

    def __repr__(self) -> str:  # pragma: no cover
        return f"FrozenJsonArray(len={len(self._items)})"


class FrozenJsonObject(Mapping[str, Any]):
    """§14.3 — Frozen JSON object value object.

    Keys must be exact str. Backing mapping preserves insertion order.
    Hashing uses the universal labeled record framing.
    """

    __slots__ = ("_items",)

    def __init__(self, items: Mapping[str, Any]) -> None:
        items_dict: dict[str, Any] = {}
        for key, value in items.items():
            if not isinstance(key, str):
                raise TypeError(f"FrozenJsonObject keys must be str, got {type(key).__name__}")
            _validate_frozen_json_item(value)
            items_dict[key] = value
        self._items = MappingProxyType(items_dict)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, key: str) -> Any:
        return self._items[key]

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._items)

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FrozenJsonObject):
            return NotImplemented
        return self._items == other._items

    def __hash__(self) -> int:
        return hash(tuple(sorted(self._items.items())))

    @property
    def items_mapping(self) -> Mapping[str, Any]:
        return self._items

    @property
    def values(self) -> Mapping[str, Any]:
        """Read-only owned mapping used by internal canonical consumers."""
        return self._items

    def __repr__(self) -> str:  # pragma: no cover
        return f"FrozenJsonObject(len={len(self._items)})"


def _validate_frozen_json_item(item: Any) -> None:
    """Validate that ``item`` is a TASK-025 canonical atom or nested container."""
    if item is None or isinstance(item, (bool, int, str, bytes)):
        return
    # Lazy import to keep module-load cost low.
    import enum as _enum
    from decimal import Decimal

    if isinstance(item, (Decimal, PIWrapper, FrozenJsonArray, FrozenJsonObject)):
        return
    if isinstance(item, _enum.Enum):
        return
    raise TypeError(
        f"FrozenJsonArray / FrozenJsonObject items must be canonical atoms "
        f"or nested FrozenJson containers; got {type(item).__name__}"
    )


# -----------------------------------------------------------------------
# §14.3 — SHA-256 helper.
# -----------------------------------------------------------------------


def sha256_hex_from_framed_bytes(framed_bytes: bytes) -> str:
    """Return the 64-lowercase-hex SHA-256 of the framed bytes."""
    return hashlib.sha256(framed_bytes).hexdigest()


# Public re-export name used by §14.3 table.
sha256_hex = sha256_hex_from_framed_bytes


__all__ = [
    "KIND_NONE",
    "KIND_BOOL_TRUE",
    "KIND_BOOL_FALSE",
    "KIND_INT",
    "KIND_STRING",
    "KIND_BYTES",
    "KIND_DECIMAL",
    "KIND_ENUM",
    "KIND_TUPLE",
    "KIND_RECORD",
    "KIND_FROZEN_JSON_ARRAY",
    "KIND_FROZEN_JSON_OBJECT",
    "KIND_RAW_PROJECTION",
    "frame_value",
    "frame_tuple",
    "frame_record",
    "PI_DECIMAL_LEXEME",
    "PIWrapper",
    "pi_decimal",
    "FrozenJsonArray",
    "FrozenJsonObject",
    "sha256_hex_from_framed_bytes",
    "sha256_hex",
]

# ruff: noqa: E501
