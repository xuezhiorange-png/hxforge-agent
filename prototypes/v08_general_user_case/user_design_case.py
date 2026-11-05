"""Versioned V08 general user design case schema (no mandatory equipment geometry)."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from hexagent.domain.quantities import (
    AbsolutePressure,
    AbsoluteTemperature,
    MassFlow,
    Power,
    PressureDifference,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import (
    _SUPPORTED_EXCHANGER,
    _SUPPORTED_FLUID,
    FluidSideSpec,
    SolverBudgetSpec,
)
from prototypes.v08_general_user_case.envelope import (
    V08_INLET_PRESSURE_MAX_PA,
    V08_INLET_PRESSURE_MIN_PA,
    V08_INLET_TEMPERATURE_MAX_K,
    V08_INLET_TEMPERATURE_MIN_K,
)

GENERAL_USER_DESIGN_CASE_SCHEMA_V1 = "hxforge.general-user-design-case.v1"


def format_engineering_decimal(value: Decimal) -> str:
    """Stable decimal string for hashes and solver handoff (no exponent)."""
    quantized = value.quantize(Decimal("0.000001"))
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


class OptionalDesignEnvelopeConstraints(BaseModel):
    """Optional installation / search bounds for V08-02; not fabricated equipment geometry."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    max_shell_inside_diameter_m: Decimal | None = None
    min_shell_inside_diameter_m: Decimal | None = None
    max_tube_length_m: Decimal | None = None
    min_tube_length_m: Decimal | None = None
    max_overall_length_m: Decimal | None = None
    provenance_note: str = Field(
        default="",
        description="Document why bounds were supplied; no implicit fixture defaults.",
    )

    @field_validator(
        "max_shell_inside_diameter_m",
        "min_shell_inside_diameter_m",
        "max_tube_length_m",
        "min_tube_length_m",
        "max_overall_length_m",
    )
    @classmethod
    def positive_finite_optional_dimension(
        cls, value: Decimal | None, info: ValidationInfo
    ) -> Decimal | None:
        if value is None:
            return None
        if not value.is_finite() or value <= 0:
            raise ValueError(f"{info.field_name} must be a positive finite decimal")
        return value

    @model_validator(mode="after")
    def bounds_consistent(self) -> Self:
        if (
            self.min_shell_inside_diameter_m is not None
            and self.max_shell_inside_diameter_m is not None
            and self.min_shell_inside_diameter_m > self.max_shell_inside_diameter_m
        ):
            raise ValueError("min_shell_inside_diameter_m exceeds max_shell_inside_diameter_m")
        if (
            self.min_tube_length_m is not None
            and self.max_tube_length_m is not None
            and self.min_tube_length_m > self.max_tube_length_m
        ):
            raise ValueError("min_tube_length_m exceeds max_tube_length_m")
        return self


