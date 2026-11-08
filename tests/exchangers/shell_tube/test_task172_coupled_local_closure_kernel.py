"""Independent tests for Task172 coupled wall-temperature closure kernel."""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service
from hexagent.exchangers.shell_tube.task172_local_runtime.coupled_closure_kernel import (
    ClosureResourceExhausted,
    _branch_heat_rates_w,
    _search_q_ts_for_acceptance,
    solve_coupled_local_closure,
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


def test_q_ts_search_finds_interior_when_endpoints_fail() -> None:
    twi, two = 300.0, 298.0
    tube_bulk, shell_bulk = 310.0, 295.0
    span = 1.0
    g_i = 10.0
    g_wall = 50.0
    g_o = 101.0 / 3.0

    def evaluate_trial(q_ts: float, _wi: float, _wo: float) -> dict:
        counter[0] += 1
        low = 100.0
        high = 101.0
        mid = 0.5 * (low + high)
        bound = 0.5 * span
        target = q_ts
        if abs(q_ts - mid) < span / 64.0:
            target = mid
        elif q_ts <= low + span * 0.02:
            target = low + 2.0 * bound
        elif q_ts >= high - span * 0.02:
            target = high + 2.0 * bound
        residual = q_ts - target
        return {
            "g_i": g_i,
            "g_wall": g_wall,
            "g_o": g_o,
            "residuals": (residual, residual, residual),
            "bounds": (bound, bound, bound),
        }

    counter = [0]
    q_ts, accepted = _search_q_ts_for_acceptance(
        twi,
        two,
        tube_bulk_k=tube_bulk,
        shell_bulk_k=shell_bulk,
        evaluate_trial=evaluate_trial,
        q_anchor=100.0,
        callback_budget=200,
        callback_counter=counter,
    )
    assert accepted
    assert 100.0 < q_ts < 101.0


def test_q_ts_search_raises_when_budget_exhausted() -> None:
    def evaluate_trial(_q: float, _wi: float, _wo: float) -> dict:
        counter[0] += 1
        return {
            "g_i": 1.0,
            "g_wall": 1.0,
            "g_o": 1.0,
            "residuals": (1.0, 1.0, 1.0),
            "bounds": (1.0, 1.0, 1.0),
        }

    counter = [5]
    with pytest.raises(ClosureResourceExhausted):
        _search_q_ts_for_acceptance(
            300.0,
            298.0,
            tube_bulk_k=310.0,
            shell_bulk_k=295.0,
            evaluate_trial=evaluate_trial,
            q_anchor=100.0,
            callback_budget=5,
            callback_counter=counter,
        )


def test_coupled_closure_solver_status_reflects_least_squares_method() -> None:
    calls = 0

    def evaluate_trial(_q: float, _wi: float, _wo: float) -> dict:
        nonlocal calls
        calls += 1
        return {
            "g_i": 10.0,
            "g_wall": 10.0,
            "g_o": 10.0,
            "residuals": (0.0, 0.0, 0.0),
            "bounds": (1.0, 1.0, 1.0),
        }

    def accept_solution(solution: tuple[float, float, float], _ctx: object) -> tuple:
        evaluated = evaluate_trial(solution[0], solution[1], solution[2])
        return evaluated, solution

    counter = [0]
    _, _, _, status_trf = solve_coupled_local_closure(
        tube_bulk_k=310.0,
        shell_bulk_k=295.0,
        wall_inner_seed=305.0,
        wall_outer_seed=298.0,
        evaluate_trial=evaluate_trial,
        accept_solution=accept_solution,
        accept_context=None,
        callback_budget=400,
        callback_counter=counter,
        least_squares_method="trf",
    )
    assert status_trf == "V08_03_COUPLED_WALL_CLOSURE_TRF"

    counter = [0]
    _, _, _, status_dog = solve_coupled_local_closure(
        tube_bulk_k=310.0,
        shell_bulk_k=295.0,
        wall_inner_seed=305.0,
        wall_outer_seed=298.0,
        evaluate_trial=evaluate_trial,
        accept_solution=accept_solution,
        accept_context=None,
        callback_budget=400,
        callback_counter=counter,
        least_squares_method="dogbox",
    )
    assert status_dog == "V08_03_COUPLED_WALL_CLOSURE_DOGBOX"
