"""
TASK-009 Phase 2 — TASK-008 adapter with typed CalculationContext,
PassedSizingGate artifact, structured runtime-failure records,
and batch error isolation.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.domain.messages import ErrorCode, RunFailure
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import rate_double_pipe
from hexagent.exchangers.double_pipe.result import RatingResult
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.context import (
    PassedSizingGate,
    SizingRequestIdentity,
    build_candidate_calculation_context,
)
from hexagent.optimization.evaluation import (
    CandidateEvaluationRecord,
    CandidateEvaluationState,
    VerificationOutcome,
)
from hexagent.optimization.identities import ManufacturableCandidate
from hexagent.properties.base import FluidIdentifier, PropertyProvider

# ---------------------------------------------------------------------------
# Rating callable type
# ---------------------------------------------------------------------------

RatingCallable = Callable[..., RatingResult]


# ---------------------------------------------------------------------------
# Geometry builder
# ---------------------------------------------------------------------------


def build_candidate_geometry(
    candidate: ManufacturableCandidate,
) -> DoublePipeGeometry:
    """Build a ``DoublePipeGeometry`` from a materialized candidate."""
    length_m = float(Decimal(candidate.effective_length_m_canonical))
    return DoublePipeGeometry(
        inner_tube_inner_diameter_m=candidate.physical_identity.inner_tube_inner_diameter_m,
        inner_tube_outer_diameter_m=candidate.physical_identity.inner_tube_outer_diameter_m,
        outer_pipe_inner_diameter_m=candidate.physical_identity.outer_pipe_inner_diameter_m,
        effective_length_m=length_m,
        wall_thermal_conductivity_w_m_k=candidate.physical_identity.wall_thermal_conductivity_w_m_k,
        inner_surface_roughness_m=candidate.physical_identity.inner_surface_roughness_m,
        annulus_surface_roughness_m=candidate.physical_identity.annulus_surface_roughness_m,
        inner_fouling_resistance_m2k_w=candidate.physical_identity.inner_fouling_resistance_m2k_w,
        outer_fouling_resistance_m2k_w=candidate.physical_identity.outer_fouling_resistance_m2k_w,
    )


# ---------------------------------------------------------------------------
# Per-candidate rating
# ---------------------------------------------------------------------------


def rate_candidate(
    candidate: ManufacturableCandidate,
    *,
    hot_fluid: FluidIdentifier,
    cold_fluid: FluidIdentifier,
    hot_mass_flow_kg_s: float,
    cold_mass_flow_kg_s: float,
    hot_inlet_temperature_k: float,
    cold_inlet_temperature_k: float,
    hot_inlet_pressure_pa: float,
    cold_inlet_pressure_pa: float,
    tube_in_hot: bool,
    flow_arrangement: FlowArrangement | str,
    provider: PropertyProvider,
    solver_params: SolverParams,
    minimum_terminal_delta_t: float,
    tube_boundary_condition: ThermalBoundaryCondition | str = "adiabatic",
    annulus_boundary_condition: ThermalBoundaryCondition | str = "adiabatic",
    context: Any = None,
    rating_fn: RatingCallable = rate_double_pipe,
) -> RatingResult:
    """Evaluate a single candidate via ``rate_double_pipe()``."""
    geometry = build_candidate_geometry(candidate)

    tbc = (
        ThermalBoundaryCondition(tube_boundary_condition)
        if isinstance(tube_boundary_condition, str)
        else tube_boundary_condition
    )
    abc = (
        ThermalBoundaryCondition(annulus_boundary_condition)
        if isinstance(annulus_boundary_condition, str)
        else annulus_boundary_condition
    )

    fa = (
        flow_arrangement
        if isinstance(flow_arrangement, FlowArrangement)
        else FlowArrangement(flow_arrangement)
    )

    return rating_fn(
        geometry=geometry,
        hot_fluid=hot_fluid,
        cold_fluid=cold_fluid,
        hot_mass_flow_kg_s=hot_mass_flow_kg_s,
        cold_mass_flow_kg_s=cold_mass_flow_kg_s,
        hot_inlet_temperature_k=hot_inlet_temperature_k,
        cold_inlet_temperature_k=cold_inlet_temperature_k,
        hot_inlet_pressure_pa=hot_inlet_pressure_pa,
        cold_inlet_pressure_pa=cold_inlet_pressure_pa,
        tube_in_hot=tube_in_hot,
        flow_arrangement=fa,
        provider=provider,
        solver_params=solver_params,
        context=context,
        minimum_terminal_delta_t=minimum_terminal_delta_t,
        tube_boundary_condition=tbc,
        annulus_boundary_condition=abc,
    )


# ---------------------------------------------------------------------------
# Batch evaluation with typed per-candidate CalculationContext
# ---------------------------------------------------------------------------


def evaluate_all_candidates(
    candidates: tuple[ManufacturableCandidate, ...],
    *,
    hot_fluid: FluidIdentifier,
    cold_fluid: FluidIdentifier,
    hot_mass_flow_kg_s: float,
    cold_mass_flow_kg_s: float,
    hot_inlet_temperature_k: float,
    cold_inlet_temperature_k: float,
    hot_inlet_pressure_pa: float,
    cold_inlet_pressure_pa: float,
    tube_in_hot: bool,
    flow_arrangement: FlowArrangement | str,
    provider: PropertyProvider,
    solver_params: SolverParams,
    minimum_terminal_delta_t: float,
    tube_boundary_condition: ThermalBoundaryCondition | str = "adiabatic",
    annulus_boundary_condition: ThermalBoundaryCondition | str = "adiabatic",
    sizing_request_identity: SizingRequestIdentity,
    gate: PassedSizingGate,
    rating_fn: RatingCallable = rate_double_pipe,
) -> tuple[CandidateEvaluationRecord, ...]:
    """Evaluate all candidates with uniform request parameters.

    Each candidate receives its own typed ``CalculationContext`` via
    ``build_candidate_calculation_context`` (accepting a full
    ``SizingRequestIdentity``).

    One candidate's adapter exception does not abort the entire batch.
    Results preserve canonical candidate order.
    Returns structured ``CandidateEvaluationRecord`` for every candidate.
    """

    # Verify gate
    if not gate.verify_digest():
        raise ValueError("PassedSizingGate digest verification failed")
    if gate.sizing_request_identity_digest != (
        sizing_request_identity.sizing_request_identity_digest
    ):
        raise ValueError("PassedSizingGate request identity digest mismatch")

    results: list[CandidateEvaluationRecord] = []
    for candidate in candidates:
        try:
            ctx = build_candidate_calculation_context(
                sizing_request_identity=sizing_request_identity,
                source_qualified_candidate_id=candidate.source_qualified_candidate_id,
            )
            result = rate_candidate(
                candidate,
                hot_fluid=hot_fluid,
                cold_fluid=cold_fluid,
                hot_mass_flow_kg_s=hot_mass_flow_kg_s,
                cold_mass_flow_kg_s=cold_mass_flow_kg_s,
                hot_inlet_temperature_k=hot_inlet_temperature_k,
                cold_inlet_temperature_k=cold_inlet_temperature_k,
                hot_inlet_pressure_pa=hot_inlet_pressure_pa,
                cold_inlet_pressure_pa=cold_inlet_pressure_pa,
                tube_in_hot=tube_in_hot,
                flow_arrangement=flow_arrangement,
                provider=provider,
                solver_params=solver_params,
                minimum_terminal_delta_t=minimum_terminal_delta_t,
                tube_boundary_condition=tube_boundary_condition,
                annulus_boundary_condition=annulus_boundary_condition,
                context=ctx,
                rating_fn=rating_fn,
            )
        except Exception as exc:
            # Structured runtime failure record — no None sentinel
            results.append(
                CandidateEvaluationRecord(
                    source_qualified_candidate_id=candidate.source_qualified_candidate_id,
                    evaluation_order_index=candidate.evaluation_order_index,
                    candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED.value,
                    feasible=False,
                    hash_verification_outcome=VerificationOutcome.NOT_RUN.value,
                    provenance_verification_outcome=VerificationOutcome.NOT_RUN.value,
                    evaluation_failure=RunFailure(
                        code=ErrorCode.TASK008_ADAPTER,
                        message=f"TASK-008 adapter raised: {exc}",
                    ),
                )
            )
            continue

        # Normal result — pass to verification
        from hexagent.optimization.evaluation import verify_and_evaluate_candidate

        rec = verify_and_evaluate_candidate(
            candidate.evaluation_order_index,
            candidate.source_qualified_candidate_id,
            result,
            sizing_request_identity_digest=sizing_request_identity.sizing_request_identity_digest,
            tube_in_hot=tube_in_hot,
            expected_provider=sizing_request_identity.expected_provider_identity,
        )
        results.append(rec)

    return tuple(results)


__all__ = [
    "RatingCallable",
    "build_candidate_geometry",
    "evaluate_all_candidates",
    "rate_candidate",
]