class UserFluidSideInputV1(BaseModel):
    """User-facing side input with explicit units or legacy SI decimal fields."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    fluid: _SUPPORTED_FLUID
    inlet_temperature_k: Decimal | None = None
    inlet_temperature: AbsoluteTemperature | None = None
    inlet_pressure_pa: Decimal | None = None
    inlet_pressure: AbsolutePressure | None = None
    mass_flow_kg_s: Decimal | None = None
    mass_flow: MassFlow | None = None

    @model_validator(mode="after")
    def resolve_and_validate(self) -> Self:
        if self.inlet_temperature is None and self.inlet_temperature_k is None:
            raise ValueError("inlet_temperature or inlet_temperature_k is required")
        if self.inlet_temperature is not None and self.inlet_temperature_k is not None:
            raise ValueError("provide inlet_temperature or inlet_temperature_k, not both")
        if self.inlet_pressure is None and self.inlet_pressure_pa is None:
            raise ValueError("inlet_pressure or inlet_pressure_pa is required")
        if self.inlet_pressure is not None and self.inlet_pressure_pa is not None:
            raise ValueError("provide inlet_pressure or inlet_pressure_pa, not both")
        if self.mass_flow is None and self.mass_flow_kg_s is None:
            raise ValueError("mass_flow or mass_flow_kg_s is required")
        if self.mass_flow is not None and self.mass_flow_kg_s is not None:
            raise ValueError("provide mass_flow or mass_flow_kg_s, not both")
        return self

    def to_fluid_side_spec(self) -> FluidSideSpec:
        temperature_k = (
            Decimal(str(self.inlet_temperature.to_si().value))
            if self.inlet_temperature is not None
            else self.inlet_temperature_k
        )
        pressure_pa = (
            Decimal(str(self.inlet_pressure.to_si().value))
            if self.inlet_pressure is not None
            else self.inlet_pressure_pa
        )
        mass_flow_kg_s = (
            Decimal(str(self.mass_flow.to_si().value))
            if self.mass_flow is not None
            else self.mass_flow_kg_s
        )
        assert temperature_k is not None and pressure_pa is not None and mass_flow_kg_s is not None
        if (
            temperature_k < V08_INLET_TEMPERATURE_MIN_K
            or temperature_k > V08_INLET_TEMPERATURE_MAX_K
        ):
            raise ValueError(
                f"inlet_temperature_k {temperature_k} outside V08 declared envelope "
                f"{V08_INLET_TEMPERATURE_MIN_K}–{V08_INLET_TEMPERATURE_MAX_K} K"
            )
        if pressure_pa < V08_INLET_PRESSURE_MIN_PA or pressure_pa > V08_INLET_PRESSURE_MAX_PA:
            raise ValueError(
                f"inlet_pressure_pa {pressure_pa} outside V08 declared envelope "
                f"{V08_INLET_PRESSURE_MIN_PA}–{V08_INLET_PRESSURE_MAX_PA} Pa"
            )
        return FluidSideSpec(
            fluid=self.fluid,
            inlet_temperature_k=temperature_k,
            inlet_pressure_pa=pressure_pa,
            mass_flow_kg_s=mass_flow_kg_s,
        )


class GeneralUserDesignCaseV1(BaseModel):
    """Immutable V08 user design case; geometry catalog fields are optional bounds only."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    schema_version: Literal["hxforge.general-user-design-case.v1"] = (
        GENERAL_USER_DESIGN_CASE_SCHEMA_V1
    )
    engineering_case_id: str = Field(min_length=3, max_length=128)
    exchanger_type: _SUPPORTED_EXCHANGER
    tube_side: UserFluidSideInputV1
    shell_side: UserFluidSideInputV1
    target_duty_w: Decimal | None = None
    target_heat_duty: Power | None = None
    max_tube_side_pressure_drop_pa: Decimal | None = None
    max_tube_side_pressure_drop: PressureDifference | None = None
    max_shell_side_pressure_drop_pa: Decimal | None = None
    max_shell_side_pressure_drop: PressureDifference | None = None
    design_envelope: OptionalDesignEnvelopeConstraints | None = None
    solver_budget: SolverBudgetSpec = Field(default_factory=SolverBudgetSpec)
    notes: str = ""

    @model_validator(mode="after")
    def resolve_scalar_fields(self) -> Self:
        if self.target_heat_duty is None and self.target_duty_w is None:
            raise ValueError("target_heat_duty or target_duty_w is required")
        if self.target_heat_duty is not None and self.target_duty_w is not None:
            raise ValueError("provide target_heat_duty or target_duty_w, not both")
        for tube_field, legacy_field, label in (
            (
                self.max_tube_side_pressure_drop,
                self.max_tube_side_pressure_drop_pa,
                "max_tube_side",
            ),
            (
                self.max_shell_side_pressure_drop,
                self.max_shell_side_pressure_drop_pa,
                "max_shell_side",
            ),
        ):
            if tube_field is not None and legacy_field is not None:
                raise ValueError(f"provide one {label} pressure drop representation only")
        if self.max_tube_side_pressure_drop_pa is None and self.max_tube_side_pressure_drop is None:
            raise ValueError(
                "max_tube_side_pressure_drop or max_tube_side_pressure_drop_pa is required"
            )
        if (
            self.max_shell_side_pressure_drop_pa is None
            and self.max_shell_side_pressure_drop is None
        ):
            raise ValueError(
                "max_shell_side_pressure_drop or max_shell_side_pressure_drop_pa is required"
            )
        if (
            self.tube_side.to_fluid_side_spec().inlet_temperature_k
            <= self.shell_side.to_fluid_side_spec().inlet_temperature_k
        ):
            raise ValueError(
                "tube_side inlet temperature must exceed shell_side inlet temperature "
                "(TUBE_HOT_SHELL_COLD equipment convention)"
            )
        return self

    def normalized_target_duty_w(self) -> Decimal:
        if self.target_heat_duty is not None:
            duty = Decimal(str(self.target_heat_duty.to_si().value)).normalize()
        else:
            duty = self.target_duty_w
        assert duty is not None
        if not duty.is_finite() or duty <= 0:
            raise ValueError("target duty must be positive and finite")
        return duty

    def normalized_max_tube_side_pressure_drop_pa(self) -> Decimal:
        if self.max_tube_side_pressure_drop is not None:
            dp = Decimal(str(self.max_tube_side_pressure_drop.to_si().value))
        else:
            dp = self.max_tube_side_pressure_drop_pa
        assert dp is not None
        if not dp.is_finite() or dp <= 0:
            raise ValueError("max_tube_side_pressure_drop must be positive and finite")
        return dp

    def normalized_max_shell_side_pressure_drop_pa(self) -> Decimal:
        if self.max_shell_side_pressure_drop is not None:
            dp = Decimal(str(self.max_shell_side_pressure_drop.to_si().value))
        else:
            dp = self.max_shell_side_pressure_drop_pa
        assert dp is not None
        if not dp.is_finite() or dp <= 0:
            raise ValueError("max_shell_side_pressure_drop must be positive and finite")
        return dp

    def normalized_fluid_sides(self) -> tuple[FluidSideSpec, FluidSideSpec]:
        return self.tube_side.to_fluid_side_spec(), self.shell_side.to_fluid_side_spec()


