"""
TASK-009 Phase 2 — SizingRequestIdentity, per-candidate CalculationContext,
and deterministic UUID5-based request IDs.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hexagent.core.canonical import sha256_digest
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.models import CatalogSnapshotRef, SizingRequest

# Frozen namespace for TASK-009 deterministic UUID5 generation.
TASK009_CONTEXT_NAMESPACE = UUID("a0b1c2d3-e4f5-6789-abcd-ef0123456789")


# ---------------------------------------------------------------------------
# OptimizationObjective
# ---------------------------------------------------------------------------


class OptimizationObjective(StrEnum):
    MINIMIZE_AREA = "minimize_area"
    MINIMIZE_LENGTH = "minimize_length"
    MAXIMIZE_DUTY_MARGIN = "maximize_duty_margin"


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
            if not isinstance(fraction, (int, float)):
                raise TypeError(f"Component fraction must be float, got {type(fraction).__name__}")
            if fraction <= 0 or fraction > 1:
                raise ValueError(f"Component fraction must be in (0, 1], got {fraction}")
            if name in seen:
                raise ValueError(f"Duplicate component name: {name!r}")
            seen.add(name)
            result.append((name, float(fraction)))
        result.sort(key=lambda p: p[0])
        return tuple(result)

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
# Candidate CalculationContext (typed)
# ---------------------------------------------------------------------------


def build_candidate_calculation_context(
    sizing_request_identity: SizingRequestIdentity | str,
    source_qualified_candidate_id: str,
) -> Any:
    """Build a typed ``CalculationContext`` for a single candidate.

    The ``request_id`` is a deterministic UUID5.
    ``design_case_revision_id`` and ``calculation_run_id`` are
    forwarded from the sizing request identity (may be None).

    Returns a ``CalculationContext`` (from ``hexagent.core.heat_balance``).
    """
    from hexagent.core.heat_balance import CalculationContext

    design_id: UUID | None
    run_id: UUID | None
    if isinstance(sizing_request_identity, str):
        digest = sizing_request_identity
        design_id = None
        run_id = None
    else:
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
# PassedSizingGate artifact
# ---------------------------------------------------------------------------


class PassedSizingGate(BaseModel):
    """Immutable artifact created when the Phase 1 cap gate passes.

    Required by Phase 2 materialization entry to proceed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str = "passed"
    sizing_request_identity_digest: str
    raw_combination_count: int
    effective_cap: int
    per_option_records: tuple[Any, ...] = Field(default_factory=tuple)

    @property
    def gate_digest(self) -> str:
        return sha256_digest(self)


__all__ = [
    "ExpectedProviderIdentity",
    "OptimizationObjective",
    "PassedSizingGate",
    "SizingRequestIdentity",
    "TASK009_CONTEXT_NAMESPACE",
    "build_candidate_calculation_context",
    "build_sizing_request_identity",
]
