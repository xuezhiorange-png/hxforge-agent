from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class PhaseHint(str, Enum):
    AUTO = "auto"
    LIQUID = "liquid"
    GAS = "gas"
    TWO_PHASE = "two_phase"


class Quantity(BaseModel):
    value: float
    unit: str


class FluidSpec(BaseModel):
    backend: str = "CoolProp"
    name: str
    composition: dict[str, float] | None = None
    phase_hint: PhaseHint = PhaseHint.AUTO


class StreamSpec(BaseModel):
    fluid: FluidSpec
    mass_flow: Quantity
    inlet_temperature: Quantity
    inlet_pressure: Quantity
    outlet_temperature: Quantity | None = None
    allowable_pressure_drop: Quantity | None = None
    fouling_resistance: Quantity = Field(
        default_factory=lambda: Quantity(value=0.0, unit="m^2*K/W")
    )


class DesignConstraints(BaseModel):
    design_pressure_hot: Quantity
    design_pressure_cold: Quantity
    design_temperature_hot: Quantity
    design_temperature_cold: Quantity
    corrosion_allowance: Quantity = Field(
        default_factory=lambda: Quantity(value=0.0, unit="mm")
    )
    required_area_margin_fraction: float = Field(default=0.10, ge=0.0, le=1.0)


class DesignCase(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    hot_stream: StreamSpec
    cold_stream: StreamSpec
    constraints: DesignConstraints
    target_duty: Quantity | None = None

    @model_validator(mode="after")
    def check_thermal_specification(self) -> "DesignCase":
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
