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

  3. ``internal_frozen_to_primitive(value)`` — accepts ONLY the recursive
     frozen shape. Reduces MappingProxyType→dict, tuple→list. Rejects
     arbitrary objects, Decimal, bytes, set, frozenset.

  4. ``canonical_json(value)`` — public serialization boundary that MUST NOT
     accept arbitrary tuples, frozenset, set, float, Decimal, bytes.

This file exercises that three-layer boundary.
"""

from __future__ import annotations

import dataclasses
import json
import math
from decimal import Decimal
from types import MappingProxyType
from typing import Any

import pytest

from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    CanonicalizationError,
    FrozenJsonArray,
    FrozenJsonObject,
    NonCanonicalFragmentError,
    PublicCanonicalDomainError,
    canonical_json,
    canonical_raw_json_or_none,
    fragment_canonical_json,
    freeze_deeply,
    internal_frozen_to_primitive,
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
    # Round 6 §1 + §4: the only internal-frozen array shape is
    # ``FrozenJsonArray``; ``tuple`` is no longer produced here.
    snap = strict_public_json_snapshot([1, "two", [None, True]])
    assert isinstance(snap, FrozenJsonArray)
    # ``FrozenJsonArray`` exposes its values via ``.values`` as a tuple.
    assert snap.values == (1, "two", FrozenJsonArray((None, True)))


def test_strict_snapshot_accepts_string_keyed_dict() -> None:
    # Round 7 (P1-1): ``strict_public_json_snapshot(dict)`` returns a
    # :class:`FrozenJsonObject` (not a raw ``MappingProxyType``).
    snap = strict_public_json_snapshot({"z": 1, "a": [1, 2]})
    assert isinstance(snap, FrozenJsonObject)
    assert tuple(snap.values.keys()) == ("a", "z")
    assert isinstance(snap.values["a"], FrozenJsonArray)


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
# internal_frozen_to_primitive — accepts only the strict snapshot shape
# --------------------------------------------------------------------------- #


def test_frozen_primitive_reduces_mapping_to_dict() -> None:
    snap = strict_public_json_snapshot({"a": 1, "b": [1, 2]})
    reduced = internal_frozen_to_primitive(snap)
    assert reduced == {"a": 1, "b": [1, 2]}
    assert isinstance(reduced, dict)
    assert isinstance(reduced["b"], list)


def test_frozen_primitive_rejects_arbitrary_object() -> None:
    with pytest.raises(NonCanonicalFragmentError):
        internal_frozen_to_primitive(object())


def test_frozen_primitive_rejects_decimal() -> None:
    with pytest.raises(NonCanonicalFragmentError):
        internal_frozen_to_primitive(Decimal("1.5"))


def test_frozen_primitive_rejects_bytes() -> None:
    with pytest.raises(NonCanonicalFragmentError):
        internal_frozen_to_primitive(b"raw")


def test_frozen_primitive_rejects_frozenset() -> None:
    with pytest.raises(NonCanonicalFragmentError):
        internal_frozen_to_primitive(frozenset({"a", "b"}))


def test_frozen_primitive_rejects_set() -> None:
    with pytest.raises(NonCanonicalFragmentError):
        internal_frozen_to_primitive({"a", "b"})


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


def test_freeze_deeply_makes_frozen_json_object_for_dict() -> None:
    # Round 7 (P1-1): ``freeze_deeply`` (``force_frozen_canonical``)
    # emits :class:`FrozenJsonObject` for ``dict`` inputs.
    frozen = freeze_deeply({"a": 1, "b": 2})
    assert isinstance(frozen, FrozenJsonObject)
    assert frozen.values["a"] == 1
    with pytest.raises(TypeError):
        frozen.values["a"] = 99  # type: ignore[index]


def test_freeze_deeply_converts_nested_lists_to_frozen_json_array() -> None:
    # Round 6 §1 + §4 + Round 7: nested lists become
    # :class:`FrozenJsonArray`; ``freeze_deeply`` produces a
    # :class:`FrozenJsonObject` for the outer dict.
    frozen = freeze_deeply({"nested": [1, 2, 3]})
    assert isinstance(frozen, FrozenJsonObject)
    assert isinstance(frozen.values["nested"], FrozenJsonArray)
    assert frozen.values["nested"].values == (1, 2, 3)


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


# --------------------------------------------------------------------------- #
# Round 8 §P0-1 / §P0-2 — detached immutable snapshot invariants
# ---------------------------------------------------------------------------


def test_round8_frozen_json_array_detached_from_input_list() -> None:
    """Calling-list mutation after construction MUST NOT affect the marker."""
    source = [1, 2]
    node = FrozenJsonArray(source)
    source.append(3)
    assert node.values == (1, 2)
    assert isinstance(node.values, tuple)


def test_round8_frozen_json_array_detached_for_nested_marker() -> None:
    """Nested-marker elements are accepted via reference; mutating the
    outer caller list MUST NOT change the marker."""
    nested = FrozenJsonObject({"a": 1})
    source = [nested]
    node = FrozenJsonArray(source)
    source.clear()
    assert len(node.values) == 1
    assert node.values[0] is nested


def test_round8_frozen_json_object_detached_from_input_dict() -> None:
    """Caller mutation of the input dict MUST NOT affect the marker."""
    source = {"a": 1, "b": 2}
    node = FrozenJsonObject(source)
    source["a"] = 999
    assert node.values["a"] == 1
    assert node.values["b"] == 2


def test_round8_frozen_json_object_detached_from_mapping_proxy_backing() -> None:
    """Round 8 §P0-2 — caller mutation through a MappingProxyType that
    shares its backing dict with a caller-owned dict MUST NOT affect the
    marker."""
    source: dict[str, Any] = {"a": 1, "b": 2}
    proxy: Any = MappingProxyType(source)
    node = FrozenJsonObject(proxy)
    source["a"] = 999
    assert node.values["a"] == 1
    assert node.values["b"] == 2


def test_round8_frozen_json_object_keys_sorted_after_detach() -> None:
    """Round 8 §P0-2 — keys are sorted at construction."""
    node = FrozenJsonObject({"z": 1, "a": 2, "m": 3})
    assert list(node.values.keys()) == ["a", "m", "z"]


def test_round8_factory_and_manual_marker_are_equivalent() -> None:
    """Round 8 §P0-3 — ``strict_public_json_snapshot({...})`` and a
    manually constructed ``FrozenJsonObject({...})`` MUST be
    equivalent in container marker type, primitive output, canonical
    hash, and immunity to caller mutation."""
    factory_node = strict_public_json_snapshot({"b": 2, "a": [1]})
    manual_node = FrozenJsonObject({"b": 2, "a": FrozenJsonArray([1])})
    assert isinstance(factory_node, FrozenJsonObject)
    assert isinstance(manual_node, FrozenJsonObject)
    assert internal_frozen_to_primitive(factory_node) == {
        "a": [1],
        "b": 2,
    }
    assert internal_frozen_to_primitive(manual_node) == {
        "a": [1],
        "b": 2,
    }
    assert internal_frozen_to_primitive(factory_node) == internal_frozen_to_primitive(manual_node)
    # Both must use sorted key order regardless of construction style.
    assert list(factory_node.values.keys()) == ["a", "b"]
    assert list(manual_node.values.keys()) == ["a", "b"]


def test_round8_factory_and_manual_markers_share_canonical_hash() -> None:
    """Round 8 §P0-3 — both styles produce the same canonical hash."""
    from hexagent.exchangers.shell_tube.tube_layout.canonical import _reduce_for_hash

    factory_node = strict_public_json_snapshot({"b": 2, "a": [1]})
    manual_node = FrozenJsonObject({"b": 2, "a": FrozenJsonArray([1])})
    assert _reduce_for_hash(factory_node) == _reduce_for_hash(manual_node)


def test_round8_factory_node_is_immune_to_caller_dict_mutation() -> None:
    """Round 8 §P0-3 — ``strict_public_json_snapshot`` must produce a
    detached marker that is immune to subsequent mutation of the
    caller's source dict.
    """
    source = {"a": 1}
    node = strict_public_json_snapshot(source)
    source["a"] = 2
    assert node.values["a"] == 1


# --------------------------------------------------------------------------- #
# Round 8 §P1-2 — hash reducer dataclass dead-path removed
# ---------------------------------------------------------------------------


def test_round8_reduce_for_hash_rejects_raw_dataclass() -> None:
    """Round 8 §P1-2 — the R7 ``dataclass`` branch is gone; raw
    dataclass instances MUST be rejected with ``CanonicalizationError``.
    """
    import dataclasses

    from hexagent.exchangers.shell_tube.tube_layout.canonical import _reduce_for_hash

    @dataclasses.dataclass(frozen=True)
    class Dummy:
        value: int

    with pytest.raises(CanonicalizationError):
        _reduce_for_hash(Dummy(1))


def test_round8_reduce_for_hash_accepts_force_frozen_canonical_dict() -> None:
    """Round 8 §P1-2 — freezing the dataclass explicitly via Layer A
    produces a hashable primitive."""
    import dataclasses

    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        _reduce_for_hash,
        force_frozen_canonical,
    )

    @dataclasses.dataclass(frozen=True)
    class Dummy:
        value: int

    frozen = force_frozen_canonical({"value": 1})
    assert _reduce_for_hash(frozen) == {"value": 1}


def test_round8_reduce_for_hash_rejects_raw_tuple() -> None:
    """Round 8 §P1-2 — raw tuple is still rejected (preserved from R7)."""
    from hexagent.exchangers.shell_tube.tube_layout.canonical import _reduce_for_hash

    with pytest.raises(CanonicalizationError):
        _reduce_for_hash(("a", "b"))


def test_round8_reduce_for_hash_rejects_raw_mapping_proxy_type() -> None:
    """Round 8 §P1-2 — raw MappingProxyType is rejected (must be wrapped
    in FrozenJsonObject first)."""
    from types import MappingProxyType

    from hexagent.exchangers.shell_tube.tube_layout.canonical import _reduce_for_hash

    with pytest.raises(CanonicalizationError):
        _reduce_for_hash(MappingProxyType({"a": 1}))


def test_round8_reduce_for_hash_rejects_non_string_key_dict() -> None:
    """Round 8 §P1-2 — non-string key dict is rejected; this is enforced
    via the FrozenJsonObject closed-input invariant at construction.
    """
    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        FrozenJsonObject,
    )

    with pytest.raises(PublicCanonicalDomainError):
        FrozenJsonObject({1: "a"})  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Round 8 §P1-1 — explicit Layer-C converter (freeze_known_*)
# ---------------------------------------------------------------------------


def test_round8_freeze_known_fragment_accepts_pre_frozen_object() -> None:
    """Round 8 §P1-1 — pre-frozen FrozenJsonObject passes through."""
    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        freeze_known_fragment,
    )

    pre_frozen = strict_public_json_snapshot({"a": [1]})
    out = freeze_known_fragment(pre_frozen)
    assert out is pre_frozen


def test_round8_freeze_known_fragment_freezes_raw_dict() -> None:
    """Round 8 §P1-1 — raw dict is deeply frozen to FrozenJsonObject."""
    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        freeze_known_fragment,
    )

    out = freeze_known_fragment({"a": [1]})
    assert isinstance(out, FrozenJsonObject)
    assert internal_frozen_to_primitive(out) == {"a": [1]}


def test_round8_freeze_known_optional_handles_none() -> None:
    """Round 8 §P1-1 — None passes through."""
    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        freeze_known_optional_fragment,
    )

    assert freeze_known_optional_fragment(None) is None


def test_round8_freeze_known_optional_handles_pre_frozen() -> None:
    """Round 8 §P1-1 — pre-frozen marker passes through unchanged."""
    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        freeze_known_optional_fragment,
    )

    pre_frozen = strict_public_json_snapshot({"a": 1})
    out = freeze_known_optional_fragment(pre_frozen)
    assert out is pre_frozen


def test_round8_freeze_known_optional_rejects_raw_tuple() -> None:
    """Round 8 §P1-1 — raw tuple is rejected."""
    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        freeze_known_optional_fragment,
    )

    with pytest.raises(PublicCanonicalDomainError):
        freeze_known_optional_fragment(("a", "b"))


def test_round8_freeze_known_optional_rejects_decimal() -> None:
    """Round 8 §P1-1 — Decimal is rejected."""
    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        freeze_known_optional_fragment,
    )

    with pytest.raises(PublicCanonicalDomainError):
        freeze_known_optional_fragment(Decimal("1.5"))


# --------------------------------------------------------------------------- #
# Round 8 §P0-1 / §P0-2 — direct mutation must fail
# ---------------------------------------------------------------------------


def test_round8_frozen_json_array_setattr_is_blocked() -> None:
    """dataclass(frozen=True) prevents ``node.values = (...)``."""
    node = FrozenJsonArray([1, 2])
    with pytest.raises(dataclasses.FrozenInstanceError):
        node.values = (3, 4)  # type: ignore[misc]


def test_round8_frozen_json_object_setattr_is_blocked() -> None:
    """dataclass(frozen=True) prevents ``node.values = {...}``."""
    node = FrozenJsonObject({"a": 1})
    with pytest.raises(dataclasses.FrozenInstanceError):
        node.values = type(node.values)({"a": 2})  # type: ignore[misc]
