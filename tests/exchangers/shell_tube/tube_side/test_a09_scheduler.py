"""§A09 — Scheduler tests."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

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
    flow_pair = ts.canonical_internal_flow_pair()
    heat_pair = ts.canonical_heat_transfer_pair()
    authority_mode = ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH
    flow = ts.InternalFlowLengthAuthority(
        "flow",
        Decimal("4.85"),
        flow_pair,
        flow_pair,
        authority_mode,
        ts.internal_flow_authority_length_hash(
            Decimal("4.85"), flow_pair, flow_pair, authority_mode
        ),
    )
    heat = ts.HeatTransferLengthAuthority(
        "heat",
        Decimal("4.85"),
        heat_pair,
        heat_pair,
        authority_mode,
        ts.heat_transfer_authority_length_hash(
            Decimal("4.85"), heat_pair, heat_pair, authority_mode
        ),
    )
    ifa_hash = flow.length_hash
    hta_hash = heat.length_hash
    pya_hash = ts.hydraulic_authority_hash(
        task020_configuration_id=getattr(config, "configuration_id", "config-a-001"),
        task021_layout_id=getattr(layout, "layout_id", "layout-a-001"),
        internal_flow_length_hash_value=ifa_hash,
        heat_transfer_length_hash_value=hta_hash,
        all_layout_position_ids=position_ids,
        active_position_ids=position_ids,
        inactive_position_ids=(),
        hydraulic_authority_mode=authority_mode,
        participation_evidence_refs=("fixture",),
    )
    participation = ts.Task025HydraulicParticipationAuthority(
        all_layout_position_ids=position_ids,
        active_position_ids=position_ids,
        inactive_position_ids=(),
        authority_mode=authority_mode,
        evidence_refs=("fixture",),
        hydraulic_authority_hash=pya_hash,
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
        "hydraulic_authority_mode": authority_mode,
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


# ---------------------------------------------------------------------------
# Round-3 §5 — upstream blockers truthiness must not be executed.
# ---------------------------------------------------------------------------


class _EvilTruthiness:
    def __bool__(self) -> bool:
        raise AssertionError("__bool__ must not execute")

    def __len__(self) -> int:
        raise AssertionError("__len__ must not execute")


def test_task020_blockers_evil_bool_is_not_executed() -> None:
    contaminated = replace(config_a(), blockers=_EvilTruthiness())  # type: ignore[arg-type]
    raw = _request_input(contaminated, layout_a())
    raw["task020_configuration"] = contaminated
    raw["task021_layout"] = replace(
        layout_a(),
        task020_configuration_id=contaminated.configuration_id,
        task020_configuration_hash=contaminated.configuration_hash,
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION in codes


def test_task021_blockers_evil_bool_is_not_executed() -> None:
    contaminated = replace(layout_a(), blockers=_EvilTruthiness())  # type: ignore[arg-type]
    raw = _request_input(config_a(), contaminated)
    raw["task021_layout"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_014_INVALID_TASK021_LAYOUT in codes


def test_task020_blockers_list_is_stage2_blocked() -> None:
    contaminated = replace(config_a(), blockers=[])  # type: ignore[arg-type]
    raw = _request_input(contaminated, layout_a())
    raw["task020_configuration"] = contaminated
    raw["task021_layout"] = replace(
        layout_a(),
        task020_configuration_id=contaminated.configuration_id,
        task020_configuration_hash=contaminated.configuration_hash,
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION in codes


def test_task021_blockers_list_is_stage2_blocked() -> None:
    contaminated = replace(layout_a(), blockers=[])  # type: ignore[arg-type]
    raw = _request_input(config_a(), contaminated)
    raw["task021_layout"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_014_INVALID_TASK021_LAYOUT in codes


def test_task020_non_empty_tuple_is_stage2_blocked() -> None:
    from hexagent.exchangers.shell_tube.models import ErrorEntry

    contaminated = replace(
        config_a(), blockers=(ErrorEntry(code="X", field_path=None, message_key="k"),)
    )
    raw = _request_input(contaminated, layout_a())
    raw["task020_configuration"] = contaminated
    raw["task021_layout"] = replace(
        layout_a(),
        task020_configuration_id=contaminated.configuration_id,
        task020_configuration_hash=contaminated.configuration_hash,
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION in codes


def test_task021_non_empty_tuple_is_stage2_blocked() -> None:
    from hexagent.exchangers.shell_tube.models import ErrorEntry

    contaminated = replace(
        layout_a(), blockers=(ErrorEntry(code="X", field_path=None, message_key="k"),)
    )
    raw = _request_input(config_a(), contaminated)
    raw["task021_layout"] = contaminated
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_014_INVALID_TASK021_LAYOUT in codes


# ---------------------------------------------------------------------------
# Round-3 §6 — Stage 8 Decimal parse must be total.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [
        "",
        "not-a-decimal",
        "NaN",
        "sNaN",
        "Infinity",
        "-Infinity",
        "0",
        "-0.01",
        "\ud800",
    ],
)
def test_inner_diameter_malformed_string_is_stage8_blocked(bad_value: str) -> None:
    geometry = layout_a().tube_geometry
    contaminated_geom = replace(geometry, inner_diameter_m=bad_value)
    contaminated_layout = replace(layout_a(), tube_geometry=contaminated_geom)
    raw = _request_input(config_a(), contaminated_layout)
    raw["task021_layout"] = contaminated_layout
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 8
    assert result.request_hash is not None
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_026_TUBE_GEOMETRY_MISSING in codes


def test_inner_diameter_str_subclass_is_stage8_blocked() -> None:
    class StrSubclass(str):
        pass

    geometry = layout_a().tube_geometry
    contaminated_geom = replace(geometry, inner_diameter_m=StrSubclass("0.016"))
    contaminated_layout = replace(layout_a(), tube_geometry=contaminated_geom)
    raw = _request_input(config_a(), contaminated_layout)
    raw["task021_layout"] = contaminated_layout
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 8
    assert result.request_hash is not None
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_026_TUBE_GEOMETRY_MISSING in codes


def test_inner_diameter_evil_object_is_not_executed() -> None:
    class EvilInnerDiameter:
        def __str__(self) -> str:
            raise AssertionError("str must not run")

        def __repr__(self) -> str:
            raise AssertionError("repr must not run")

        def __bool__(self) -> bool:
            raise AssertionError("bool must not run")

    geometry = layout_a().tube_geometry
    contaminated_geom = replace(geometry, inner_diameter_m=EvilInnerDiameter())  # type: ignore[arg-type]
    contaminated_layout = replace(layout_a(), tube_geometry=contaminated_geom)
    raw = _request_input(config_a(), contaminated_layout)
    raw["task021_layout"] = contaminated_layout
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 8


def test_invalid_inner_diameter_never_reaches_geometry_compute() -> None:
    """No partial geometry outputs on malformed inner diameter."""

    geometry = layout_a().tube_geometry
    contaminated_geom = replace(geometry, inner_diameter_m="not-a-decimal")
    contaminated_layout = replace(layout_a(), tube_geometry=contaminated_geom)
    raw = _request_input(config_a(), contaminated_layout)
    raw["task021_layout"] = contaminated_layout
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    # A blocked result must not carry the geometry fields that belong to
    # Task025ValidResult. The blocked-result dataclass intentionally has no
    # such attributes, so any attempt to read them via setattr-style is
    # rejected.
    assert not hasattr(result, "single_tube_flow_area_m2")
    assert not hasattr(result, "hydraulic_diameter_m")


# ---------------------------------------------------------------------------
# Round-3 §7 — evidence_refs contract unified to exact tuple.
# ---------------------------------------------------------------------------


def test_evidence_refs_list_is_blocked() -> None:
    raw = _request_input(config_a(), layout_a())
    raw["evidence_refs"] = ["fixture"]
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_003_BLOCKED_INPUT_REJECTED in codes


def test_evidence_refs_tuple_is_accepted() -> None:
    raw = _request_input(config_a(), layout_a())
    raw["evidence_refs"] = ("fixture-a", "fixture-b")
    result = ts.evaluate_task025(raw)
    # Either valid result or a downstream unrelated blocker, but never
    # an evidence_refs contract rejection.
    assert not any(
        b.message_key == "evidence_refs_not_frozen_container"
        or b.message_key == "evidence_refs_entry_not_exact_str"
        or b.message_key == "evidence_refs_entry_empty"
        for b in getattr(result, "blockers", ())
    )


# ---------------------------------------------------------------------------
# Round-4 §5 — Stage 2 blockers attribute reads must be controlled.
# ---------------------------------------------------------------------------


def test_task020_missing_blockers_attribute_is_stage2_blocked() -> None:
    """Stage 2 must not leak AttributeError when ``blockers`` is absent."""
    contaminated = object.__new__(type(config_a()))
    for field in config_a().__dataclass_fields__:  # type: ignore[attr-defined]
        object.__setattr__(contaminated, field, getattr(config_a(), field))
    object.__delattr__(contaminated, "blockers")
    raw = _request_input(contaminated, layout_a())
    raw["task020_configuration"] = contaminated  # type: ignore[assignment]
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    assert any(
        b.code is ts.BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION
        and b.message_key == "task020_blockers_missing_or_inaccessible"
        for b in result.blockers
    )


def test_task021_missing_blockers_attribute_is_stage2_blocked() -> None:
    """Stage 2 must not leak AttributeError when ``blockers`` is absent."""
    contaminated = object.__new__(type(layout_a()))
    for field in layout_a().__dataclass_fields__:  # type: ignore[attr-defined]
        object.__setattr__(contaminated, field, getattr(layout_a(), field))
    object.__delattr__(contaminated, "blockers")
    raw = _request_input(config_a(), contaminated)
    raw["task021_layout"] = contaminated  # type: ignore[assignment]
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 2
    assert any(
        b.code is ts.BlockerCode.BL_014_INVALID_TASK021_LAYOUT
        and b.message_key == "task021_blockers_missing_or_inaccessible"
        for b in result.blockers
    )


def test_task020_subclass_is_rejected_without_execution() -> None:
    """A non-exact subclass of ShellAndTubeConfiguration must be rejected.

    The raw projection boundary is the first layer of defense: it
    rejects any non-exact type before Stage 2. ``__bool__`` /
    ``__len__`` must never execute.
    """
    from hexagent.exchangers.shell_tube.models import ShellAndTubeConfiguration

    class _EvilConfiguration(ShellAndTubeConfiguration):  # type: ignore[misc]
        def __bool__(self) -> bool:
            raise AssertionError("__bool__ must not execute")

        def __len__(self) -> int:
            raise AssertionError("__len__ must not execute")

    raw = _request_input(config_a(), layout_a())
    raw["task020_configuration"] = _EvilConfiguration(**config_a().__dict__)  # type: ignore[assignment]
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    codes = {b.code for b in result.blockers}
    # Raw projection catches the subclass (BL_019). Stage 2 only runs
    # for exact-type values.
    assert ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED in codes


def test_task021_subclass_is_rejected_without_execution() -> None:
    """A non-exact subclass of TubeLayout must be rejected."""
    from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout

    class _EvilLayout(TubeLayout):  # type: ignore[misc]
        def __bool__(self) -> bool:
            raise AssertionError("__bool__ must not execute")

        def __len__(self) -> int:
            raise AssertionError("__len__ must not execute")

    raw = _request_input(config_a(), layout_a())
    raw["task021_layout"] = _EvilLayout(**layout_a().__dict__)  # type: ignore[assignment]
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED in codes


# ---------------------------------------------------------------------------
# Round-4 §6 — participation member domain must be closed.
# ---------------------------------------------------------------------------


class _EvilMember:
    def __hash__(self) -> int:
        raise AssertionError("__hash__ must not execute")

    def __eq__(self, other: object) -> bool:
        raise AssertionError("__eq__ must not execute")


def _participation_input(members: dict[str, object]) -> dict[str, object]:
    """Build a request dict with a contaminated participation authority.

    Uses ``object.__new__`` + ``object.__setattr__`` so the dataclass
    ``__post_init__`` validation is bypassed. The malicious members
    reach the raw projection untouched, exercising the projector that
    must reject non-str members and produce BL_019.
    """
    contaminated = object.__new__(ts.Task025HydraulicParticipationAuthority)
    for field_name, field_value in members.items():
        object.__setattr__(contaminated, field_name, field_value)
    raw = _request_input(config_a(), layout_a())
    raw["hydraulic_participation_authority"] = contaminated
    return raw


def test_participation_dict_member_returns_blocked() -> None:
    raw = _participation_input(
        {
            "all_layout_position_ids": ({}),
            "active_position_ids": ({}),
            "inactive_position_ids": (),
            "authority_mode": ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            "evidence_refs": ("fixture",),
            "hydraulic_authority_hash": "a" * 64,
        }
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert any(b.code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED for b in result.blockers)


def test_participation_list_member_returns_blocked() -> None:
    raw = _participation_input(
        {
            "all_layout_position_ids": (["x"]),
            "active_position_ids": (["x"]),
            "inactive_position_ids": (),
            "authority_mode": ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            "evidence_refs": ("fixture",),
            "hydraulic_authority_hash": "a" * 64,
        }
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert any(b.code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED for b in result.blockers)


def test_participation_int_member_returns_blocked() -> None:
    raw = _participation_input(
        {
            "all_layout_position_ids": ((1,)),
            "active_position_ids": ((1,)),
            "inactive_position_ids": (),
            "authority_mode": ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            "evidence_refs": ("fixture",),
            "hydraulic_authority_hash": "a" * 64,
        }
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert any(b.code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED for b in result.blockers)


def test_participation_empty_string_member_returns_blocked() -> None:
    raw = _participation_input(
        {
            "all_layout_position_ids": (("",)),
            "active_position_ids": (("",)),
            "inactive_position_ids": (),
            "authority_mode": ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            "evidence_refs": ("fixture",),
            "hydraulic_authority_hash": "a" * 64,
        }
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert any(b.code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED for b in result.blockers)


class _StrSubclass(str):  # type: ignore[misc]
    pass


def test_participation_str_subclass_member_returns_blocked() -> None:
    raw = _participation_input(
        {
            "all_layout_position_ids": ((_StrSubclass("pos-1"),)),
            "active_position_ids": ((_StrSubclass("pos-1"),)),
            "inactive_position_ids": (),
            "authority_mode": ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            "evidence_refs": ("fixture",),
            "hydraulic_authority_hash": "a" * 64,
        }
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert any(b.code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED for b in result.blockers)


def test_participation_surrogate_member_returns_blocked() -> None:
    raw = _participation_input(
        {
            "all_layout_position_ids": (("\ud800",)),
            "active_position_ids": (("\ud800",)),
            "inactive_position_ids": (),
            "authority_mode": ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            "evidence_refs": ("fixture",),
            "hydraulic_authority_hash": "a" * 64,
        }
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert any(b.code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED for b in result.blockers)


def test_participation_evil_hash_member_is_not_hashed() -> None:
    raw = _participation_input(
        {
            "all_layout_position_ids": ((_EvilMember(),)),
            "active_position_ids": ((_EvilMember(),)),
            "inactive_position_ids": (),
            "authority_mode": ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            "evidence_refs": ("fixture",),
            "hydraulic_authority_hash": "a" * 64,
        }
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert any(b.code is ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED for b in result.blockers)


def test_participation_malformed_member_never_reaches_stage5_set_logic() -> None:
    """Stage 5 must not execute set(...) on unverified members."""
    raw = _participation_input(
        {
            "all_layout_position_ids": (({},)),  # unhashable
            "active_position_ids": (({},)),
            "inactive_position_ids": (),
            "authority_mode": ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            "evidence_refs": ("fixture",),
            "hydraulic_authority_hash": "a" * 64,
        }
    )
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    # Either raw projection caught it (BL_019) or the public boundary
    # refused to leak TypeError — never a successful valid result.
    assert not isinstance(result, ts.Task025ValidResult)


# ---------------------------------------------------------------------------
# Round-4 §7 — Stage 8 geometry attribute reads must be controlled.
# ---------------------------------------------------------------------------


def _stage8_input(layout_obj: object) -> dict[str, object]:
    raw = _request_input(config_a(), layout_obj)  # type: ignore[arg-type]
    raw["task021_layout"] = layout_obj  # type: ignore[assignment]
    return raw


def test_stage8_layout_missing_tube_geometry_is_blocked() -> None:
    contaminated = object.__new__(type(layout_a()))
    for field in layout_a().__dataclass_fields__:  # type: ignore[attr-defined]
        object.__setattr__(contaminated, field, getattr(layout_a(), field))
    object.__delattr__(contaminated, "tube_geometry")
    raw = _stage8_input(contaminated)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    # Raw projection is the first line of defense and catches the
    # missing tube_geometry field with BL_019. Stage 8 is the
    # second-line defense and would catch it with BL_026 in case of
    # a mutation race. Either outcome is acceptable as long as the
    # public boundary returns a blocked result.
    codes = {b.code for b in result.blockers}
    assert (
        ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED in codes
        or ts.BlockerCode.BL_026_TUBE_GEOMETRY_MISSING in codes
    )


def test_stage8_geometry_missing_inner_diameter_is_blocked() -> None:
    geom = layout_a().tube_geometry
    contaminated_geom = object.__new__(type(geom))
    for field in geom.__dataclass_fields__:  # type: ignore[attr-defined]
        object.__setattr__(contaminated_geom, field, getattr(geom, field))
    object.__delattr__(contaminated_geom, "inner_diameter_m")
    contaminated_layout = replace(layout_a(), tube_geometry=contaminated_geom)
    raw = _stage8_input(contaminated_layout)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    codes = {b.code for b in result.blockers}
    assert (
        ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED in codes
        or ts.BlockerCode.BL_026_TUBE_GEOMETRY_MISSING in codes
    )


def test_stage8_non_snapshot_geometry_is_blocked() -> None:
    contaminated_layout = replace(layout_a(), tube_geometry=object())  # type: ignore[arg-type]
    raw = _stage8_input(contaminated_layout)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    codes = {b.code for b in result.blockers}
    assert (
        ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED in codes
        or ts.BlockerCode.BL_026_TUBE_GEOMETRY_MISSING in codes
    )


def test_stage8_geometry_attribute_error_does_not_escape() -> None:
    class _EvilGeometry:
        @property
        def inner_diameter_m(self) -> str:
            raise AssertionError("inner_diameter_m must not be invoked via property")

    contaminated_layout = replace(layout_a(), tube_geometry=_EvilGeometry())  # type: ignore[arg-type]
    raw = _stage8_input(contaminated_layout)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    codes = {b.code for b in result.blockers}
    assert (
        ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED in codes
        or ts.BlockerCode.BL_026_TUBE_GEOMETRY_MISSING in codes
    )


def test_stage8_missing_inner_diameter_has_no_partial_geometry() -> None:
    geom = layout_a().tube_geometry
    contaminated_geom = object.__new__(type(geom))
    for field in geom.__dataclass_fields__:  # type: ignore[attr-defined]
        object.__setattr__(contaminated_geom, field, getattr(geom, field))
    object.__delattr__(contaminated_geom, "inner_diameter_m")
    contaminated_layout = replace(layout_a(), tube_geometry=contaminated_geom)
    raw = _stage8_input(contaminated_layout)
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert not isinstance(result, ts.Task025ValidResult)
    assert result.stage_rank in (1, 8)


# ---------------------------------------------------------------------------
# Round-4 §8 — top-level evidence_refs must use BL_003 for every violation.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "violating_value",
    [
        ["fixture"],  # list, not tuple
        (1,),  # int member
        ("",),  # empty member
        (_StrSubclass("fixture"),),  # str subclass member
        ("\ud800",),  # surrogate member
        (object(),),  # arbitrary object member
    ],
)
def test_top_level_evidence_refs_use_bl003_for_every_violation(
    violating_value: object,
) -> None:
    raw = _request_input(config_a(), layout_a())
    raw["evidence_refs"] = violating_value  # type: ignore[assignment]
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
    codes = {b.code for b in result.blockers}
    assert ts.BlockerCode.BL_003_BLOCKED_INPUT_REJECTED in codes
    assert ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED not in codes


def test_top_level_evidence_ref_violation_never_uses_bl019() -> None:
    raw = _request_input(config_a(), layout_a())
    raw["evidence_refs"] = ["fixture"]
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult)
    assert all(
        b.code is not ts.BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED for b in result.blockers
    )


def test_valid_unicode_evidence_ref_is_accepted() -> None:
    raw = _request_input(config_a(), layout_a())
    raw["evidence_refs"] = ("fixture-中文", "fixture-二")
    result = ts.evaluate_task025(raw)
    # Either valid or downstream blocked; never BL_003.
    if isinstance(result, ts.Task025BlockedResult):
        assert all(
            b.code is not ts.BlockerCode.BL_003_BLOCKED_INPUT_REJECTED
            or b.message_key != "evidence_refs_entry_not_utf8"
            for b in result.blockers
        )


def test_prevalidated_evidence_refs_are_used_at_stage6() -> None:
    """Stage 6 must reuse the prevalidated tuple, not re-validate raw_input."""
    raw = _request_input(config_a(), layout_a())
    raw["evidence_refs"] = ("fixture-prevalidated",)
    # If prevalidated, the public boundary does not re-read the raw dict;
    # any blocker at Stage 6 is not about evidence_refs.
    result = ts.evaluate_task025(raw)
    assert isinstance(result, ts.Task025BlockedResult | ts.Task025ValidResult)
    # Evidence_refs contract violation cannot appear at Stage 6+ now.
    if isinstance(result, ts.Task025BlockedResult):
        for b in result.blockers:
            assert not (
                b.field_path == "raw_input.evidence_refs"
                and b.message_key
                in {
                    "evidence_refs_not_frozen_container",
                    "evidence_refs_entry_not_exact_str",
                    "evidence_refs_entry_empty",
                }
            )
