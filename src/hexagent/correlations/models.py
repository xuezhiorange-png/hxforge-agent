"""Frozen Pydantic models and StrEnum types for the correlation domain.

All models use ``frozen=True`` and ``extra="forbid"`` to enforce
immutability and prevent accidental field leakage.
"""

from __future__ import annotations

import math
import re
from enum import StrEnum
from typing import Any, Literal

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
    implementation_unavailable = "implementation_unavailable"


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
# Item 2: Fully-anchored SemVer regex — rejects trailing junk and build metadata
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$"
)
_DOI_RE = re.compile(r"^10\.\d{4,9}/[^\s]+$")
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _is_valid_id(value: str) -> bool:
    return bool(_VALID_ID_RE.match(value))


def _is_valid_version(value: str) -> bool:
    return bool(_SEMVER_RE.match(value))


def _validate_no_nan_inf(value: float, field_name: str) -> None:
    if math.isnan(value):
        raise ValueError(f"{field_name} must not be NaN")
    if math.isinf(value):
        raise ValueError(f"{field_name} must not be Inf")


def _validate_hash_format(value: str, field_name: str) -> None:
    """Validate that value matches sha256:<64-hex> format."""
    if not _HASH_RE.match(value):
        raise ValueError(f"{field_name} must match sha256:<64 lowercase hex>, got {value!r}")


def _normalize_semver_prerelease(prerelease: str) -> tuple[tuple[int, int | str], ...]:
    """Parse a SemVer prerelease string into a tuple of dot-separated identifiers.

    Each identifier is encoded as ``(0, int_value)`` for numeric identifiers
    and ``(1, str_value)`` for alphanumeric identifiers.  This ensures
    ``numeric < alphanumeric`` per the SemVer specification and avoids
    ``TypeError`` when comparing ``int`` vs ``str``.

    Leading zeros in numeric identifiers are rejected (except literal ``0``).
    """
    if not prerelease:
        return ()
    parts: list[tuple[int, int | str]] = []
    for part in prerelease.split("."):
        # Reject leading zeros in numeric identifiers (e.g. "01", "007")
        if part.isdigit() and len(part) > 1 and part[0] == "0":
            raise ValueError(
                f"Leading zeros not allowed in numeric prerelease identifier: {part!r}"
            )
        try:
            parts.append((0, int(part)))
        except ValueError:
            parts.append((1, part))
    return tuple(parts)


def parse_semver(version: str) -> tuple[int, int, int, tuple[tuple[int, int | str], ...]]:
    """Parse a SemVer string into (major, minor, patch, prerelease_tuple).

    Prerelease identifiers are compared by SemVer precedence:
    - Numeric identifiers compared numerically (encoded as ``(0, int_val)``)
    - Alphanumeric identifiers compared lexically (encoded as ``(1, str_val)``)
    - Numeric < alphanumeric
    - Fewer identifiers < more identifiers (when prefix matches)
    """
    match = re.match(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(.+))?$", version)
    if not match:
        raise ValueError(f"Invalid SemVer string: {version!r}")
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    prerelease = _normalize_semver_prerelease(match.group(4) or "")
    return (major, minor, patch, prerelease)


