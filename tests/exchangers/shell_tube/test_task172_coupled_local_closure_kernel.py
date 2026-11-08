"""Independent tests for Task172 coupled wall-temperature closure kernel."""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service
from hexagent.exchangers.shell_tube.task172_local_runtime.coupled_closure_kernel import (
    _branch_heat_rates_w,
)
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


def test_branch_heat_rates_match_validated_task172_result() -> None:
    token = bind_experimental_thermal_boundary_v1(_variable_water_binding())
    try:
        outcome = task172_service.validate_request(_request(), CoolPropProvider())
    finally:
        reset_experimental_thermal_boundary(token)
    assert type(outcome) is Task172LocalResult
    q = float(outcome.signed_q_hot_to_cold_w)
    twi = float(outcome.wall_temperature_inner_k)
    two = float(outcome.wall_temperature_outer_k)
    g_i = 1.0 / float(outcome.inner_film_resistance_k_w)
    g_wall = 1.0 / float(outcome.wall_resistance_k_w)
    g_o = 1.0 / float(outcome.outer_film_resistance_k_w)
    evaluated = {"g_i": g_i, "g_wall": g_wall, "g_o": g_o}
    tube_bulk = float(outcome.tube_bulk_temperature_k)
    shell_bulk = float(outcome.shell_bulk_temperature_k)
    qi, qw, qo = _branch_heat_rates_w(
        evaluated,
        tube_bulk_k=tube_bulk,
        shell_bulk_k=shell_bulk,
        twi_value=twi,
        two_value=two,
    )
    scale = max(abs(q), 1.0)
    assert abs(qi - qw) / scale < 1e-6
    assert abs(qw - qo) / scale < 1e-6
    assert abs(qw - q) / scale < 1e-5


@pytest.mark.timeout(1200)
def test_r23_variable_water_closure_reference_request_validates() -> None:
    """Regression witness: primary Task172 path still closes under original acceptance gate."""
    token = bind_experimental_thermal_boundary_v1(_variable_water_binding())
    try:
        outcome = task172_service.validate_request(_request(), CoolPropProvider())
    finally:
        reset_experimental_thermal_boundary(token)
    assert type(outcome) is Task172LocalResult
    assert outcome.residual_acceptance_state == "PASS_C_RESIDUAL_SPECIFIC_ULP_OPERATION_BOUND"
    assert float(outcome.signed_q_hot_to_cold_w) > 0.0
