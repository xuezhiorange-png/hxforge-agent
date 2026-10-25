"""R25: experimental wide-ΔT Task172 closure profile (variable water temperature only)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service
from hexagent.exchangers.shell_tube.task172_local_runtime.models import Task172BlockedResult
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


def test_residual_ratio_helper_parses_blocked_diagnostics() -> None:
    diagnostics = (
        "1000.0",
        "300.0",
        "299.0",
        "1.5e-9",
        "1e-10",
        "1e-10",
        "1e-9",
        "1e-8",
        "1e-8",
    )
    ratios = task172_service._residual_acceptance_ratios_from_diagnostics(diagnostics)
    assert ratios is not None
    assert ratios[0] == 1.5


def test_frozen_reference_still_uses_six_function_evaluation_cap() -> None:
    provider = CoolPropProvider()
    captured: list[int] = []
    original = task172_service.least_squares

    def track_least_squares(*_args: object, **kwargs: object) -> object:
        captured.append(int(kwargs["max_nfev"]))
        return original(*_args, **kwargs)

    with patch.object(task172_service, "least_squares", side_effect=track_least_squares):
        outcome = task172_service.validate_request(_request(), provider)
    assert captured
    assert all(value == task172_service._FROZEN_MAX_NFEV for value in captured)
    assert type(outcome) is not Task172BlockedResult or outcome.failure_code != (
        "BLOCKED_SOLVER_RESOURCE_EXHAUSTION"
    )


def test_wide_experimental_profile_activates_only_with_variable_water_binding() -> None:
    token = bind_experimental_thermal_boundary_v1(_variable_water_binding())
    try:
        assert task172_service._experimental_wide_delta_t_solver_active() is True
    finally:
        reset_experimental_thermal_boundary(token)
    assert task172_service._experimental_wide_delta_t_solver_active() is False


@pytest.mark.parametrize(
    ("residual", "bound", "expected"),
    [
        (Decimal("1.2e-9"), Decimal("1e-9"), False),
        (Decimal("8e-10"), Decimal("1e-9"), True),
    ],
)
def test_physical_residual_acceptance_is_not_relaxed(
    residual: Decimal, bound: Decimal, expected: bool
) -> None:
    assert (abs(residual) <= bound) is expected
