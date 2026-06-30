"""TASK-010 application services.

Wraps domain services with registry resolution, canonical request context,
and projection from public API DTOs to domain models.

RatingApplicationService — full rating pipeline.
SizingService — re-exported from sizing_service.py (Phase 1 projection).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hexagent.api.canonical_request import (
    build_rating_canonical_request_context,
    compute_api_request_digest,
)
from hexagent.api.models import (
    RatingApiRequest,
    ResolvedProviderAuthority,
    SolverParamsSpec,
)
from hexagent.api.projection import (
    project_geometry_spec_to_geometry,
    project_solver_spec_to_solver,
    project_validation_to_design_case,
)
from hexagent.api.registry import ProviderRegistry

# Re-export the sizing service (Phase 1 projection) — no duplication.
from hexagent.api.sizing_service import SizingService, SizingServiceResult  # noqa: E402
from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.double_pipe.result import RatingResult
from hexagent.exchangers.double_pipe.service import DoublePipeRatingService
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import PropertyProvider

# ---------------------------------------------------------------------------
# RatingServiceResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RatingServiceResult:
    """Immutable result from the rating application service.

    Carries the domain ``RatingResult`` plus all API-layer artifacts
    needed for envelope construction, audit trails, and provenance.
    """

    result: RatingResult
    resolved_provider: ResolvedProviderAuthority
    request_digest: str
    canonical_request_snapshot: dict[str, Any]
    geometry_artifact: dict[str, Any]
    solver_artifact: dict[str, Any]
    warnings: tuple[Any, ...]
    blockers: tuple[Any, ...]
    provenance: ProvenanceGraph


# ---------------------------------------------------------------------------
# RatingApplicationService
# ---------------------------------------------------------------------------


class RatingApplicationService:
    """Application service for double-pipe rating requests.

    Responsibilities:
    1. Accept validated ``RatingApiRequest``
    2. Resolve provider authority via ``ProviderRegistry``
    3. Build canonical request context and compute request digest
    4. Project API DTOs to domain models
    5. Execute the rating via the real ``DoublePipeRatingService`` kernel
    6. Return a frozen ``RatingServiceResult`` with all artifacts

    The service accepts both a ``ProviderRegistry`` (for authority resolution)
    and a ``PropertyProvider`` (the actual CoolProp instance used by the
    rating kernel).  These are separate concerns: the registry produces
    ``ResolvedProviderAuthority`` for audit/envelope, while the property
    provider supplies fluid properties to the engineering kernel.
    """

    def __init__(
        self,
        *,
        provider_registry: ProviderRegistry,
        property_provider: PropertyProvider,
    ) -> None:
        self._provider_registry = provider_registry
        self._property_provider = property_provider

    def rate(self, request: RatingApiRequest) -> RatingServiceResult:
        """Execute a full rating pipeline.

        Steps:
        1. Resolve provider authority
        2. Build canonical request context
        3. Compute request digest
        4. Project to domain (design case, geometry, solver params)
        5. Parse flow arrangement and boundary conditions
        6. Execute rating via ``DoublePipeRatingService``
        7. Build geometry/solver artifacts
        8. Return frozen ``RatingServiceResult``
        """
        # 1. Resolve provider authority
        resolved = self._provider_registry.resolve(request.provider_ref)

        # 2. Build canonical request context
        context = build_rating_canonical_request_context(
            request=request,
            resolved_provider=resolved,
        )

        # 3. Compute request digest
        request_digest = compute_api_request_digest(context)

        # 4. Project to domain
        design_case = project_validation_to_design_case(request.case)
        geometry = project_geometry_spec_to_geometry(request.geometry)
        effective_solver = project_solver_spec_to_solver(
            request.solver_params if request.solver_params is not None else SolverParamsSpec()
        )

        # 5. Parse flow arrangement and boundary conditions
        flow_arrangement = FlowArrangement(request.flow_arrangement)
        tube_bc = ThermalBoundaryCondition(request.tube_boundary_condition)
        annulus_bc = ThermalBoundaryCondition(request.annulus_boundary_condition)

        # 6. Execute rating using the REAL service with REAL provider
        rating_svc = DoublePipeRatingService(provider=self._property_provider)
        result = rating_svc.rate(
            design_case,
            geometry,
            tube_in_hot=request.tube_in_hot,
            flow_arrangement=flow_arrangement,
            solver_params=effective_solver,
            tube_boundary_condition=tube_bc,
            annulus_boundary_condition=annulus_bc,
            minimum_terminal_delta_t=request.case.minimum_terminal_delta_t.si_value,
        )

        # 7. Build artifacts
        geometry_artifact = {
            "inner_tube_inner_diameter_m": geometry.inner_tube_inner_diameter_m,
            "inner_tube_outer_diameter_m": geometry.inner_tube_outer_diameter_m,
            "outer_pipe_inner_diameter_m": geometry.outer_pipe_inner_diameter_m,
            "effective_length_m": geometry.effective_length_m,
            "wall_thermal_conductivity_w_m_k": geometry.wall_thermal_conductivity_w_m_k,
            "inner_surface_roughness_m": geometry.inner_surface_roughness_m,
            "annulus_surface_roughness_m": geometry.annulus_surface_roughness_m,
        }
        solver_artifact = {
            "absolute_residual_w": effective_solver.absolute_residual_w,
            "relative_residual_fraction": effective_solver.relative_residual_fraction,
            "bracket_temperature_tolerance_k": effective_solver.bracket_temperature_tolerance_k,
            "max_iterations": effective_solver.max_iterations,
        }

        # 8. Return frozen result
        return RatingServiceResult(
            result=result,
            resolved_provider=resolved,
            request_digest=request_digest,
            canonical_request_snapshot=context,
            geometry_artifact=geometry_artifact,
            solver_artifact=solver_artifact,
            warnings=result.warnings,
            blockers=result.blockers,
            provenance=result.provenance_graph,
        )


__all__ = [
    "RatingApplicationService",
    "RatingServiceResult",
    "SizingService",
    "SizingServiceResult",
]
