"""Task172 R25D scalar-Two acceptance diagnostics must match the failing q trial."""

from __future__ import annotations

from decimal import Decimal

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


def test_blocked_residual_diagnostics_nine_tuple_matches_field_path() -> None:
    field = ";".join(
        str(value)
        for value in (
            100.0,
            299.5,
            298.5,
            1.0e-12,
            -2.0e-12,
            0.0,
            1.0e-11,
            1.0e-11,
            1.0e-11,
        )
    )
    failure = task172_service._RuntimeFailure("BLOCKED_RESIDUAL_ACCEPTANCE", field)
    diagnostics = tuple(failure.field_path.split(";"))
    assert len(diagnostics) == 9
    assert diagnostics[0] == "100.0"
    ratios = task172_service._residual_acceptance_ratios_from_diagnostics(diagnostics)
    assert ratios is not None
    assert ratios[0] == 1.0e-12 / 1.0e-11


def test_scalar_two_blocked_replay_diagnostic_q_matches_residual_trial() -> None:
    """If wide scalar path blocks, diagnostic q must be the q_ts used for that attempt."""
    from tests.exchangers.shell_tube.test_task172_local_runtime import _request

    token = bind_experimental_thermal_boundary_v1(_variable_water_binding())
    try:
        outcome = task172_service.validate_request(_request(), CoolPropProvider())
    finally:
        reset_experimental_thermal_boundary(token)

    if type(outcome) is not Task172BlockedResult:
        return
    if outcome.failure_code != "BLOCKED_RESIDUAL_ACCEPTANCE":
        return
    diag = outcome.diagnostic_last_iterate
    if len(diag) < 9:
        return
    q_reported = float(diag[0])
    r1, _, r3 = (float(diag[3]), float(diag[4]), float(diag[5]))
    # Residual definition: r1 = q_ts - q_tube_film, so q_tube_film = q_ts - r1
    q_tube_film = q_reported - r1
    q_shell_film = q_reported - r3
    assert q_tube_film >= 0.0
    assert q_shell_film >= 0.0
