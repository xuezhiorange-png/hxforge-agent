"""Round-3 canonical boundary tests for TASK-021 Slice A.

Round 3 §6 (P1-1) requires a strict three-layer separation:

  1. ``strict_public_json_snapshot(value)`` — accepts only the §6.1 canonical
     JSON domain (null / bool / int / str / list / string-keyed dict).
     Recursively copies and freezes. Rejects float, Decimal, bytes, tuple,
     set, frozenset, arbitrary objects, non-string mapping keys.

  2. ``freeze_deeply(value)`` — recursively converts an already-canonical
     primitive into a deeply-frozen shape (mapping→MappingProxyType,
     list→tuple, leaves preserved). Rejects out-of-domain types and never
     silently coerces.

  3. ``frozen_fragment_to_primitive(value)`` — accepts ONLY the recursive
     frozen shape. Reduces MappingProxyType→dict, tuple→list. Rejects
     arbitrary objects, Decimal, bytes, set, frozenset.

  4. ``canonical_json(value)`` — public serialization boundary that MUST NOT
     accept arbitrary tuples, frozenset, set, float, Decimal, bytes.

This file exercises that three-layer boundary.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal
from types import MappingProxyType
from typing import Any

import pytest

from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    CanonicalizationError,
    NonCanonicalFragmentError,
    PublicCanonicalDomainError,
    canonical_json,
    canonical_raw_json_or_none,
    fragment_canonical_json,
    freeze_deeply,
    frozen_fragment_to_primitive,
    quantized_decimal_string,
    strict_public_json_snapshot,
)

# --------------------------------------------------------------------------- #
# canonical_json — fail-closed at the public serialization boundary
# --------------------------------------------------------------------------- #


def test_canonical_json_sorts_keys_and_rejects_float() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    with pytest.raises(CanonicalizationError):
        canonical_json({"x": 1.0})


def test_canonical_json_rejects_tuple() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_json((1, 2, 3))


def test_canonical_json_rejects_frozenset() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_json(frozenset({"a", "b"}))


def test_canonical_json_rejects_set() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_json({"a", "b", "c"})


def test_canonical_json_rejects_bytes() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_json(b"hi")


def test_canonical_json_rejects_decimal() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_json(Decimal("1.5"))


def test_canonical_json_rejects_non_string_mapping_key() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_json({1: "value"})


def test_coordinate_quantization_is_half_even() -> None:
    assert quantized_decimal_string(Decimal("0.0000000000015")) == "0.000000000002"
    assert quantized_decimal_string(Decimal("0.0000000000025")) == "0.000000000002"


# --------------------------------------------------------------------------- #
# strict_public_json_snapshot — accept only canonical JSON domain
# --------------------------------------------------------------------------- #


def test_strict_snapshot_accepts_primitives() -> None:
    assert strict_public_json_snapshot(None) is None
    assert strict_public_json_snapshot(True) is True
    assert strict_public_json_snapshot(42) == 42
    assert strict_public_json_snapshot("hi") == "hi"


def test_strict_snapshot_accepts_lists() -> None:
    snap = strict_public_json_snapshot([1, "two", [None, True]])
    assert isinstance(snap, tuple)
    assert snap[2] == (None, True)


def test_strict_snapshot_accepts_string_keyed_dict() -> None:
    snap = strict_public_json_snapshot({"z": 1, "a": [1, 2]})
    assert isinstance(snap, MappingProxyType)
    assert tuple(snap.keys()) == ("a", "z")
    assert isinstance(snap["a"], tuple)


@pytest.mark.parametrize(
    "bad_value",
    [
        0.5,
        Decimal("1.5"),
        b"bytes",
        ("a", "b"),
        frozenset({"a"}),
        {"a", "b"},
        object(),
        {1: "value"},
    ],
)
def test_strict_snapshot_rejects_out_of_domain_inputs(bad_value: Any) -> None:
    with pytest.raises(PublicCanonicalDomainError):
        strict_public_json_snapshot(bad_value)


# --------------------------------------------------------------------------- #
# frozen_fragment_to_primitive — accepts only the strict snapshot shape
# --------------------------------------------------------------------------- #


def test_frozen_primitive_reduces_mapping_to_dict() -> None:
    snap = strict_public_json_snapshot({"a": 1, "b": [1, 2]})
    reduced = frozen_fragment_to_primitive(snap)
    assert reduced == {"a": 1, "b": [1, 2]}
    assert isinstance(reduced, dict)
    assert isinstance(reduced["b"], list)


def test_frozen_primitive_rejects_arbitrary_object() -> None:
    with pytest.raises(NonCanonicalFragmentError):
        frozen_fragment_to_primitive(object())


def test_frozen_primitive_rejects_decimal() -> None:
    with pytest.raises(NonCanonicalFragmentError):
        frozen_fragment_to_primitive(Decimal("1.5"))


def test_frozen_primitive_rejects_bytes() -> None:
    with pytest.raises(NonCanonicalFragmentError):
        frozen_fragment_to_primitive(b"raw")


def test_frozen_primitive_rejects_frozenset() -> None:
    with pytest.raises(NonCanonicalFragmentError):
        frozen_fragment_to_primitive(frozenset({"a", "b"}))


def test_frozen_primitive_rejects_set() -> None:
    with pytest.raises(NonCanonicalFragmentError):
        frozen_fragment_to_primitive({"a", "b"})


# --------------------------------------------------------------------------- #
# canonical_raw_json_or_none — fail-closed for §12.8 raw_failing_field
# --------------------------------------------------------------------------- #


def test_canonical_raw_json_or_none_returns_none_for_unsupported() -> None:
    assert canonical_raw_json_or_none(0.5) is None
    assert canonical_raw_json_or_none(Decimal("1.5")) is None
    assert canonical_raw_json_or_none(b"raw") is None
    assert canonical_raw_json_or_none((1, 2, 3)) is None
    assert canonical_raw_json_or_none(frozenset({"a"})) is None
    assert canonical_raw_json_or_none(object()) is None
    assert canonical_raw_json_or_none({1: "value"}) is None


def test_canonical_raw_json_or_none_preserves_supported_inputs() -> None:
    assert canonical_raw_json_or_none(None) is None
    assert canonical_raw_json_or_none("raw") == "raw"
    primitive = canonical_raw_json_or_none({"b": "raw-2", "a": [1, 2]})
    assert primitive == {"a": [1, 2], "b": "raw-2"}


def test_canonical_raw_json_or_none_stable_for_repeated_invalid_input() -> None:
    a = canonical_raw_json_or_none(0.5)
    b = canonical_raw_json_or_none(Decimal("3.14"))
    c = canonical_raw_json_or_none((1, 2))
    assert a is None and b is None and c is None


# --------------------------------------------------------------------------- #
# freeze_deeply — internal hardening of an already-canonical primitive
# --------------------------------------------------------------------------- #


def test_freeze_deeply_makes_mapping_proxy_for_dict() -> None:
    frozen = freeze_deeply({"a": 1, "b": 2})
    assert isinstance(frozen, MappingProxyType)
    assert frozen["a"] == 1
    with pytest.raises(TypeError):
        frozen["a"] = 99  # type: ignore[index]


def test_freeze_deeply_converts_nested_lists_to_tuples() -> None:
    frozen = freeze_deeply({"nested": [1, 2, 3]})
    assert isinstance(frozen["nested"], tuple)


def test_freeze_deeply_rejects_bytes() -> None:
    with pytest.raises(PublicCanonicalDomainError):
        freeze_deeply({"raw": b"x"})


def test_freeze_deeply_rejects_decimals_silently_stringifying() -> None:
    with pytest.raises(PublicCanonicalDomainError):
        freeze_deeply({"d": Decimal("0.1")})


def test_freeze_deeply_rejects_set_and_tuple_and_uses_public_boundary() -> None:
    """Round 4 §7: ``freeze_deeply`` is now a thin wrapper over the public
    canonical JSON boundary. It MUST reject ``set``, ``tuple``, ``frozenset``,
    ``Decimal``, ``bytes``, ``float``, ``memoryview``, dataclasses, enums, and
    arbitrary objects — every historical bypass route is closed.
    """

    # Set / tuple / frozenset: rejected.
    with pytest.raises(PublicCanonicalDomainError):
        freeze_deeply({"items": {"a", "b"}})
    with pytest.raises(PublicCanonicalDomainError):
        freeze_deeply({"items": ("a", "b")})
    with pytest.raises(PublicCanonicalDomainError):
        freeze_deeply({"items": frozenset({"a", "b"})})
    # Decimal / bytes / float: rejected.
    with pytest.raises(PublicCanonicalDomainError):
        freeze_deeply({"x": Decimal("1")})
    with pytest.raises(PublicCanonicalDomainError):
        freeze_deeply({"x": b"a"})
    with pytest.raises(PublicCanonicalDomainError):
        freeze_deeply({"x": 1.5})
    # Arbitrary object / dataclass / enum: rejected.
    with pytest.raises(PublicCanonicalDomainError):
        freeze_deeply({"x": object()})


def test_freeze_deeply_rejects_non_string_mapping_key() -> None:
    with pytest.raises((PublicCanonicalDomainError, CanonicalizationError)):
        freeze_deeply({1: "value"})


# --------------------------------------------------------------------------- #
# fragment_canonical_json — canonical JSON via snapshot
# --------------------------------------------------------------------------- #


def test_fragment_canonical_json_round_trips() -> None:
    raw = {"a": 1, "b": [2, 3, "x"]}
    assert json.loads(fragment_canonical_json(raw)) == raw


def test_fragment_canonical_json_rejects_non_canonical_input() -> None:
    with pytest.raises(PublicCanonicalDomainError):
        fragment_canonical_json({"raw": 1.5})


def test_fragment_canonical_captures_state_per_invocation() -> None:
    """Each freeze+canonical capture is independent of subsequent mutations."""

    raw: dict[str, object] = {"a": [1, 2], "b": {"c": 3}}
    h1 = fragment_canonical_json(raw)
    raw["a"] = [1, 2, 99]  # type: ignore[assignment]
    raw["b"] = {"c": 99}  # type: ignore[assignment]
    h2 = fragment_canonical_json(raw)
    assert h1 != h2
    assert json.loads(h1) == {"a": [1, 2], "b": {"c": 3}}


# --------------------------------------------------------------------------- #
# Public boundary rejects arbitrary objects (round 3 §6 explicit assertions)
# --------------------------------------------------------------------------- #


def test_public_canonical_boundary_rejects_arbitrary_object() -> None:
    class Custom:
        pass

    with pytest.raises(PublicCanonicalDomainError):
        strict_public_json_snapshot(Custom())


def test_public_canonical_boundary_rejects_nan_like_inputs() -> None:
    with pytest.raises((PublicCanonicalDomainError, PublicCanonicalDomainError)):
        strict_public_json_snapshot(float("nan"))
    with pytest.raises((PublicCanonicalDomainError, PublicCanonicalDomainError)):
        strict_public_json_snapshot(math.inf)


def test_blocked_returned_by_canonical_raw_is_none_with_non_string_keys() -> None:
    raw = {(1, 2): "x"}
    assert canonical_raw_json_or_none(raw) is None


def test_canonical_raw_handles_dict_with_floats_via_none() -> None:
    raw = {"radius": 0.5}
    assert canonical_raw_json_or_none(raw) is None
