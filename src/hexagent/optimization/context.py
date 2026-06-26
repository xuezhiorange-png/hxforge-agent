"""
TASK-009 Phase 2 — SizingRequestIdentity, per-candidate CalculationContext,
deterministic UUID5-based request IDs, PassedSizingGate artifact, and
MaterializedCandidateSet artifact.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.models import (
    CatalogSnapshotRef,
    OptionRawCountRecord,
    SizingRequest,
)

# Frozen namespace for TASK-009 deterministic UUID5 generation.
TASK009_CONTEXT_NAMESPACE = UUID("a0b1c2d3-e4f5-6789-abcd-ef0123456789")

# ---------------------------------------------------------------------------
# Hard cap constant
# ---------------------------------------------------------------------------

HARD_RAW_COMBINATION_CAP = 10000

# ---------------------------------------------------------------------------
# OptimizationObjective — frozen API values
# ---------------------------------------------------------------------------


class OptimizationObjective(StrEnum):
    MINIMUM_OUTER_HEAT_TRANSFER_AREA = "minimum_outer_heat_transfer_area"
    MINIMUM_EFFECTIVE_LENGTH = "minimum_effective_length"


# ---------------------------------------------------------------------------
# ExpectedProviderIdentity
# ---------------------------------------------------------------------------


class ExpectedProviderIdentity(BaseModel):
    """The provider identity that TASK-009 expects TASK-008 to use."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    git_revision: str
    reference_state_policy: str
    configuration_fingerprint: str | None = None
    cache_policy_version: str | None = None

    def matches(self, actual: Any) -> bool:
        """Check if *actual* (ProviderIdentitySnapshot) matches.

        ``name``, ``version``, ``git_revision``, ``reference_state_policy``
        are mandatory.  ``configuration_fingerprint`` and
        ``cache_policy_version`` are matched only when self has a non-None
        value.
        """
        try:
            if actual.name != self.name:
                return False
            if actual.version != self.version:
                return False
            if actual.git_revision != self.git_revision:
                return False
            if actual.reference_state_policy != self.reference_state_policy:
                return False
            if (
                self.configuration_fingerprint is not None
                and actual.configuration_fingerprint != self.configuration_fingerprint
            ):
                return False
            return not (
                self.cache_policy_version is not None
                and actual.cache_policy_version != self.cache_policy_version
            )
        except (AttributeError, TypeError):
            return False


# ---------------------------------------------------------------------------
# Finite/range validators for identity numeric fields
# ---------------------------------------------------------------------------


def _validate_positive_finite_float(value: object, field_name: str) -> float:
    """Reject bool, NaN, Inf, zero and negatives."""
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be float, not bool")
    if not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric, got {type(value).__name__}")
    f = float(value)
    if not math.isfinite(f):
        raise ValueError(f"{field_name} must be finite, got {f}")
    if f <= 0:
        raise ValueError(f"{field_name} must be positive, got {f}")
    return f


def _validate_non_negative_finite_float(value: object, field_name: str) -> float:
    """Reject bool, NaN, Inf, negative.  Zero is allowed."""
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be float, not bool")
    if not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric, got {type(value).__name__}")
    f = float(value)
    if not math.isfinite(f):
        raise ValueError(f"{field_name} must be finite, got {f}")
    if f < 0:
        raise ValueError(f"{field_name} must be >= 0, got {f}")
    return f


# ---------------------------------------------------------------------------
# SizingRequestIdentity — full immutable identity
# ---------------------------------------------------------------------------


