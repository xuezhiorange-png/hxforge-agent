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
from hexagent.properties.base import ReferenceStatePolicy


class StrictBaseModel(BaseModel):
    """Base model that rejects any unknown fields at construction time."""

    model_config = ConfigDict(extra="forbid")


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


class FluidSpec(StrictBaseModel):
    backend: str
    name: str
    composition: dict[str, float] | None = None
    phase_hint: PhaseHint = PhaseHint.AUTO


class TPStateSpec(StrictBaseModel):
    """Temperature-pressure state specification."""

    type: Literal["TP"]
    temperature: AbsoluteTemperature
    pressure: AbsolutePressure
    schema_version: Literal["1.0"] = "1.0"


class PHStateSpec(StrictBaseModel):
    """Pressure-enthalpy state specification.

    ``reference_state`` is required to ensure the caller explicitly
    declares the enthalpy reference convention.  Omitting it produces
    a structured validation error, not a runtime TypeError.
    """

    type: Literal["PH"]
    pressure: AbsolutePressure
    enthalpy: SpecificEnthalpy
    reference_state: ReferenceStatePolicy
    schema_version: Literal["1.0"] = "1.0"

    def to_provider_args(self) -> dict[str, object]:
        """Convert to arguments for :meth:`PropertyProvider.state_ph`.

        Returns a deterministic dict with SI values and the reference
        state identifier, suitable for direct ``**`` unpacking.
        """
        return {
            "pressure_pa": self.pressure.si_value,
            "enthalpy_j_kg": self.enthalpy.si_value,
            "reference_state": self.reference_state,
        }


class PQStateSpec(StrictBaseModel):
    """Pressure-quality state specification."""

    type: Literal["PQ"]
    pressure: AbsolutePressure
    quality: float = Field(ge=0, le=1)
    schema_version: Literal["1.0"] = "1.0"


StateSpec = Annotated[
    TPStateSpec | PHStateSpec | PQStateSpec, Discriminator("type")
]


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


class StreamSpec(StrictBaseModel):
    fluid: FluidSpec
    mass_flow: MassFlow
    inlet_temperature: AbsoluteTemperature | None = None
    inlet_pressure: AbsolutePressure | None = None
    state_spec: StateSpec | None = None
    outlet_temperature: AbsoluteTemperature | None = None
    allowable_pressure_drop: PressureDifference | None = None
    fouling_resistance: FoulingResistanceSpec

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

    @property
    def inlet_temperature_k(self) -> float | None:
        """Return inlet temperature in kelvin from either TP state_spec or legacy field."""
        if self.state_spec is not None and isinstance(self.state_spec, TPStateSpec):
            return self.state_spec.temperature.si_value
        if self.inlet_temperature is not None:
            return self.inlet_temperature.si_value
        return None

    @property
    def inlet_pressure_pa(self) -> float | None:
        """Return inlet pressure in pascal from either TP state_spec or legacy field."""
        if self.state_spec is not None and isinstance(self.state_spec, TPStateSpec):
            return self.state_spec.pressure.si_value
        if self.inlet_pressure is not None:
            return self.inlet_pressure.si_value
        return None

    @property
    def state_spec_type(self) -> str | None:
        """Return the state spec type ('TP', 'PH', 'PQ') or None if legacy."""
        if self.state_spec is not None:
            return self.state_spec.type
        return None


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
