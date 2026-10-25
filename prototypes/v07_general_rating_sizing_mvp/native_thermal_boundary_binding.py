"""Bind general engineering case inlet conditions into Task173 experimental thermal context."""

# ruff: noqa: E501

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    EXPERIMENTAL_THERMAL_BOUNDARY_AUTHORITY_ID,
    EXPERIMENTAL_THERMAL_BOUNDARY_SCHEMA,
    ExperimentalThermalBoundaryBindingV1,
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    matches_frozen_reference_boundary,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import REFERENCE_PRESSURE_PA
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    SHELL_INLET_T_K,
    SHELL_MASS_FLOW_KG_S,
    TUBE_INLET_T_K,
    TUBE_MASS_FLOW_KG_S,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.case_streams import (
    shell_stream_spec,
    tube_stream_spec,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.variable_shell_mass_flow import (
    experimental_live_variable_shell_mass_flow_enabled,
)
from prototypes.v07_general_rating_sizing_mvp.variable_tube_mass_flow import (
    experimental_live_variable_tube_mass_flow_enabled,
)
from prototypes.v07_general_rating_sizing_mvp.variable_water_temperature import (
    experimental_variable_water_temperature_enabled,
)

_ALLOWED_FLUID = "PURE_ORDINARY_WATER"


def validate_case_for_native_thermal_binding(case: EngineeringCase) -> None:
    status, detail = case.applicability_status()
    if status != "IN_SCOPE":
        raise ValueError(f"engineering case not in scope for native thermal binding: {detail}")
    tube = tube_stream_spec(case)
    shell = shell_stream_spec(case)
    if tube.fluid != _ALLOWED_FLUID or shell.fluid != _ALLOWED_FLUID:
        raise ValueError("native thermal binding supports PURE_ORDINARY_WATER only")
    if (
        not experimental_live_variable_tube_mass_flow_enabled(case)
        and tube.mass_flow_kg_s != TUBE_MASS_FLOW_KG_S
    ):
        raise ValueError("tube mass flow must match frozen Task173 kernel for experimental binding")
    if (
        not experimental_live_variable_shell_mass_flow_enabled(case)
        and shell.mass_flow_kg_s != SHELL_MASS_FLOW_KG_S
    ):
        raise ValueError(
            "shell mass flow must match frozen Task173 kernel for experimental binding"
        )
    if tube.inlet_pressure_pa != REFERENCE_PRESSURE_PA:
        raise ValueError("tube inlet pressure must match REFERENCE_PRESSURE_PA")
    if shell.inlet_pressure_pa != REFERENCE_PRESSURE_PA:
        raise ValueError("shell inlet pressure must match REFERENCE_PRESSURE_PA")


def build_native_thermal_boundary_from_case(
    case: EngineeringCase,
    provider: CoolPropProvider,
    *,
    tube_property_evaluation_pressure_pa: Decimal | None = None,
    shell_property_evaluation_pressure_pa: Decimal | None = None,
) -> ExperimentalThermalBoundaryBindingV1:
    validate_case_for_native_thermal_binding(case)
    tube = tube_stream_spec(case)
    shell = shell_stream_spec(case)
    return build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=tube.inlet_temperature_k,
        shell_inlet_temperature_k=shell.inlet_temperature_k,
        tube_mass_flow_kg_s=tube.mass_flow_kg_s,
        shell_mass_flow_kg_s=shell.mass_flow_kg_s,
        allow_live_variable_tube_mass_flow=experimental_live_variable_tube_mass_flow_enabled(case),
        allow_live_variable_shell_mass_flow=experimental_live_variable_shell_mass_flow_enabled(
            case
        ),
        allow_variable_water_temperature=experimental_variable_water_temperature_enabled(case),
        tube_property_evaluation_pressure_pa=tube_property_evaluation_pressure_pa,
        shell_property_evaluation_pressure_pa=shell_property_evaluation_pressure_pa,
    )


def disclosure_document(binding: ExperimentalThermalBoundaryBindingV1 | None) -> dict[str, Any]:
    if binding is None:
        return {
            "schema_version": EXPERIMENTAL_THERMAL_BOUNDARY_SCHEMA,
            "binding_status": "FROZEN_REFERENCE_BOUNDARY",
            "authority_id": None,
            "tube_inlet_temperature_k": str(TUBE_INLET_T_K),
            "shell_inlet_temperature_k": str(SHELL_INLET_T_K),
            "participates_in_task173_mesh": True,
            "participates_via": "service frozen constants",
        }
    return {
        "schema_version": binding.schema_version,
        "binding_status": (
            "FROZEN_REFERENCE_BOUNDARY"
            if matches_frozen_reference_boundary(binding)
            else "EXPERIMENTAL_LIVE_BOUNDARY"
        ),
        "authority_id": binding.authority_id,
        "thermal_variant": binding.thermal_variant,
        "tube_inlet_temperature_k": str(binding.tube_inlet_temperature_k),
        "shell_inlet_temperature_k": str(binding.shell_inlet_temperature_k),
        "tube_inlet_enthalpy_j_kg": str(binding.tube_inlet_enthalpy_j_kg),
        "shell_inlet_enthalpy_j_kg": str(binding.shell_inlet_enthalpy_j_kg),
        "tube_mass_flow_kg_s": str(binding.tube_mass_flow_kg_s),
        "shell_mass_flow_kg_s": str(binding.shell_mass_flow_kg_s),
        "reference_pressure_pa": str(binding.reference_pressure_pa),
        "tube_property_evaluation_pressure_pa": str(binding.tube_property_evaluation_pressure_pa),
        "shell_property_evaluation_pressure_pa": str(binding.shell_property_evaluation_pressure_pa),
        "participates_in_task173_mesh": True,
        "participates_via": EXPERIMENTAL_THERMAL_BOUNDARY_AUTHORITY_ID,
    }


@contextmanager
def native_thermal_boundary_session(
    case: EngineeringCase,
    provider: CoolPropProvider,
    *,
    enable_live_binding: bool,
    tube_property_evaluation_pressure_pa: Decimal | None = None,
    shell_property_evaluation_pressure_pa: Decimal | None = None,
) -> Iterator[ExperimentalThermalBoundaryBindingV1 | None]:
    if not enable_live_binding:
        yield None
        return
    binding = build_native_thermal_boundary_from_case(
        case,
        provider,
        tube_property_evaluation_pressure_pa=tube_property_evaluation_pressure_pa,
        shell_property_evaluation_pressure_pa=shell_property_evaluation_pressure_pa,
    )
    token = bind_experimental_thermal_boundary_v1(binding)
    try:
        yield binding
    finally:
        reset_experimental_thermal_boundary(token)
