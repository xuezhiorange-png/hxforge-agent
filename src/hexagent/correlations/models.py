"""Frozen Pydantic models and StrEnum types for the correlation domain.

All models use ``frozen=True`` and ``extra="forbid"`` to enforce
immutability and prevent accidental field leakage.
"""

from __future__ import annotations

import math
import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hexagent.domain.messages import EngineeringMessage

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CorrelationPurpose(StrEnum):
    """Physical purpose of a correlation."""

    heat_transfer_coefficient = "heat_transfer_coefficient"
    nusselt_number = "nusselt_number"
    friction_factor = "friction_factor"
    pressure_drop = "pressure_drop"
    void_fraction = "void_fraction"
    two_phase_multiplier = "two_phase_multiplier"
    fin_efficiency = "fin_efficiency"
    mass_transfer = "mass_transfer"
    mechanical_allowable = "mechanical_allowable"
    cost_estimation = "cost_estimation"


class GeometryType(StrEnum):
    """Flow geometry classification."""

    circular_tube = "circular_tube"
    annulus = "annulus"
    double_pipe = "double_pipe"
    shell_side = "shell_side"
    tube_bundle = "tube_bundle"
    plate_channel = "plate_channel"
    finned_tube = "finned_tube"
    microchannel = "microchannel"
    generic = "generic"


class PhaseRegime(StrEnum):
    """Fluid phase regime."""

    single_phase_liquid = "single_phase_liquid"
    single_phase_gas = "single_phase_gas"
    single_phase_unknown = "single_phase_unknown"
    boiling = "boiling"
    condensation = "condensation"
    two_phase = "two_phase"
    supercritical = "supercritical"
    generic = "generic"


class FlowRegime(StrEnum):
    """Flow regime classification."""

    laminar = "laminar"
    transitional = "transitional"
    turbulent = "turbulent"
    mixed = "mixed"
    not_applicable = "not_applicable"


class ApplicabilityVariable(StrEnum):
    """Dimensionless or dimensional variables used in applicability envelopes."""

    reynolds = "reynolds"
    prandtl = "prandtl"
    relative_roughness = "relative_roughness"
    diameter_ratio = "diameter_ratio"
    graetz = "graetz"
    peclet = "peclet"
    mach = "mach"
    quality = "quality"
    boiling_number = "boiling_number"
    weber = "weber"
    froude = "froude"
    reduced_pressure = "reduced_pressure"
    wall_to_bulk_viscosity_ratio = "wall_to_bulk_viscosity_ratio"


class CorrelationImplementationStatus(StrEnum):
    """Implementation maturity status of a correlation."""

    metadata_only = "metadata_only"
    implemented = "implemented"
    validated = "validated"
    deprecated = "deprecated"
    withdrawn = "withdrawn"


class SourceVerificationStatus(StrEnum):
    """Source verification status."""

    unverified = "unverified"
    secondary_source = "secondary_source"
    primary_source_checked = "primary_source_checked"
    independently_verified = "independently_verified"


class OutOfRangeAction(StrEnum):
    """Action to take when applicability limits are exceeded."""

    block = "block"
    warn = "warn"
    allow_explicit_opt_in = "allow_explicit_opt_in"
    fallback_required = "fallback_required"


class ApplicabilityStatus(StrEnum):
    """Overall applicability assessment result."""

    applicable = "applicable"
    recommended_range_exceeded = "recommended_range_exceeded"
    absolute_range_exceeded = "absolute_range_exceeded"
    missing_input = "missing_input"
    incompatible_geometry = "incompatible_geometry"
    incompatible_phase = "incompatible_phase"
    incompatible_flow_regime = "incompatible_flow_regime"
    explicit_extrapolation = "explicit_extrapolation"


class VariableApplicabilityStatus(StrEnum):
    """Per-variable applicability assessment result."""

    applicable = "applicable"
    below_absolute = "below_absolute"
    above_absolute = "above_absolute"
    below_recommended = "below_recommended"
    above_recommended = "above_recommended"
    missing = "missing"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+")
_DOI_RE = re.compile(r"^10\.\d{4,9}/[^\s]+$")


def _is_valid_id(value: str) -> bool:
    return bool(_VALID_ID_RE.match(value))


