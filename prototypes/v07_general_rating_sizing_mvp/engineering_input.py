"""Versioned general engineering input for experimental rating + sizing MVP."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GENERAL_ENGINEERING_CASE_SCHEMA = "hxforge.general-engineering-case.v1"
GENERAL_ENGINEERING_CASE_SCHEMA_V2 = "hxforge.general-engineering-case.v2"

_SUPPORTED_FLUID = Literal["PURE_ORDINARY_WATER"]
_SUPPORTED_EXCHANGER = Literal["SHELL_AND_TUBE_FIXED_TUBESHEET_SINGLE_PHASE"]


class FluidSideSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    fluid: _SUPPORTED_FLUID
    inlet_temperature_k: Decimal
    inlet_pressure_pa: Decimal
    mass_flow_kg_s: Decimal

    @field_validator("inlet_temperature_k", "inlet_pressure_pa", "mass_flow_kg_s")
    @classmethod
    def positive_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("fluid side values must be positive finite decimals")
        return value


class CandidateGenerationConstraints(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    shell_inside_diameter_m: Decimal
    tube_outer_diameter_m: Decimal
    tube_wall_thickness_m: Decimal
    tube_pitch_m: Decimal
    tube_lengths_m: tuple[Decimal, ...] = Field(min_length=1, max_length=8)
    baffle_spacings_m: tuple[Decimal, ...] = Field(min_length=1, max_length=8)
    baffle_count: int = Field(ge=2, le=32)
    tube_pass_count: int = Field(default=1, ge=1, le=2)
    shell_inside_diameters_m: tuple[Decimal, ...] = Field(default_factory=tuple, max_length=4)

    @field_validator("shell_inside_diameters_m")
    @classmethod
    def shell_diameter_list_positive(cls, values: tuple[Decimal, ...]) -> tuple[Decimal, ...]:
        for value in values:
            if not value.is_finite() or value <= 0:
                raise ValueError("shell_inside_diameters_m entries must be positive")
        return values

    @field_validator(
        "shell_inside_diameter_m",
        "tube_outer_diameter_m",
        "tube_wall_thickness_m",
        "tube_pitch_m",
    )
    @classmethod
    def positive_geometry(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("geometry must be positive")
        return value


class BaselineGeometryPair(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    tube_length_m: Decimal
    baffle_spacing_m: Decimal
    shell_inside_diameter_m: Decimal | None = None
    physical_tube_count: int | None = None


class SolverBudgetSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    total_budget_s: float = Field(default=3600.0, gt=0, le=7200.0)
    max_candidates_to_rate: int = Field(default=3, ge=1, le=8)
    enable_full_task173_rating: bool = True


class PhysicalConsistencyError(ValueError):
    """Raised when design temperatures/duty violate basic heat-transfer feasibility."""


class GeneralEngineeringCaseV1(BaseModel):
    """Experimental case input; maps to reviewed Task173 service envelope when in scope."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    schema_version: Literal["hxforge.general-engineering-case.v1"] = GENERAL_ENGINEERING_CASE_SCHEMA
    engineering_case_id: str = Field(min_length=3, max_length=128)
    exchanger_type: _SUPPORTED_EXCHANGER
    cold_side: FluidSideSpec
    hot_side: FluidSideSpec
    bind_task172_c3_reference_geometry: bool = Field(
        default=False,
        description=(
            "When true, bind candidate enumeration to the C3-qualified implementation-validation "
            "reference geometry (Task025 parallel area / Reynolds envelope), not arbitrary layout."
        ),
    )
    target_duty_w: Decimal
    max_tube_side_pressure_drop_pa: Decimal
    max_shell_side_pressure_drop_pa: Decimal
    candidate_constraints: CandidateGenerationConstraints
    solver_budget: SolverBudgetSpec = Field(default_factory=SolverBudgetSpec)
    notes: str = ""

    @field_validator(
        "target_duty_w",
        "max_tube_side_pressure_drop_pa",
        "max_shell_side_pressure_drop_pa",
    )
    @classmethod
    def positive_targets(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("targets must be positive finite decimals")
        return value

    @model_validator(mode="after")
    def applicability_envelope(self) -> GeneralEngineeringCaseV1:
        """Fail closed outside the water–water single-phase envelope wired to Task173 R2."""
        if self.exchanger_type != "SHELL_AND_TUBE_FIXED_TUBESHEET_SINGLE_PHASE":
            raise ValueError("unsupported exchanger_type for MVP")
        for side in (self.cold_side, self.hot_side):
            if side.fluid != "PURE_ORDINARY_WATER":
                raise ValueError("MVP supports PURE_ORDINARY_WATER only")
        if self.cold_side.mass_flow_kg_s != Decimal("12.000000"):
            raise ValueError(
                "cold_side mass_flow_kg_s must be 12.000000 kg/s for current Task173 service binding"
            )
        if self.hot_side.mass_flow_kg_s != Decimal("20.000000"):
            raise ValueError(
                "hot_side mass_flow_kg_s must be 20.000000 kg/s for current Task173 service binding"
            )
        lo = Decimal("298.15")
        hi = Decimal("300.00")
        for side in (self.cold_side, self.hot_side):
            if side.inlet_temperature_k < lo or side.inlet_temperature_k > hi:
                raise ValueError(
                    "inlet temperatures must stay within 298.15–300.00 K service envelope"
                )
            if side.inlet_pressure_pa < Decimal("100000") or side.inlet_pressure_pa > Decimal(
                "101325"
            ):
                raise ValueError(
                    "inlet pressure must stay within 100000–101325 Pa service envelope"
                )
        if self.candidate_constraints.tube_pass_count != 1:
            raise ValueError("v0.7 sizing supports tube_pass_count=1 only")
        return self

    def heat_transfer_convention(self) -> dict[str, str]:
        """Document side identities and SI energy convention for reports."""
        return {
            "kernel_thermal_variant": "TUBE_HOT_SHELL_COLD",
            "tube_stream_field": "cold_side",
            "shell_stream_field": "hot_side",
            "tube_mass_flow_kg_s": "12.000000",
            "shell_mass_flow_kg_s": "20.000000",
            "kernel_tube_inlet_temperature_k": "300.00",
            "kernel_shell_inlet_temperature_k": "298.15",
            "target_duty_sign": "POSITIVE_WHEN_HEAT_FLOWS_TUBE_TO_SHELL",
            "duty_unit": "W",
            "temperature_unit": "K",
            "mass_flow_unit": "kg_s",
            "pressure_unit": "Pa_absolute",
            "energy_balance": "Q_tube_release_equals_Q_shell_absorption_steady_state",
        }

    def physical_consistency_status(self) -> tuple[str, str | None]:
        """Basic feasibility checks without mutating the stored case JSON."""
        if self.cold_side.inlet_temperature_k <= self.hot_side.inlet_temperature_k:
            return (
                "BLOCKED",
                "cold_side.inlet_temperature_k must exceed hot_side.inlet_temperature_k "
                "for TUBE_HOT_SHELL_COLD (tube is the hotter stream)",
            )
        cp_water = Decimal("4180")
        tube_cap = cp_water * self.cold_side.mass_flow_kg_s
        shell_cap = cp_water * self.hot_side.mass_flow_kg_s
        max_tube_drop = tube_cap * (self.cold_side.inlet_temperature_k - Decimal("298.15"))
        max_shell_rise = shell_cap * (Decimal("300.00") - self.hot_side.inlet_temperature_k)
        max_duty = min(max_tube_drop, max_shell_rise)
        if self.target_duty_w > max_duty * Decimal("1.05"):
            return (
                "BLOCKED",
                f"target_duty_w {self.target_duty_w} W exceeds coarse envelope cap {max_duty} W",
            )
        return "VALID", None

    def applicability_status(self) -> tuple[str, str | None]:
        try:
            self.model_validate(self.model_dump())
        except Exception as exc:
            return "BLOCKED", str(exc)
        physical, detail = self.physical_consistency_status()
        if physical == "BLOCKED":
            return "BLOCKED", detail
        return "IN_SCOPE", None


class GeneralEngineeringCaseV2(BaseModel):
    """R4+ case input: equipment sides (tube/shell) separate from thermal roles (hot/cold)."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    schema_version: Literal["hxforge.general-engineering-case.v2"] = (
        GENERAL_ENGINEERING_CASE_SCHEMA_V2
    )
    engineering_case_id: str = Field(min_length=3, max_length=128)
    exchanger_type: _SUPPORTED_EXCHANGER
    tube_side: FluidSideSpec
    shell_side: FluidSideSpec
    bind_task172_c3_reference_geometry: bool = Field(default=False)
    target_duty_w: Decimal
    max_tube_side_pressure_drop_pa: Decimal
    max_shell_side_pressure_drop_pa: Decimal
    candidate_constraints: CandidateGenerationConstraints
    solver_budget: SolverBudgetSpec = Field(default_factory=SolverBudgetSpec)
    experimental_sizing_objective: Literal[
        "PARETO_ONLY",
        "MIN_NOMINAL_TUBE_AREA",
        "MAX_DUTY",
        "MIN_SHELL_DP_PREVIEW",
    ] = "PARETO_ONLY"
    experimental_candidate_selection_mode: Literal[
        "FIRST_N_DISTINCT_GEOMETRY",
        "MIN_NOMINAL_TUBE_AREA_SEARCH",
        "VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13",
    ] = "FIRST_N_DISTINCT_GEOMETRY"
    experimental_bundle_geometry_mode: Literal[
        "FIXED",
        "VARIABLE_SHELL_DIAMETER_R13",
    ] = "FIXED"
    experimental_live_thermal_hydraulic_postpass: bool = False
    experimental_transitional_tube_hydraulic: bool = Field(
        default=False,
        description=(
            "Opt-in Churchill (1977) transitional tube friction for live post-pass when frozen "
            "Task027 blocks 2000<Re<4000. Does not alter Task027/Task029 production paths."
        ),
    )
    experimental_engineering_tube_local_loss: bool = Field(
        default=False,
        description=(
            "When true, Task028 local-loss component authorities come from tube_local_loss_engineering "
            "instead of the Task168 historical template."
        ),
    )
    tube_local_loss_engineering: object | None = Field(
        default=None,
        description="R21 engineering tube local-loss component specification (see engineering_tube_local_loss_geometry).",
    )
    experimental_live_variable_tube_mass_flow: bool = Field(
        default=False,
        description=(
            "When true, tube_side.mass_flow_kg_s participates in experimental live Task173 "
            "enthalpy propagation and Task172 local requests."
        ),
    )
    experimental_live_variable_shell_mass_flow: bool = Field(
        default=False,
        description=(
            "When true, shell_side.mass_flow_kg_s participates in experimental live Task173 "
            "enthalpy propagation, Task172 local requests, and live Task032/Task166 post-pass."
        ),
    )
    experimental_two_way_bulk_pressure_feedback: bool = Field(
        default=False,
        description=(
            "When true, iterate Task173 rating with side-specific bulk property pressures "
            "P_bulk=(P_inlet+P_outlet)/2 from live hydraulic post-pass (experimental only)."
        ),
    )
    experimental_variable_water_temperature: bool = Field(
        default=False,
        description=(
            "When true, tube/shell inlet temperatures from the case (290–320 K envelope) "
            "drive CoolProp, Task173 mesh, and Task172 local properties (experimental only)."
        ),
    )
    r10_baseline_geometry_pairs: tuple[BaselineGeometryPair, ...] = ()
    r12_baseline_geometry_fingerprints: tuple[BaselineGeometryPair, ...] = ()
    notes: str = ""

    @field_validator(
        "target_duty_w",
        "max_tube_side_pressure_drop_pa",
        "max_shell_side_pressure_drop_pa",
    )
    @classmethod
    def positive_targets(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("targets must be positive finite decimals")
        return value

    @model_validator(mode="after")
    def applicability_envelope(self) -> GeneralEngineeringCaseV2:
        if self.exchanger_type != "SHELL_AND_TUBE_FIXED_TUBESHEET_SINGLE_PHASE":
            raise ValueError("unsupported exchanger_type for MVP")
        for side in (self.tube_side, self.shell_side):
            if side.fluid != "PURE_ORDINARY_WATER":
                raise ValueError("MVP supports PURE_ORDINARY_WATER only")
        if self.experimental_live_variable_tube_mass_flow:
            from prototypes.v07_general_rating_sizing_mvp.variable_tube_mass_flow import (
                validate_variable_tube_mass_flow_kg_s,
            )

            validate_variable_tube_mass_flow_kg_s(self.tube_side.mass_flow_kg_s)
        elif self.tube_side.mass_flow_kg_s != Decimal("12.000000"):
            raise ValueError("tube_side mass_flow_kg_s must be 12.000000 kg/s for Task173 binding")
        if self.experimental_live_variable_shell_mass_flow:
            from prototypes.v07_general_rating_sizing_mvp.variable_shell_mass_flow import (
                validate_variable_shell_mass_flow_kg_s,
            )

            validate_variable_shell_mass_flow_kg_s(self.shell_side.mass_flow_kg_s)
        elif self.shell_side.mass_flow_kg_s != Decimal("20.000000"):
            raise ValueError("shell_side mass_flow_kg_s must be 20.000000 kg/s for Task173 binding")
        if self.tube_side.inlet_temperature_k <= self.shell_side.inlet_temperature_k:
            raise ValueError(
                "tube_side.inlet_temperature_k must exceed shell_side.inlet_temperature_k "
                "(hot fluid on tube, cold fluid on shell)"
            )
        if self.experimental_variable_water_temperature:
            from prototypes.v07_general_rating_sizing_mvp.variable_water_temperature import (
                validate_case_variable_water_temperature,
            )

            validate_case_variable_water_temperature(self)
        else:
            lo = Decimal("298.15")
            hi = Decimal("300.00")
            for side in (self.tube_side, self.shell_side):
                if side.inlet_temperature_k < lo or side.inlet_temperature_k > hi:
                    raise ValueError(
                        "inlet temperatures must stay within 298.15–300.00 K service envelope"
                    )
        for label, side in (
            ("tube_side", self.tube_side),
            ("shell_side", self.shell_side),
        ):
            if side.inlet_pressure_pa < Decimal("100000") or side.inlet_pressure_pa > Decimal(
                "101325"
            ):
                raise ValueError(
                    f"{label} inlet pressure must stay within 100000–101325 Pa service envelope"
                )
        if self.candidate_constraints.tube_pass_count != 1:
            raise ValueError("v0.7 sizing supports tube_pass_count=1 only")
        if (
            self.experimental_transitional_tube_hydraulic
            and not self.experimental_live_thermal_hydraulic_postpass
        ):
            raise ValueError(
                "experimental_transitional_tube_hydraulic requires "
                "experimental_live_thermal_hydraulic_postpass=true"
            )
        if self.experimental_engineering_tube_local_loss:
            if not self.experimental_live_thermal_hydraulic_postpass:
                raise ValueError(
                    "experimental_engineering_tube_local_loss requires "
                    "experimental_live_thermal_hydraulic_postpass=true"
                )
            if not self.experimental_transitional_tube_hydraulic:
                raise ValueError(
                    "experimental_engineering_tube_local_loss requires "
                    "experimental_transitional_tube_hydraulic=true"
                )
            if self.tube_local_loss_engineering is None:
                raise ValueError(
                    "tube_local_loss_engineering is required when "
                    "experimental_engineering_tube_local_loss is true"
                )
            from prototypes.v07_general_rating_sizing_mvp.engineering_tube_local_loss_geometry import (
                TubeLocalLossEngineeringInput,
            )

            if not isinstance(self.tube_local_loss_engineering, TubeLocalLossEngineeringInput):
                TubeLocalLossEngineeringInput.model_validate(self.tube_local_loss_engineering)
        if self.experimental_two_way_bulk_pressure_feedback and not (
            self.experimental_live_thermal_hydraulic_postpass
        ):
            raise ValueError(
                "experimental_two_way_bulk_pressure_feedback requires "
                "experimental_live_thermal_hydraulic_postpass=true"
            )
        if self.experimental_variable_water_temperature and not (
            self.experimental_live_thermal_hydraulic_postpass
        ):
            raise ValueError(
                "experimental_variable_water_temperature requires "
                "experimental_live_thermal_hydraulic_postpass=true"
            )
        return self

    def heat_transfer_convention(self) -> dict[str, str]:
        return {
            "kernel_thermal_variant": "TUBE_HOT_SHELL_COLD",
            "tube_equipment_side": "tube_side",
            "shell_equipment_side": "shell_side",
            "tube_thermal_role": "HOT",
            "shell_thermal_role": "COLD",
            "tube_mass_flow_kg_s": (
                str(self.tube_side.mass_flow_kg_s)
                if self.experimental_live_variable_tube_mass_flow
                else "12.000000"
            ),
            "shell_mass_flow_kg_s": (
                str(self.shell_side.mass_flow_kg_s)
                if self.experimental_live_variable_shell_mass_flow
                else "20.000000"
            ),
            "kernel_tube_inlet_temperature_k": "300.00",
            "kernel_shell_inlet_temperature_k": "298.15",
            "user_tube_inlet_temperature_k": str(self.tube_side.inlet_temperature_k),
            "user_shell_inlet_temperature_k": str(self.shell_side.inlet_temperature_k),
            "target_duty_sign": "POSITIVE_WHEN_HEAT_FLOWS_TUBE_TO_SHELL",
        }

    def physical_consistency_status(self) -> tuple[str, str | None]:
        cp_water = Decimal("4180")
        tube_cap = cp_water * self.tube_side.mass_flow_kg_s
        shell_cap = cp_water * self.shell_side.mass_flow_kg_s
        max_tube_drop = tube_cap * (self.tube_side.inlet_temperature_k - Decimal("298.15"))
        max_shell_rise = shell_cap * (Decimal("300.00") - self.shell_side.inlet_temperature_k)
        max_duty = min(max_tube_drop, max_shell_rise)
        if self.target_duty_w > max_duty * Decimal("1.05"):
            return (
                "BLOCKED",
                f"target_duty_w {self.target_duty_w} W exceeds coarse envelope cap {max_duty} W",
            )
        return "VALID", None

    def applicability_status(self) -> tuple[str, str | None]:
        try:
            self.model_validate(self.model_dump())
        except Exception as exc:
            return "BLOCKED", str(exc)
        physical, detail = self.physical_consistency_status()
        if physical == "BLOCKED":
            return "BLOCKED", detail
        return "IN_SCOPE", None
