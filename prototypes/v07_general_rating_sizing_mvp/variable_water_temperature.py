"""R23: experimental variable water inlet temperature (opt-in, non-production)."""

from __future__ import annotations

from decimal import Decimal

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV2

VARIABLE_WATER_TEMPERATURE_MIN_K = Decimal("290")
VARIABLE_WATER_TEMPERATURE_MAX_K = Decimal("320")


def experimental_variable_water_temperature_enabled(case: EngineeringCase) -> bool:
    return bool(getattr(case, "experimental_variable_water_temperature", False))


def validate_variable_water_inlet_temperature_k(temperature_k: Decimal, *, label: str) -> None:
    if (
        temperature_k < VARIABLE_WATER_TEMPERATURE_MIN_K
        or temperature_k > VARIABLE_WATER_TEMPERATURE_MAX_K
    ):
        raise ValueError(
            f"{label} inlet_temperature_k {temperature_k} K outside experimental "
            f"variable-water domain {VARIABLE_WATER_TEMPERATURE_MIN_K}–"
            f"{VARIABLE_WATER_TEMPERATURE_MAX_K} K"
        )


def validate_case_variable_water_temperature(case: EngineeringCase) -> None:
    if not experimental_variable_water_temperature_enabled(case):
        return
    if not isinstance(case, GeneralEngineeringCaseV2):
        raise ValueError(
            "experimental_variable_water_temperature requires general-engineering-case v2"
        )
    if not case.experimental_live_thermal_hydraulic_postpass:
        raise ValueError(
            "experimental_variable_water_temperature requires "
            "experimental_live_thermal_hydraulic_postpass=true"
        )
    from prototypes.v07_general_rating_sizing_mvp.case_streams import (
        shell_stream_spec,
        tube_stream_spec,
    )

    tube = tube_stream_spec(case)
    shell = shell_stream_spec(case)
    validate_variable_water_inlet_temperature_k(tube.inlet_temperature_k, label="tube_side")
    validate_variable_water_inlet_temperature_k(shell.inlet_temperature_k, label="shell_side")
    if tube.inlet_temperature_k <= shell.inlet_temperature_k:
        raise ValueError(
            "tube_side.inlet_temperature_k must exceed shell_side.inlet_temperature_k "
            "(TUBE_HOT_SHELL_COLD)"
        )