def _is_valid_version(value: str) -> bool:
    return bool(_SEMVER_RE.match(value))


def _validate_no_nan_inf(value: float, field_name: str) -> None:
    if math.isnan(value):
        raise ValueError(f"{field_name} must not be NaN")
    if math.isinf(value):
        raise ValueError(f"{field_name} must not be Inf")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class CorrelationKey(BaseModel):
    """Unique identifier for a correlation, combining ID and version."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: str
    version: str

    @field_validator("correlation_id")
    @classmethod
    def _validate_correlation_id(cls, v: str) -> str:
        if not v:
            raise ValueError("correlation_id must not be empty")
        if not _is_valid_id(v):
            raise ValueError(f"correlation_id must match [a-z0-9._-]+, got {v!r}")
        return v

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: str) -> str:
        if not v:
            raise ValueError("version must not be empty")
        if not _is_valid_version(v):
            raise ValueError(f"version must have at least major.minor.patch, got {v!r}")
        return v


class NumericBound(BaseModel):
    """Single-variable numeric bound within an applicability envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    variable: ApplicabilityVariable
    minimum: float | None = None
    maximum: float | None = None
    minimum_inclusive: bool = True
    maximum_inclusive: bool = True
    recommended_minimum: float | None = None
    recommended_maximum: float | None = None
    tolerance_fraction: float = 0.0

    @model_validator(mode="after")
    def _validate_bounds(self) -> NumericBound:
        # No NaN/Inf in any numeric field
        for fname in ("minimum", "maximum", "recommended_minimum", "recommended_maximum"):
            val: float | None = getattr(self, fname)
            if val is not None:
                _validate_no_nan_inf(val, fname)
        # tolerance >= 0
        _validate_no_nan_inf(self.tolerance_fraction, "tolerance_fraction")
        if self.tolerance_fraction < 0:
            raise ValueError(f"tolerance_fraction must be >= 0, got {self.tolerance_fraction}")
        # min < max when both set
        if self.minimum is not None and self.maximum is not None and self.minimum >= self.maximum:
            raise ValueError(f"minimum ({self.minimum}) must be < maximum ({self.maximum})")
        # recommended within absolute
        if (
            self.recommended_minimum is not None
            and self.minimum is not None
            and self.recommended_minimum < self.minimum
        ):
            raise ValueError(
                f"recommended_minimum ({self.recommended_minimum}) "
                f"must be >= minimum ({self.minimum})"
            )
        if (
            self.recommended_maximum is not None
            and self.maximum is not None
            and self.recommended_maximum > self.maximum
        ):
            raise ValueError(
                f"recommended_maximum ({self.recommended_maximum}) "
                f"must be <= maximum ({self.maximum})"
            )
        return self


class ApplicabilityEnvelope(BaseModel):
    """Combined geometry, phase, flow and numeric applicability limits."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    geometry_types: frozenset[GeometryType] = frozenset({GeometryType.generic})
    phase_regimes: frozenset[PhaseRegime] = frozenset({PhaseRegime.generic})
    flow_regimes: frozenset[FlowRegime] = frozenset({FlowRegime.not_applicable})
    bounds: tuple[NumericBound, ...] = ()
    required_inputs: frozenset[ApplicabilityVariable] = frozenset()
    excluded_conditions: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class BibliographicSource(BaseModel):
    """Bibliographic reference for a correlation source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    authors: tuple[str, ...] = ()
    title: str = Field(min_length=1)
    publication: str = Field(min_length=1)
    year: int
    edition: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    isbn: str | None = None
    standard_id: str | None = None
    equation_or_clause: str | None = None
    verification_status: SourceVerificationStatus = SourceVerificationStatus.unverified
    verification_note: str = ""

    @field_validator("year")
    @classmethod
    def _validate_year(cls, v: int) -> int:
        if v < 1900 or v > 2099:
            raise ValueError(f"year must be in range 1900-2099, got {v}")
        return v

    @field_validator("doi")
    @classmethod
    def _validate_doi(cls, v: str | None) -> str | None:
        if v is not None and v != "" and not _DOI_RE.match(v):
            raise ValueError(f"DOI format invalid, got {v!r}")
        return v