class NormalizedUserDesignCase(BaseModel):
    """Canonical SI snapshot consumed by validation and solver handoff."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    schema_version: str = GENERAL_USER_DESIGN_CASE_SCHEMA_V1
    engineering_case_id: str
    exchanger_type: _SUPPORTED_EXCHANGER
    tube_side: FluidSideSpec
    shell_side: FluidSideSpec
    target_duty_w: Decimal
    max_tube_side_pressure_drop_pa: Decimal
    max_shell_side_pressure_drop_pa: Decimal
    design_envelope: OptionalDesignEnvelopeConstraints | None
    solver_budget: SolverBudgetSpec
    notes: str

    @classmethod
    def from_user_case(cls, case: GeneralUserDesignCaseV1) -> NormalizedUserDesignCase:
        tube, shell = case.normalized_fluid_sides()
        return cls(
            engineering_case_id=case.engineering_case_id,
            exchanger_type=case.exchanger_type,
            tube_side=tube,
            shell_side=shell,
            target_duty_w=case.normalized_target_duty_w(),
            max_tube_side_pressure_drop_pa=case.normalized_max_tube_side_pressure_drop_pa(),
            max_shell_side_pressure_drop_pa=case.normalized_max_shell_side_pressure_drop_pa(),
            design_envelope=case.design_envelope,
            solver_budget=case.solver_budget,
            notes=case.notes,
        )

    def input_snapshot_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "engineering_case_id": self.engineering_case_id,
            "exchanger_type": self.exchanger_type,
            "tube_side": self.tube_side.model_dump(mode="json"),
            "shell_side": self.shell_side.model_dump(mode="json"),
            "target_duty_w": format_engineering_decimal(self.target_duty_w),
            "max_tube_side_pressure_drop_pa": format_engineering_decimal(
                self.max_tube_side_pressure_drop_pa
            ),
            "max_shell_side_pressure_drop_pa": format_engineering_decimal(
                self.max_shell_side_pressure_drop_pa
            ),
            "solver_budget": self.solver_budget.model_dump(mode="json"),
            "notes": self.notes,
        }
        if self.design_envelope is not None:
            payload["design_envelope"] = self.design_envelope.model_dump(mode="json")
        return payload
