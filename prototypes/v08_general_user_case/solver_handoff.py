"""Executable solver parameter binding for validated V08 user cases."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    EXPERIMENTAL_THERMAL_BOUNDARY_SCHEMA,
    ExperimentalThermalBoundaryBindingV1,
    build_experimental_thermal_boundary_v1,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.property_provider_identity import (
    build_property_provider_identity,
)
from prototypes.v08_general_user_case.physical_feasibility import PhysicalFeasibilityReport
from prototypes.v08_general_user_case.user_design_case import (
    NormalizedUserDesignCase,
    format_engineering_decimal,
)

V08_SOLVER_HANDOFF_SCHEMA_V1 = "hxforge.v08-solver-parameter-handoff.v1"

V08DownstreamReadiness = Literal[
    "THERMAL_HYDRAULIC_PARAMETERS_READY",
    "VALIDATED_INPUT_ONLY",
    "BLOCKED",
]


class V08SolverHandoffV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    schema_version: Literal["hxforge.v08-solver-parameter-handoff.v1"] = (
        V08_SOLVER_HANDOFF_SCHEMA_V1
    )
    engineering_case_id: str
    input_schema_version: str
    normalized_input_hash: str
    downstream_readiness: V08DownstreamReadiness
    geometry_required_for_full_design: bool = False
    consumable_parameters: dict[str, str]
    pressure_limits_pa: dict[str, str]
    thermal_binding: dict[str, Any] | None = None
    property_provider_identity: dict[str, Any]
    physical_feasibility: dict[str, Any]
    warnings: tuple[str, ...] = ()
    provenance: dict[str, str] = Field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def build_solver_handoff(
    case: NormalizedUserDesignCase,
    feasibility: PhysicalFeasibilityReport,
    provider: CoolPropProvider,
) -> V08SolverHandoffV1:
    if not feasibility.ok:
        raise ValueError("cannot build solver handoff from failed feasibility report")

    input_hash = canonical_sha256(case.input_snapshot_dict())
    consumable = {
        "tube_mass_flow_kg_s": format_engineering_decimal(case.tube_side.mass_flow_kg_s),
        "shell_mass_flow_kg_s": format_engineering_decimal(case.shell_side.mass_flow_kg_s),
        "tube_inlet_temperature_k": format_engineering_decimal(case.tube_side.inlet_temperature_k),
        "shell_inlet_temperature_k": format_engineering_decimal(case.shell_side.inlet_temperature_k),
        "tube_inlet_pressure_pa": format_engineering_decimal(case.tube_side.inlet_pressure_pa),
        "shell_inlet_pressure_pa": format_engineering_decimal(case.shell_side.inlet_pressure_pa),
        "target_duty_w": format_engineering_decimal(case.target_duty_w),
        "thermal_variant": "TUBE_HOT_SHELL_COLD",
    }
    pressure_limits = {
        "max_tube_side_pressure_drop_pa": format_engineering_decimal(
            case.max_tube_side_pressure_drop_pa
        ),
        "max_shell_side_pressure_drop_pa": format_engineering_decimal(
            case.max_shell_side_pressure_drop_pa
        ),
    }

    warnings: list[str] = []
    thermal_binding_doc: dict[str, Any] | None = None
    readiness: V08DownstreamReadiness

    if feasibility.thermal_binding_ready:
        binding: ExperimentalThermalBoundaryBindingV1 = build_experimental_thermal_boundary_v1(
            provider=provider,
            tube_inlet_temperature_k=case.tube_side.inlet_temperature_k,
            shell_inlet_temperature_k=case.shell_side.inlet_temperature_k,
            tube_mass_flow_kg_s=case.tube_side.mass_flow_kg_s,
            shell_mass_flow_kg_s=case.shell_side.mass_flow_kg_s,
            allow_live_variable_tube_mass_flow=True,
            allow_live_variable_shell_mass_flow=True,
            allow_variable_water_temperature=True,
            tube_property_evaluation_pressure_pa=case.tube_side.inlet_pressure_pa,
            shell_property_evaluation_pressure_pa=case.shell_side.inlet_pressure_pa,
        )
        thermal_binding_doc = {
            "schema_version": EXPERIMENTAL_THERMAL_BOUNDARY_SCHEMA,
            "authority_id": binding.authority_id,
            "tube_inlet_temperature_k": str(binding.tube_inlet_temperature_k),
            "shell_inlet_temperature_k": str(binding.shell_inlet_temperature_k),
            "tube_mass_flow_kg_s": str(binding.tube_mass_flow_kg_s),
            "shell_mass_flow_kg_s": str(binding.shell_mass_flow_kg_s),
            "tube_inlet_enthalpy_j_kg": str(binding.tube_inlet_enthalpy_j_kg),
            "shell_inlet_enthalpy_j_kg": str(binding.shell_inlet_enthalpy_j_kg),
            "tube_property_evaluation_pressure_pa": str(
                binding.tube_property_evaluation_pressure_pa
            ),
            "shell_property_evaluation_pressure_pa": str(
                binding.shell_property_evaluation_pressure_pa
            ),
        }
        readiness = "THERMAL_HYDRAULIC_PARAMETERS_READY"
    else:
        readiness = "VALIDATED_INPUT_ONLY"
        warnings.append(
            "Inlet state validated but outside current Task173 experimental thermal-binding "
            "envelope; V08-02+ must not silently clamp to frozen 330 kW reference conditions."
        )

    return V08SolverHandoffV1(
        engineering_case_id=case.engineering_case_id,
        input_schema_version=case.schema_version,
        normalized_input_hash=input_hash,
        downstream_readiness=readiness,
        geometry_required_for_full_design=True,
        consumable_parameters=consumable,
        pressure_limits_pa=pressure_limits,
        thermal_binding=thermal_binding_doc,
        property_provider_identity=build_property_provider_identity(provider),
        physical_feasibility=feasibility.as_dict(),
        warnings=tuple(warnings),
        provenance={
            "handoff_builder": "v08_general_user_case.solver_handoff.build_solver_handoff",
            "normalized_input_hash": input_hash,
            "geometry_generation_task": "V08-02",
        },
    )
