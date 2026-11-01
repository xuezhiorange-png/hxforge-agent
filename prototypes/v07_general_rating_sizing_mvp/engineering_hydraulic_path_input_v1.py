"""Versioned engineering hydraulic path input contract (R26G)."""

# ruff: noqa: E501

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import CandidateSelectionRecord
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase

SCHEMA_VERSION = "hxforge.engineering-hydraulic-path-input.v1"

EngineeringInputStatus = Literal[
    "DEMONSTRATION",
    "ASSUMPTION_BASED",
    "AUTHORIZED_ENGINEERING_INPUT",
]
PathSide = Literal["TUBE", "SHELL"]
LossConvention = Literal["K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"]
PathCompletenessDeclaration = Literal[
    "FULL_TUBE_AND_SHELL_EXTERNAL_PATH",
    "PARTIAL_DECLARED",
]

TubeComponentType = Literal[
    "ENTRANCE",
    "EXIT",
    "CHANNEL_HEAD",
    "NOZZLE",
    "CONTRACTION",
    "EXPANSION",
]
ShellExternalComponentType = Literal[
    "SHELL_INLET_NOZZLE",
    "SHELL_OUTLET_NOZZLE",
    "SHELL_INLET_TRANSITION",
    "SHELL_OUTLET_TRANSITION",
    "SHELL_EXTERNAL_LOCAL",
]


class FluidDensitySourceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    kind: Literal["COOLPROP_TP", "CASE_SIDE_INLET"]
    fluid_role: Literal["TUBE_SIDE", "SHELL_SIDE"] | None = None
    temperature_k: Decimal | None = None
    pressure_pa: Decimal | None = None
    property_source_id: str = Field(default="CoolProp-6.6", min_length=3, max_length=64)
    property_source_version: str = Field(default="1.0.0", min_length=1, max_length=64)

    @model_validator(mode="after")
    def kind_requires_fields(self) -> FluidDensitySourceV1:
        if self.kind == "COOLPROP_TP" and (self.temperature_k is None or self.pressure_pa is None):
            raise ValueError("COOLPROP_TP requires temperature_k and pressure_pa")
        if self.kind == "CASE_SIDE_INLET" and self.fluid_role is None:
            raise ValueError("CASE_SIDE_INLET requires fluid_role")
        return self


