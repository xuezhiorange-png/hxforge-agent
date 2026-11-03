"""R25D: physical Two bracket scalar closure and shell-only conductance."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service
from hexagent.exchangers.shell_tube.task172_local_runtime.models import Task172LocalResult
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    EXPERIMENTAL_THERMAL_BOUNDARY_SCHEMA,
    EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_WATER_TEMPERATURE_R23_AUTHORITY_ID,
    ExperimentalThermalBoundaryBindingV1,
    bind_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from tests.exchangers.shell_tube.test_task172_local_runtime import _request


def _variable_water_binding() -> ExperimentalThermalBoundaryBindingV1:
    from decimal import Decimal

    return ExperimentalThermalBoundaryBindingV1(
        schema_version=EXPERIMENTAL_THERMAL_BOUNDARY_SCHEMA,
        authority_id=EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_WATER_TEMPERATURE_R23_AUTHORITY_ID,
        thermal_variant="TUBE_HOT_SHELL_COLD",
        tube_inlet_temperature_k=Decimal("310"),
        shell_inlet_temperature_k=Decimal("295"),
        tube_mass_flow_kg_s=Decimal("12"),
        shell_mass_flow_kg_s=Decimal("20"),
        reference_pressure_pa=Decimal("101325"),
        tube_inlet_enthalpy_j_kg=Decimal("1"),
        shell_inlet_enthalpy_j_kg=Decimal("1"),
        tube_property_evaluation_pressure_pa=Decimal("101325"),
        shell_property_evaluation_pressure_pa=Decimal("101325"),
        variable_water_temperature_enabled=True,
    )


def test_r25d_profile_and_shell_conductance_helper() -> None:
    profile = task172_service._WIDE_DELTA_T_EXPERIMENTAL_NUMERICAL_PROFILE_ID
    assert "R25D" in profile
    provider = CoolPropProvider()
    request = _request()
    tube_bulk, _, _ = task172_service._snapshot(
        provider,
        request,
        "TUBE",
        f"{request.support.tube_cell_id}:CELL_MEAN",
        request.tube_bulk_state.temperature_k,
        request.tube_bulk_state.pressure_pa,
    )
    shell_bulk, _, _ = task172_service._snapshot(
        provider,
        request,
        "SHELL",
        f"{request.support.shell_cell_id}:CELL_MEAN",
        request.shell_bulk_state.temperature_k,
        request.shell_bulk_state.pressure_pa,
    )
    tube_h, _, _, _, _ = task172_service._tube_base_htc(
        request, tube_bulk, request.tube_mass_flow_kg_s
    )
    shell_h, _, _, _ = task172_service._shell_base_htc(
        request, shell_bulk, request.shell_mass_flow_kg_s
    )
    two_k = 300.0
    g_o = task172_service._shell_outer_wall_conductance_w_per_k(
        request,
        provider,
        shell_bulk,
        shell_h,
        two_k,
    )
    assert g_o > 0.0


def test_r23_support0_lower_endpoint_hole_replay_exposes_bracket_gap() -> None:
    """Replay 310/295 n=1 mesh: Support:0 LOWER_ENDPOINT hole, no valid F(q) sign pair."""
    from pathlib import Path

    from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
    from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
        load_general_engineering_case_json,
    )
    from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
        native_thermal_boundary_session,
    )
    from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
        build_native_cell_context,
    )

    fixture = (
        Path(__file__).resolve().parents[1] / "fixtures/r23_variable_water_temperature_n1_case.json"
    )
    case = load_general_engineering_case_json(fixture.read_text(encoding="utf-8"))
    native = build_native_cell_context(case)
    provider = CoolPropProvider()
    stats = t173._CellSearchStats()
    with native_thermal_boundary_session(case, provider, enable_live_binding=True):
        token = t173._CANDIDATE_RATING_CONTEXT.set(native.context)
        try:
            try:
                t173._candidate_transient_outer_boundary(1, provider, native.shell_authority, stats)
            except t173._Stage3Failure as exc:
                assert exc.code == "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED"
                assert any("sign_pair_found=false" in d for d in exc.diagnostics)
            else:
                raise AssertionError("expected mesh bracket unresolved for 310/295 n=1")
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)
    assert stats.task172_numerical_hole_trials, "mesh must record TASK172 numerical holes"
    sid = stats.task172_numerical_hole_trials[0]["physical_support_id"]
    holes = [h for h in stats.task172_numerical_hole_trials if h["physical_support_id"] == sid]
    assert holes, "blocking support must record TASK172 numerical holes on replay"
    assert all(h["failure_code"] == "BLOCKED_RESIDUAL_ACCEPTANCE" for h in holes)
    assert stats.maximum_hole_recovery_depth_observed >= 1
    if stats.endpoint_hole_level_receipts:
        level_receipts = [
            r for r in stats.endpoint_hole_level_receipts if r.physical_support_id == sid
        ]
        assert level_receipts
        assert not any(r.sign_pair_found for r in level_receipts)


def test_wide_solver_replay_on_frozen_request_still_validates() -> None:
    token = bind_experimental_thermal_boundary_v1(_variable_water_binding())
    try:
        outcome = task172_service.validate_request(_request(), CoolPropProvider())
    finally:
        reset_experimental_thermal_boundary(token)
    assert type(outcome) is Task172LocalResult