class SizingRequestIdentity(BaseModel):
    """Complete immutable identity of a sizing + candidate optimization request.

    All fields are frozen and extra keys are forbidden.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Fluid identities
    hot_fluid_name: str
    cold_fluid_name: str
    hot_fluid_equation_of_state: str
    cold_fluid_equation_of_state: str
    hot_fluid_normalized_components: tuple[tuple[str, float], ...] = Field(default_factory=tuple)
    cold_fluid_normalized_components: tuple[tuple[str, float], ...] = Field(default_factory=tuple)

    # Inlet conditions
    hot_inlet_temperature_k: float
    cold_inlet_temperature_k: float
    hot_inlet_pressure_pa: float
    cold_inlet_pressure_pa: float
    hot_mass_flow_kg_s: float
    cold_mass_flow_kg_s: float

    # Flow configuration
    flow_arrangement: str  # FlowArrangement.value
    tube_in_hot: bool
    tube_boundary_condition: str  # ThermalBoundaryCondition.value
    annulus_boundary_condition: str

    # Duty & optimization
    minimum_terminal_delta_t: float
    required_duty_w: float
    duty_absolute_tolerance_w: float
    duty_relative_tolerance: float
    optimization_objective: OptimizationObjective
    top_n: int

    # Request bounds
    request_raw_combination_cap: int | None = None
    minimum_effective_length_m: float | None = None
    maximum_effective_length_m: float | None = None

    # Catalog refs (canonical ordered)
    catalog_snapshot_identities: tuple[CatalogSnapshotRef, ...] = Field(default_factory=tuple)

    # Solver parameters (REQUIRED — no defaults)
    rating_solver_absolute_residual_w: float
    rating_solver_relative_residual_fraction: float
    rating_solver_bracket_temperature_tolerance_k: float
    rating_solver_max_iterations: int

    # Expected provider
    expected_provider_identity: ExpectedProviderIdentity

    # Domain context (UUID | None — never synthesised)
    design_case_revision_id: UUID | None = None
    calculation_run_id: UUID | None = None

    # Software metadata
    rating_software_version: str = ""
    execution_context_policy_version: str = ""

    # --- Validators ---

    @field_validator("top_n", mode="before")
    @classmethod
    def _validate_top_n(cls, value: object) -> int:
        if isinstance(value, bool):
            raise TypeError("top_n must be int, not bool")
        if not isinstance(value, int):
            raise TypeError(f"top_n must be int, got {type(value).__name__}")
        if value < 1:
            raise ValueError(f"top_n must be >= 1, got {value}")
        return value

    @field_validator(
        "hot_fluid_normalized_components", "cold_fluid_normalized_components", mode="before"
    )
    @classmethod
    def _canonicalize_components(cls, value: object) -> tuple[tuple[str, float], ...]:
        if not isinstance(value, (list, tuple)):
            raise TypeError(f"components must be a list or tuple, got {type(value).__name__}")
        seen: set[str] = set()
        result: list[tuple[str, float]] = []
        for item in value:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise TypeError(f"Each component must be a 2-tuple (name, fraction), got {item!r}")
            name, fraction = item
            if not isinstance(name, str):
                raise TypeError(f"Component name must be str, got {type(name).__name__}")
            # Reject bool
            if isinstance(fraction, bool):
                raise TypeError("Component fraction must be float, not bool")
            if not isinstance(fraction, (int, float)):
                raise TypeError(f"Component fraction must be float, got {type(fraction).__name__}")
            f = float(fraction)
            if not math.isfinite(f):
                raise ValueError(f"Component fraction must be finite, got {f}")
            if f <= 0 or f > 1:
                raise ValueError(f"Component fraction must be in (0, 1], got {f}")
            if name in seen:
                raise ValueError(f"Duplicate component name: {name!r}")
            seen.add(name)
            result.append((name, f))
        result.sort(key=lambda p: p[0])
        return tuple(result)

    @field_validator("request_raw_combination_cap", mode="before")
    @classmethod
    def _validate_raw_cap(cls, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise TypeError("raw combination cap must be int, not bool")
        if not isinstance(value, int):
            raise TypeError(f"raw combination cap must be int, got {type(value).__name__}")
        if value < 1 or value > HARD_RAW_COMBINATION_CAP:
            raise ValueError(
                f"raw combination cap must be in 1..{HARD_RAW_COMBINATION_CAP}, got {value}"
            )
        return value

    # --- Numeric finite/range validators ---

    @field_validator(
        "hot_inlet_temperature_k",
        "cold_inlet_temperature_k",
        "hot_inlet_pressure_pa",
        "cold_inlet_pressure_pa",
        "hot_mass_flow_kg_s",
        "cold_mass_flow_kg_s",
        "minimum_terminal_delta_t",
        "required_duty_w",
        "rating_solver_absolute_residual_w",
        "rating_solver_relative_residual_fraction",
        "rating_solver_bracket_temperature_tolerance_k",
        mode="before",
    )
    @classmethod
    def _positive_finite_float(cls, value: object, info: Any) -> float:
        if info.field_name is None:
            raise ValueError("field_name required")
        return _validate_positive_finite_float(value, info.field_name)

    @field_validator(
        "duty_absolute_tolerance_w",
        "duty_relative_tolerance",
        mode="before",
    )
    @classmethod
    def _non_negative_finite_float(cls, value: object, info: Any) -> float:
        if info.field_name is None:
            raise ValueError("field_name required")
        return _validate_non_negative_finite_float(value, info.field_name)

    @field_validator(
        "minimum_effective_length_m",
        "maximum_effective_length_m",
        mode="before",
    )
    @classmethod
    def _optional_positive_finite(cls, value: object, info: Any) -> float | None:
        if value is None:
            return None
        if info.field_name is None:
            raise ValueError("field_name required")
        return _validate_positive_finite_float(value, info.field_name)

    @field_validator("rating_solver_max_iterations", mode="before")
    @classmethod
    def _validate_max_iterations(cls, value: object) -> int:
        if isinstance(value, bool):
            raise TypeError("max_iterations must be int, not bool")
        if not isinstance(value, int):
            raise TypeError(f"max_iterations must be int, got {type(value).__name__}")
        if value < 1:
            raise ValueError(f"max_iterations must be >= 1, got {value}")
        return value

    @property
    def sizing_request_identity_digest(self) -> str:
        """Deterministic SHA-256 content hash of the full identity."""
        return sha256_digest(self)


# ---------------------------------------------------------------------------
# Build SizingRequestIdentity
# ---------------------------------------------------------------------------


def build_sizing_request_identity(
    request: SizingRequest,
    *,
    hot_fluid_name: str,
    cold_fluid_name: str,
    hot_fluid_equation_of_state: str,
    cold_fluid_equation_of_state: str,
    hot_inlet_temperature_k: float,
    cold_inlet_temperature_k: float,
    hot_inlet_pressure_pa: float,
    cold_inlet_pressure_pa: float,
    hot_mass_flow_kg_s: float,
    cold_mass_flow_kg_s: float,
    tube_in_hot: bool,
    flow_arrangement: FlowArrangement | str,
    tube_boundary_condition: str = "adiabatic",
    annulus_boundary_condition: str = "adiabatic",
    minimum_terminal_delta_t: float,
    required_duty_w: float,
    duty_absolute_tolerance_w: float,
    duty_relative_tolerance: float,
    optimization_objective: OptimizationObjective,
    top_n: int,
    solver_params: SolverParams,
    expected_provider_identity: ExpectedProviderIdentity,
    rating_software_version: str = "",
    execution_context_policy_version: str = "",
    hot_fluid_normalized_components: tuple[tuple[str, float], ...] = (),
    cold_fluid_normalized_components: tuple[tuple[str, float], ...] = (),
    design_case_revision_id: UUID | None = None,
    calculation_run_id: UUID | None = None,
) -> SizingRequestIdentity:
    """Construct a fully typed ``SizingRequestIdentity``.

    Catalog refs are extracted from the request and canonically sorted.
    """
    from hexagent.optimization.catalog import catalog_identity_key

    sorted_cats = sorted(request.catalogs, key=catalog_identity_key)
    refs = tuple(
        CatalogSnapshotRef(
            catalog_id=cat.catalog_id,
            catalog_version=cat.catalog_version,
            catalog_content_hash=cat.catalog_content_hash,
            source_identity=cat.source_identity,
            schema_version=cat.schema_version,
        )
        for cat in sorted_cats
    )

    fa = (
        flow_arrangement.value
        if isinstance(flow_arrangement, FlowArrangement)
        else flow_arrangement
    )

    return SizingRequestIdentity(
        hot_fluid_name=hot_fluid_name,
        cold_fluid_name=cold_fluid_name,
        hot_fluid_equation_of_state=hot_fluid_equation_of_state,
        cold_fluid_equation_of_state=cold_fluid_equation_of_state,
        hot_fluid_normalized_components=hot_fluid_normalized_components,
        cold_fluid_normalized_components=cold_fluid_normalized_components,
        hot_inlet_temperature_k=hot_inlet_temperature_k,
        cold_inlet_temperature_k=cold_inlet_temperature_k,
        hot_inlet_pressure_pa=hot_inlet_pressure_pa,
        cold_inlet_pressure_pa=cold_inlet_pressure_pa,
        hot_mass_flow_kg_s=hot_mass_flow_kg_s,
        cold_mass_flow_kg_s=cold_mass_flow_kg_s,
        tube_in_hot=tube_in_hot,
        flow_arrangement=fa,
        tube_boundary_condition=tube_boundary_condition,
        annulus_boundary_condition=annulus_boundary_condition,
        minimum_terminal_delta_t=minimum_terminal_delta_t,
        required_duty_w=required_duty_w,
        duty_absolute_tolerance_w=duty_absolute_tolerance_w,
        duty_relative_tolerance=duty_relative_tolerance,
        optimization_objective=optimization_objective,
        top_n=top_n,
        request_raw_combination_cap=request.request_raw_combination_cap,
        minimum_effective_length_m=request.minimum_effective_length_m,
        maximum_effective_length_m=request.maximum_effective_length_m,
        catalog_snapshot_identities=refs,
        rating_solver_absolute_residual_w=solver_params.absolute_residual_w,
        rating_solver_relative_residual_fraction=solver_params.relative_residual_fraction,
        rating_solver_bracket_temperature_tolerance_k=solver_params.bracket_temperature_tolerance_k,
        rating_solver_max_iterations=solver_params.max_iterations,
        expected_provider_identity=expected_provider_identity,
        design_case_revision_id=design_case_revision_id,
        calculation_run_id=calculation_run_id,
        rating_software_version=rating_software_version,
        execution_context_policy_version=execution_context_policy_version,
    )


# ---------------------------------------------------------------------------
# Candidate CalculationContext (typed — returns exact type)
# ---------------------------------------------------------------------------


def build_candidate_calculation_context(
    sizing_request_identity: SizingRequestIdentity,
    source_qualified_candidate_id: str,
) -> Any:
    """Build a typed ``CalculationContext`` for a single candidate.

    The ``request_id`` is a deterministic UUID5.
    ``design_case_revision_id`` and ``calculation_run_id`` are
    forwarded from the sizing request identity (may be None).
    """
    from hexagent.core.heat_balance import CalculationContext

    digest = sizing_request_identity.sizing_request_identity_digest
    design_id = sizing_request_identity.design_case_revision_id
    run_id = sizing_request_identity.calculation_run_id

    name = f"{digest}:{source_qualified_candidate_id}"
    request_id = uuid5(TASK009_CONTEXT_NAMESPACE, name)

    return CalculationContext(
        request_id=request_id,
        design_case_revision_id=design_id,
        calculation_run_id=run_id,
    )


# ---------------------------------------------------------------------------
# PassedSizingGate artifact — must validate semantic invariants
# ---------------------------------------------------------------------------


class PassedSizingGate(BaseModel):
    """Immutable artifact created when the Phase 1 cap gate passes.

    Required by Phase 2 materialization entry to proceed.
    Constructor validates semantic invariants.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["passed"]
    sizing_request_identity_digest: str
    raw_combination_count: int
    effective_cap: int
    per_option_records: tuple[OptionRawCountRecord, ...]
    gate_digest: str

    @field_validator("raw_combination_count", mode="before")
    @classmethod
    def _validate_raw_count(cls, value: object) -> int:
        if isinstance(value, bool):
            raise TypeError("raw_combination_count must be int, not bool")
        if not isinstance(value, int):
            raise TypeError(f"raw_combination_count must be int, got {type(value).__name__}")
        if value < 0:
            raise ValueError(f"raw_combination_count must be >= 0, got {value}")
        return value

    @field_validator("effective_cap", mode="before")
    @classmethod
    def _validate_effective_cap(cls, value: object) -> int:
        if isinstance(value, bool):
            raise TypeError("effective_cap must be int, not bool")
        if not isinstance(value, int):
            raise TypeError(f"effective_cap must be int, got {type(value).__name__}")
        if value < 1 or value > HARD_RAW_COMBINATION_CAP:
            raise ValueError(f"effective_cap must be in 1..{HARD_RAW_COMBINATION_CAP}, got {value}")
        return value

    @field_validator("per_option_records", mode="after")
    @classmethod
    def _validate_per_option_records(
        cls, records: tuple[OptionRawCountRecord, ...]
    ) -> tuple[OptionRawCountRecord, ...]:
        seen: set[str] = set()
        for rec in records:
            if isinstance(rec.raw_count, bool):
                raise TypeError("raw_count in per_option_records must be int, not bool")
            if not isinstance(rec.raw_count, int):
                raise TypeError(
                    f"raw_count in per_option_records must be int, "
                    f"got {type(rec.raw_count).__name__}"
                )
            if rec.raw_count < 0:
                raise ValueError(f"raw_count must be non-negative, got {rec.raw_count}")
            key = (
                f"{rec.catalog_id}:{rec.catalog_version}:"
                f"{rec.catalog_content_hash}:{rec.source_identity}:"
                f"{rec.schema_version}:{rec.assembly_option_id}:"
                f"{rec.canonical_length_quantum_m}"
            )
            if key in seen:
                raise ValueError(f"Duplicate per-option record key: {key}")
            seen.add(key)
        # Sort by canonical compound key
        sorted_recs = sorted(
            records,
            key=lambda r: (
                r.catalog_id,
                r.catalog_version,
                r.catalog_content_hash,
                r.assembly_option_id,
                r.canonical_length_quantum_m,
            ),
        )
        return tuple(sorted_recs)

    @model_validator(mode="after")
    def _validate_gate_invariants(self) -> Self:
        errors: list[str] = []
        if self.status != "passed":
            errors.append(f"gate status must be 'passed', got {self.status!r}")
        if self.raw_combination_count > self.effective_cap:
            errors.append(
                f"raw_combination_count ({self.raw_combination_count}) "
                f"exceeds effective_cap ({self.effective_cap})"
            )
        total_raw = sum(r.raw_count for r in self.per_option_records)
        if total_raw != self.raw_combination_count:
            errors.append(
                f"sum(record.raw_count) ({total_raw}) "
                f"!= raw_combination_count ({self.raw_combination_count})"
            )
        if errors:
            raise ValueError("; ".join(errors))
        return self

    def verify_digest(self) -> bool:
        """Recalculate digest from payload and compare against stored."""
        payload = self.model_copy(update={"gate_digest": ""})
        expected = sha256_digest(payload)
        return self.gate_digest == expected


