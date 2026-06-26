"""
TASK-009 Phase 2 — TASK-008 adapter with typed CalculationContext,
MaterializedCandidateSet artifact, input verification, provider consistency,
and strict-stop batch evaluation (P0-10).
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from hexagent.core.heat_balance import CalculationContext
from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.domain.messages import ErrorCode, RunFailure
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import rate_double_pipe
from hexagent.exchangers.double_pipe.result import RatingResult
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.context import (
    MaterializedCandidateSet,
    SizingRequestIdentity,
    build_candidate_calculation_context,
)
from hexagent.optimization.evaluation import (
    CandidateEvaluationRecord,
    CandidateEvaluationState,
    VerificationOutcome,
    check_provider_consistency,
    verify_and_evaluate_candidate,
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
# Input-parameter verification (P0-4)
# ---------------------------------------------------------------------------


def _verify_identity_consistency(
    sizing_request_identity: SizingRequestIdentity,
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
    tube_boundary_condition: ThermalBoundaryCondition | str,
    annulus_boundary_condition: ThermalBoundaryCondition | str,
    minimum_terminal_delta_t: float,
    solver_params: SolverParams,
) -> None:
    """Verify actual computation parameters match ``SizingRequestIdentity``.

    Raises ``ValueError`` on any mismatch.
    """
    errors: list[str] = []

    # Fluid identity
    if hot_fluid.name != sizing_request_identity.hot_fluid_name:
        errors.append(
            f"hot_fluid.name={hot_fluid.name!r} != "
            f"sizing_request_identity.hot_fluid_name={sizing_request_identity.hot_fluid_name!r}"
        )
    if hot_fluid.equation_of_state_backend != sizing_request_identity.hot_fluid_equation_of_state:
        errors.append(
            f"hot_fluid.equation_of_state_backend={hot_fluid.equation_of_state_backend!r} != "
            f"sizing_request_identity.hot_fluid_equation_of_state="
            f"{sizing_request_identity.hot_fluid_equation_of_state!r}"
        )
    if cold_fluid.name != sizing_request_identity.cold_fluid_name:
        errors.append(
            f"cold_fluid.name={cold_fluid.name!r} != "
            f"sizing_request_identity.cold_fluid_name={sizing_request_identity.cold_fluid_name!r}"
        )
    if cold_fluid.equation_of_state_backend != sizing_request_identity.cold_fluid_equation_of_state:
        errors.append(
            f"cold_fluid.equation_of_state_backend={cold_fluid.equation_of_state_backend!r} != "
            f"sizing_request_identity.cold_fluid_equation_of_state="
            f"{sizing_request_identity.cold_fluid_equation_of_state!r}"
        )

    # Fluid components (P0-3): compare canonical-sorted (name, fraction) tuples
    hot_components = tuple(sorted(hot_fluid.components, key=lambda p: p[0]))
    if hot_components != sizing_request_identity.hot_fluid_normalized_components:
        errors.append(
            f"hot_fluid.components={hot_components} != "
            f"sizing_request_identity.hot_fluid_normalized_components="
            f"{sizing_request_identity.hot_fluid_normalized_components}"
        )
    cold_components = tuple(sorted(cold_fluid.components, key=lambda p: p[0]))
    if cold_components != sizing_request_identity.cold_fluid_normalized_components:
        errors.append(
            f"cold_fluid.components={cold_components} != "
            f"sizing_request_identity.cold_fluid_normalized_components="
            f"{sizing_request_identity.cold_fluid_normalized_components}"
        )

    # Inlet conditions
    if hot_mass_flow_kg_s != sizing_request_identity.hot_mass_flow_kg_s:
        errors.append(
            f"hot_mass_flow_kg_s={hot_mass_flow_kg_s} != "
            f"sizing_request_identity.hot_mass_flow_kg_s={sizing_request_identity.hot_mass_flow_kg_s}"
        )
    if cold_mass_flow_kg_s != sizing_request_identity.cold_mass_flow_kg_s:
        errors.append(
            f"cold_mass_flow_kg_s={cold_mass_flow_kg_s} != "
            f"sizing_request_identity.cold_mass_flow_kg_s={sizing_request_identity.cold_mass_flow_kg_s}"
        )
    if hot_inlet_temperature_k != sizing_request_identity.hot_inlet_temperature_k:
        errors.append(
            f"hot_inlet_temperature_k={hot_inlet_temperature_k} != "
            f"sizing_request_identity.hot_inlet_temperature_k={sizing_request_identity.hot_inlet_temperature_k}"
        )
    if cold_inlet_temperature_k != sizing_request_identity.cold_inlet_temperature_k:
        errors.append(
            f"cold_inlet_temperature_k={cold_inlet_temperature_k} != "
            f"sizing_request_identity.cold_inlet_temperature_k={sizing_request_identity.cold_inlet_temperature_k}"
        )
    if hot_inlet_pressure_pa != sizing_request_identity.hot_inlet_pressure_pa:
        errors.append(
            f"hot_inlet_pressure_pa={hot_inlet_pressure_pa} != "
            f"sizing_request_identity.hot_inlet_pressure_pa={sizing_request_identity.hot_inlet_pressure_pa}"
        )
    if cold_inlet_pressure_pa != sizing_request_identity.cold_inlet_pressure_pa:
        errors.append(
            f"cold_inlet_pressure_pa={cold_inlet_pressure_pa} != "
            f"sizing_request_identity.cold_inlet_pressure_pa={sizing_request_identity.cold_inlet_pressure_pa}"
        )

    # Flow configuration
    actual_flow_arrangement = (
        flow_arrangement.value
        if isinstance(flow_arrangement, FlowArrangement)
        else flow_arrangement
    )
    if actual_flow_arrangement != sizing_request_identity.flow_arrangement:
        errors.append(
            f"flow_arrangement={actual_flow_arrangement!r} != "
            f"sizing_request_identity.flow_arrangement={sizing_request_identity.flow_arrangement!r}"
        )

    if tube_in_hot != sizing_request_identity.tube_in_hot:
        errors.append(
            f"tube_in_hot={tube_in_hot} != "
            f"sizing_request_identity.tube_in_hot={sizing_request_identity.tube_in_hot}"
        )

    actual_tube_bc = (
        tube_boundary_condition.value
        if isinstance(tube_boundary_condition, ThermalBoundaryCondition)
        else tube_boundary_condition
    )
    if actual_tube_bc != sizing_request_identity.tube_boundary_condition:
        errors.append(
            f"tube_boundary_condition={actual_tube_bc!r} != "
            f"sizing_request_identity.tube_boundary_condition={sizing_request_identity.tube_boundary_condition!r}"
        )

    actual_annulus_bc = (
        annulus_boundary_condition.value
        if isinstance(annulus_boundary_condition, ThermalBoundaryCondition)
        else annulus_boundary_condition
    )
    if actual_annulus_bc != sizing_request_identity.annulus_boundary_condition:
        errors.append(
            f"annulus_boundary_condition={actual_annulus_bc!r} != "
            f"sizing_request_identity.annulus_boundary_condition="
            f"{sizing_request_identity.annulus_boundary_condition!r}"
        )

    # Duty parameters
    if minimum_terminal_delta_t != sizing_request_identity.minimum_terminal_delta_t:
        errors.append(
            f"minimum_terminal_delta_t={minimum_terminal_delta_t} != "
            f"sizing_request_identity.minimum_terminal_delta_t={sizing_request_identity.minimum_terminal_delta_t}"
        )

    # Solver parameters
    if (
        solver_params.absolute_residual_w
        != sizing_request_identity.rating_solver_absolute_residual_w
    ):
        errors.append(
            f"solver_params.absolute_residual_w={solver_params.absolute_residual_w} != "
            f"sizing_request_identity.rating_solver_absolute_residual_w="
            f"{sizing_request_identity.rating_solver_absolute_residual_w}"
        )
    if (
        solver_params.relative_residual_fraction
        != sizing_request_identity.rating_solver_relative_residual_fraction
    ):
        errors.append(
            f"solver_params.relative_residual_fraction="
            f"{solver_params.relative_residual_fraction} != "
            f"sizing_request_identity.rating_solver_relative_residual_fraction="
            f"{sizing_request_identity.rating_solver_relative_residual_fraction}"
        )
    if (
        solver_params.bracket_temperature_tolerance_k
        != sizing_request_identity.rating_solver_bracket_temperature_tolerance_k
    ):
        errors.append(
            f"solver_params.bracket_temperature_tolerance_k="
            f"{solver_params.bracket_temperature_tolerance_k} != "
            f"sizing_request_identity.rating_solver_bracket_temperature_tolerance_k="
            f"{sizing_request_identity.rating_solver_bracket_temperature_tolerance_k}"
        )
    if solver_params.max_iterations != sizing_request_identity.rating_solver_max_iterations:
        errors.append(
            f"solver_params.max_iterations={solver_params.max_iterations} != "
            f"sizing_request_identity.rating_solver_max_iterations="
            f"{sizing_request_identity.rating_solver_max_iterations}"
        )

    if errors:
        raise ValueError(
            "Input parameter mismatch with SizingRequestIdentity:\n  - " + "\n  - ".join(errors)
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
    context: CalculationContext,
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
# Batch evaluation with strict-stop (P0-10) and provider consistency (P0-5)
# ---------------------------------------------------------------------------


def evaluate_all_candidates(
    candidate_set: MaterializedCandidateSet,
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
    rating_fn: RatingCallable = rate_double_pipe,
) -> tuple[CandidateEvaluationRecord, ...]:
    """Evaluate all candidates with strict serial pipeline (P0-1, P0-10).

    Accepts a ``MaterializedCandidateSet`` artifact for provenance verification
    (replaces separate ``candidates`` + ``gate`` params).

    Strict serial pipeline (P0-1):
      For each candidate in sequence:
        1. Build ``CalculationContext``
        2. Call ``rate_candidate()``
        3. Call ``verify_and_evaluate_candidate()`` for hash + provenance verification
      - If adapter raises → emit ``RUNTIME_FAILED`` for that candidate,
        ``UNEVALUATED`` for all remaining candidates, STOP.
      - If hash/provenance fails → emit ``UNEVALUATED`` for all remaining
        candidates, STOP.

    After all candidates are processed, ``check_provider_consistency()`` is
    applied to the full result set (P0-5).
    """

    # ------------------------------------------------------------------
    # P0-3: Verify MaterializedCandidateSet
    # ------------------------------------------------------------------
    if not candidate_set.verify_digest():
        raise ValueError("MaterializedCandidateSet digest verification failed")
    if candidate_set.sizing_request_identity_digest != (
        sizing_request_identity.sizing_request_identity_digest
    ):
        raise ValueError("MaterializedCandidateSet sizing_request_identity_digest mismatch")

    # Verify candidate ordering matches the set's ordered_candidate_ids
    actual_ids = tuple(c.source_qualified_candidate_id for c in candidates)
    if actual_ids != candidate_set.ordered_candidate_ids:
        raise ValueError(
            f"Candidate ordering mismatch with MaterializedCandidateSet: "
            f"expected {candidate_set.ordered_candidate_ids}, "
            f"got {actual_ids}"
        )

    # ------------------------------------------------------------------
    # P0-4: Verify input parameters against SizingRequestIdentity
    # ------------------------------------------------------------------
    _verify_identity_consistency(
        sizing_request_identity=sizing_request_identity,
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
        tube_boundary_condition=tube_boundary_condition,
        annulus_boundary_condition=annulus_boundary_condition,
        minimum_terminal_delta_t=minimum_terminal_delta_t,
        solver_params=solver_params,
    )

    # ------------------------------------------------------------------
    # P0-1: Strict serial pipeline — rate then verify per candidate
    # ------------------------------------------------------------------
    results: list[CandidateEvaluationRecord] = []
    strict_stop = False

    for candidate in candidates:
        if strict_stop:
            results.append(
                CandidateEvaluationRecord(
                    source_qualified_candidate_id=candidate.source_qualified_candidate_id,
                    evaluation_order_index=candidate.evaluation_order_index,
                    candidate_evaluation_state=CandidateEvaluationState.UNEVALUATED,
                    feasible=False,
                    hash_verification_outcome=VerificationOutcome.NOT_RUN,
                    provenance_verification_outcome=VerificationOutcome.NOT_RUN,
                )
            )
            continue

        # --- Step 1: Build CalculationContext ---
        ctx = build_candidate_calculation_context(
            sizing_request_identity=sizing_request_identity,
            source_qualified_candidate_id=candidate.source_qualified_candidate_id,
        )

        # --- Step 2: Rate candidate (adapter) ---
        try:
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
            results.append(
                CandidateEvaluationRecord(
                    source_qualified_candidate_id=candidate.source_qualified_candidate_id,
                    evaluation_order_index=candidate.evaluation_order_index,
                    candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED,
                    feasible=False,
                    hash_verification_outcome=VerificationOutcome.NOT_RUN,
                    provenance_verification_outcome=VerificationOutcome.NOT_RUN,
                    evaluation_failure=RunFailure(
                        code=ErrorCode.TASK008_ADAPTER,
                        message=f"TASK-008 adapter raised: {exc}",
                    ),
                )
            )
            strict_stop = True
            continue

        # --- Step 3: Verify hash + provenance ---
        rec = verify_and_evaluate_candidate(
            candidate.evaluation_order_index,
            candidate.source_qualified_candidate_id,
            result,
            sizing_request_identity_digest=(sizing_request_identity.sizing_request_identity_digest),
            tube_in_hot=tube_in_hot,
            expected_provider=sizing_request_identity.expected_provider_identity,
        )

        # Activate strict stop on verification failure
        if rec.candidate_evaluation_state in (
            CandidateEvaluationState.RUNTIME_FAILED,
            CandidateEvaluationState.INTEGRITY_INVALID,
        ):
            strict_stop = True

        results.append(rec)

    # ------------------------------------------------------------------
    # P0-5: Provider consistency across all candidates
    # ------------------------------------------------------------------
    merged = check_provider_consistency(tuple(results))

    return merged


__all__ = [
    "RatingCallable",
    "build_candidate_geometry",
    "evaluate_all_candidates",
    "rate_candidate",
]
