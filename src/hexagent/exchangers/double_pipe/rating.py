"""Main rating kernel for fixed-geometry double-pipe heat exchangers.

This module provides the ``rate_double_pipe()`` pure function that
solves for heat duty Q via a Brent root-finding iteration on the
residual ``Q − UA(Q)·LMTD(Q)``.  Each residual evaluation:

1. Back-calculates trial outlet enthalpies from Q
2. Retrieves outlet states via PropertyProvider.state_ph()
3. Retrieves bulk states via PropertyProvider.state_tp() at T_bulk
4. Calls TASK-007 correlation service for tube and annulus sides
5. Builds thermal resistance and computes UA
6. Computes LMTD and residual

The function ALWAYS returns a RatingResult; it never raises for domain errors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid5

from hexagent.core.heat_balance import (
    CalculationContext,
    ExecutionContextSnapshot,
    PropertyCallRecord,
    ProviderIdentitySnapshot,
)
from hexagent.correlations.flow import FlowPropertiesInput, ThermalBoundaryCondition
from hexagent.correlations.geometry import CircularTubeGeometry, ConcentricAnnulusGeometry
from hexagent.correlations.hx_result import CorrelationResult
from hexagent.correlations.service import CalculationContext as CorrCalculationContext
from hexagent.correlations.service import evaluate_hx_correlation
from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity, ErrorCode
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.result import (
    ApplicabilitySnapshot,
    FluidStateSnapshot,
    RatingRequestIdentity,
    RatingResult,
    RatingStatus,
    ResistanceBreakdownModel,
    SelectedCorrelationSnapshot,
    SolverDetailsModel,
    _provenance_graph_digest,
    build_provenance,
    build_provenance_core,
    compute_result_hash,
)
from hexagent.exchangers.double_pipe.solver import (
    SolverParams,
    SolverResult,
    SolverTermination,
    solve_rating,
)
from hexagent.exchangers.double_pipe.thermal import (
    FlowArrangement,
    ThermalResistanceBreakdown,
    build_thermal_resistance,
    compute_wall_resistance,
    effectiveness_counterflow,
    effectiveness_parallel,
    lmtd_counterflow,
    lmtd_parallel,
)
from hexagent.properties.base import FluidIdentifier, FluidState, PhaseRegion, PropertyProvider
from hexagent.properties.errors import PropertyServiceError

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

_SOFTWARE_VERSION = "0.1.0"
_PROVENANCE_NAMESPACE = uuid5(
    UUID("00000000-0000-0000-0000-000000000000"),
    "hexagent:double_pipe_rating:provenance",
)

# Allowed single-phase regions
_SINGLE_PHASE: frozenset[PhaseRegion] = frozenset(
    {
        PhaseRegion.LIQUID,
        PhaseRegion.GAS,
        PhaseRegion.SUPERCRITICAL,
        PhaseRegion.SUPERCRITICAL_GAS,
        PhaseRegion.SUPERCRITICAL_LIQUID,
    }
)

# Default minimum terminal temperature difference [K]
_DEFAULT_MINIMUM_TERMINAL_DELTA_T = 0.5

# Energy balance closure tolerance
_ENERGY_RESIDUAL_ABS_TOL = 1e-3
_ENERGY_RESIDUAL_REL_TOL = 1e-8


# ---------------------------------------------------------------------------
# Trial evaluation dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrialEvaluation:
    """Immutable snapshot of a single trial Q evaluation."""

    q_w: float
    residual_w: float | None
    feasible: bool
    hot_outlet_state: FluidState | None
    cold_outlet_state: FluidState | None
    hot_bulk_state: FluidState | None
    cold_bulk_state: FluidState | None
    tube_flow_input: FlowPropertiesInput | None
    annulus_flow_input: FlowPropertiesInput | None
    tube_result: CorrelationResult | None
    annulus_result: CorrelationResult | None
    property_calls: tuple[PropertyCallRecord, ...]
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_warning(
    code: ErrorCode,
    message: str,
    context: tuple[tuple[str, Any], ...] = (),
) -> EngineeringMessage:
    return EngineeringMessage(
        code=code,
        severity=EngineeringMessageSeverity.WARNING,
        message=message,
        source_module="exchangers.double_pipe.rating",
        context=context,
    )


def _make_blocker(
    code: ErrorCode,
    message: str,
    context: tuple[tuple[str, Any], ...] = (),
) -> EngineeringMessage:
    return EngineeringMessage(
        code=code,
        severity=EngineeringMessageSeverity.BLOCKER,
        message=message,
        source_module="exchangers.double_pipe.rating",
        context=context,
    )


def _provider_snapshot(provider: PropertyProvider | None) -> ProviderIdentitySnapshot:
    """Build a ProviderIdentitySnapshot from the provider."""
    if provider is None:
        return ProviderIdentitySnapshot(
            name="",
            version="",
            git_revision="",
            reference_state_policy="",
        )
    return ProviderIdentitySnapshot(
        name=provider.name,
        version=provider.version,
        git_revision=getattr(provider, "git_revision", ""),
        reference_state_policy=provider.reference_state_policy.value,
    )


def _make_fluid_state_snapshot(state: FluidState) -> FluidStateSnapshot:
    """Build a FluidStateSnapshot from a FluidState."""
    return FluidStateSnapshot(
        temperature_k=state.temperature_k,
        pressure_pa=state.pressure_pa,
        enthalpy_j_kg=state.enthalpy_j_kg,
        density_kg_m3=state.density_kg_m3,
        cp_j_kg_k=state.cp_j_kg_k,
        viscosity_pa_s=state.viscosity_pa_s,
        conductivity_w_m_k=state.conductivity_w_m_k,
        phase=state.phase.value,
    )


def _make_selected_correlation_snapshot(
    corr_result: CorrelationResult,
) -> SelectedCorrelationSnapshot | None:
    """Build a SelectedCorrelationSnapshot from a CorrelationResult."""
    sc = corr_result.selected_correlation
    if sc is None:
        return None
    return SelectedCorrelationSnapshot(
        correlation_id=sc.correlation_id,
        version=sc.version,
    )


def _make_applicability_snapshot(
    corr_result: CorrelationResult,
) -> ApplicabilitySnapshot | None:
    """Build an ApplicabilitySnapshot from a CorrelationResult."""
    aa = corr_result.applicability_assessment
    if aa is None:
        return None
    return ApplicabilitySnapshot(
        status=corr_result.applicability_status,
    )


def _build_request_identity(
    *,
    geometry: DoublePipeGeometry,
    hot_fluid: FluidIdentifier,
    cold_fluid: FluidIdentifier,
    hot_mass_flow_kg_s: float,
    cold_mass_flow_kg_s: float,
    hot_inlet_temperature_k: float,
    cold_inlet_temperature_k: float,
    hot_inlet_pressure_pa: float,
    cold_inlet_pressure_pa: float,
    flow_arrangement: FlowArrangement,
    solver_params: SolverParams,
    minimum_terminal_delta_t: float,
    tube_boundary_condition: ThermalBoundaryCondition,
    annulus_boundary_condition: ThermalBoundaryCondition,
) -> RatingRequestIdentity:
    return RatingRequestIdentity(
        hot_fluid_name=hot_fluid.name,
        hot_fluid_backend=hot_fluid.equation_of_state_backend,
        hot_fluid_components=hot_fluid.components,
        cold_fluid_name=cold_fluid.name,
        cold_fluid_backend=cold_fluid.equation_of_state_backend,
        cold_fluid_components=cold_fluid.components,
        hot_mass_flow_kg_s=hot_mass_flow_kg_s,
        cold_mass_flow_kg_s=cold_mass_flow_kg_s,
        hot_inlet_pressure_pa=hot_inlet_pressure_pa,
        cold_inlet_pressure_pa=cold_inlet_pressure_pa,
        hot_inlet_temperature_k=hot_inlet_temperature_k,
        cold_inlet_temperature_k=cold_inlet_temperature_k,
        flow_arrangement=flow_arrangement.value,
        geometry=geometry.to_dict(),
        solver_absolute_residual_w=solver_params.absolute_residual_w,
        solver_relative_residual_fraction=solver_params.relative_residual_fraction,
        solver_bracket_temperature_tolerance_k=solver_params.bracket_temperature_tolerance_k,
        solver_max_iterations=solver_params.max_iterations,
        minimum_terminal_delta_t=minimum_terminal_delta_t,
        tube_boundary_condition=tube_boundary_condition.value,
        annulus_boundary_condition=annulus_boundary_condition.value,
    )


def _build_provider_call_record(
    state: FluidState,
    *,
    query_type: str,
    inputs: tuple[tuple[str, float], ...],
    provider: PropertyProvider,
    stage: str,
    stream_role: str,
    sequence_index: int,
    success: bool = True,
    error_code: str | None = None,
    error_message: str | None = None,
) -> PropertyCallRecord:
    prov = state.provenance
    return PropertyCallRecord(
        fluid=prov.fluid_identifier,
        query_type=query_type,
        inputs=inputs,
        backend_name=prov.backend_name,
        backend_version=prov.backend_version,
        reference_state_policy=prov.reference_state_policy.value,
        stage=stage,
        result_temperature_k=state.temperature_k,
        result_pressure_pa=state.pressure_pa,
        result_enthalpy_j_kg=state.enthalpy_j_kg,
        result_phase=state.phase.value,
        result_density_kg_m3=state.density_kg_m3,
        result_cp_j_kg_k=state.cp_j_kg_k,
        result_viscosity_pa_s=state.viscosity_pa_s,
        result_conductivity_w_m_k=state.conductivity_w_m_k,
        result_entropy_j_kg_k=state.entropy_j_kg_k,
        result_quality=state.quality,
        success=success,
        error_code=error_code,
        error_message=error_message,
        stream_role=stream_role,
        sequence_index=sequence_index,
        backend_git_revision=getattr(provider, "git_revision", ""),
        configuration_fingerprint=prov.configuration_fingerprint,
        validation_level=prov.validation_level.value,
        cache_policy_version=prov.cache_policy_version,
    )


def _build_failed_provider_call_record(
    *,
    fluid_name: str,
    query_type: str,
    inputs: tuple[tuple[str, float], ...],
    provider: PropertyProvider,
    stage: str,
    stream_role: str,
    sequence_index: int,
    error_code: str,
    error_message: str,
) -> PropertyCallRecord:
    return PropertyCallRecord(
        fluid=fluid_name,
        query_type=query_type,
        inputs=inputs,
        backend_name=provider.name,
        backend_version=provider.version,
        reference_state_policy=provider.reference_state_policy.value,
        stage=stage,
        success=False,
        error_code=error_code,
        error_message=error_message,
        stream_role=stream_role,
        sequence_index=sequence_index,
    )


# ---------------------------------------------------------------------------
# Quick-blocked/failed result builder
# ---------------------------------------------------------------------------


def _make_solver_details(solver_result: SolverResult) -> SolverDetailsModel:
    return SolverDetailsModel(
        iterations=solver_result.iterations,
        residual_w=solver_result.residual_w,
        initial_bracket_low_w=solver_result.initial_bracket_low_w,
        initial_bracket_high_w=solver_result.initial_bracket_high_w,
        final_bracket_low_w=solver_result.final_bracket_low_w,
        final_bracket_high_w=solver_result.final_bracket_high_w,
        final_bracket_width_w=solver_result.final_bracket_width_w,
        final_bracket_temperature_effect_k=solver_result.final_bracket_temperature_effect_k,
        function_evaluations=solver_result.function_evaluations,
        termination_reason=solver_result.termination_reason.value,
        residual_tolerance_w=max(
            solver_result.solver_params.absolute_residual_w,
            solver_result.solver_params.relative_residual_fraction
            * max(abs(solver_result.q_solution_w), 1.0),
        ),
    )


def _make_resistance_breakdown(
    R: ThermalResistanceBreakdown,
) -> ResistanceBreakdownModel:
    return ResistanceBreakdownModel(
        r_conv_inner=R.r_conv_inner,
        r_foul_inner=R.r_foul_inner,
        r_wall=R.r_wall,
        r_foul_outer=R.r_foul_outer,
        r_conv_outer=R.r_conv_outer,
        total_resistance=R.total_resistance_kw,
        ua_w_k=R.ua_w_k,
    )


def _build_empty_resistance() -> ResistanceBreakdownModel:
    return ResistanceBreakdownModel(
        r_conv_inner=0.0,
        r_foul_inner=0.0,
        r_wall=0.0,
        r_foul_outer=0.0,
        r_conv_outer=0.0,
        total_resistance=0.0,
        ua_w_k=0.0,
    )


def _build_empty_solver_details() -> SolverDetailsModel:
    return SolverDetailsModel(
        iterations=0,
        residual_w=0.0,
        initial_bracket_low_w=0.0,
        initial_bracket_high_w=0.0,
        final_bracket_low_w=0.0,
        final_bracket_high_w=0.0,
        final_bracket_width_w=0.0,
        final_bracket_temperature_effect_k=0.0,
        function_evaluations=0,
        termination_reason="not_started",
        residual_tolerance_w=0.0,
    )


def _blocked_result(
    *,
    blockers: list[EngineeringMessage],
    warnings: list[EngineeringMessage] | None = None,
    property_calls: list[PropertyCallRecord] | None = None,
    request_identity: RatingRequestIdentity | None = None,
    provider_identity: ProviderIdentitySnapshot | None = None,
    execution_context: ExecutionContextSnapshot | None = None,
    flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW,
) -> RatingResult:
    """Build a BLOCKED RatingResult with full provenance."""
    ctx = execution_context or ExecutionContextSnapshot()
    warnings = warnings or []
    property_calls = property_calls or []
    provider_identity = provider_identity or ProviderIdentitySnapshot(
        name="",
        version="",
        git_revision="",
        reference_state_policy="",
    )
    ri = request_identity or RatingRequestIdentity(
        hot_fluid_name="",
        hot_fluid_backend="HEOS",
        hot_fluid_components=(),
        cold_fluid_name="",
        cold_fluid_backend="HEOS",
        cold_fluid_components=(),
        hot_mass_flow_kg_s=0.0,
        cold_mass_flow_kg_s=0.0,
        hot_inlet_pressure_pa=0.0,
        cold_inlet_pressure_pa=0.0,
        hot_inlet_temperature_k=0.0,
        cold_inlet_temperature_k=0.0,
        flow_arrangement=flow_arrangement.value,
        geometry={},
        solver_absolute_residual_w=0.0,
        solver_relative_residual_fraction=0.0,
        solver_bracket_temperature_tolerance_k=0.0,
        solver_max_iterations=0,
        minimum_terminal_delta_t=0.0,
        tube_boundary_condition="constant_wall_temperature",
        annulus_boundary_condition="inner_wall_heated",
    )

    # Compute core provenance (without RESULT node)
    core_graph, core_nodes, core_edges = build_provenance_core(
        flow_arrangement=flow_arrangement,
        property_calls=property_calls,
        iterations=0,
        converged=False,
        warnings=warnings,
        blockers=blockers,
        execution_context=ctx,
        request_identity=ri,
    )
    core_provenance_digest = _provenance_graph_digest(core_graph)

    # Compute result hash from core_provenance_digest
    result_hash = compute_result_hash(
        request_identity=ri,
        provider_identity=provider_identity,
        flow_arrangement=flow_arrangement,
        heat_duty_w=None,
        hot_outlet_temperature_k=None,
        cold_outlet_temperature_k=None,
        tube_reynolds=None,
        tube_prandtl=None,
        tube_nusselt=None,
        tube_h=None,
        tube_selected_correlation_id=None,
        tube_selected_correlation_version=None,
        tube_applicability_status=None,
        annulus_reynolds=None,
        annulus_prandtl=None,
        annulus_nusselt=None,
        annulus_h=None,
        annulus_selected_correlation_id=None,
        annulus_selected_correlation_version=None,
        annulus_applicability_status=None,
        area_inner_m2=0.0,
        area_outer_m2=0.0,
        resistance_breakdown=_build_empty_resistance(),
        U_inner_basis=None,
        U_outer_basis=None,
        UA_w_k=None,
        C_hot_w_k=None,
        C_cold_w_k=None,
        C_min_w_k=None,
        C_max_w_k=None,
        capacity_ratio=None,
        NTU=None,
        effectiveness=None,
        LMTD_k=None,
        energy_residual_w=None,
        ua_lmtd_residual_w=None,
        iterations=0,
        converged=False,
        solver_termination_reason="blocked",
        solver_details=_build_empty_solver_details(),
        property_calls=tuple(property_calls),
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        status=RatingStatus.BLOCKED,
        provenance_digest=core_provenance_digest,
    )

    # Rebuild provenance with the real result_hash (adding RESULT node)
    provenance_graph = build_provenance(
        flow_arrangement=flow_arrangement,
        property_calls=property_calls,
        iterations=0,
        converged=False,
        warnings=warnings,
        blockers=blockers,
        result_hash=result_hash,
        execution_context=ctx,
        request_identity=ri,
    )
    provenance_digest = _provenance_graph_digest(provenance_graph)

    return RatingResult(
        status=RatingStatus.BLOCKED,
        flow_arrangement=flow_arrangement,
        heat_duty_w=None,
        hot_outlet_temperature_k=None,
        cold_outlet_temperature_k=None,
        area_inner_m2=0.0,
        area_outer_m2=0.0,
        resistance_breakdown=_build_empty_resistance(),
        iterations=0,
        converged=False,
        solver_termination_reason="blocked",
        solver_details=_build_empty_solver_details(),
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        property_calls=tuple(property_calls),
        provider_identity=provider_identity,
        request_identity=ri,
        execution_context=ctx,
        result_hash=result_hash,
        provenance_graph=provenance_graph,
        provenance_digest=provenance_digest,
        core_provenance_digest=core_provenance_digest,
    )


def _failed_result(
    *,
    solver_result: SolverResult,
    warnings: list[EngineeringMessage] | None = None,
    property_calls: list[PropertyCallRecord] | None = None,
    request_identity: RatingRequestIdentity | None = None,
    provider_identity: ProviderIdentitySnapshot | None = None,
    execution_context: ExecutionContextSnapshot | None = None,
    flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW,
) -> RatingResult:
    """Build a FAILED RatingResult with full provenance."""
    from hexagent.domain.messages import RunFailure

    ctx = execution_context or ExecutionContextSnapshot()
    warnings = warnings or []
    property_calls = property_calls or []
    provider_identity = provider_identity or ProviderIdentitySnapshot(
        name="",
        version="",
        git_revision="",
        reference_state_policy="",
    )
    ri = request_identity or RatingRequestIdentity(
        hot_fluid_name="",
        hot_fluid_backend="HEOS",
        hot_fluid_components=(),
        cold_fluid_name="",
        cold_fluid_backend="HEOS",
        cold_fluid_components=(),
        hot_mass_flow_kg_s=0.0,
        cold_mass_flow_kg_s=0.0,
        hot_inlet_pressure_pa=0.0,
        cold_inlet_pressure_pa=0.0,
        hot_inlet_temperature_k=0.0,
        cold_inlet_temperature_k=0.0,
        flow_arrangement=flow_arrangement.value,
        geometry={},
        solver_absolute_residual_w=0.0,
        solver_relative_residual_fraction=0.0,
        solver_bracket_temperature_tolerance_k=0.0,
        solver_max_iterations=0,
        minimum_terminal_delta_t=0.0,
        tube_boundary_condition="constant_wall_temperature",
        annulus_boundary_condition="inner_wall_heated",
    )

    failure_code_map = {
        SolverTermination.BRACKET_NOT_FOUND: ErrorCode.SOLVER_BRACKET_NOT_FOUND,
        SolverTermination.NON_CONVERGENCE: ErrorCode.SOLVER_NON_CONVERGENCE,
        SolverTermination.PROPERTY_FAILURE: ErrorCode.PROPERTY_EVALUATION_FAILED,
        SolverTermination.ZERO_DUTY: ErrorCode.ENERGY_BALANCE_NOT_CLOSED,
        SolverTermination.TEMPERATURE_CROSSING: ErrorCode.TEMPERATURE_CROSSING,
    }
    code = failure_code_map.get(solver_result.termination_reason, ErrorCode.SOLVER_NON_CONVERGENCE)
    failure = RunFailure(
        code=code,
        message=f"Solver did not converge: {solver_result.termination_reason.value}",
    )

    blockers = [
        _make_blocker(code, failure.message),
    ]

    solver_details = _make_solver_details(solver_result)

    # Compute core provenance (without RESULT node)
    core_graph, core_nodes, core_edges = build_provenance_core(
        flow_arrangement=flow_arrangement,
        property_calls=property_calls,
        iterations=solver_result.iterations,
        converged=False,
        warnings=warnings,
        blockers=blockers,
        execution_context=ctx,
        request_identity=ri,
    )
    core_provenance_digest = _provenance_graph_digest(core_graph)

    result_hash = compute_result_hash(
        request_identity=ri,
        provider_identity=provider_identity,
        flow_arrangement=flow_arrangement,
        heat_duty_w=None,
        hot_outlet_temperature_k=None,
        cold_outlet_temperature_k=None,
        tube_reynolds=None,
        tube_prandtl=None,
        tube_nusselt=None,
        tube_h=None,
        tube_selected_correlation_id=None,
        tube_selected_correlation_version=None,
        tube_applicability_status=None,
        annulus_reynolds=None,
        annulus_prandtl=None,
        annulus_nusselt=None,
        annulus_h=None,
        annulus_selected_correlation_id=None,
        annulus_selected_correlation_version=None,
        annulus_applicability_status=None,
        area_inner_m2=0.0,
        area_outer_m2=0.0,
        resistance_breakdown=_build_empty_resistance(),
        U_inner_basis=None,
        U_outer_basis=None,
        UA_w_k=None,
        C_hot_w_k=None,
        C_cold_w_k=None,
        C_min_w_k=None,
        C_max_w_k=None,
        capacity_ratio=None,
        NTU=None,
        effectiveness=None,
        LMTD_k=None,
        energy_residual_w=None,
        ua_lmtd_residual_w=None,
        iterations=solver_result.iterations,
        converged=False,
        solver_termination_reason=solver_result.termination_reason.value,
        solver_details=solver_details,
        property_calls=tuple(property_calls),
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        failure=failure,
        status=RatingStatus.FAILED,
        provenance_digest=core_provenance_digest,
    )

    provenance_graph = build_provenance(
        flow_arrangement=flow_arrangement,
        property_calls=property_calls,
        iterations=solver_result.iterations,
        converged=False,
        warnings=warnings,
        blockers=blockers,
        result_hash=result_hash,
        execution_context=ctx,
        request_identity=ri,
    )
    provenance_digest = _provenance_graph_digest(provenance_graph)

    return RatingResult(
        status=RatingStatus.FAILED,
        flow_arrangement=flow_arrangement,
        heat_duty_w=None,
        hot_outlet_temperature_k=None,
        cold_outlet_temperature_k=None,
        area_inner_m2=0.0,
        area_outer_m2=0.0,
        resistance_breakdown=_build_empty_resistance(),
        iterations=solver_result.iterations,
        converged=False,
        solver_termination_reason=solver_result.termination_reason.value,
        solver_details=solver_details,
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        failure=failure,
        property_calls=tuple(property_calls),
        provider_identity=provider_identity,
        request_identity=ri,
        execution_context=ctx,
        result_hash=result_hash,
        provenance_graph=provenance_graph,
        provenance_digest=provenance_digest,
        core_provenance_digest=core_provenance_digest,
    )


# ---------------------------------------------------------------------------
# Q_max computation via PropertyProvider
# ---------------------------------------------------------------------------


def _compute_q_max(
    *,
    provider: PropertyProvider,
    hot_fluid: FluidIdentifier,
    cold_fluid: FluidIdentifier,
    hot_inlet_temperature_k: float,
    cold_inlet_temperature_k: float,
    hot_inlet_pressure_pa: float,
    cold_inlet_pressure_pa: float,
    h_hot_in: float,
    h_cold_in: float,
    hot_mass_flow_kg_s: float,
    cold_mass_flow_kg_s: float,
    minimum_terminal_delta_t: float,
    flow_arrangement: FlowArrangement,
    property_calls: list[PropertyCallRecord],
    seq_idx: int,
) -> tuple[float, int]:
    """Compute Q_max for the bracket upper bound using PropertyProvider.

    For both counter-flow and parallel-flow, the exit pinch is coupled,
    but the same enthalpy-based limits apply as an upper bound:
    - Hot stream: T_hot_out_min = T_cold_in + minimum_terminal_delta_t
    - Cold stream: T_cold_out_max = T_hot_in - minimum_terminal_delta_t

    Returns (q_max, updated_seq_idx).
    """
    # Hot stream limit: hot cannot cool below T_cold_in + terminal_delta_t
    T_hot_out_min = cold_inlet_temperature_k + minimum_terminal_delta_t
    # Cold stream limit: cold cannot heat above T_hot_in - terminal_delta_t
    T_cold_out_max = hot_inlet_temperature_k - minimum_terminal_delta_t

    # Query hot limit state
    hot_limit_inputs = (
        ("temperature_k", T_hot_out_min),
        ("pressure_pa", hot_inlet_pressure_pa),
    )
    hot_limit_state = provider.state_tp(hot_fluid, T_hot_out_min, hot_inlet_pressure_pa)
    property_calls.append(
        _build_provider_call_record(
            hot_limit_state,
            query_type="TP",
            inputs=hot_limit_inputs,
            provider=provider,
            stage="q_max",
            stream_role="hot_limit",
            sequence_index=seq_idx,
        )
    )
    seq_idx += 1

    # Query cold limit state
    cold_limit_inputs = (
        ("temperature_k", T_cold_out_max),
        ("pressure_pa", cold_inlet_pressure_pa),
    )
    cold_limit_state = provider.state_tp(cold_fluid, T_cold_out_max, cold_inlet_pressure_pa)
    property_calls.append(
        _build_provider_call_record(
            cold_limit_state,
            query_type="TP",
            inputs=cold_limit_inputs,
            provider=provider,
            stage="q_max",
            stream_role="cold_limit",
            sequence_index=seq_idx,
        )
    )
    seq_idx += 1

    # Compute enthalpy-based Q limits
    Q_hot_limit = hot_mass_flow_kg_s * (h_hot_in - hot_limit_state.enthalpy_j_kg)
    Q_cold_limit = cold_mass_flow_kg_s * (cold_limit_state.enthalpy_j_kg - h_cold_in)

    q_max = min(Q_hot_limit, Q_cold_limit)

    return q_max, seq_idx


# ---------------------------------------------------------------------------
# Main rating function
# ---------------------------------------------------------------------------


def rate_double_pipe(
    *,
    geometry: DoublePipeGeometry,
    hot_fluid: FluidIdentifier,
    cold_fluid: FluidIdentifier,
    hot_mass_flow_kg_s: float,
    cold_mass_flow_kg_s: float,
    hot_inlet_temperature_k: float,
    cold_inlet_temperature_k: float,
    hot_inlet_pressure_pa: float,
    cold_inlet_pressure_pa: float,
    tube_in_hot: bool,  # True = hot fluid in inner tube
    flow_arrangement: FlowArrangement,
    provider: PropertyProvider,
    solver_params: SolverParams | None = None,
    context: CalculationContext | None = None,
    minimum_terminal_delta_t: float = _DEFAULT_MINIMUM_TERMINAL_DELTA_T,
    tube_boundary_condition: ThermalBoundaryCondition = (
        ThermalBoundaryCondition.constant_wall_temperature
    ),
    annulus_boundary_condition: ThermalBoundaryCondition = (
        ThermalBoundaryCondition.inner_wall_heated
    ),
) -> RatingResult:
    """Rate a fixed-geometry double-pipe heat exchanger.

    This is a pure function that takes geometry, operating conditions, a
    PropertyProvider, and returns a RatingResult with duty, outlet states,
    thermal-hydraulic diagnostics, provenance, and deterministic hash.

    Parameters
    ----------
    geometry :
        Fixed double-pipe geometry with validation.
    hot_fluid / cold_fluid :
        Fluid identifiers for the hot and cold streams.
    hot_mass_flow_kg_s / cold_mass_flow_kg_s :
        Mass flow rates [kg/s], must be > 0.
    hot_inlet_temperature_k / cold_inlet_temperature_k :
        Inlet temperatures [K].  Hot must be > cold.
    hot_inlet_pressure_pa / cold_inlet_pressure_pa :
        Inlet pressures [Pa].
    tube_in_hot :
        If True, hot fluid flows in the inner tube; if False, cold does.
    flow_arrangement :
        COUNTERFLOW or PARALLEL.
    provider :
        Thermophysical property provider (dependency injection).
    solver_params :
        Solver control parameters (defaults if None).
    context :
        Optional calculation context for provenance identity.
    minimum_terminal_delta_t :
        Minimum terminal temperature difference [K] for Q_max computation.
        Default 0.5 K.
    tube_boundary_condition :
        Thermal boundary condition for the tube side.
    annulus_boundary_condition :
        Thermal boundary condition for the annulus side.
    """
    params = solver_params or SolverParams()
    ctx = context or CalculationContext()
    # Build ExecutionContextSnapshot from CalculationContext fields
    ctx_snapshot = ExecutionContextSnapshot(
        request_id=ctx.request_id,
        design_case_revision_id=ctx.design_case_revision_id,
        calculation_run_id=ctx.calculation_run_id,
    )

    # Mutable accumulators for provenance
    property_calls: list[PropertyCallRecord] = []
    warnings: list[EngineeringMessage] = []
    blockers: list[EngineeringMessage] = []

    request_identity = _build_request_identity(
        geometry=geometry,
        hot_fluid=hot_fluid,
        cold_fluid=cold_fluid,
        hot_mass_flow_kg_s=hot_mass_flow_kg_s,
        cold_mass_flow_kg_s=cold_mass_flow_kg_s,
        hot_inlet_temperature_k=hot_inlet_temperature_k,
        cold_inlet_temperature_k=cold_inlet_temperature_k,
        hot_inlet_pressure_pa=hot_inlet_pressure_pa,
        cold_inlet_pressure_pa=cold_inlet_pressure_pa,
        flow_arrangement=flow_arrangement,
        solver_params=params,
        minimum_terminal_delta_t=minimum_terminal_delta_t,
        tube_boundary_condition=tube_boundary_condition,
        annulus_boundary_condition=annulus_boundary_condition,
    )

    provider_identity = _provider_snapshot(provider)

    # =====================================================================
    # 1. INPUT VALIDATION
    # =====================================================================

    if hot_mass_flow_kg_s <= 0 or not math.isfinite(hot_mass_flow_kg_s):
        blockers.append(
            _make_blocker(
                ErrorCode.NON_POSITIVE_MASS_FLOW,
                f"Hot-side mass flow must be > 0, got {hot_mass_flow_kg_s}",
                (("mass_flow_kg_s", hot_mass_flow_kg_s), ("side", "hot")),
            )
        )
        return _blocked_result(
            blockers=blockers,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    if cold_mass_flow_kg_s <= 0 or not math.isfinite(cold_mass_flow_kg_s):
        blockers.append(
            _make_blocker(
                ErrorCode.NON_POSITIVE_MASS_FLOW,
                f"Cold-side mass flow must be > 0, got {cold_mass_flow_kg_s}",
                (("mass_flow_kg_s", cold_mass_flow_kg_s), ("side", "cold")),
            )
        )
        return _blocked_result(
            blockers=blockers,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    if hot_inlet_temperature_k <= cold_inlet_temperature_k:
        blockers.append(
            _make_blocker(
                ErrorCode.INVALID_FLOW_SIDE_ASSIGNMENT,
                f"Hot inlet ({hot_inlet_temperature_k} K) must exceed"
                f" cold inlet ({cold_inlet_temperature_k} K)",
                (
                    ("hot_inlet_temperature_k", hot_inlet_temperature_k),
                    ("cold_inlet_temperature_k", cold_inlet_temperature_k),
                ),
            )
        )
        return _blocked_result(
            blockers=blockers,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    if flow_arrangement not in (FlowArrangement.COUNTERFLOW, FlowArrangement.PARALLEL):
        blockers.append(
            _make_blocker(
                ErrorCode.INPUT_INCONSISTENT,
                f"Unsupported flow arrangement: {flow_arrangement!r}",
                (("flow_arrangement", str(flow_arrangement)),),
            )
        )
        return _blocked_result(
            blockers=blockers,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    # Validate minimum_terminal_delta_t
    if minimum_terminal_delta_t <= 0 or not math.isfinite(minimum_terminal_delta_t):
        blockers.append(
            _make_blocker(
                ErrorCode.INPUT_INCONSISTENT,
                f"minimum_terminal_delta_t must be > 0, got {minimum_terminal_delta_t}",
                (("minimum_terminal_delta_t", minimum_terminal_delta_t),),
            )
        )
        return _blocked_result(
            blockers=blockers,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    # =====================================================================
    # 2. GET INLET STATES
    # =====================================================================

    seq_idx = 0

    # Hot inlet state via TP query
    hot_inlet_inputs = (
        ("temperature_k", hot_inlet_temperature_k),
        ("pressure_pa", hot_inlet_pressure_pa),
    )
    try:
        hot_inlet_state = provider.state_tp(
            hot_fluid, hot_inlet_temperature_k, hot_inlet_pressure_pa
        )
        property_calls.append(
            _build_provider_call_record(
                hot_inlet_state,
                query_type="TP",
                inputs=hot_inlet_inputs,
                provider=provider,
                stage="inlet",
                stream_role="hot_inlet",
                sequence_index=seq_idx,
            )
        )
        seq_idx += 1
    except PropertyServiceError as exc:
        property_calls.append(
            _build_failed_provider_call_record(
                fluid_name=hot_fluid.name,
                query_type="TP",
                inputs=hot_inlet_inputs,
                provider=provider,
                stage="inlet",
                stream_role="hot_inlet",
                sequence_index=seq_idx,
                error_code=(
                    exc.error_code.value if hasattr(exc, "error_code") else "property_unavailable"
                ),
                error_message=str(exc),
            )
        )
        blockers.append(
            _make_blocker(
                ErrorCode.PROPERTY_EVALUATION_FAILED,
                f"Hot-side inlet property evaluation failed: {exc}",
                (("fluid", hot_fluid.name), ("stage", "inlet")),
            )
        )
        return _blocked_result(
            blockers=blockers,
            property_calls=property_calls,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    # Cold inlet state via TP query
    cold_inlet_inputs = (
        ("temperature_k", cold_inlet_temperature_k),
        ("pressure_pa", cold_inlet_pressure_pa),
    )
    try:
        cold_inlet_state = provider.state_tp(
            cold_fluid, cold_inlet_temperature_k, cold_inlet_pressure_pa
        )
        property_calls.append(
            _build_provider_call_record(
                cold_inlet_state,
                query_type="TP",
                inputs=cold_inlet_inputs,
                provider=provider,
                stage="inlet",
                stream_role="cold_inlet",
                sequence_index=seq_idx,
            )
        )
        seq_idx += 1
    except PropertyServiceError as exc:
        property_calls.append(
            _build_failed_provider_call_record(
                fluid_name=cold_fluid.name,
                query_type="TP",
                inputs=cold_inlet_inputs,
                provider=provider,
                stage="inlet",
                stream_role="cold_inlet",
                sequence_index=seq_idx,
                error_code=(
                    exc.error_code.value if hasattr(exc, "error_code") else "property_unavailable"
                ),
                error_message=str(exc),
            )
        )
        blockers.append(
            _make_blocker(
                ErrorCode.PROPERTY_EVALUATION_FAILED,
                f"Cold-side inlet property evaluation failed: {exc}",
                (("fluid", cold_fluid.name), ("stage", "inlet")),
            )
        )
        return _blocked_result(
            blockers=blockers,
            property_calls=property_calls,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    # Validate single-phase
    if hot_inlet_state.phase not in _SINGLE_PHASE:
        blockers.append(
            _make_blocker(
                ErrorCode.PHASE_NOT_SUPPORTED,
                f"Hot-side inlet phase {hot_inlet_state.phase.value} is not single-phase",
                (("phase", hot_inlet_state.phase.value), ("fluid", hot_fluid.name)),
            )
        )
        return _blocked_result(
            blockers=blockers,
            property_calls=property_calls,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    if cold_inlet_state.phase not in _SINGLE_PHASE:
        blockers.append(
            _make_blocker(
                ErrorCode.PHASE_NOT_SUPPORTED,
                f"Cold-side inlet phase {cold_inlet_state.phase.value} is not single-phase",
                (("phase", cold_inlet_state.phase.value), ("fluid", cold_fluid.name)),
            )
        )
        return _blocked_result(
            blockers=blockers,
            property_calls=property_calls,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    # Build inlet state snapshots for result
    hot_inlet_state_snapshot = _make_fluid_state_snapshot(hot_inlet_state)
    cold_inlet_state_snapshot = _make_fluid_state_snapshot(cold_inlet_state)

    # =====================================================================
    # 3. COMPUTE INLET ENTHALPIES AND CAPACITY RATES
    # =====================================================================

    h_hot_in = hot_inlet_state.enthalpy_j_kg
    h_cold_in = cold_inlet_state.enthalpy_j_kg

    C_hot = hot_mass_flow_kg_s * hot_inlet_state.cp_j_kg_k
    C_cold = cold_mass_flow_kg_s * cold_inlet_state.cp_j_kg_k
    C_min = min(C_hot, C_cold)
    C_max = max(C_hot, C_cold)
    capacity_ratio = C_min / C_max if C_max > 0 else 0.0

    # =====================================================================
    # 4. BUILD GEOMETRY QUANTITIES
    # =====================================================================

    D_i = geometry.inner_tube_inner_diameter_m
    D_o = geometry.inner_tube_outer_diameter_m
    D_outer = geometry.outer_pipe_inner_diameter_m
    L = geometry.effective_length_m
    k_wall = geometry.wall_thermal_conductivity_w_m_k

    area_inner_m2 = geometry.area_inner_m2
    area_outer_m2 = geometry.area_outer_m2

    wall_resistance = compute_wall_resistance(D_i, D_o, L, k_wall)

    # =====================================================================
    # 5. COMPUTE Q_MAX FOR BRACKET via PropertyProvider
    # =====================================================================

    try:
        q_max, seq_idx = _compute_q_max(
            provider=provider,
            hot_fluid=hot_fluid,
            cold_fluid=cold_fluid,
            hot_inlet_temperature_k=hot_inlet_temperature_k,
            cold_inlet_temperature_k=cold_inlet_temperature_k,
            hot_inlet_pressure_pa=hot_inlet_pressure_pa,
            cold_inlet_pressure_pa=cold_inlet_pressure_pa,
            h_hot_in=h_hot_in,
            h_cold_in=h_cold_in,
            hot_mass_flow_kg_s=hot_mass_flow_kg_s,
            cold_mass_flow_kg_s=cold_mass_flow_kg_s,
            minimum_terminal_delta_t=minimum_terminal_delta_t,
            flow_arrangement=flow_arrangement,
            property_calls=property_calls,
            seq_idx=seq_idx,
        )
    except PropertyServiceError as exc:
        property_calls.append(
            _build_failed_provider_call_record(
                fluid_name=hot_fluid.name,
                query_type="TP",
                inputs=(),
                provider=provider,
                stage="q_max",
                stream_role="q_max",
                sequence_index=seq_idx,
                error_code=(
                    exc.error_code.value if hasattr(exc, "error_code") else "property_unavailable"
                ),
                error_message=str(exc),
            )
        )
        blockers.append(
            _make_blocker(
                ErrorCode.PROPERTY_EVALUATION_FAILED,
                f"Q_max property evaluation failed: {exc}",
                (("stage", "q_max"),),
            )
        )
        return _blocked_result(
            blockers=blockers,
            property_calls=property_calls,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    if q_max <= 0:
        blockers.append(
            _make_blocker(
                ErrorCode.SOLVER_BRACKET_NOT_FOUND,
                "Maximum feasible duty is non-positive",
                (("q_max", q_max),),
            )
        )
        return _blocked_result(
            blockers=blockers,
            property_calls=property_calls,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    # =====================================================================
    # 6. DEFINE RESIDUAL FUNCTION
    # =====================================================================

    # Build correlation geometry objects
    tube_geom = CircularTubeGeometry(
        inside_diameter_m=D_i,
        heat_transfer_length_m=L,
    )
    annulus_geom = ConcentricAnnulusGeometry(
        inner_tube_outer_diameter_m=D_o,
        outer_pipe_inside_diameter_m=D_outer,
        heat_transfer_length_m=L,
        heated_surface="inner",
    )

    def _evaluate_trial(Q: float) -> TrialEvaluation:
        """Evaluate a single trial Q and return a TrialEvaluation."""
        nonlocal seq_idx

        trial_prop_calls: list[PropertyCallRecord] = []
        trial_warnings: list[EngineeringMessage] = []
        trial_blockers: list[EngineeringMessage] = []

        if Q < 0:
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=None,
                cold_outlet_state=None,
                hot_bulk_state=None,
                cold_bulk_state=None,
                tube_flow_input=None,
                annulus_flow_input=None,
                tube_result=None,
                annulus_result=None,
                property_calls=(),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.INPUT_INCONSISTENT,
                        f"Negative Q trial: {Q}",
                        (("q_w", Q),),
                    ),
                ),
            )

        # --- 6a. Trial outlet enthalpies ---
        h_hot_out = h_hot_in - Q / hot_mass_flow_kg_s
        h_cold_out = h_cold_in + Q / cold_mass_flow_kg_s

        # --- 6b. Back-calculate outlet states via PH query ---
        hot_outlet_inputs = (
            ("pressure_pa", hot_inlet_pressure_pa),
            ("enthalpy_j_kg", h_hot_out),
        )
        cold_outlet_inputs = (
            ("pressure_pa", cold_inlet_pressure_pa),
            ("enthalpy_j_kg", h_cold_out),
        )

        hot_outlet_state: FluidState | None = None
        cold_outlet_state: FluidState | None = None

        try:
            hot_outlet_state = provider.state_ph(
                hot_fluid,
                hot_inlet_pressure_pa,
                h_hot_out,
                reference_state=provider.reference_state_policy,
            )
            trial_prop_calls.append(
                _build_provider_call_record(
                    hot_outlet_state,
                    query_type="PH",
                    inputs=hot_outlet_inputs,
                    provider=provider,
                    stage="brent_evaluation",
                    stream_role="hot_solver",
                    sequence_index=seq_idx,
                )
            )
            seq_idx += 1
        except PropertyServiceError as exc:
            trial_prop_calls.append(
                _build_failed_provider_call_record(
                    fluid_name=hot_fluid.name,
                    query_type="PH",
                    inputs=hot_outlet_inputs,
                    provider=provider,
                    stage="brent_evaluation",
                    stream_role="hot_solver",
                    sequence_index=seq_idx,
                    error_code=(
                        exc.error_code.value
                        if hasattr(exc, "error_code")
                        else "property_unavailable"
                    ),
                    error_message=str(exc),
                )
            )
            seq_idx += 1
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=None,
                cold_outlet_state=None,
                hot_bulk_state=None,
                cold_bulk_state=None,
                tube_flow_input=None,
                annulus_flow_input=None,
                tube_result=None,
                annulus_result=None,
                property_calls=tuple(trial_prop_calls),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PROPERTY_EVALUATION_FAILED,
                        f"Hot-side outlet property evaluation failed: {exc}",
                        (("fluid", hot_fluid.name), ("stage", "brent_evaluation")),
                    ),
                ),
            )

        try:
            cold_outlet_state = provider.state_ph(
                cold_fluid,
                cold_inlet_pressure_pa,
                h_cold_out,
                reference_state=provider.reference_state_policy,
            )
            trial_prop_calls.append(
                _build_provider_call_record(
                    cold_outlet_state,
                    query_type="PH",
                    inputs=cold_outlet_inputs,
                    provider=provider,
                    stage="brent_evaluation",
                    stream_role="cold_solver",
                    sequence_index=seq_idx,
                )
            )
            seq_idx += 1
        except PropertyServiceError as exc:
            trial_prop_calls.append(
                _build_failed_provider_call_record(
                    fluid_name=cold_fluid.name,
                    query_type="PH",
                    inputs=cold_outlet_inputs,
                    provider=provider,
                    stage="brent_evaluation",
                    stream_role="cold_solver",
                    sequence_index=seq_idx,
                    error_code=(
                        exc.error_code.value
                        if hasattr(exc, "error_code")
                        else "property_unavailable"
                    ),
                    error_message=str(exc),
                )
            )
            seq_idx += 1
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=hot_outlet_state,
                cold_outlet_state=None,
                hot_bulk_state=None,
                cold_bulk_state=None,
                tube_flow_input=None,
                annulus_flow_input=None,
                tube_result=None,
                annulus_result=None,
                property_calls=tuple(trial_prop_calls),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PROPERTY_EVALUATION_FAILED,
                        f"Cold-side outlet property evaluation failed: {exc}",
                        (("fluid", cold_fluid.name), ("stage", "brent_evaluation")),
                    ),
                ),
            )

        # --- 6c. Validate single-phase outlet states ---
        if hot_outlet_state.phase not in _SINGLE_PHASE:
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=hot_outlet_state,
                cold_outlet_state=cold_outlet_state,
                hot_bulk_state=None,
                cold_bulk_state=None,
                tube_flow_input=None,
                annulus_flow_input=None,
                tube_result=None,
                annulus_result=None,
                property_calls=tuple(trial_prop_calls),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PHASE_NOT_SUPPORTED,
                        f"Hot-side outlet phase {hot_outlet_state.phase.value} is not single-phase",
                        (("phase", hot_outlet_state.phase.value), ("fluid", hot_fluid.name)),
                    ),
                ),
            )
        if cold_outlet_state.phase not in _SINGLE_PHASE:
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=hot_outlet_state,
                cold_outlet_state=cold_outlet_state,
                hot_bulk_state=None,
                cold_bulk_state=None,
                tube_flow_input=None,
                annulus_flow_input=None,
                tube_result=None,
                annulus_result=None,
                property_calls=tuple(trial_prop_calls),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PHASE_NOT_SUPPORTED,
                        f"Cold-side outlet phase {cold_outlet_state.phase.value}"
                        " is not single-phase",
                        (("phase", cold_outlet_state.phase.value), ("fluid", cold_fluid.name)),
                    ),
                ),
            )

        # --- 6d. Bulk temperatures and PropertyProvider queries ---
        T_bulk_hot = (hot_inlet_temperature_k + hot_outlet_state.temperature_k) / 2.0
        T_bulk_cold = (cold_inlet_temperature_k + cold_outlet_state.temperature_k) / 2.0
        P_bulk_hot = hot_inlet_pressure_pa  # no pressure drop
        P_bulk_cold = cold_inlet_pressure_pa  # no pressure drop

        # Query bulk states via PropertyProvider at T_bulk
        hot_bulk_state: FluidState | None = None
        cold_bulk_state: FluidState | None = None

        try:
            hot_bulk_state = provider.state_tp(hot_fluid, T_bulk_hot, P_bulk_hot)
            trial_prop_calls.append(
                _build_provider_call_record(
                    hot_bulk_state,
                    query_type="TP",
                    inputs=(
                        ("temperature_k", T_bulk_hot),
                        ("pressure_pa", P_bulk_hot),
                    ),
                    provider=provider,
                    stage="bulk",
                    stream_role="hot_bulk",
                    sequence_index=seq_idx,
                )
            )
            seq_idx += 1
        except PropertyServiceError as exc:
            trial_prop_calls.append(
                _build_failed_provider_call_record(
                    fluid_name=hot_fluid.name,
                    query_type="TP",
                    inputs=(
                        ("temperature_k", T_bulk_hot),
                        ("pressure_pa", P_bulk_hot),
                    ),
                    provider=provider,
                    stage="bulk",
                    stream_role="hot_bulk",
                    sequence_index=seq_idx,
                    error_code=(
                        exc.error_code.value
                        if hasattr(exc, "error_code")
                        else "property_unavailable"
                    ),
                    error_message=str(exc),
                )
            )
            seq_idx += 1
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=hot_outlet_state,
                cold_outlet_state=cold_outlet_state,
                hot_bulk_state=None,
                cold_bulk_state=None,
                tube_flow_input=None,
                annulus_flow_input=None,
                tube_result=None,
                annulus_result=None,
                property_calls=tuple(trial_prop_calls),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PROPERTY_EVALUATION_FAILED,
                        f"Hot-side bulk property evaluation failed: {exc}",
                        (("fluid", hot_fluid.name), ("stage", "bulk")),
                    ),
                ),
            )

        try:
            cold_bulk_state = provider.state_tp(cold_fluid, T_bulk_cold, P_bulk_cold)
            trial_prop_calls.append(
                _build_provider_call_record(
                    cold_bulk_state,
                    query_type="TP",
                    inputs=(
                        ("temperature_k", T_bulk_cold),
                        ("pressure_pa", P_bulk_cold),
                    ),
                    provider=provider,
                    stage="bulk",
                    stream_role="cold_bulk",
                    sequence_index=seq_idx,
                )
            )
            seq_idx += 1
        except PropertyServiceError as exc:
            trial_prop_calls.append(
                _build_failed_provider_call_record(
                    fluid_name=cold_fluid.name,
                    query_type="TP",
                    inputs=(
                        ("temperature_k", T_bulk_cold),
                        ("pressure_pa", P_bulk_cold),
                    ),
                    provider=provider,
                    stage="bulk",
                    stream_role="cold_bulk",
                    sequence_index=seq_idx,
                    error_code=(
                        exc.error_code.value
                        if hasattr(exc, "error_code")
                        else "property_unavailable"
                    ),
                    error_message=str(exc),
                )
            )
            seq_idx += 1
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=hot_outlet_state,
                cold_outlet_state=cold_outlet_state,
                hot_bulk_state=hot_bulk_state,
                cold_bulk_state=None,
                tube_flow_input=None,
                annulus_flow_input=None,
                tube_result=None,
                annulus_result=None,
                property_calls=tuple(trial_prop_calls),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PROPERTY_EVALUATION_FAILED,
                        f"Cold-side bulk property evaluation failed: {exc}",
                        (("fluid", cold_fluid.name), ("stage", "bulk")),
                    ),
                ),
            )

        # --- 6e. Validate bulk phases ---
        if hot_bulk_state.phase not in _SINGLE_PHASE:
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=hot_outlet_state,
                cold_outlet_state=cold_outlet_state,
                hot_bulk_state=hot_bulk_state,
                cold_bulk_state=cold_bulk_state,
                tube_flow_input=None,
                annulus_flow_input=None,
                tube_result=None,
                annulus_result=None,
                property_calls=tuple(trial_prop_calls),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PHASE_NOT_SUPPORTED,
                        f"Hot-side bulk phase {hot_bulk_state.phase.value} is not single-phase",
                        (("phase", hot_bulk_state.phase.value), ("fluid", hot_fluid.name)),
                    ),
                ),
            )
        if cold_bulk_state.phase not in _SINGLE_PHASE:
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=hot_outlet_state,
                cold_outlet_state=cold_outlet_state,
                hot_bulk_state=hot_bulk_state,
                cold_bulk_state=cold_bulk_state,
                tube_flow_input=None,
                annulus_flow_input=None,
                tube_result=None,
                annulus_result=None,
                property_calls=tuple(trial_prop_calls),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PHASE_NOT_SUPPORTED,
                        f"Cold-side bulk phase {cold_bulk_state.phase.value} is not single-phase",
                        (("phase", cold_bulk_state.phase.value), ("fluid", cold_fluid.name)),
                    ),
                ),
            )

        # --- 6f. Assign tube and annulus flows based on tube_in_hot ---
        # Hot stream: heating=False (being cooled)
        # Cold stream: heating=True (being heated)
        if tube_in_hot:
            tube_flow = FlowPropertiesInput(
                mass_flow_kg_s=hot_mass_flow_kg_s,
                density_kg_m3=hot_bulk_state.density_kg_m3,
                dynamic_viscosity_pa_s=hot_bulk_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=hot_bulk_state.conductivity_w_m_k,
                specific_heat_j_kg_k=hot_bulk_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_hot,
                heating=False,  # hot stream is being cooled
            )
            annulus_flow = FlowPropertiesInput(
                mass_flow_kg_s=cold_mass_flow_kg_s,
                density_kg_m3=cold_bulk_state.density_kg_m3,
                dynamic_viscosity_pa_s=cold_bulk_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=cold_bulk_state.conductivity_w_m_k,
                specific_heat_j_kg_k=cold_bulk_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_cold,
                heating=True,  # cold stream is being heated
            )
        else:
            tube_flow = FlowPropertiesInput(
                mass_flow_kg_s=cold_mass_flow_kg_s,
                density_kg_m3=cold_bulk_state.density_kg_m3,
                dynamic_viscosity_pa_s=cold_bulk_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=cold_bulk_state.conductivity_w_m_k,
                specific_heat_j_kg_k=cold_bulk_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_cold,
                heating=True,  # cold stream is being heated
            )
            annulus_flow = FlowPropertiesInput(
                mass_flow_kg_s=hot_mass_flow_kg_s,
                density_kg_m3=hot_bulk_state.density_kg_m3,
                dynamic_viscosity_pa_s=hot_bulk_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=hot_bulk_state.conductivity_w_m_k,
                specific_heat_j_kg_k=hot_bulk_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_hot,
                heating=False,  # hot stream is being cooled
            )

        # --- 6g. Evaluate tube correlation ---
        corr_ctx = CorrCalculationContext()

        tube_result = evaluate_hx_correlation(
            geometry=tube_geom,
            flow=tube_flow,
            boundary_condition=tube_boundary_condition,
            context=corr_ctx,
        )
        # Propagate correlation warnings
        for w in tube_result.warnings:
            trial_warnings.append(w)

        if tube_result.status.value == "blocked" or tube_result.heat_transfer_coefficient <= 0:
            for b in tube_result.blockers:
                trial_blockers.append(b)
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=hot_outlet_state,
                cold_outlet_state=cold_outlet_state,
                hot_bulk_state=hot_bulk_state,
                cold_bulk_state=cold_bulk_state,
                tube_flow_input=tube_flow,
                annulus_flow_input=annulus_flow,
                tube_result=tube_result,
                annulus_result=None,
                property_calls=tuple(trial_prop_calls),
                warnings=tuple(trial_warnings),
                blockers=tuple(trial_blockers),
            )

        # --- 6h. Evaluate annulus correlation ---
        annulus_result = evaluate_hx_correlation(
            geometry=annulus_geom,
            flow=annulus_flow,
            boundary_condition=annulus_boundary_condition,
            context=corr_ctx,
        )
        # Propagate correlation warnings
        for w in annulus_result.warnings:
            trial_warnings.append(w)

        if (
            annulus_result.status.value == "blocked"
            or annulus_result.heat_transfer_coefficient <= 0
        ):
            for b in annulus_result.blockers:
                trial_blockers.append(b)
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=hot_outlet_state,
                cold_outlet_state=cold_outlet_state,
                hot_bulk_state=hot_bulk_state,
                cold_bulk_state=cold_bulk_state,
                tube_flow_input=tube_flow,
                annulus_flow_input=annulus_flow,
                tube_result=tube_result,
                annulus_result=annulus_result,
                property_calls=tuple(trial_prop_calls),
                warnings=tuple(trial_warnings),
                blockers=tuple(trial_blockers),
            )

        # --- 6i. Extract h values ---
        h_tube = tube_result.heat_transfer_coefficient
        h_annulus = annulus_result.heat_transfer_coefficient

        # --- 6j. Build thermal resistance ---
        R_breakdown = build_thermal_resistance(
            h_inner=h_tube,
            h_outer=h_annulus,
            area_inner_m2=area_inner_m2,
            area_outer_m2=area_outer_m2,
            wall_resistance_kw=wall_resistance,
            fouling_inner_m2k_w=geometry.inner_fouling_resistance_m2k_w,
            fouling_outer_m2k_w=geometry.outer_fouling_resistance_m2k_w,
        )
        UA = R_breakdown.ua_w_k

        # --- 6k. Compute outlet temperatures ---
        T_h_out = hot_outlet_state.temperature_k
        T_c_out = cold_outlet_state.temperature_k

        # --- 6l. Compute LMTD ---
        if flow_arrangement == FlowArrangement.COUNTERFLOW:
            lmtd = lmtd_counterflow(
                hot_inlet_temperature_k,
                T_h_out,
                cold_inlet_temperature_k,
                T_c_out,
            )
        else:
            lmtd = lmtd_parallel(
                hot_inlet_temperature_k,
                T_h_out,
                cold_inlet_temperature_k,
                T_c_out,
            )

        if not math.isfinite(lmtd) or lmtd <= 0:
            return TrialEvaluation(
                q_w=Q,
                residual_w=None,
                feasible=False,
                hot_outlet_state=hot_outlet_state,
                cold_outlet_state=cold_outlet_state,
                hot_bulk_state=hot_bulk_state,
                cold_bulk_state=cold_bulk_state,
                tube_flow_input=tube_flow,
                annulus_flow_input=annulus_flow,
                tube_result=tube_result,
                annulus_result=annulus_result,
                property_calls=tuple(trial_prop_calls),
                warnings=tuple(trial_warnings),
                blockers=(
                    _make_blocker(
                        ErrorCode.TEMPERATURE_CROSSING,
                        f"LMTD is not finite and > 0: {lmtd}",
                        (("lmtd_k", lmtd),),
                    ),
                ),
            )

        # --- 6m. Residual ---
        residual = Q - UA * lmtd
        return TrialEvaluation(
            q_w=Q,
            residual_w=residual,
            feasible=True,
            hot_outlet_state=hot_outlet_state,
            cold_outlet_state=cold_outlet_state,
            hot_bulk_state=hot_bulk_state,
            cold_bulk_state=cold_bulk_state,
            tube_flow_input=tube_flow,
            annulus_flow_input=annulus_flow,
            tube_result=tube_result,
            annulus_result=annulus_result,
            property_calls=tuple(trial_prop_calls),
            warnings=tuple(trial_warnings),
            blockers=(),
        )

    def residual_fn(Q: float) -> float:
        """Evaluate residual Q - UA(Q) × LMTD(Q).

        The solver calls this; it must return a float.
        Infeasible trials are handled by returning a large residual
        that guides bracket construction.
        """
        trial = _evaluate_trial(Q)
        if not trial.feasible or trial.residual_w is None:
            # For bracket-finding guidance: return a large residual
            # that signals this Q is not feasible
            return 1e12
        return trial.residual_w

    # =====================================================================
    # 7. SOLVE
    # =====================================================================

    solver_result = solve_rating(
        residual_fn=residual_fn,
        q_max=q_max,
        params=params,
        c_effective_w_k=C_min,
    )

    # =====================================================================
    # 8. POST-PROCESS
    # =====================================================================

    if not solver_result.converged:
        return _failed_result(
            solver_result=solver_result,
            warnings=warnings,
            property_calls=property_calls,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    Q_sol = solver_result.q_solution_w

    # =====================================================================
    # 9. FINAL STATE CONSISTENCY
    # =====================================================================

    # Re-evaluate at the solution Q for final diagnostics
    final_trial = _evaluate_trial(Q_sol)

    # Propagate trial property calls and warnings to global accumulators
    for pc in final_trial.property_calls:
        property_calls.append(pc)
    for w in final_trial.warnings:
        warnings.append(w)

    # Check feasibility of final evaluation
    if (
        not final_trial.feasible
        or final_trial.hot_outlet_state is None
        or final_trial.cold_outlet_state is None
        or final_trial.hot_bulk_state is None
        or final_trial.cold_bulk_state is None
        or final_trial.tube_flow_input is None
        or final_trial.annulus_flow_input is None
        or final_trial.tube_result is None
        or final_trial.annulus_result is None
    ):
        for b in final_trial.blockers:
            blockers.append(b)
        return _blocked_result(
            blockers=blockers,
            warnings=warnings,
            property_calls=property_calls,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    # Extract final states
    hot_outlet_final = final_trial.hot_outlet_state
    cold_outlet_final = final_trial.cold_outlet_state
    hot_bulk_final = final_trial.hot_bulk_state
    cold_bulk_final = final_trial.cold_bulk_state
    tube_result_final = final_trial.tube_result
    annulus_result_final = final_trial.annulus_result

    # Compute final outlet states via PH queries (for result snapshot)
    h_hot_out_sol = h_hot_in - Q_sol / hot_mass_flow_kg_s
    h_cold_out_sol = h_cold_in + Q_sol / cold_mass_flow_kg_s

    # Final property state snapshots
    hot_outlet_snapshot = _make_fluid_state_snapshot(hot_outlet_final)
    cold_outlet_snapshot = _make_fluid_state_snapshot(cold_outlet_final)
    hot_bulk_snapshot = _make_fluid_state_snapshot(hot_bulk_final)
    cold_bulk_snapshot = _make_fluid_state_snapshot(cold_bulk_final)

    # --- Validate hot/cold outlet phases ---
    if hot_outlet_final.phase not in _SINGLE_PHASE:
        blockers.append(
            _make_blocker(
                ErrorCode.PHASE_NOT_SUPPORTED,
                f"Hot-side outlet phase {hot_outlet_final.phase.value} is not single-phase",
                (("phase", hot_outlet_final.phase.value), ("fluid", hot_fluid.name)),
            )
        )
    if cold_outlet_final.phase not in _SINGLE_PHASE:
        blockers.append(
            _make_blocker(
                ErrorCode.PHASE_NOT_SUPPORTED,
                f"Cold-side outlet phase {cold_outlet_final.phase.value} is not single-phase",
                (("phase", cold_outlet_final.phase.value), ("fluid", cold_fluid.name)),
            )
        )

    # --- Check tube correlation success ---
    tube_h_val = tube_result_final.heat_transfer_coefficient
    if tube_result_final.status.value == "blocked" or tube_h_val <= 0:
        for b in tube_result_final.blockers:
            blockers.append(b)
        if not blockers:
            blockers.append(
                _make_blocker(
                    ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
                    "Tube correlation is blocked or returned zero h",
                    (),
                )
            )

    # --- Check annulus correlation success ---
    annulus_h_val = annulus_result_final.heat_transfer_coefficient
    if annulus_result_final.status.value == "blocked" or annulus_h_val <= 0:
        for b in annulus_result_final.blockers:
            blockers.append(b)
        if not blockers:
            blockers.append(
                _make_blocker(
                    ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
                    "Annulus correlation is blocked or returned zero h",
                    (),
                )
            )

    # --- Final thermal diagnostics ---
    T_h_out_sol = hot_outlet_final.temperature_k
    T_c_out_sol = cold_outlet_final.temperature_k

    # --- Terminal temperature differences ---
    if flow_arrangement == FlowArrangement.COUNTERFLOW:
        # Counter-flow: all terminal ΔT must be positive
        dt_hot_in_cold_out = hot_inlet_temperature_k - T_c_out_sol
        dt_hot_out_cold_in = T_h_out_sol - cold_inlet_temperature_k
        if dt_hot_in_cold_out <= 0 or dt_hot_out_cold_in <= 0:
            blockers.append(
                _make_blocker(
                    ErrorCode.TEMPERATURE_CROSSING,
                    f"Terminal temperature differences must be positive for counter-flow "
                    f"(dt1={dt_hot_in_cold_out}, dt2={dt_hot_out_cold_in})",
                    (
                        ("dt_hot_in_cold_out", dt_hot_in_cold_out),
                        ("dt_hot_out_cold_in", dt_hot_out_cold_in),
                    ),
                )
            )
    else:
        # Parallel-flow: hot outlet must be > cold outlet
        if T_h_out_sol <= T_c_out_sol:
            blockers.append(
                _make_blocker(
                    ErrorCode.TEMPERATURE_CROSSING,
                    f"Hot outlet ({T_h_out_sol} K) must exceed cold outlet ({T_c_out_sol} K) "
                    f"for parallel flow",
                    (
                        ("hot_outlet_k", T_h_out_sol),
                        ("cold_outlet_k", T_c_out_sol),
                    ),
                )
            )

    # --- LMTD at solution ---
    if flow_arrangement == FlowArrangement.COUNTERFLOW:
        lmtd_final = lmtd_counterflow(
            hot_inlet_temperature_k,
            T_h_out_sol,
            cold_inlet_temperature_k,
            T_c_out_sol,
        )
    else:
        lmtd_final = lmtd_parallel(
            hot_inlet_temperature_k,
            T_h_out_sol,
            cold_inlet_temperature_k,
            T_c_out_sol,
        )

    if not math.isfinite(lmtd_final) or lmtd_final <= 0:
        blockers.append(
            _make_blocker(
                ErrorCode.TEMPERATURE_CROSSING,
                f"LMTD is not finite and > 0 at solution: {lmtd_final}",
                (("lmtd_k", lmtd_final),),
            )
        )

    # --- Final resistance breakdown ---
    if tube_h_val > 0 and annulus_h_val > 0:
        R_breakdown_final = build_thermal_resistance(
            h_inner=tube_h_val,
            h_outer=annulus_h_val,
            area_inner_m2=area_inner_m2,
            area_outer_m2=area_outer_m2,
            wall_resistance_kw=wall_resistance,
            fouling_inner_m2k_w=geometry.inner_fouling_resistance_m2k_w,
            fouling_outer_m2k_w=geometry.outer_fouling_resistance_m2k_w,
        )
        UA_final = R_breakdown_final.ua_w_k
        rb_model = _make_resistance_breakdown(R_breakdown_final)
    else:
        UA_final = 0.0
        rb_model = _build_empty_resistance()

    # --- Check UA ---
    if not math.isfinite(UA_final) or UA_final <= 0:
        blockers.append(
            _make_blocker(
                ErrorCode.ENERGY_BALANCE_NOT_CLOSED,
                f"UA is not finite and > 0 at solution: {UA_final}",
                (("ua_w_k", UA_final),),
            )
        )

    # --- ε-NTU diagnostics ---
    NTU_final = UA_final / C_min if C_min > 0 else 0.0
    if flow_arrangement == FlowArrangement.COUNTERFLOW:
        eps_calc = effectiveness_counterflow(NTU_final, capacity_ratio)
    else:
        eps_calc = effectiveness_parallel(NTU_final, capacity_ratio)

    # --- Overall U values ---
    U_inner = UA_final / area_inner_m2 if area_inner_m2 > 0 else 0.0
    U_outer = UA_final / area_outer_m2 if area_outer_m2 > 0 else 0.0

    # =====================================================================
    # 10. ENERGY BALANCE CLOSURE
    # =====================================================================

    Q_hot = hot_mass_flow_kg_s * (h_hot_in - h_hot_out_sol)
    Q_cold = cold_mass_flow_kg_s * (h_cold_out_sol - h_cold_in)

    energy_residual_w = abs(Q_hot - Q_cold)
    max_abs_q = max(abs(Q_hot), abs(Q_cold), 1.0)
    energy_tolerance = max(_ENERGY_RESIDUAL_ABS_TOL, _ENERGY_RESIDUAL_REL_TOL * max_abs_q)

    if energy_residual_w > energy_tolerance:
        blockers.append(
            _make_blocker(
                ErrorCode.ENERGY_BALANCE_NOT_CLOSED,
                f"Energy balance not closed: residual={energy_residual_w:.6e} W, "
                f"tolerance={energy_tolerance:.6e} W",
                (
                    ("energy_residual_w", energy_residual_w),
                    ("energy_tolerance_w", energy_tolerance),
                    ("Q_hot_w", Q_hot),
                    ("Q_cold_w", Q_cold),
                ),
            )
        )

    # --- UA-LMTD residual ---
    ua_lmtd_residual = (
        abs(Q_sol - UA_final * lmtd_final) if UA_final > 0 and lmtd_final > 0 else 0.0
    )
    if UA_final > 0 and lmtd_final > 0:
        ua_lmtd_tolerance = max(
            _ENERGY_RESIDUAL_ABS_TOL, _ENERGY_RESIDUAL_REL_TOL * max(abs(Q_sol), 1.0)
        )
        if ua_lmtd_residual > ua_lmtd_tolerance:
            blockers.append(
                _make_blocker(
                    ErrorCode.ENERGY_BALANCE_NOT_CLOSED,
                    f"UA-LMTD residual not closed: residual={ua_lmtd_residual:.6e} W, "
                    f"tolerance={ua_lmtd_tolerance:.6e} W",
                    (
                        ("ua_lmtd_residual_w", ua_lmtd_residual),
                        ("ua_lmtd_tolerance_w", ua_lmtd_tolerance),
                    ),
                )
            )

    # --- Propagate correlation warnings to global ---
    for w in tube_result_final.warnings:
        warnings.append(w)
    for w in annulus_result_final.warnings:
        warnings.append(w)

    # --- Check if any blockers were found during final consistency ---
    if blockers:
        return _blocked_result(
            blockers=blockers,
            warnings=warnings,
            property_calls=property_calls,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    # =====================================================================
    # 11. BUILD CORRELATION SNAPSHOTS
    # =====================================================================

    tube_sel_corr_snapshot = _make_selected_correlation_snapshot(tube_result_final)
    annulus_sel_corr_snapshot = _make_selected_correlation_snapshot(annulus_result_final)
    tube_app_snapshot = _make_applicability_snapshot(tube_result_final)
    annulus_app_snapshot = _make_applicability_snapshot(annulus_result_final)

    # Extract correlation ID/version for result fields
    tube_corr_id = tube_sel_corr_snapshot.correlation_id if tube_sel_corr_snapshot else None
    tube_corr_ver = tube_sel_corr_snapshot.version if tube_sel_corr_snapshot else None
    tube_app_status = tube_result_final.applicability_status or None
    annulus_corr_id = (
        annulus_sel_corr_snapshot.correlation_id if annulus_sel_corr_snapshot else None
    )
    annulus_corr_ver = annulus_sel_corr_snapshot.version if annulus_sel_corr_snapshot else None
    annulus_app_status = annulus_result_final.applicability_status or None

    # =====================================================================
    # 12. MAP TUBE/ANNULUS SIDES
    # =====================================================================

    if tube_in_hot:
        tube_side_inlet_snapshot = hot_inlet_state_snapshot
        tube_side_outlet_snapshot = hot_outlet_snapshot
        tube_bulk_snapshot = hot_bulk_snapshot
        annulus_side_inlet_snapshot = cold_inlet_state_snapshot
        annulus_side_outlet_snapshot = cold_outlet_snapshot
        annulus_bulk_snapshot = cold_bulk_snapshot
    else:
        tube_side_inlet_snapshot = cold_inlet_state_snapshot
        tube_side_outlet_snapshot = cold_outlet_snapshot
        tube_bulk_snapshot = cold_bulk_snapshot
        annulus_side_inlet_snapshot = hot_inlet_state_snapshot
        annulus_side_outlet_snapshot = hot_outlet_snapshot
        annulus_bulk_snapshot = hot_bulk_snapshot

    # =====================================================================
    # 13. HASH TWO-LAYER
    # =====================================================================

    solver_details = _make_solver_details(solver_result)

    # Step 1: Build core provenance (without RESULT node)
    core_graph, core_nodes, core_edges = build_provenance_core(
        flow_arrangement=flow_arrangement,
        property_calls=property_calls,
        iterations=solver_result.iterations,
        converged=True,
        warnings=warnings,
        blockers=[],
        execution_context=ctx_snapshot,
        request_identity=request_identity,
    )

    # Step 2: Compute core_provenance_digest
    core_provenance_digest = _provenance_graph_digest(core_graph)

    # Step 3: Compute result_hash using core_provenance_digest
    result_hash = compute_result_hash(
        request_identity=request_identity,
        provider_identity=provider_identity,
        flow_arrangement=flow_arrangement,
        heat_duty_w=Q_sol,
        hot_outlet_temperature_k=T_h_out_sol,
        cold_outlet_temperature_k=T_c_out_sol,
        tube_reynolds=tube_result_final.reynolds_number,
        tube_prandtl=tube_result_final.prandtl_number,
        tube_nusselt=tube_result_final.nusselt_number,
        tube_h=tube_h_val,
        tube_selected_correlation_id=tube_corr_id,
        tube_selected_correlation_version=tube_corr_ver,
        tube_applicability_status=tube_app_status,
        annulus_reynolds=annulus_result_final.reynolds_number,
        annulus_prandtl=annulus_result_final.prandtl_number,
        annulus_nusselt=annulus_result_final.nusselt_number,
        annulus_h=annulus_h_val,
        annulus_selected_correlation_id=annulus_corr_id,
        annulus_selected_correlation_version=annulus_corr_ver,
        annulus_applicability_status=annulus_app_status,
        area_inner_m2=area_inner_m2,
        area_outer_m2=area_outer_m2,
        resistance_breakdown=rb_model,
        U_inner_basis=U_inner,
        U_outer_basis=U_outer,
        UA_w_k=UA_final,
        C_hot_w_k=C_hot,
        C_cold_w_k=C_cold,
        C_min_w_k=C_min,
        C_max_w_k=C_max,
        capacity_ratio=capacity_ratio,
        NTU=NTU_final,
        effectiveness=eps_calc,
        LMTD_k=lmtd_final,
        energy_residual_w=energy_residual_w,
        ua_lmtd_residual_w=ua_lmtd_residual,
        iterations=solver_result.iterations,
        converged=True,
        solver_termination_reason=solver_result.termination_reason.value,
        solver_details=solver_details,
        property_calls=tuple(property_calls),
        warnings=tuple(warnings),
        blockers=(),
        status=RatingStatus.SUCCEEDED,
        provenance_digest=core_provenance_digest,
    )

    # Step 4: Add RESULT node via build_provenance
    provenance_graph = build_provenance(
        flow_arrangement=flow_arrangement,
        property_calls=property_calls,
        iterations=solver_result.iterations,
        converged=True,
        warnings=warnings,
        blockers=[],
        result_hash=result_hash,
        execution_context=ctx_snapshot,
        request_identity=request_identity,
    )

    # Step 5: Compute final provenance_digest from full graph
    provenance_digest = _provenance_graph_digest(provenance_graph)

    # =====================================================================
    # 14. BUILD RESULT
    # =====================================================================

    result = RatingResult(
        status=RatingStatus.SUCCEEDED,
        flow_arrangement=flow_arrangement,
        heat_duty_w=Q_sol,
        hot_outlet_temperature_k=T_h_out_sol,
        cold_outlet_temperature_k=T_c_out_sol,
        tube_reynolds=tube_result_final.reynolds_number,
        tube_prandtl=tube_result_final.prandtl_number,
        tube_nusselt=tube_result_final.nusselt_number,
        tube_h=tube_h_val,
        tube_selected_correlation_id=tube_corr_id,
        tube_selected_correlation_version=tube_corr_ver,
        tube_applicability_status=tube_app_status,
        annulus_reynolds=annulus_result_final.reynolds_number,
        annulus_prandtl=annulus_result_final.prandtl_number,
        annulus_nusselt=annulus_result_final.nusselt_number,
        annulus_h=annulus_h_val,
        annulus_selected_correlation_id=annulus_corr_id,
        annulus_selected_correlation_version=annulus_corr_ver,
        annulus_applicability_status=annulus_app_status,
        area_inner_m2=area_inner_m2,
        area_outer_m2=area_outer_m2,
        resistance_breakdown=rb_model,
        U_inner_basis=U_inner,
        U_outer_basis=U_outer,
        UA_w_k=UA_final,
        C_hot_w_k=C_hot,
        C_cold_w_k=C_cold,
        C_min_w_k=C_min,
        C_max_w_k=C_max,
        capacity_ratio=capacity_ratio,
        NTU=NTU_final,
        effectiveness=eps_calc,
        LMTD_k=lmtd_final,
        energy_residual_w=energy_residual_w,
        ua_lmtd_residual_w=ua_lmtd_residual,
        iterations=solver_result.iterations,
        converged=True,
        solver_termination_reason=solver_result.termination_reason.value,
        solver_details=solver_details,
        warnings=tuple(warnings),
        blockers=(),
        property_calls=tuple(property_calls),
        provider_identity=provider_identity,
        request_identity=request_identity,
        execution_context=ctx_snapshot,
        result_hash=result_hash,
        provenance_graph=provenance_graph,
        provenance_digest=provenance_digest,
        core_provenance_digest=core_provenance_digest,
        # New fields: state snapshots
        hot_inlet_state=hot_inlet_state_snapshot,
        cold_inlet_state=cold_inlet_state_snapshot,
        hot_outlet_state=hot_outlet_snapshot,
        cold_outlet_state=cold_outlet_snapshot,
        tube_side_inlet_state=tube_side_inlet_snapshot,
        tube_side_outlet_state=tube_side_outlet_snapshot,
        annulus_side_inlet_state=annulus_side_inlet_snapshot,
        annulus_side_outlet_state=annulus_side_outlet_snapshot,
        tube_bulk_state=tube_bulk_snapshot,
        annulus_bulk_state=annulus_bulk_snapshot,
        tube_selected_correlation=tube_sel_corr_snapshot,
        annulus_selected_correlation=annulus_sel_corr_snapshot,
        tube_applicability=tube_app_snapshot,
        annulus_applicability=annulus_app_snapshot,
    )

    return result
