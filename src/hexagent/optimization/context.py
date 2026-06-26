"""
TASK-009 Phase 2 — SizingRequestIdentity, candidate calculation context,
and deterministic UUID5-based request IDs.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field

from hexagent.core.canonical import sha256_digest
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.models import CatalogSnapshotRef, SizingRequest

# Frozen namespace for TASK-009 deterministic UUID5 generation.
TASK009_CONTEXT_NAMESPACE = UUID("a0b1c2d3-e4f5-6789-abcd-ef0123456789")


# ---------------------------------------------------------------------------
# ExpectedProviderIdentity
# ---------------------------------------------------------------------------


class ExpectedProviderIdentity(BaseModel):
    """The provider identity that TASK-009 expects TASK-008 to use.

    All candidates in a sizing run must use the same provider instance
    with matching identity.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    git_revision: str
    reference_state_policy: str
    configuration_fingerprint: str | None = None
    cache_policy_version: str | None = None

    def matches(self, actual: Any) -> bool:
        """Check if *actual* (e.g. ProviderIdentitySnapshot) matches.

        ``name``, ``version``, ``git_revision``, ``reference_state_policy``
        are mandatory matches.  ``configuration_fingerprint`` and
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
# SizingRequestIdentity — full immutable identity of a sizing request
# ---------------------------------------------------------------------------


class SizingRequestIdentity(BaseModel):
    """Complete immutable identity of a sizing + candidate optimization request.

    Captures all fields that drive the engineering analysis, suitable
    for provenance, audit, and repeatability verification.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- Fluid & duty ---
    hot_fluid_name: str
    hot_fluid_backend: str
    hot_fluid_components: tuple[tuple[str, float], ...] = Field(default_factory=tuple)
    cold_fluid_name: str
    cold_fluid_backend: str
    cold_fluid_components: tuple[tuple[str, float], ...] = Field(default_factory=tuple)
    hot_mass_flow_kg_s: float
    cold_mass_flow_kg_s: float
    hot_inlet_temperature_k: float
    cold_inlet_temperature_k: float
    hot_inlet_pressure_pa: float
    cold_inlet_pressure_pa: float
    tube_in_hot: bool
    flow_arrangement: FlowArrangement
    minimum_terminal_delta_t: float
    required_duty_w: float | None = None

    # --- Bounds & cap ---
    minimum_effective_length_m: float | None = None
    maximum_effective_length_m: float | None = None
    request_raw_combination_cap: int | None = None
    top_n: int | None = None

    # --- Solver params ---
    solver_absolute_residual_w: float
    solver_relative_residual_fraction: float
    solver_bracket_temperature_tolerance_k: float
    solver_max_iterations: int

    # --- Boundary conditions ---
    tube_boundary_condition: str
    annulus_boundary_condition: str

    # --- Catalog refs (canonical ordered) ---
    catalog_refs: tuple[CatalogSnapshotRef, ...] = Field(default_factory=tuple)

    # --- Expected provider ---
    expected_provider: ExpectedProviderIdentity | None = None

    # --- Domain context ---
    design_case_revision_id: str | None = None
    calculation_run_id: str | None = None
    rating_software_version: str = ""
    execution_context_policy_version: str = ""

    @property
    def sizing_request_identity_digest(self) -> str:
        """Deterministic SHA-256 content hash of the full identity.

        Any field mutation changes the digest.
        """
        return sha256_digest(self)


# ---------------------------------------------------------------------------
# Build SizingRequestIdentity from a SizingRequest + processing context
# ---------------------------------------------------------------------------


def build_sizing_request_identity(
    request: SizingRequest,
    *,
    hot_fluid_name: str,
    hot_fluid_backend: str,
    cold_fluid_name: str,
    cold_fluid_backend: str,
    hot_mass_flow_kg_s: float,
    cold_mass_flow_kg_s: float,
    hot_inlet_temperature_k: float,
    cold_inlet_temperature_k: float,
    hot_inlet_pressure_pa: float,
    cold_inlet_pressure_pa: float,
    tube_in_hot: bool,
    flow_arrangement: FlowArrangement,
    minimum_terminal_delta_t: float,
    required_duty_w: float | None = None,
    solver_params: SolverParams | None = None,
    tube_boundary_condition: str = "adiabatic",
    annulus_boundary_condition: str = "adiabatic",
    expected_provider: ExpectedProviderIdentity | None = None,
    design_case_revision_id: str | None = None,
    calculation_run_id: str | None = None,
    rating_software_version: str = "",
    execution_context_policy_version: str = "",
    hot_fluid_components: tuple[tuple[str, float], ...] = (),
    cold_fluid_components: tuple[tuple[str, float], ...] = (),
) -> SizingRequestIdentity:
    """Construct a ``SizingRequestIdentity`` from a request + explicit params.

    Catalog refs are extracted from the request and sorted by identity
    key for canonical ordering.
    """
    from hexagent.optimization.catalog import catalog_identity_key

    # Sort catalog refs canonically
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

    sp = solver_params or SolverParams()

    return SizingRequestIdentity(
        hot_fluid_name=hot_fluid_name,
        hot_fluid_backend=hot_fluid_backend,
        hot_fluid_components=hot_fluid_components,
        cold_fluid_name=cold_fluid_name,
        cold_fluid_backend=cold_fluid_backend,
        cold_fluid_components=cold_fluid_components,
        hot_mass_flow_kg_s=hot_mass_flow_kg_s,
        cold_mass_flow_kg_s=cold_mass_flow_kg_s,
        hot_inlet_temperature_k=hot_inlet_temperature_k,
        cold_inlet_temperature_k=cold_inlet_temperature_k,
        hot_inlet_pressure_pa=hot_inlet_pressure_pa,
        cold_inlet_pressure_pa=cold_inlet_pressure_pa,
        tube_in_hot=tube_in_hot,
        flow_arrangement=flow_arrangement,
        minimum_terminal_delta_t=minimum_terminal_delta_t,
        required_duty_w=required_duty_w,
        minimum_effective_length_m=request.minimum_effective_length_m,
        maximum_effective_length_m=request.maximum_effective_length_m,
        request_raw_combination_cap=request.request_raw_combination_cap,
        solver_absolute_residual_w=sp.absolute_residual_w,
        solver_relative_residual_fraction=sp.relative_residual_fraction,
        solver_bracket_temperature_tolerance_k=sp.bracket_temperature_tolerance_k,
        solver_max_iterations=sp.max_iterations,
        tube_boundary_condition=tube_boundary_condition,
        annulus_boundary_condition=annulus_boundary_condition,
        catalog_refs=refs,
        expected_provider=expected_provider,
        design_case_revision_id=design_case_revision_id,
        calculation_run_id=calculation_run_id,
        rating_software_version=rating_software_version,
        execution_context_policy_version=execution_context_policy_version,
    )


# ---------------------------------------------------------------------------
# Candidate calculation context (UUID5-based, deterministic)
# ---------------------------------------------------------------------------


def candidate_request_id(
    sizing_request_identity_digest: str,
    source_qualified_candidate_id: str,
) -> UUID:
    """Deterministic UUID5 for a single candidate evaluation.

    The name is ``<digest>:<sq_id>``.
    """
    name = f"{sizing_request_identity_digest}:{source_qualified_candidate_id}"
    return uuid5(TASK009_CONTEXT_NAMESPACE, name)


__all__ = [
    "ExpectedProviderIdentity",
    "SizingRequestIdentity",
    "TASK009_CONTEXT_NAMESPACE",
    "build_sizing_request_identity",
    "candidate_request_id",
]