def create_passed_sizing_gate(
    sizing_request_identity_digest: str,
    raw_combination_count: int,
    effective_cap: int,
    per_option_records: tuple[OptionRawCountRecord, ...],
) -> PassedSizingGate:
    """Factory: compute deterministic gate_digest."""
    gate = PassedSizingGate(
        status="passed",
        sizing_request_identity_digest=sizing_request_identity_digest,
        raw_combination_count=raw_combination_count,
        effective_cap=effective_cap,
        per_option_records=per_option_records,
        gate_digest="",
    )
    digest = sha256_digest(gate)
    return PassedSizingGate(
        status="passed",
        sizing_request_identity_digest=sizing_request_identity_digest,
        raw_combination_count=raw_combination_count,
        effective_cap=effective_cap,
        per_option_records=per_option_records,
        gate_digest=digest,
    )


# ---------------------------------------------------------------------------
# MaterializedCandidateSet — binds materialization to gate + request
# ---------------------------------------------------------------------------

from typing import Self  # noqa: E402


class MaterializedCandidateSet(BaseModel):
    """Immutable artifact binding materialized candidates to their gate.

    Required by the batch evaluator before any TASK-008 call.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sizing_request_identity_digest: str
    passed_gate_digest: str
    catalog_snapshot_identities: tuple[CatalogSnapshotRef, ...]
    minimum_effective_length_m: float | None = None
    maximum_effective_length_m: float | None = None
    raw_combination_count: int
    unique_candidate_count: int
    ordered_candidate_ids: tuple[str, ...]
    candidate_set_digest: str

    def verify_digest(self) -> bool:
        """Recalculate digest from payload and compare."""
        payload = self.model_copy(update={"candidate_set_digest": ""})
        expected = sha256_digest(payload)
        return self.candidate_set_digest == expected


def create_materialized_candidate_set(
    sizing_request_identity_digest: str,
    passed_gate_digest: str,
    catalog_snapshot_identities: tuple[CatalogSnapshotRef, ...],
    minimum_effective_length_m: float | None,
    maximum_effective_length_m: float | None,
    raw_combination_count: int,
    ordered_candidates: tuple[Any, ...],
) -> MaterializedCandidateSet:
    """Factory: build artifact from materialized candidates."""
    unique_count = len(ordered_candidates)
    ordered_ids = tuple(c.source_qualified_candidate_id for c in ordered_candidates)
    mcs = MaterializedCandidateSet(
        sizing_request_identity_digest=sizing_request_identity_digest,
        passed_gate_digest=passed_gate_digest,
        catalog_snapshot_identities=catalog_snapshot_identities,
        minimum_effective_length_m=minimum_effective_length_m,
        maximum_effective_length_m=maximum_effective_length_m,
        raw_combination_count=raw_combination_count,
        unique_candidate_count=unique_count,
        ordered_candidate_ids=ordered_ids,
        candidate_set_digest="",
    )
    digest = sha256_digest(mcs)
    return mcs.model_copy(update={"candidate_set_digest": digest})


# ---------------------------------------------------------------------------
# ProviderConsistencyResult — run-level provider consistency artifact
# ---------------------------------------------------------------------------


class ProviderConsistencyResult(BaseModel):
    """Result of a cross-candidate provider identity consistency check."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["not_applicable", "consistent", "inconsistent"]
    verified_provider_identity_digests: tuple[str, ...]
    consistency_digest: str


def build_provider_consistency_result(
    status: Literal["not_applicable", "consistent", "inconsistent"],
    verified_digests: tuple[str, ...],
) -> ProviderConsistencyResult:
    """Factory for ProviderConsistencyResult with deterministic digest."""
    result = ProviderConsistencyResult(
        status=status,
        verified_provider_identity_digests=verified_digests,
        consistency_digest="",
    )
    digest = sha256_digest(result)
    return ProviderConsistencyResult(
        status=status,
        verified_provider_identity_digests=verified_digests,
        consistency_digest=digest,
    )


__all__ = [
    "ExpectedProviderIdentity",
    "HARD_RAW_COMBINATION_CAP",
    "MaterializedCandidateSet",
    "OptimizationObjective",
    "PassedSizingGate",
    "ProviderConsistencyResult",
    "SizingRequestIdentity",
    "TASK009_CONTEXT_NAMESPACE",
    "build_candidate_calculation_context",
    "build_provider_consistency_result",
    "build_sizing_request_identity",
    "create_materialized_candidate_set",
    "create_passed_sizing_gate",
]
