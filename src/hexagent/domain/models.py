from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Discriminator, Field, model_validator

from hexagent.domain.quantities import (
    AbsolutePressure,
    AbsoluteTemperature,
    FoulingResistance,
    Length,
    MassFlow,
    Power,
    PressureDifference,
    Quantity,
    SpecificEnthalpy,
)

# ---------------------------------------------------------------------------
# ITEM 4: Strict public input base model
# ---------------------------------------------------------------------------

class StrictBaseModel(BaseModel):
    """Base model that rejects any unknown fields at construction time."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PhaseHint(StrEnum):
    AUTO = "auto"
    LIQUID = "liquid"
    GAS = "gas"
    TWO_PHASE = "two_phase"


class FoulingSourceType(StrEnum):
    STANDARD = "STANDARD"
    VENDOR = "VENDOR"
    USER = "USER"
    ASSUMED = "ASSUMED"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED_REFERENCE = "UNVERIFIED_REFERENCE"


# ---------------------------------------------------------------------------
# ITEM 4: FluidSpec → StrictBaseModel
# ---------------------------------------------------------------------------

class FluidSpec(StrictBaseModel):
    backend: str = "CoolProp"
    name: str
    composition: dict[str, float] | None = None
    phase_hint: PhaseHint = PhaseHint.AUTO


# ---------------------------------------------------------------------------
# ITEM 1: State-spec discriminated union
# ---------------------------------------------------------------------------

class TPStateSpec(StrictBaseModel):
    """Temperature–pressure state specification."""

    type: Literal["TP"]
    temperature: AbsoluteTemperature
    pressure: AbsolutePressure
    schema_version: str = "1.0"


class PHStateSpec(StrictBaseModel):
    """Pressure–enthalpy state specification."""

    type: Literal["PH"]
    pressure: AbsolutePressure
    enthalpy: SpecificEnthalpy
    schema_version: str = "1.0"


class PQStateSpec(StrictBaseModel):
    """Pressure–quality state specification."""

    type: Literal["PQ"]
    pressure: AbsolutePressure
    quality: float = Field(ge=0, le=1)
    schema_version: str = "1.0"


StateSpec = Annotated[
    TPStateSpec | PHStateSpec | PQStateSpec, Discriminator("type")
]


# ---------------------------------------------------------------------------
# ITEM 2: Structured fouling resistance
# ---------------------------------------------------------------------------

class FoulingSource(StrictBaseModel):
    """Traceable origin of a fouling-resistance value."""

    source_type: FoulingSourceType
    reference_id: str
    edition: str
    table_or_clause: str
    verification_status: VerificationStatus
    note: str


class FoulingResistanceSpec(StrictBaseModel):
    """Structured fouling resistance with provenance."""

    value: FoulingResistance
    source: FoulingSource


# ---------------------------------------------------------------------------
# StreamSpec (modified with state_spec + fouling_resistance_spec)
# ---------------------------------------------------------------------------

class StreamSpec(StrictBaseModel):
    fluid: FluidSpec
    mass_flow: MassFlow
    # Legacy fields kept Optional for backward compatibility
    inlet_temperature: AbsoluteTemperature | None = None
    inlet_pressure: AbsolutePressure | None = None
    # New structured state specification
    state_spec: StateSpec | None = None
    outlet_temperature: AbsoluteTemperature | None = None
    allowable_pressure_drop: PressureDifference | None = None
    # Legacy fouling field kept Optional for backward compatibility
    fouling_resistance: FoulingResistance | None = None
    # New structured fouling specification
    fouling_resistance_spec: FoulingResistanceSpec | None = None

    @model_validator(mode="after")
    def _check_state_specification(self) -> StreamSpec:
        has_state = self.state_spec is not None
        has_legacy_temp = self.inlet_temperature is not None
        has_legacy_pres = self.inlet_pressure is not None
        if has_state and (has_legacy_temp or has_legacy_pres):
            raise ValueError(
                "Cannot provide both state_spec and legacy "
                "inlet_temperature/inlet_pressure."
            )
        if not has_state and not (has_legacy_temp and has_legacy_pres):
            raise ValueError(
                "Must provide either state_spec or both "
                "inlet_temperature and inlet_pressure."
            )
        return self

    @model_validator(mode="after")
    def _check_fouling_specification(self) -> StreamSpec:
        has_spec = self.fouling_resistance_spec is not None
        has_legacy = self.fouling_resistance is not None
        if has_spec and has_legacy:
            raise ValueError(
                "Cannot provide both fouling_resistance_spec and "
                "legacy fouling_resistance."
            )
        if not has_spec and not has_legacy:
            raise ValueError(
                "Must provide either fouling_resistance_spec or "
                "fouling_resistance."
            )
        return self


# ---------------------------------------------------------------------------
# Design constraints and design case
# ---------------------------------------------------------------------------

class DesignConstraints(StrictBaseModel):
    design_pressure_hot: AbsolutePressure
    design_pressure_cold: AbsolutePressure
    design_temperature_hot: AbsoluteTemperature
    design_temperature_cold: AbsoluteTemperature
    corrosion_allowance: Length | None = None
    required_area_margin_fraction: float = Field(ge=0.0, le=1.0)


class DesignCase(StrictBaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    hot_stream: StreamSpec
    cold_stream: StreamSpec
    constraints: DesignConstraints
    target_duty: Power | None = None

    @model_validator(mode="after")
    def check_thermal_specification(self) -> DesignCase:
        known_outlets = sum(
            x is not None
            for x in (self.hot_stream.outlet_temperature, self.cold_stream.outlet_temperature)
        )
        if self.target_duty is None and known_outlets == 0:
            raise ValueError(
                "Provide target_duty or at least one stream outlet temperature."
            )
        return self


# ---------------------------------------------------------------------------
# Result / provenance models (remain plain BaseModel — not public input)
# ---------------------------------------------------------------------------

class WarningMessage(BaseModel):
    code: str
    severity: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class ProvenanceRecord(BaseModel):
    formula_id: str
    formula_version: str
    source_reference: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    applicability_status: str


class CalculationResult(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    status: str
    outputs: dict[str, Any]
    warnings: list[WarningMessage] = Field(default_factory=list)
    provenance: list[ProvenanceRecord] = Field(default_factory=list)


__all__ = [
    "AbsolutePressure",
    "AbsoluteTemperature",
    "CalculationResult",
    "DesignCase",
    "DesignConstraints",
    "FluidSpec",
    "FoulingResistance",
    "FoulingResistanceSpec",
    "FoulingSource",
    "FoulingSourceType",
    "Length",
    "MassFlow",
    "PhaseHint",
    "PHStateSpec",
    "Power",
    "PQStateSpec",
    "PressureDifference",
    "ProvenanceRecord",
    "Quantity",
    "StateSpec",
    "StreamSpec",
    "StrictBaseModel",
    "TPStateSpec",
    "VerificationStatus",
    "WarningMessage",
]
