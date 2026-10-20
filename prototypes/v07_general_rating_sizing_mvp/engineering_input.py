"""Versioned general engineering input for experimental rating + sizing MVP."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GENERAL_ENGINEERING_CASE_SCHEMA = "hxforge.general-engineering-case.v1"

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
            "hot_side_role": "HEAT_SOURCE_SHELL_SIDE",
            "cold_side_role": "HEAT_SINK_TUBE_SIDE",
            "target_duty_sign": "POSITIVE_WHEN_HEAT_FLOWS_HOT_TO_COLD",
            "duty_unit": "W",
            "temperature_unit": "K",
            "mass_flow_unit": "kg_s",
            "pressure_unit": "Pa_absolute",
            "energy_balance": "Q_hot_release_equals_Q_cold_absorption_steady_state",
        }

    def physical_consistency_status(self) -> tuple[str, str | None]:
        """Basic feasibility checks without mutating the stored case JSON."""
        if self.hot_side.inlet_temperature_k <= self.cold_side.inlet_temperature_k:
            return (
                "BLOCKED",
                "hot_side.inlet_temperature_k must exceed cold_side.inlet_temperature_k "
                "for positive target_duty_w (hot fluid heats cold fluid)",
            )
        cp_water = Decimal("4180")
        hot_cap = cp_water * self.hot_side.mass_flow_kg_s
        cold_cap = cp_water * self.cold_side.mass_flow_kg_s
        max_hot_drop = hot_cap * (self.hot_side.inlet_temperature_k - Decimal("298.15"))
        max_cold_rise = cold_cap * (Decimal("300.00") - self.cold_side.inlet_temperature_k)
        max_duty = min(max_hot_drop, max_cold_rise)
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
