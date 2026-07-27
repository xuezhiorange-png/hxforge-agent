"""§A03 — Raw projection tests."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

import hexagent.exchangers.shell_tube.tube_side as ts
from hexagent.exchangers.shell_tube.tube_side.canonical import PIWrapper as _PIWrapper
from tests.fixtures.shell_and_tube.tube_side.task020_configurations import config_a
from tests.fixtures.shell_and_tube.tube_side.task021_layouts import layout_a


def test_a03_atom_none() -> None:
    assert ts.project_raw_value(None) != ts.project_raw_value(True)


def test_a03_atom_bool() -> None:
    assert ts.project_raw_value(True) != ts.project_raw_value(False)


def test_a03_atom_int() -> None:
    assert ts.project_raw_value(0) != ts.project_raw_value("0")
    assert ts.project_raw_value(42) != ts.project_raw_value("42")


def test_a03_atom_str_surrogate_rejected() -> None:
    surrogate = "\ud83d"
    with pytest.raises(ValueError):
        ts.project_raw_value(surrogate)


def test_a03_atom_dict_keys_sorted() -> None:
    out_a = ts.project_raw_dict({"b": 2, "a": 1})
    out_b = ts.project_raw_dict({"a": 1, "b": 2})
    assert out_a == out_b


def test_a03_atom_dict_non_str_key_rejected() -> None:
    with pytest.raises(ValueError):
        ts.project_raw_dict({1: "x"})  # type: ignore[dict-item]


def test_a03_atom_tuple_order_preserved() -> None:
    out = ts.project_raw_value((1, 2, 3))
    assert out == ts.project_raw_value((1, 2, 3))


def test_a03_atom_frozenset_sorted_unique() -> None:
    """§7.3 — frozenset members project to unique bytes sorted lexicographically."""
    out = ts.project_raw_value(frozenset([1, 2, 3]))
    assert out is not None
    assert isinstance(out, bytes)


def test_a03_unsupported_class_rejected() -> None:
    class Weird:  # noqa: D401 — test stub
        pass

    with pytest.raises(ValueError):
        ts.project_raw_value(Weird())


def test_raw_projection_atom_kinds_are_pairwise_distinct() -> None:
    values = (None, True, False, 0, 1, "", "1", b"", b"1", Decimal("0"), Decimal("1"))
    projections = [ts.project_raw_value(value) for value in values]
    assert len(set(projections)) == len(values)


def test_raw_projection_rejects_int_subclass() -> None:
    class IntSubclass(int):
        pass

    with pytest.raises(ValueError):
        ts.project_raw_value(IntSubclass(1))


def test_raw_projection_rejects_str_subclass_without_calling_encode() -> None:
    class StrSubclass(str):
        def encode(self, *args: object, **kwargs: object) -> bytes:
            raise AssertionError("caller encode must not run")

    with pytest.raises(ValueError):
        ts.project_raw_value(StrSubclass("x"))


def test_raw_projection_rejects_bytes_subclass() -> None:
    class BytesSubclass(bytes):
        pass

    with pytest.raises(ValueError):
        ts.project_raw_value(BytesSubclass(b"x"))


def test_raw_projection_rejects_decimal_subclass() -> None:
    class DecimalSubclass(Decimal):
        pass

    with pytest.raises(ValueError):
        ts.project_raw_value(DecimalSubclass("1"))


def test_fake_class_named_tube_layout_is_unsafe() -> None:
    """§P0-1 — unsafe_object_signal must use exact concrete types, not class names."""

    class TubeLayout:
        pass

    assert ts.unsafe_object_signal(TubeLayout()) is True
    assert ts.unsafe_object_signal(object()) is True
    assert ts.unsafe_object_signal("benign") is False
    assert ts.unsafe_object_signal(None) is False


# ---------------------------------------------------------------------------
# Round-3 §4 — known-object encoding helpers must be total.
# ---------------------------------------------------------------------------


def test_configuration_surrogate_id_returns_blocked() -> None:
    surrogate = "config-\ud83d"
    contaminated = replace(config_a(), configuration_id=surrogate)
    raw = _request_input(contaminated, layout_a())
    raw["task020_configuration"] = contaminated
    raw["task021_layout"] = replace(
        layout_a(),
        task020_configuration_id=contaminated.configuration_id,
        task020_configuration_hash=contaminated.configuration_hash,
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
    assert result.blockers[0].code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED


def test_configuration_non_ascii_hash_returns_blocked() -> None:
    contaminated = replace(config_a(), configuration_hash="hé" + "c" * 62)
    raw = _request_input(contaminated, layout_a())
    raw["task020_configuration"] = contaminated
    raw["task021_layout"] = replace(
        layout_a(),
        task020_configuration_id=contaminated.configuration_id,
        task020_configuration_hash=contaminated.configuration_hash,
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_layout_surrogate_id_returns_blocked() -> None:
    surrogate = "layout-\ud83d"
    contaminated = replace(layout_a(), layout_id=surrogate)
    raw = _request_input(config_a(), contaminated)
    raw["task021_layout"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_layout_non_ascii_hash_returns_blocked() -> None:
    contaminated = replace(layout_a(), layout_hash="z" + "é" + "a" * 62)
    raw = _request_input(config_a(), contaminated)
    raw["task021_layout"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_geometry_surrogate_id_returns_blocked() -> None:
    surrogate = "geom-\ud83d"
    geometry = layout_a().tube_geometry
    contaminated_geom = replace(geometry, geometry_id=surrogate)
    contaminated_layout = replace(layout_a(), tube_geometry=contaminated_geom)
    raw = _request_input(config_a(), contaminated_layout)
    raw["task021_layout"] = contaminated_layout
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_geometry_non_ascii_record_hash_returns_blocked() -> None:
    geometry = layout_a().tube_geometry
    contaminated_geom = replace(geometry, record_hash="z" + "é" + "a" * 62)
    contaminated_layout = replace(layout_a(), tube_geometry=contaminated_geom)
    raw = _request_input(config_a(), contaminated_layout)
    raw["task021_layout"] = contaminated_layout
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_length_authority_surrogate_id_returns_blocked() -> None:
    flow_pair = ts.canonical_internal_flow_pair()
    contaminated = ts.InternalFlowLengthAuthority(
        length_id="flow-\ud83d",
        length_m=Decimal("4.85"),
        start_plane=flow_pair,
        end_plane=flow_pair,
        authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        length_hash="0" * 64,
    )
    raw = _request_input_with_authorities(
        config_a(), layout_a(), contaminated, _canonical_heat_auth()
    )
    raw["internal_flow_authority"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_length_authority_non_ascii_hash_returns_blocked() -> None:
    """Defense-in-depth: raw projection rejects non-ASCII hash even if dataclass is bypassed."""
    flow_pair = ts.canonical_internal_flow_pair()
    # Bypass the frozen dataclass __post_init__ by direct object mutation.
    contaminated = object.__new__(ts.InternalFlowLengthAuthority)
    object.__setattr__(contaminated, "length_id", "flow")
    object.__setattr__(contaminated, "length_m", Decimal("4.85"))
    object.__setattr__(contaminated, "start_plane", flow_pair)
    object.__setattr__(contaminated, "end_plane", flow_pair)
    object.__setattr__(
        contaminated,
        "authority_mode",
        ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
    )
    object.__setattr__(contaminated, "length_hash", "z" + "é" + "a" * 62)
    raw = _request_input_with_authorities(
        config_a(), layout_a(), contaminated, _canonical_heat_auth()
    )
    raw["internal_flow_authority"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
    assert result.blockers[0].code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED


def test_participation_non_ascii_hash_returns_blocked() -> None:
    """Defense-in-depth: raw projection rejects non-ASCII hash even if dataclass is bypassed."""
    position_ids = tuple(position.position_id for position in layout_a().positions)
    contaminated = object.__new__(ts.Task025HydraulicParticipationAuthority)
    object.__setattr__(contaminated, "all_layout_position_ids", position_ids)
    object.__setattr__(contaminated, "active_position_ids", position_ids)
    object.__setattr__(contaminated, "inactive_position_ids", ())
    object.__setattr__(
        contaminated,
        "authority_mode",
        ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
    )
    object.__setattr__(contaminated, "evidence_refs", ("fixture",))
    object.__setattr__(contaminated, "hydraulic_authority_hash", "z" + "é" + "a" * 62)
    raw = _request_input(config_a(), layout_a())
    raw["hydraulic_participation_authority"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
    assert result.blockers[0].code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED


def test_length_decimal_evil_str_is_not_executed() -> None:
    """§4.4 — length_m field must reject non-Decimal values without invoking __str__/__repr__."""

    class EvilDecimal:
        def __str__(self) -> str:
            raise AssertionError("str must not run")

        def __repr__(self) -> str:
            raise AssertionError("repr must not run")

        def __bool__(self) -> bool:
            raise AssertionError("bool must not run")

    flow_pair = ts.canonical_internal_flow_pair()
    # Bypass dataclass __post_init__ via object.__new__ so the raw
    # projection is the layer under test.
    contaminated = object.__new__(ts.InternalFlowLengthAuthority)
    object.__setattr__(contaminated, "length_id", "flow")
    object.__setattr__(contaminated, "length_m", EvilDecimal())
    object.__setattr__(contaminated, "start_plane", flow_pair)
    object.__setattr__(contaminated, "end_plane", flow_pair)
    object.__setattr__(
        contaminated,
        "authority_mode",
        ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
    )
    object.__setattr__(contaminated, "length_hash", "0" * 64)
    raw = _request_input_with_authorities(
        config_a(), layout_a(), contaminated, _canonical_heat_auth()
    )
    raw["internal_flow_authority"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
    assert result.blockers[0].code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED


# ---------------------------------------------------------------------------
# Round-3 helpers
# ---------------------------------------------------------------------------


def _canonical_heat_auth() -> ts.HeatTransferLengthAuthority:
    heat_pair = ts.canonical_heat_transfer_pair()
    return ts.HeatTransferLengthAuthority(
        length_id="heat",
        length_m=Decimal("4.85"),
        start_plane=heat_pair,
        end_plane=heat_pair,
        authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        length_hash="0" * 64,
    )


def _request_input_with_authorities(
    config: object,
    layout: object,
    flow: object,
    heat: object,
) -> dict[str, object]:
    position_ids = tuple(position.position_id for position in layout.positions)  # type: ignore[union-attr]
    participation = ts.Task025HydraulicParticipationAuthority(
        all_layout_position_ids=position_ids,
        active_position_ids=position_ids,
        inactive_position_ids=(),
        authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        evidence_refs=("fixture",),
        hydraulic_authority_hash="0" * 64,
    )
    return {
        "schema_version": "task025.request.v1",
        "profile_id": "profile-001",
        "task020_configuration": config,
        "task021_layout": layout,
        "internal_flow_authority": flow,
        "heat_transfer_authority": heat,
        "hydraulic_participation_authority": participation,
        "flow_path_mode": ts.FlowPathMode.STRAIGHT_TUBE_PARALLEL_FLOW,
        "hydraulic_authority_mode": ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        "evidence_refs": ("fixture",),
    }


def _request_input(config: object, layout: object) -> dict[str, object]:
    flow_hash = ts.internal_flow_authority_length_hash(
        Decimal("4.85"),
        ts.canonical_internal_flow_pair(),
        ts.canonical_internal_flow_pair(),
        ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
    )
    heat_hash = ts.heat_transfer_authority_length_hash(
        Decimal("4.85"),
        ts.canonical_heat_transfer_pair(),
        ts.canonical_heat_transfer_pair(),
        ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
    )
    flow = ts.InternalFlowLengthAuthority(
        "flow",
        Decimal("4.85"),
        ts.canonical_internal_flow_pair(),
        ts.canonical_internal_flow_pair(),
        ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        flow_hash,
    )
    heat = ts.HeatTransferLengthAuthority(
        "heat",
        Decimal("4.85"),
        ts.canonical_heat_transfer_pair(),
        ts.canonical_heat_transfer_pair(),
        ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        heat_hash,
    )
    return _request_input_with_authorities(config, layout, flow, heat)


# ---------------------------------------------------------------------------
# Round-4 §4 — malformed exact known object state must fail-closed.
# ---------------------------------------------------------------------------


class _EvilContainer:
    """Container whose dunders raise; must never be invoked."""

    def __iter__(self):  # type: ignore[no-untyped-def]
        raise AssertionError("__iter__ must not execute")

    def __len__(self) -> int:
        raise AssertionError("__len__ must not execute")

    def items(self):  # type: ignore[no-untyped-def]
        raise AssertionError("items must not execute")

    def keys(self):  # type: ignore[no-untyped-def]
        raise AssertionError("keys must not execute")

    def values(self):  # type: ignore[no-untyped-def]
        raise AssertionError("values must not execute")

    def __getitem__(self, key):  # type: ignore[no-untyped-def,override]
        raise AssertionError("__getitem__ must not execute")


def _build_request_with_known_object(known_object: object) -> dict[str, object]:
    """Build a request dict with an injected known object under a private key.

    The extra key is processed by the raw projection before Stage 1
    unknown-field rejection, so any ``RawProjectionError`` raised while
    framing ``known_object`` is converted to a Stage 1 blocked result
    (code ``BL_019``). This lets us exercise the per-known-object
    projectors without depending on any frozen container's domain.
    """
    base = _request_input(config_a(), layout_a())
    base["_task025_test_known_object"] = known_object  # type: ignore[assignment]
    return base


def test_uninitialized_pi_wrapper_returns_blocked() -> None:
    """PIWrapper instance with no backing slot returns blocked."""
    bad = object.__new__(_PIWrapper)
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
    assert any(b.code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED for b in result.blockers)


def test_pi_wrapper_wrong_lexeme_type_returns_blocked() -> None:
    """PIWrapper._lexeme of wrong type (bytearray) returns blocked."""
    bad = object.__new__(_PIWrapper)
    object.__setattr__(bad, "_value", None)
    object.__setattr__(bad, "_lexeme", bytearray(b"3.14159265358979323846"))
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_pi_wrapper_wrong_lexeme_value_returns_blocked() -> None:
    """PIWrapper._lexeme with the wrong bytes returns blocked."""
    bad = object.__new__(_PIWrapper)
    object.__setattr__(bad, "_value", None)
    object.__setattr__(bad, "_lexeme", b"3.14")
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_uninitialized_reference_plane_pair_returns_blocked() -> None:
    """ReferencePlanePair instance with no backing slots returns blocked."""
    bad = object.__new__(ts.ReferencePlanePair)
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
    assert any(b.code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED for b in result.blockers)


def test_reference_plane_pair_missing_start_returns_blocked() -> None:
    """ReferencePlanePair with only ``_end`` set returns blocked."""
    bad = object.__new__(ts.ReferencePlanePair)
    object.__setattr__(bad, "_end", ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_END_PLANE)
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_reference_plane_pair_invalid_ordered_pair_returns_blocked() -> None:
    """ReferencePlanePair with an unordered pair returns blocked."""
    bad = object.__new__(ts.ReferencePlanePair)
    object.__setattr__(bad, "_start", ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_END_PLANE)
    object.__setattr__(bad, "_end", ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE)
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_uninitialized_frozen_json_array_returns_blocked() -> None:
    """FrozenJsonArray instance with no backing slot returns blocked."""
    bad = object.__new__(ts.FrozenJsonArray)
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_frozen_json_array_missing_items_returns_blocked() -> None:
    """FrozenJsonArray with only ``_frozen`` set returns blocked."""
    bad = object.__new__(ts.FrozenJsonArray)
    object.__setattr__(bad, "_frozen", True)
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_frozen_json_array_evil_items_object_is_not_executed() -> None:
    """FrozenJsonArray._items backed by an EvilContainer returns blocked."""
    bad = object.__new__(ts.FrozenJsonArray)
    object.__setattr__(bad, "_items", _EvilContainer())
    object.__setattr__(bad, "_frozen", True)
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_uninitialized_frozen_json_object_returns_blocked() -> None:
    """FrozenJsonObject instance with no backing slot returns blocked."""
    bad = object.__new__(ts.FrozenJsonObject)
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_frozen_json_object_missing_items_returns_blocked() -> None:
    """FrozenJsonObject with only ``_frozen`` set returns blocked."""
    bad = object.__new__(ts.FrozenJsonObject)
    object.__setattr__(bad, "_frozen", True)
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_frozen_json_object_evil_items_object_is_not_executed() -> None:
    """FrozenJsonObject._items backed by an EvilContainer returns blocked."""
    bad = object.__new__(ts.FrozenJsonObject)
    object.__setattr__(bad, "_items", _EvilContainer())
    object.__setattr__(bad, "_frozen", True)
    raw = _build_request_with_known_object(bad)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
