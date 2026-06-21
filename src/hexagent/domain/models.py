from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from hexagent.domain.quantities import (
    AbsolutePressure,
    AbsoluteTemperature,
    FoulingResistance,
    Length,
    MassFlow,
    Power,
    PressureDifference,
    Quantity,
)


class PhaseHint(StrEnum):
    AUTO = "auto"
    LIQUID = "liquid"
    GAS = "gas"
    TWO_PHASE = "two_phase"


class FluidSpec(BaseModel):
    backend: str = "CoolProp"
    name: str
    composition: dict[str, float] | None = None
    phase_hint: PhaseHint = PhaseHint.AUTO


class StreamSpec(BaseModel):
    fluid: FluidSpec
    mass_flow: MassFlow
    inlet_temperature: AbsoluteTemperature
    inlet_pressure: AbsolutePressure
    outlet_temperature: AbsoluteTemperature | None = None
    allowable_pressure_drop: PressureDifference | None = None
    fouling_resistance: FoulingResistance


class DesignConstraints(BaseModel):
    design_pressure_hot: AbsolutePressure
    design_pressure_cold: AbsolutePressure
    design_temperature_hot: AbsoluteTemperature
    design_temperature_cold: AbsoluteTemperature
    corrosion_allowance: Length | None = None
    required_area_margin_fraction: float = Field(ge=0.0, le=1.0)


class DesignCase(BaseModel):
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
    "Length",
    "MassFlow",
    "PhaseHint",
    "Power",
    "PressureDifference",
    "ProvenanceRecord",
    "Quantity",
    "StreamSpec",
    "WarningMessage",
]