class HydraulicPathComponentV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    component_id: str = Field(min_length=1, max_length=64)
    side: PathSide
    component_type: str = Field(min_length=3, max_length=64)
    reference_plane: str = Field(min_length=3, max_length=128)
    path_sequence_index: int = Field(ge=0, le=64)
    reference_flow_area_m2: Decimal | None = None
    nozzle_inside_diameter_m: Decimal | None = None
    mass_flow_kg_s: Decimal
    fluid_density_source: FluidDensitySourceV1
    loss_coefficient: Decimal
    loss_coefficient_convention: LossConvention = (
        "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"
    )
    coefficient_source_id: str = Field(min_length=3, max_length=256)
    coefficient_source_version: str = Field(min_length=1, max_length=64)
    coefficient_source_location: str = Field(min_length=3, max_length=512)
    geometry_evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=8)
    engineering_input_status: EngineeringInputStatus
    multiplicity: int = Field(default=1, ge=1, le=32)

    @field_validator(
        "loss_coefficient",
        "reference_flow_area_m2",
        "nozzle_inside_diameter_m",
        "mass_flow_kg_s",
    )
    @classmethod
    def positive_finite(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if not value.is_finite() or value <= 0:
            raise ValueError("hydraulic path numeric fields must be positive and finite")
        return value

    @model_validator(mode="after")
    def area_or_nozzle(self) -> HydraulicPathComponentV1:
        if self.reference_flow_area_m2 is None and self.nozzle_inside_diameter_m is None:
            raise ValueError(
                "each component requires reference_flow_area_m2 or nozzle_inside_diameter_m"
            )
        if self.reference_flow_area_m2 is not None and self.nozzle_inside_diameter_m is not None:
            raise ValueError("provide reference_flow_area_m2 or nozzle_inside_diameter_m, not both")
        return self


class EngineeringHydraulicPathBindingV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    engineering_case_id: str = Field(min_length=1, max_length=128)
    candidate_id: str = Field(min_length=8, max_length=64)
    candidate_hash: str = Field(min_length=8, max_length=128)
    geometry_projection_hash: str = Field(min_length=8, max_length=128)


class EngineeringHydraulicPathInputV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    schema_version: Literal["hxforge.engineering-hydraulic-path-input.v1"]
    binding: EngineeringHydraulicPathBindingV1
    path_completeness_declaration: PathCompletenessDeclaration
    tube_side_components: tuple[HydraulicPathComponentV1, ...] = Field(default_factory=tuple)
    shell_external_components: tuple[HydraulicPathComponentV1, ...] = Field(default_factory=tuple)
    bell_delaware_internal_scope: str = Field(
        default=(
            "Shell-side Bell–Delaware internal bundle pressure drop is taken from live rating "
            "post-pass; it must not be duplicated in shell_external_components."
        ),
        min_length=10,
        max_length=1024,
    )

    @model_validator(mode="after")
    def components_on_correct_side(self) -> EngineeringHydraulicPathInputV1:
        for component in self.tube_side_components:
            if component.side != "TUBE":
                raise ValueError("tube_side_components must have side=TUBE")
        for component in self.shell_external_components:
            if component.side != "SHELL":
                raise ValueError("shell_external_components must have side=SHELL")
        if not self.tube_side_components and not self.shell_external_components:
            raise ValueError("at least one tube or shell external component is required")
        return self


def nozzle_flow_area_m2(nozzle_inside_diameter_m: Decimal) -> Decimal:
    area = Decimal(str(math.pi)) * (nozzle_inside_diameter_m / Decimal(2)) ** 2
    return area.quantize(Decimal("0.0000000001"))


def resolved_reference_flow_area_m2(component: HydraulicPathComponentV1) -> Decimal:
    if component.reference_flow_area_m2 is not None:
        return component.reference_flow_area_m2
    assert component.nozzle_inside_diameter_m is not None
    return nozzle_flow_area_m2(component.nozzle_inside_diameter_m)


def load_engineering_hydraulic_path_input_v1(
    data: dict[str, Any],
) -> EngineeringHydraulicPathInputV1:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported hydraulic path input schema: {data.get('schema_version')}")
    return EngineeringHydraulicPathInputV1.model_validate(data)


def load_engineering_hydraulic_path_input_v1_json(text: str) -> EngineeringHydraulicPathInputV1:
    import json

    return load_engineering_hydraulic_path_input_v1(json.loads(text))


def validate_path_input_binding(
    path_input: EngineeringHydraulicPathInputV1,
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
) -> list[str]:
    errors: list[str] = []
    binding = path_input.binding
    case_id = getattr(case, "engineering_case_id", None)
    if case_id is not None and binding.engineering_case_id != case_id:
        errors.append("engineering_case_id mismatch")
    if binding.candidate_id != record.candidate_id:
        errors.append("candidate_id mismatch")
    if binding.candidate_hash != record.candidate_hash:
        errors.append("candidate_hash mismatch")
    if binding.geometry_projection_hash != record.geometry_projection_hash:
        errors.append("geometry_projection_hash mismatch")
    return errors


def build_r26g_demonstration_hydraulic_path_input_v1(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
) -> EngineeringHydraulicPathInputV1:
    """Explicit DEMONSTRATION-only path inputs for software chain verification (not owner design)."""
    tube_mass = Decimal(str(case.tube_side.mass_flow_kg_s))
    shell_mass = Decimal(str(case.shell_side.mass_flow_kg_s))
    tube_t = Decimal(str(case.tube_side.inlet_temperature_k))
    tube_p = Decimal(str(case.tube_side.inlet_pressure_pa))
    shell_t = Decimal(str(case.shell_side.inlet_temperature_k))
    shell_p = Decimal(str(case.shell_side.inlet_pressure_pa))
    demo_src = "R26G-DEMONSTRATION-NOT-PRODUCTION-DESIGN"
    tube_density = FluidDensitySourceV1(
        kind="COOLPROP_TP",
        temperature_k=tube_t,
        pressure_pa=tube_p,
    )
    shell_density = FluidDensitySourceV1(
        kind="COOLPROP_TP",
        temperature_k=shell_t,
        pressure_pa=shell_p,
    )
    common_coeff = {
        "loss_coefficient_convention": "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        "coefficient_source_id": "R26G-DEMO-K-SOURCE",
        "coefficient_source_version": "2026-R26G",
        "coefficient_source_location": "Demonstration loss coefficients for full-path software verification only",
        "geometry_evidence_refs": (demo_src,),
        "engineering_input_status": "DEMONSTRATION",
    }
    tube_components = (
        HydraulicPathComponentV1(
            component_id="R26G-DEMO-TUBE-INLET-NOZZLE",
            side="TUBE",
            component_type="NOZZLE",
            reference_plane="TUBE_INLET_NOZZLE_PLANE",
            path_sequence_index=0,
            nozzle_inside_diameter_m=Decimal("0.100"),
            mass_flow_kg_s=tube_mass,
            fluid_density_source=tube_density,
            loss_coefficient=Decimal("0.4"),
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R26G-DEMO-TUBE-CHANNEL-HEAD",
            side="TUBE",
            component_type="CHANNEL_HEAD",
            reference_plane="TUBE_CHANNEL_HEAD_PLANE",
            path_sequence_index=1,
            reference_flow_area_m2=Decimal("0.012"),
            mass_flow_kg_s=tube_mass,
            fluid_density_source=tube_density,
            loss_coefficient=Decimal("0.6"),
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R26G-DEMO-TUBE-BUNDLE-ENTRANCE",
            side="TUBE",
            component_type="ENTRANCE",
            reference_plane="TUBE_BUNDLE_ENTRANCE_PLANE",
            path_sequence_index=2,
            reference_flow_area_m2=Decimal("0.00785"),
            mass_flow_kg_s=tube_mass,
            fluid_density_source=tube_density,
            loss_coefficient=Decimal("0.5"),
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R26G-DEMO-TUBE-BUNDLE-EXIT",
            side="TUBE",
            component_type="EXIT",
            reference_plane="TUBE_BUNDLE_EXIT_PLANE",
            path_sequence_index=3,
            reference_flow_area_m2=Decimal("0.00785"),
            mass_flow_kg_s=tube_mass,
            fluid_density_source=tube_density,
            loss_coefficient=Decimal("1.0"),
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R26G-DEMO-TUBE-OUTLET-NOZZLE",
            side="TUBE",
            component_type="NOZZLE",
            reference_plane="TUBE_OUTLET_NOZZLE_PLANE",
            path_sequence_index=4,
            nozzle_inside_diameter_m=Decimal("0.100"),
            mass_flow_kg_s=tube_mass,
            fluid_density_source=tube_density,
            loss_coefficient=Decimal("0.4"),
            **common_coeff,
        ),
    )
    shell_components = (
        HydraulicPathComponentV1(
            component_id="R26G-DEMO-SHELL-INLET-NOZZLE",
            side="SHELL",
            component_type="SHELL_INLET_NOZZLE",
            reference_plane="SHELL_INLET_NOZZLE_PLANE",
            path_sequence_index=0,
            nozzle_inside_diameter_m=Decimal("0.150"),
            mass_flow_kg_s=shell_mass,
            fluid_density_source=shell_density,
            loss_coefficient=Decimal("0.5"),
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R26G-DEMO-SHELL-INLET-TRANSITION",
            side="SHELL",
            component_type="SHELL_INLET_TRANSITION",
            reference_plane="SHELL_INLET_TRANSITION_PLANE",
            path_sequence_index=1,
            reference_flow_area_m2=Decimal("0.20"),
            mass_flow_kg_s=shell_mass,
            fluid_density_source=shell_density,
            loss_coefficient=Decimal("0.3"),
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R26G-DEMO-SHELL-OUTLET-TRANSITION",
            side="SHELL",
            component_type="SHELL_OUTLET_TRANSITION",
            reference_plane="SHELL_OUTLET_TRANSITION_PLANE",
            path_sequence_index=2,
            reference_flow_area_m2=Decimal("0.20"),
            mass_flow_kg_s=shell_mass,
            fluid_density_source=shell_density,
            loss_coefficient=Decimal("0.3"),
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R26G-DEMO-SHELL-OUTLET-NOZZLE",
            side="SHELL",
            component_type="SHELL_OUTLET_NOZZLE",
            reference_plane="SHELL_OUTLET_NOZZLE_PLANE",
            path_sequence_index=3,
            nozzle_inside_diameter_m=Decimal("0.150"),
            mass_flow_kg_s=shell_mass,
            fluid_density_source=shell_density,
            loss_coefficient=Decimal("0.5"),
            **common_coeff,
        ),
    )
    return EngineeringHydraulicPathInputV1(
        schema_version=SCHEMA_VERSION,
        binding=EngineeringHydraulicPathBindingV1(
            engineering_case_id=str(getattr(case, "engineering_case_id", "")),
            candidate_id=record.candidate_id,
            candidate_hash=record.candidate_hash,
            geometry_projection_hash=record.geometry_projection_hash,
        ),
        path_completeness_declaration="FULL_TUBE_AND_SHELL_EXTERNAL_PATH",
        tube_side_components=tube_components,
        shell_external_components=shell_components,
    )


R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS: dict[str, dict[str, Any]] = {
    "mid_band": {
        "scenario_id": "R27B-ASSUMPTION-K-MID-BAND",
        "source_nature": "CONFIGURABLE_ASSUMPTION_SCENARIO",
        "disclosure": "Mid-band K values for R27B full-path sizing; not owner-verified design data.",
        "tube_nozzle_k": Decimal("0.45"),
        "tube_channel_head_k": Decimal("0.55"),
        "tube_bundle_entrance_k": Decimal("0.5"),
        "tube_bundle_exit_k": Decimal("0.9"),
        "shell_nozzle_k": Decimal("0.5"),
        "shell_transition_k": Decimal("0.35"),
    },
    "low_loss_sensitivity": {
        "scenario_id": "R27B-ASSUMPTION-K-LOW-SENSITIVITY",
        "source_nature": "CONFIGURABLE_ASSUMPTION_SCENARIO",
        "disclosure": "Lower-bound sensitivity scenario for assumption-based K values.",
        "tube_nozzle_k": Decimal("0.35"),
        "tube_channel_head_k": Decimal("0.45"),
        "tube_bundle_entrance_k": Decimal("0.4"),
        "tube_bundle_exit_k": Decimal("0.7"),
        "shell_nozzle_k": Decimal("0.4"),
        "shell_transition_k": Decimal("0.25"),
    },
    "high_loss_sensitivity": {
        "scenario_id": "R27B-ASSUMPTION-K-HIGH-SENSITIVITY",
        "source_nature": "CONFIGURABLE_ASSUMPTION_SCENARIO",
        "disclosure": "Upper-bound sensitivity scenario for assumption-based K values.",
        "tube_nozzle_k": Decimal("0.55"),
        "tube_channel_head_k": Decimal("0.65"),
        "tube_bundle_entrance_k": Decimal("0.6"),
        "tube_bundle_exit_k": Decimal("1.1"),
        "shell_nozzle_k": Decimal("0.6"),
        "shell_transition_k": Decimal("0.45"),
    },
}


def _preliminary_nozzle_mid_inside_diameter_m(
    preliminary_nozzle_sizing: dict[str, Any],
    side_key: Literal["tube_side", "shell_side"],
) -> Decimal:
    side = preliminary_nozzle_sizing["sides"][side_key]
    mid = next(c for c in side["diameter_candidates_m"] if c.get("assumption_label") == "mid_band")
    return Decimal(str(mid["inside_diameter_m"]))


def _assumption_channel_head_area_m2(
    *,
    bundle_parallel_flow_area_m2: Decimal,
    nozzle_inside_diameter_m: Decimal,
) -> Decimal:
    nozzle_area = nozzle_flow_area_m2(nozzle_inside_diameter_m)
    scaled = bundle_parallel_flow_area_m2 * Decimal("1.25")
    return max(scaled, nozzle_area)


def _assumption_shell_transition_area_m2(*, shell_inside_diameter_m: Decimal) -> Decimal:
    shell_cross = Decimal(str(math.pi)) * (shell_inside_diameter_m / Decimal(2)) ** 2
    return (shell_cross * Decimal("0.35")).quantize(Decimal("0.0000000001"))


def build_r27b_assumption_based_hydraulic_path_input_v1(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    preliminary_nozzle_sizing: dict[str, Any],
    loss_scenario_key: str = "mid_band",
) -> EngineeringHydraulicPathInputV1:
    """R27B: preliminary nozzle IDs + candidate bundle areas + configurable assumed K values."""
    scenario = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS.get(loss_scenario_key)
    if scenario is None:
        raise ValueError(f"unknown R27B loss scenario: {loss_scenario_key}")

    tube_mass = Decimal(str(case.tube_side.mass_flow_kg_s))
    shell_mass = Decimal(str(case.shell_side.mass_flow_kg_s))
    tube_density = FluidDensitySourceV1(kind="CASE_SIDE_INLET", fluid_role="TUBE_SIDE")
    shell_density = FluidDensitySourceV1(kind="CASE_SIDE_INLET", fluid_role="SHELL_SIDE")

    tube_nozzle_d = _preliminary_nozzle_mid_inside_diameter_m(
        preliminary_nozzle_sizing, "tube_side"
    )
    shell_nozzle_d = _preliminary_nozzle_mid_inside_diameter_m(
        preliminary_nozzle_sizing, "shell_side"
    )
    if record.task025_total_parallel_flow_area_m2 is None:
        raise ValueError(
            f"candidate {record.candidate_id} missing task025_total_parallel_flow_area_m2"
        )
    bundle_area = Decimal(str(record.task025_total_parallel_flow_area_m2))
    shell_id = Decimal(str(record.shell_inside_diameter_m or "0.56"))
    channel_area = _assumption_channel_head_area_m2(
        bundle_parallel_flow_area_m2=bundle_area,
        nozzle_inside_diameter_m=tube_nozzle_d,
    )
    shell_transition_area = _assumption_shell_transition_area_m2(shell_inside_diameter_m=shell_id)

    coeff_src = str(scenario["scenario_id"])
    common_coeff = {
        "loss_coefficient_convention": "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        "coefficient_source_id": coeff_src,
        "coefficient_source_version": "2026-R27B",
        "coefficient_source_location": (
            "R27B configurable assumption scenario for calculation-first full-path sizing"
        ),
        "geometry_evidence_refs": (
            "R27A-PRELIMINARY-NOZZLE-VELOCITY-BAND",
            record.geometry_projection_hash,
        ),
        "engineering_input_status": "ASSUMPTION_BASED",
    }

    tube_components = (
        HydraulicPathComponentV1(
            component_id="R27B-ASSUMP-TUBE-INLET-NOZZLE",
            side="TUBE",
            component_type="NOZZLE",
            reference_plane="TUBE_INLET_NOZZLE_PLANE",
            path_sequence_index=0,
            nozzle_inside_diameter_m=tube_nozzle_d,
            mass_flow_kg_s=tube_mass,
            fluid_density_source=tube_density,
            loss_coefficient=scenario["tube_nozzle_k"],
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R27B-ASSUMP-TUBE-CHANNEL-HEAD",
            side="TUBE",
            component_type="CHANNEL_HEAD",
            reference_plane="TUBE_CHANNEL_HEAD_PLANE",
            path_sequence_index=1,
            reference_flow_area_m2=channel_area,
            mass_flow_kg_s=tube_mass,
            fluid_density_source=tube_density,
            loss_coefficient=scenario["tube_channel_head_k"],
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R27B-ASSUMP-TUBE-BUNDLE-ENTRANCE",
            side="TUBE",
            component_type="ENTRANCE",
            reference_plane="TUBE_BUNDLE_ENTRANCE_PLANE",
            path_sequence_index=2,
            reference_flow_area_m2=bundle_area,
            mass_flow_kg_s=tube_mass,
            fluid_density_source=tube_density,
            loss_coefficient=scenario["tube_bundle_entrance_k"],
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R27B-ASSUMP-TUBE-BUNDLE-EXIT",
            side="TUBE",
            component_type="EXIT",
            reference_plane="TUBE_BUNDLE_EXIT_PLANE",
            path_sequence_index=3,
            reference_flow_area_m2=bundle_area,
            mass_flow_kg_s=tube_mass,
            fluid_density_source=tube_density,
            loss_coefficient=scenario["tube_bundle_exit_k"],
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R27B-ASSUMP-TUBE-OUTLET-NOZZLE",
            side="TUBE",
            component_type="NOZZLE",
            reference_plane="TUBE_OUTLET_NOZZLE_PLANE",
            path_sequence_index=4,
            nozzle_inside_diameter_m=tube_nozzle_d,
            mass_flow_kg_s=tube_mass,
            fluid_density_source=tube_density,
            loss_coefficient=scenario["tube_nozzle_k"],
            **common_coeff,
        ),
    )
    shell_components = (
        HydraulicPathComponentV1(
            component_id="R27B-ASSUMP-SHELL-INLET-NOZZLE",
            side="SHELL",
            component_type="SHELL_INLET_NOZZLE",
            reference_plane="SHELL_INLET_NOZZLE_PLANE",
            path_sequence_index=0,
            nozzle_inside_diameter_m=shell_nozzle_d,
            mass_flow_kg_s=shell_mass,
            fluid_density_source=shell_density,
            loss_coefficient=scenario["shell_nozzle_k"],
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R27B-ASSUMP-SHELL-INLET-TRANSITION",
            side="SHELL",
            component_type="SHELL_INLET_TRANSITION",
            reference_plane="SHELL_INLET_TRANSITION_PLANE",
            path_sequence_index=1,
            reference_flow_area_m2=shell_transition_area,
            mass_flow_kg_s=shell_mass,
            fluid_density_source=shell_density,
            loss_coefficient=scenario["shell_transition_k"],
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R27B-ASSUMP-SHELL-OUTLET-TRANSITION",
            side="SHELL",
            component_type="SHELL_OUTLET_TRANSITION",
            reference_plane="SHELL_OUTLET_TRANSITION_PLANE",
            path_sequence_index=2,
            reference_flow_area_m2=shell_transition_area,
            mass_flow_kg_s=shell_mass,
            fluid_density_source=shell_density,
            loss_coefficient=scenario["shell_transition_k"],
            **common_coeff,
        ),
        HydraulicPathComponentV1(
            component_id="R27B-ASSUMP-SHELL-OUTLET-NOZZLE",
            side="SHELL",
            component_type="SHELL_OUTLET_NOZZLE",
            reference_plane="SHELL_OUTLET_NOZZLE_PLANE",
            path_sequence_index=3,
            nozzle_inside_diameter_m=shell_nozzle_d,
            mass_flow_kg_s=shell_mass,
            fluid_density_source=shell_density,
            loss_coefficient=scenario["shell_nozzle_k"],
            **common_coeff,
        ),
    )
    return EngineeringHydraulicPathInputV1(
        schema_version=SCHEMA_VERSION,
        binding=EngineeringHydraulicPathBindingV1(
            engineering_case_id=str(getattr(case, "engineering_case_id", "")),
            candidate_id=record.candidate_id,
            candidate_hash=record.candidate_hash,
            geometry_projection_hash=record.geometry_projection_hash,
        ),
        path_completeness_declaration="FULL_TUBE_AND_SHELL_EXTERNAL_PATH",
        tube_side_components=tube_components,
        shell_external_components=shell_components,
    )