class UncertaintySpec(BaseModel):
    """Uncertainty specification for a correlation result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relative_uncertainty_fraction: float | None = None
    confidence_level_fraction: float | None = None
    basis: str = Field(min_length=1)
    source_id: str | None = None

    @model_validator(mode="after")
    def _validate_values(self) -> UncertaintySpec:
        if self.relative_uncertainty_fraction is not None:
            _validate_no_nan_inf(
                self.relative_uncertainty_fraction,
                "relative_uncertainty_fraction",
            )
            if self.relative_uncertainty_fraction < 0:
                raise ValueError(
                    f"relative_uncertainty_fraction must be >= 0, "
                    f"got {self.relative_uncertainty_fraction}"
                )
        if self.confidence_level_fraction is not None:
            _validate_no_nan_inf(self.confidence_level_fraction, "confidence_level_fraction")
            if not (0.0 < self.confidence_level_fraction <= 1.0):
                raise ValueError(
                    f"confidence_level_fraction must be in (0, 1], "
                    f"got {self.confidence_level_fraction}"
                )
        return self


class OutOfRangePolicy(BaseModel):
    """Policy for handling out-of-range applicability violations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    absolute_violation: OutOfRangeAction = OutOfRangeAction.block
    recommended_violation: OutOfRangeAction = OutOfRangeAction.warn
    missing_input: OutOfRangeAction = OutOfRangeAction.block
    incompatible_geometry: OutOfRangeAction = OutOfRangeAction.block
    incompatible_phase: OutOfRangeAction = OutOfRangeAction.block


class CorrelationDefinition(BaseModel):
    """Complete definition of a correlation with metadata, envelope and source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    key: CorrelationKey
    name: str = Field(min_length=1)
    purpose: CorrelationPurpose
    description: str = Field(min_length=1)
    geometry: frozenset[GeometryType]
    phase_regimes: frozenset[PhaseRegime]
    envelope: ApplicabilityEnvelope
    source: BibliographicSource
    uncertainty: UncertaintySpec | None = None
    out_of_range_policy: OutOfRangePolicy = Field(default_factory=OutOfRangePolicy)
    implementation_status: CorrelationImplementationStatus = (
        CorrelationImplementationStatus.metadata_only
    )
    implementation_ref: str | None = None
    supersedes: CorrelationKey | None = None
    tags: frozenset[str] = frozenset()
    definition_hash: str = ""


class CorrelationApplicabilityInput(BaseModel):
    """Input values for an applicability assessment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    geometry: GeometryType
    phase_regime: PhaseRegime
    flow_regime: FlowRegime
    values: dict[ApplicabilityVariable, float] = Field(default_factory=dict)
    allow_extrapolation: bool = False


class VariableAssessment(BaseModel):
    """Per-variable assessment result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    variable: ApplicabilityVariable
    supplied_value: float | None = None
    absolute_minimum: float | None = None
    absolute_maximum: float | None = None
    recommended_minimum: float | None = None
    recommended_maximum: float | None = None
    status: VariableApplicabilityStatus = VariableApplicabilityStatus.applicable


class ApplicabilityAssessment(BaseModel):
    """Complete applicability assessment result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    correlation_key: CorrelationKey
    status: ApplicabilityStatus
    variable_results: tuple[VariableAssessment, ...] = ()
    warnings: tuple[EngineeringMessage, ...] = ()
    blockers: tuple[EngineeringMessage, ...] = ()
    allows_evaluation: bool = False
    assessment_hash: str = ""


__all__ = [
    "ApplicabilityAssessment",
    "ApplicabilityEnvelope",
    "ApplicabilityStatus",
    "ApplicabilityVariable",
    "BibliographicSource",
    "CorrelationApplicabilityInput",
    "CorrelationDefinition",
    "CorrelationImplementationStatus",
    "CorrelationKey",
    "CorrelationPurpose",
    "FlowRegime",
    "GeometryType",
    "NumericBound",
    "OutOfRangeAction",
    "OutOfRangePolicy",
    "PhaseRegime",
    "SourceVerificationStatus",
    "UncertaintySpec",
    "VariableApplicabilityStatus",
    "VariableAssessment",
]
