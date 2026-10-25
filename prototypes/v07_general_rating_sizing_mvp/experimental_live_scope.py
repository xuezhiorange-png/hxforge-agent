"""Supported envelope for experimental live-rating CLI (R9)."""

from __future__ import annotations

from decimal import Decimal

from prototypes.v07_general_rating_sizing_mvp.case_streams import (
    shell_stream_spec,
    tube_stream_spec,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV2
from prototypes.v07_general_rating_sizing_mvp.variable_shell_mass_flow import (
    experimental_live_variable_shell_mass_flow_enabled,
    validate_variable_shell_mass_flow_kg_s,
)
from prototypes.v07_general_rating_sizing_mvp.variable_tube_mass_flow import (
    experimental_live_variable_tube_mass_flow_enabled,
    validate_variable_tube_mass_flow_kg_s,
)
from prototypes.v07_general_rating_sizing_mvp.variable_water_temperature import (
    experimental_variable_water_temperature_enabled,
    validate_variable_water_inlet_temperature_k,
)

_SUPPORTED_SHELL_INLET_K = Decimal("298.15")
_SUPPORTED_TUBE_FLOW = Decimal("12.000000")
_SUPPORTED_SHELL_FLOW = Decimal("20.000000")
_SUPPORTED_PRESSURE_PA = Decimal("101325")


def check_experimental_live_rating_scope(
    case: EngineeringCase,
) -> tuple[str, str | None]:
    """Return (IN_SCOPE | INPUT_OUT_OF_SUPPORTED_SCOPE, detail)."""
    if not isinstance(case, GeneralEngineeringCaseV2):
        return (
            "INPUT_OUT_OF_SUPPORTED_SCOPE",
            "experimental-live-rating requires hxforge.general-engineering-case.v2 JSON",
        )
    scope, detail = case.applicability_status()
    if scope == "BLOCKED":
        return "INPUT_OUT_OF_SUPPORTED_SCOPE", detail or "input_validation_blocked"
    if case.exchanger_type != "SHELL_AND_TUBE_FIXED_TUBESHEET_SINGLE_PHASE":
        return "INPUT_OUT_OF_SUPPORTED_SCOPE", "unsupported exchanger_type"
    bundle_mode = getattr(case, "experimental_bundle_geometry_mode", "FIXED")
    if not case.bind_task172_c3_reference_geometry and bundle_mode != "VARIABLE_SHELL_DIAMETER_R13":
        return (
            "INPUT_OUT_OF_SUPPORTED_SCOPE",
            "bind_task172_c3_reference_geometry must be true for experimental live rating "
            "unless experimental_bundle_geometry_mode=VARIABLE_SHELL_DIAMETER_R13",
        )
    tube = tube_stream_spec(case)
    shell = shell_stream_spec(case)
    if tube.fluid != "PURE_ORDINARY_WATER" or shell.fluid != "PURE_ORDINARY_WATER":
        return "INPUT_OUT_OF_SUPPORTED_SCOPE", "only PURE_ORDINARY_WATER single-phase is supported"
    if experimental_live_variable_tube_mass_flow_enabled(case):
        try:
            validate_variable_tube_mass_flow_kg_s(tube.mass_flow_kg_s)
        except ValueError as exc:
            return "INPUT_OUT_OF_SUPPORTED_SCOPE", str(exc)
    elif tube.mass_flow_kg_s != _SUPPORTED_TUBE_FLOW:
        return "INPUT_OUT_OF_SUPPORTED_SCOPE", "tube_side mass_flow_kg_s must be 12.000000 kg/s"
    if experimental_live_variable_shell_mass_flow_enabled(case):
        try:
            validate_variable_shell_mass_flow_kg_s(shell.mass_flow_kg_s)
        except ValueError as exc:
            return "INPUT_OUT_OF_SUPPORTED_SCOPE", str(exc)
    elif shell.mass_flow_kg_s != _SUPPORTED_SHELL_FLOW:
        return "INPUT_OUT_OF_SUPPORTED_SCOPE", "shell_side mass_flow_kg_s must be 20.000000 kg/s"
    if tube.inlet_pressure_pa != _SUPPORTED_PRESSURE_PA:
        return "INPUT_OUT_OF_SUPPORTED_SCOPE", "tube inlet pressure must be 101325 Pa"
    if shell.inlet_pressure_pa != _SUPPORTED_PRESSURE_PA:
        return "INPUT_OUT_OF_SUPPORTED_SCOPE", "shell inlet pressure must be 101325 Pa"
    if experimental_variable_water_temperature_enabled(case):
        try:
            validate_variable_water_inlet_temperature_k(tube.inlet_temperature_k, label="tube_side")
            validate_variable_water_inlet_temperature_k(
                shell.inlet_temperature_k, label="shell_side"
            )
        except ValueError as exc:
            return "INPUT_OUT_OF_SUPPORTED_SCOPE", str(exc)
    elif shell.inlet_temperature_k != _SUPPORTED_SHELL_INLET_K:
        return (
            "INPUT_OUT_OF_SUPPORTED_SCOPE",
            "shell_side.inlet_temperature_k must be 298.15 K unless "
            "experimental_variable_water_temperature=true",
        )
    if tube.inlet_temperature_k <= shell.inlet_temperature_k:
        return (
            "INPUT_OUT_OF_SUPPORTED_SCOPE",
            "tube_side inlet must exceed shell_side inlet (TUBE_HOT_SHELL_COLD)",
        )
    return "IN_SCOPE", None