def compare_semver(v1: str, v2: str) -> int:
    """Compare two SemVer strings. Returns -1, 0, or 1.

    Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2.
    Uses SemVer precedence rules including prerelease comparison.
    """
    p1 = parse_semver(v1)  # (major, minor, patch, prerelease)
    p2 = parse_semver(v2)
    # Compare (major, minor, patch) as tuples
    core1 = (p1[0], p1[1], p1[2])
    core2 = (p2[0], p2[1], p2[2])
    if core1 != core2:
        return -1 if core1 < core2 else 1
    # Same core: prerelease < no prerelease
    pre1, pre2 = p1[3], p2[3]
    if pre1 and not pre2:
        return -1  # pre1 < pre2
    if not pre1 and pre2:
        return 1  # pre1 > pre2
    if not pre1 and not pre2:
        return 0  # both stable, equal
    # Both prerelease: compare using the same encoding as _normalize_semver_prerelease
    e1, e2 = pre1, pre2
    if e1 < e2:
        return -1
    if e1 > e2:
        return 1
    return 0


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
            raise ValueError(f"version must be valid SemVer, got {v!r}")
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
        # tolerance >= 0 and <= 1.0
        _validate_no_nan_inf(self.tolerance_fraction, "tolerance_fraction")
        if self.tolerance_fraction < 0:
            raise ValueError(f"tolerance_fraction must be >= 0, got {self.tolerance_fraction}")
        if self.tolerance_fraction > 1.0:
            raise ValueError(f"tolerance_fraction must be <= 1.0, got {self.tolerance_fraction}")
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
        # Item 3: recommended_minimum <= recommended_maximum
        if (
            self.recommended_minimum is not None
            and self.recommended_maximum is not None
            and self.recommended_minimum > self.recommended_maximum
        ):
            raise ValueError(
                f"recommended_minimum ({self.recommended_minimum}) "
                f"must be <= recommended_maximum ({self.recommended_maximum})"
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

    @model_validator(mode="after")
    def _validate_envelope(self) -> ApplicabilityEnvelope:
        # Item 3: Reject duplicate NumericBound.variable entries
        seen_vars: set[ApplicabilityVariable] = set()
        for bound in self.bounds:
            if bound.variable in seen_vars:
                raise ValueError(f"Duplicate NumericBound.variable entry: {bound.variable!r}")
            seen_vars.add(bound.variable)

        # Item 3: Every bounded variable must appear in required_inputs
        for bound in self.bounds:
            if bound.variable not in self.required_inputs:
                raise ValueError(
                    f"Variable {bound.variable!r} has bounds but is not in required_inputs"
                )

        # Item 3: Sort bounds by variable name for canonical ordering
        if self.bounds != tuple(sorted(self.bounds, key=lambda b: b.variable.value)):
            sorted_bounds = tuple(sorted(self.bounds, key=lambda b: b.variable.value))
            object.__setattr__(self, "bounds", sorted_bounds)

        return self


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
    incompatible_flow_regime: OutOfRangeAction = OutOfRangeAction.block


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
    definition_hash: str

    @field_validator("definition_hash")
    @classmethod
    def _validate_definition_hash(cls, v: str) -> str:
        if not v:
            raise ValueError("definition_hash must not be empty")
        _validate_hash_format(v, "definition_hash")
        return v

    @model_validator(mode="after")
    def _validate_definition(self) -> CorrelationDefinition:
        # Item 3: geometry must equal envelope.geometry_types
        if self.geometry != self.envelope.geometry_types:
            raise ValueError("CorrelationDefinition.geometry must equal envelope.geometry_types")
        # Item 3: phase_regimes must equal envelope.phase_regimes
        if self.phase_regimes != self.envelope.phase_regimes:
            raise ValueError(
                "CorrelationDefinition.phase_regimes must equal envelope.phase_regimes"
            )
        # Item 7: implementation_ref required for implemented/validated
        if (
            self.implementation_status
            in (
                CorrelationImplementationStatus.implemented,
                CorrelationImplementationStatus.validated,
            )
            and not self.implementation_ref
        ):
            raise ValueError(
                f"implementation_ref is required for {self.implementation_status.value} status"
            )
        # Item 7: source.verification_status >= primary_source_checked for validated
        if self.implementation_status == CorrelationImplementationStatus.validated:
            min_status = SourceVerificationStatus.primary_source_checked
            status_order = [
                SourceVerificationStatus.unverified,
                SourceVerificationStatus.secondary_source,
                SourceVerificationStatus.primary_source_checked,
                SourceVerificationStatus.independently_verified,
            ]
            if status_order.index(self.source.verification_status) < status_order.index(min_status):
                raise ValueError(
                    f"Validated definition requires source.verification_status >= "
                    f"primary_source_checked, got {self.source.verification_status.value}"
                )
        # Item 7: Reject self-supersession
        if (
            self.supersedes is not None
            and self.supersedes.correlation_id == self.key.correlation_id
            and self.supersedes.version == self.key.version
        ):
            raise ValueError("Correlation cannot supersede itself (same key)")
        return self

    @classmethod
    def create(cls, **kwargs: Any) -> CorrelationDefinition:
        """Factory that auto-computes definition_hash.

        Uses model_construct for the intermediate (unvalidated) step,
        then validates the final result with model_validate to ensure
        all validators run including hash format check.
        """
        kwargs.pop("definition_hash", None)
        # Construct without validation to get the canonical payload
        temp = cls.model_construct(**{k: v for k, v in kwargs.items() if k in cls.model_fields})
        computed = compute_definition_hash(temp)
        # Full validation with the computed hash
        return cls.model_validate({**temp.model_dump(), "definition_hash": computed})


class CorrelationApplicabilityInput(BaseModel):
    """Input values for an applicability assessment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    geometry: GeometryType
    phase_regime: PhaseRegime
    flow_regime: FlowRegime
    values: tuple[tuple[ApplicabilityVariable, float], ...] = ()
    allow_extrapolation: bool = False

    @field_validator("values", mode="before")
    @classmethod
    def _normalize_values(cls, v: Any) -> tuple[tuple[ApplicabilityVariable, float], ...]:
        """Accept dict, list-of-pairs, or tuple-of-pairs.

        Normalize to sorted deduplicated tuple. Reject NaN/Inf.
        """
        pairs: list[tuple[ApplicabilityVariable, float]] = []
        if isinstance(v, dict):
            raw = list(v.items())
        elif isinstance(v, (list, tuple)):
            raw = list(v)
        else:
            raise ValueError(f"values must be dict or list-of-pairs, got {type(v).__name__}")

        seen: set[ApplicabilityVariable] = set()
        for item in raw:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError(f"Each value pair must be (variable, float), got {item!r}")
            var, val = item
            if isinstance(var, str):
                var = ApplicabilityVariable(var)
            if not isinstance(val, (int, float)):
                raise ValueError(f"Value must be numeric, got {val!r}")
            _validate_no_nan_inf(float(val), f"value for {var}")
            if var in seen:
                raise ValueError(f"Duplicate variable in values: {var!r}")
            seen.add(var)
            pairs.append((var, float(val)))
        return tuple(sorted(pairs, key=lambda p: p[0].value))


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


class ApplicabilityIdentitySnapshot(BaseModel):
    """Immutable snapshot of the inputs needed to recompute assessment_hash.

    Stored inside ApplicabilityAssessment so that ``verify_assessment_hash()``
    can recompute and verify the hash after JSON round-trip.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    definition_hash: str
    geometry: GeometryType
    phase_regime: PhaseRegime
    flow_regime: FlowRegime
    input_values: tuple[tuple[ApplicabilityVariable, float], ...]
    policy: OutOfRangePolicy
    allow_extrapolation: bool


class ApplicabilityAssessment(BaseModel):
    """Complete applicability assessment result.

    ``allows_evaluation`` is ``Field(init=False)``: it is NOT a public
    constructor parameter and must not appear in caller-supplied data.
    The value is always derived from ``self.blockers`` by the model
    validator — callers cannot set it.

    ``identity_snapshot`` stores the authoritative inputs needed to
    recompute ``assessment_hash``.  It is included in serialization so
    that ``verify_assessment_hash()`` works after a JSON round-trip.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    correlation_key: CorrelationKey
    status: ApplicabilityStatus
    variable_results: tuple[VariableAssessment, ...] = ()
    warnings: tuple[EngineeringMessage, ...] = ()
    blockers: tuple[EngineeringMessage, ...] = ()
    allows_evaluation: bool = Field(init=False, default=False)
    assessment_hash: str
    identity_snapshot: ApplicabilityIdentitySnapshot | None = None

    @field_validator("assessment_hash")
    @classmethod
    def _validate_assessment_hash(cls, v: str) -> str:
        if not v:
            raise ValueError("assessment_hash must not be empty")
        _validate_hash_format(v, "assessment_hash")
        return v

    @model_validator(mode="before")
    @classmethod
    def _reject_allows_evaluation_input(cls, data: Any) -> Any:
        """allows_evaluation is derived, not caller-settable.

        Reject it in the constructor and direct model_validate calls.
        For JSON round-trip, model_validate / model_validate_json strip it
        before reaching this validator.
        """
        if isinstance(data, dict) and "allows_evaluation" in data:
            raise ValueError("allows_evaluation is a derived field and cannot be set via input")
        return data

    @model_validator(mode="after")
    def _validate_and_derive_assessment(self) -> ApplicabilityAssessment:
        # Item 5: Derive allows_evaluation from blockers
        derived = not bool(self.blockers)
        object.__setattr__(self, "allows_evaluation", derived)
        # Item 5: if status is applicable → no blockers
        if self.status == ApplicabilityStatus.applicable and self.blockers:
            raise ValueError("applicable status must not have blockers")
        # Item 5: if status has no blockers but non-applicable → allows_evaluation=True
        if (
            self.status != ApplicabilityStatus.applicable
            and not self.blockers
            and not self.allows_evaluation
        ):
            raise ValueError(
                "Non-applicable status with no blockers must have allows_evaluation=True"
            )
        return self

    def verify_assessment_hash(self) -> bool:
        """Recompute assessment_hash from the identity snapshot and compare.

        Returns True if the stored hash matches the recomputed hash.
        Returns False if identity_snapshot is missing or hash mismatches.
        """
        if self.identity_snapshot is None:
            return False
        snap = self.identity_snapshot
        recomputed = compute_assessment_hash(
            definition_hash=snap.definition_hash,
            correlation_key=self.correlation_key,
            geometry=snap.geometry,
            phase_regime=snap.phase_regime,
            flow_regime=snap.flow_regime,
            input_values=snap.input_values,
            status=self.status,
            variable_results=self.variable_results,
            warnings=self.warnings,
            blockers=self.blockers,
            policy=snap.policy,
            allow_extrapolation=snap.allow_extrapolation,
        )
        return recomputed == self.assessment_hash

    # -- JSON round-trip support -------------------------------------------------
    # model_dump() includes allows_evaluation (it is a field).
    # model_validate() / model_validate_json() strip it so that round-trip
    # data can be deserialized without triggering the before-validator.

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> ApplicabilityAssessment:
        if isinstance(obj, dict) and "allows_evaluation" in obj:
            obj = {k: v for k, v in obj.items() if k != "allows_evaluation"}
        return super().model_validate(obj, **kwargs)

    @classmethod
    def model_validate_json(
        cls, json_data: str | bytes | bytearray, **kwargs: Any
    ) -> ApplicabilityAssessment:
        import json as _json

        data = _json.loads(json_data)
        if isinstance(data, dict) and "allows_evaluation" in data:
            data = {k: v for k, v in data.items() if k != "allows_evaluation"}
        return cls.model_validate(data, **kwargs)


def compute_definition_hash(defn: CorrelationDefinition) -> str:
    """Compute the canonical definition hash excluding the definition_hash field itself."""
    from hexagent.core.canonical import sha256_digest

    dump = defn.model_dump()
    dump.pop("definition_hash", None)
    return sha256_digest(dump)


def compute_assessment_hash(
    *,
    definition_hash: str,
    correlation_key: CorrelationKey,
    geometry: GeometryType,
    phase_regime: PhaseRegime,
    flow_regime: FlowRegime,
    input_values: tuple[tuple[ApplicabilityVariable, float], ...],
    status: ApplicabilityStatus,
    variable_results: tuple[VariableAssessment, ...],
    warnings: tuple[EngineeringMessage, ...],
    blockers: tuple[EngineeringMessage, ...],
    policy: OutOfRangePolicy,
    allow_extrapolation: bool,
) -> str:
    """Compute a canonical assessment hash that is order-independent.

    Includes the COMPLETE input identity: definition_hash, correlation_key,
    geometry, phase, flow, all input values, status, variable results,
    warnings, blockers, policy (all 6 fields), and allow_extrapolation.
    """
    from hexagent.core.canonical import sha256_digest

    # Sort variable results by variable name for canonical ordering
    sorted_vrs = tuple(sorted(variable_results, key=lambda vr: vr.variable.value))

    # Sort warning/blocker codes for canonical ordering (full message payload)
    def _canonicalize_message(msg: EngineeringMessage) -> dict[str, Any]:
        """Full canonical payload of an EngineeringMessage for hashing."""
        return {
            "code": msg.code.value,
            "severity": msg.severity.value,
            "message": msg.message,
            "source_module": msg.source_module,
            "context": [(k, v) for k, v in msg.context],
            "allows_continuation": msg.allows_continuation,
        }

    warning_data = sorted(
        [_canonicalize_message(w) for w in warnings],
        key=lambda d: (d["code"], d["message"]),
    )
    blocker_data = sorted(
        [_canonicalize_message(b) for b in blockers],
        key=lambda d: (d["code"], d["message"]),
    )
    # Sort input values for canonical ordering
    sorted_input_values = sorted(
        [(var.value, val) for var, val in input_values], key=lambda x: x[0]
    )

    payload = {
        "definition_hash": definition_hash,
        "correlation_key": {
            "correlation_id": correlation_key.correlation_id,
            "version": correlation_key.version,
        },
        "geometry": geometry.value,
        "phase_regime": phase_regime.value,
        "flow_regime": flow_regime.value,
        "input_values": sorted_input_values,
        "status": status.value,
        "variable_results": [
            {
                "variable": vr.variable.value,
                "supplied_value": vr.supplied_value,
                "absolute_minimum": vr.absolute_minimum,
                "absolute_maximum": vr.absolute_maximum,
                "recommended_minimum": vr.recommended_minimum,
                "recommended_maximum": vr.recommended_maximum,
                "status": vr.status.value,
            }
            for vr in sorted_vrs
        ],
        "warning_data": warning_data,
        "blocker_data": blocker_data,
        "policy": {
            "absolute_violation": policy.absolute_violation.value,
            "recommended_violation": policy.recommended_violation.value,
            "missing_input": policy.missing_input.value,
            "incompatible_geometry": policy.incompatible_geometry.value,
            "incompatible_phase": policy.incompatible_phase.value,
            "incompatible_flow_regime": policy.incompatible_flow_regime.value,
        },
        "allow_extrapolation": allow_extrapolation,
    }
    return sha256_digest(payload)


__all__ = [
    "ApplicabilityAssessment",
    "ApplicabilityEnvelope",
    "ApplicabilityIdentitySnapshot",
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
    "compare_semver",
    "compute_assessment_hash",
    "compute_definition_hash",
    "parse_semver",
]
