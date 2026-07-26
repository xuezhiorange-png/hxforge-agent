"""§A09 — Scheduler tests."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import hexagent.exchangers.shell_tube.tube_side as ts
from hexagent.exchangers.shell_tube.models import Orientation
from tests.fixtures.shell_and_tube.tube_side.task020_configurations import config_a
from tests.fixtures.shell_and_tube.tube_side.task021_layouts import layout_a, layout_b


def test_a09_stage_ranks_constant() -> None:
    assert ts.STAGE_RANKS == 9


def test_a09_top_level_non_dict_returns_blocked() -> None:
    """§4.2 — non-dict branch returns Task025BlockedResult with stage_rank=1."""
    result = ts.evaluate_task025("not-a-dict")
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
    assert (
        result.blockers and result.blockers[0].code is ts.BlockerCode.BL_003_BLOCKED_INPUT_REJECTED
    )


def test_a09_top_level_none_returns_blocked() -> None:
    result = ts.evaluate_task025(None)
    assert isinstance(result, ts.Task025BlockedResult)


def test_a09_top_level_int_returns_blocked() -> None:
    result = ts.evaluate_task025(42)
    assert isinstance(result, ts.Task025BlockedResult)


def test_a09_blocked_result_has_stable_hash() -> None:
    """§6.4 — blocked_result_hash is 64-hex."""
    result1 = ts.evaluate_task025(None)
    result2 = ts.evaluate_task025("xyz")
    # Both are blocked results.
    assert isinstance(result1, ts.Task025BlockedResult)
    assert isinstance(result2, ts.Task025BlockedResult)
    # Both hashes are 64-lowercase-hex.
    assert len(result1.blocked_result_hash) == 64
    assert len(result2.blocked_result_hash) == 64
    assert all(c in "0123456789abcdef" for c in result1.blocked_result_hash)
    assert all(c in "0123456789abcdef" for c in result2.blocked_result_hash)


def _request_input(config: object, layout: object) -> dict[str, object]:
    position_ids = tuple(position.position_id for position in layout.positions)  # type: ignore[union-attr]
    participation = ts.Task025HydraulicParticipationAuthority(
        all_layout_position_ids=position_ids,
        active_position_ids=position_ids,
        inactive_position_ids=(),
        authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        evidence_refs=("fixture",),
        hydraulic_authority_hash="0" * 64,
    )
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


def test_mixed_task020_task021_fixture_is_blocked() -> None:
    result = ts.evaluate_task025(_request_input(config_a(), layout_b()))
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    assert ts.BlockerCode.BL_024_TASK020_IDENTITY_MISMATCH in {b.code for b in result.blockers}


def test_task020_configuration_id_mismatch_is_blocked() -> None:
    result = ts.evaluate_task025(
        _request_input(config_a(), replace(layout_a(), task020_configuration_id="wrong"))
    )
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    assert ts.BlockerCode.BL_024_TASK020_IDENTITY_MISMATCH in {b.code for b in result.blockers}


def test_task020_configuration_hash_mismatch_is_blocked() -> None:
    result = ts.evaluate_task025(
        _request_input(config_a(), replace(layout_a(), task020_configuration_hash="f" * 64))
    )
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    assert ts.BlockerCode.BL_025_TASK021_IDENTITY_MISMATCH in {b.code for b in result.blockers}


def test_upstream_orientation_mismatch_is_blocked() -> None:
    config = config_a()
    layout = replace(layout_a(), equipment_orientation=Orientation.VERTICAL)
    result = ts.evaluate_task025(_request_input(config, layout))
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2


def test_every_missing_required_field_returns_stage1_blocked() -> None:
    base = _request_input(config_a(), layout_a())
    for field in ts.TASK025_REQUEST_FIELDS:
        candidate = dict(base)
        candidate.pop(field)
        result = ts.evaluate_task025(candidate)
        assert isinstance(result, ts.Task025BlockedResult)
        assert result.stage_rank == 1
        assert any(f"missing_field:{field}" in entry.evidence_refs for entry in result.blockers)


def test_unknown_and_missing_fields_are_deterministic() -> None:
    base = _request_input(config_a(), layout_a())
    first = dict(base)
    first.pop("evidence_refs")
    first["unknown"] = None
    second = {
        "unknown": None,
        **{key: value for key, value in base.items() if key != "evidence_refs"},
    }
    first_result = ts.evaluate_task025(first)
    second_result = ts.evaluate_task025(second)
    assert isinstance(first_result, ts.Task025BlockedResult)
    assert isinstance(second_result, ts.Task025BlockedResult)
    assert first_result.blocked_result_hash == second_result.blocked_result_hash


def test_raw_projection_cycle_returns_blocked() -> None:
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    result = ts.evaluate_task025(cyclic)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
    assert result.blockers[0].code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED


def test_raw_projection_indirect_cycle_returns_blocked() -> None:
    cyclic: dict[str, object] = {}
    cyclic["link"] = (cyclic,)
    result = ts.evaluate_task025(cyclic)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_raw_projection_depth_limit_returns_blocked() -> None:
    value: object = None
    for _ in range(65):
        value = (value,)
    result = ts.evaluate_task025(value)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_public_entry_never_leaks_raw_input_exception() -> None:
    class Evil:
        def __repr__(self) -> str:
            raise AssertionError("repr must not run")

    result = ts.evaluate_task025({"evil": Evil()})
    assert isinstance(result, ts.Task025BlockedResult)


def test_invalid_evidence_ref_type_returns_blocked() -> None:
    raw = _request_input(config_a(), layout_a())
    raw["evidence_refs"] = (1,)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_003_BLOCKED_INPUT_REJECTED in codes


def test_empty_evidence_ref_returns_blocked() -> None:
    raw = _request_input(config_a(), layout_a())
    raw["evidence_refs"] = ("",)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_003_BLOCKED_INPUT_REJECTED in codes


def test_request_construction_failure_does_not_escape() -> None:
    class StrSubclass(str):
        pass

    raw = _request_input(config_a(), layout_a())
    raw["evidence_refs"] = (StrSubclass("x"),)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    # Must not be a Python builtin error.
    assert result.stage_rank == 1


def test_task020_configuration_with_blockers_is_stage2_blocked() -> None:
    from hexagent.exchangers.shell_tube.models import ErrorEntry

    config = config_a()
    contaminated = replace(
        config, blockers=(ErrorEntry(code="X", field_path=None, message_key="k"),)
    )
    raw = _request_input(contaminated, layout_a())
    # Ensure layout still cross-binds to contaminated config id+hash.
    contaminated_layout = replace(
        layout_a(),
        task020_configuration_id=contaminated.configuration_id,
        task020_configuration_hash=contaminated.configuration_hash,
    )
    raw["task020_configuration"] = contaminated
    raw["task021_layout"] = contaminated_layout
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION in codes


def test_layout_with_non_tube_position_returns_blocked() -> None:
    class NotTubePosition:
        def __init__(self) -> None:
            self.position_id = "p0"

    raw = _request_input(config_a(), layout_a())
    contaminated = replace(layout_a(), positions=(NotTubePosition(),))
    raw["task021_layout"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_layout_position_property_is_not_executed() -> None:
    class ExplodingPosition:
        @property
        def position_id(self) -> str:
            raise AssertionError("property must not execute")

    raw = _request_input(config_a(), layout_a())
    contaminated = replace(layout_a(), positions=(ExplodingPosition(),))
    raw["task021_layout"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)


def test_layout_with_invalid_geometry_returns_blocked() -> None:
    class NotGeometry:
        def __init__(self) -> None:
            self.geometry_id = "g"
            self.record_hash = "r" * 64
            self.snapshot_hash = "s" * 64

    raw = _request_input(config_a(), layout_a())
    contaminated = replace(layout_a(), tube_geometry=NotGeometry())
    raw["task021_layout"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_layout_geometry_property_is_not_executed() -> None:
    class ExplodingGeometry:
        @property
        def geometry_id(self) -> str:
            raise AssertionError("geometry_id property must not execute")

        @property
        def record_hash(self) -> str:
            raise AssertionError("record_hash property must not execute")

        @property
        def snapshot_hash(self) -> str:
            raise AssertionError("snapshot_hash property must not execute")

    raw = _request_input(config_a(), layout_a())
    contaminated = replace(layout_a(), tube_geometry=ExplodingGeometry())
    raw["task021_layout"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)


# ruff: noqa: E501
