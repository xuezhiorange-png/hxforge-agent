"""R27E: Task172 tube-side regime isolation (laminar vs turbulent C3 wall correction)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service
from hexagent.exchangers.shell_tube.task172_local_runtime.service import FlowRegime
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


def test_non_experimental_laminar_still_blocked_c3_regime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = CoolPropProvider()
    original_state = provider.state_tp

    def high_viscosity(fluid, temperature_k: float, pressure_pa: float):
        state = original_state(fluid, temperature_k, pressure_pa)
        return replace(state, viscosity_pa_s=state.viscosity_pa_s * 100.0)

    monkeypatch.setattr(provider, "state_tp", high_viscosity)
    request = _request()
    tube_bulk, _, _ = task172_service._snapshot(
        provider,
        request,
        "TUBE",
        f"{request.support.tube_cell_id}:CELL_MEAN",
        request.tube_bulk_state.temperature_k,
        request.tube_bulk_state.pressure_pa,
    )
    with pytest.raises(task172_service._RuntimeFailure) as exc:
        task172_service._resolve_tube_side_htc(
            request, tube_bulk, request.tube_mass_flow_kg_s
        )
    assert exc.value.code == "BLOCKED_TUBE_C3_REGIME_NOT_APPLICABLE"


def test_experimental_laminar_skips_c3_wall_pr_correction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = bind_experimental_thermal_boundary_v1(_variable_water_binding())
    try:
        provider = CoolPropProvider()
        original_state = provider.state_tp

        def high_viscosity(fluid, temperature_k: float, pressure_pa: float):
            state = original_state(fluid, temperature_k, pressure_pa)
            return replace(state, viscosity_pa_s=state.viscosity_pa_s * 100.0)

        monkeypatch.setattr(provider, "state_tp", high_viscosity)
        request = _request()
        tube_bulk, _, _ = task172_service._snapshot(
            provider,
            request,
            "TUBE",
            f"{request.support.tube_cell_id}:CELL_MEAN",
            request.tube_bulk_state.temperature_k,
            request.tube_bulk_state.pressure_pa,
        )
        resolved = task172_service._resolve_tube_side_htc(
            request, tube_bulk, request.tube_mass_flow_kg_s
        )
        assert resolved.flow_regime is FlowRegime.LAMINAR
        assert resolved.apply_c3_wall_pr_correction is False
        twi = float(request.tube_bulk_state.temperature_k) - 0.05
        g_plain = task172_service._tube_inner_wall_conductance_w_per_k(
            request,
            provider,
            tube_bulk,
            resolved.htc_w_m2_k,
            twi,
            apply_c3_wall_pr_correction=False,
        )
        g_misapplied_c3 = task172_service._tube_inner_wall_conductance_w_per_k(
            request,
            provider,
            tube_bulk,
            resolved.htc_w_m2_k,
            twi,
            apply_c3_wall_pr_correction=True,
        )
        assert g_misapplied_c3 != pytest.approx(g_plain, rel=1e-6)
    finally:
        reset_experimental_thermal_boundary(token)


def test_transition_raises_thermal_correlation_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = bind_experimental_thermal_boundary_v1(_variable_water_binding())
    try:
        from hexagent.exchangers.shell_tube.tube_side_thermal.single_phase import SinglePhaseOutputs

        real_compute = task172_service.compute_single_phase

        def transition_compute(*args, **kwargs):
            out = real_compute(*args, **kwargs)
            return SinglePhaseOutputs(
                bulk_velocity_m_s=out.bulk_velocity_m_s,
                reynolds_number=Decimal("2500"),
                prandtl_number=out.prandtl_number,
                nusselt_number=Decimal("0"),
                tube_side_heat_transfer_coefficient_w_m2_k=Decimal("0"),
                flow_regime=FlowRegime.TRANSITION,
                correlation_id="",
                correlation_version="",
            )

        monkeypatch.setattr(task172_service, "compute_single_phase", transition_compute)
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
        with pytest.raises(task172_service._RuntimeFailure) as exc:
            task172_service._resolve_tube_side_htc(
                request, tube_bulk, request.tube_mass_flow_kg_s
            )
        assert exc.value.code == "THERMAL_CORRELATION_UNAVAILABLE"
    finally:
        reset_experimental_thermal_boundary(token)
