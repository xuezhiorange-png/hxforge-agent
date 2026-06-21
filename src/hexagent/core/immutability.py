"""Recursive deep-freeze utility for domain model immutability guarantees.

Converts mutable containers to their immutable equivalents:
- ``dict`` → ``types.MappingProxyType`` (recursively)
- ``list`` → ``tuple`` (recursively)
- ``set`` / ``frozenset`` → ``tuple`` (sorted, recursively)

Primitives, ``None``, ``UUID``, ``datetime``, ``Enum``, ``str``, ``int``,
``float`` pass through unchanged.

Any unsupported mutable type raises ``TypeError`` — the freeze contract
is strict: unknown types must not silently retain mutability.
"""

from __future__ import annotations

import types
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

# Types that are known to be immutable and safe to pass through.
_KNOWN_IMMUTABLE: frozenset[type] = frozenset(
    {
        type(None),
        bool,
        int,
        float,
        str,
        bytes,
        UUID,
        datetime,
        Enum,
        types.MappingProxyType,
        tuple,
        frozenset,
    }
)


def deep_freeze(obj: Any) -> Any:
    """Recursively convert *obj* to an immutable representation.

    ``dict`` → ``MappingProxyType`` with recursively frozen values.
    ``list`` / ``set`` / ``frozenset`` → ``tuple`` with recursively
    frozen elements.

    Primitives, ``None``, ``UUID``, ``datetime`` and ``Enum`` instances
    are returned unchanged.

    Raises ``TypeError`` if an unsupported mutable type is encountered,
    ensuring no silently-mutable containers slip through.
    """
    if isinstance(obj, (type(None), bool, int, float, str, bytes)):
        return obj
    if isinstance(obj, UUID):
        return obj
    if isinstance(obj, datetime):
        return obj
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, types.MappingProxyType):
        return obj  # already frozen
    if isinstance(obj, dict):
        frozen = {k: deep_freeze(v) for k, v in obj.items()}
        return types.MappingProxyType(frozen)
    if isinstance(obj, (list, tuple)):
        return tuple(deep_freeze(item) for item in obj)
    if isinstance(obj, (set, frozenset)):
        return tuple(
            sorted(
                (deep_freeze(item) for item in obj),
                key=lambda x: repr(x),
            )
        )
    # Reject unknown types — they may be mutable.  The caller must
    # either convert to a supported type or prove immutability.
    raise TypeError(
        f"deep_freeze does not support type {type(obj).__name__!r}. "
        f"Convert to a supported container (dict, list, tuple, set, "
        f"frozenset) or a known-immutable type before freezing."
    )


def assert_frozen(obj: Any, path: str = "root") -> None:
    """Recursively verify that *obj* contains no mutable containers.

    Raises ``AssertionError`` with the path to the first mutable
    container found.
    """
    if isinstance(obj, dict):
        raise AssertionError(f"Mutable dict found at {path}; expected MappingProxyType")
    if isinstance(obj, list):
        raise AssertionError(f"Mutable list found at {path}; expected tuple")
    if isinstance(obj, set):
        raise AssertionError(f"Mutable set found at {path}; expected tuple")
    if isinstance(obj, types.MappingProxyType):
        for k, v in obj.items():
            assert_frozen(v, f"{path}.{k}")
    elif isinstance(obj, (tuple,)):
        for i, item in enumerate(obj):
            assert_frozen(item, f"{path}[{i}]")


__all__ = ["deep_freeze", "assert_frozen"]
