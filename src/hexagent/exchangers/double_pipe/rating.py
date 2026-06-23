"""Main rating kernel for fixed-geometry double-pipe heat exchangers.

This module provides the ``rate_double_pipe()`` pure function that
solves for heat duty Q via a Brent root-finding iteration on the
residual ``Q − UA(Q)·LMTD(Q)``.  Each residual evaluation:

1. Back-calculates trial outlet enthalpies from Q
2. Retrieves outlet states via PropertyProvider.state_ph()
3. Calls TASK-007 correlation service for tube and annulus sides
4. Builds thermal resistance and computes UA
5. Computes LMTD and residual

The function ALWAYS returns a RatingResult; it never raises for domain errors.
"""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID, uuid5

from hexagent.core.heat_balance import (
    CalculationContext,
    ExecutionContextSnapshot,
    PropertyCallRecord,
    ProviderIdentitySnapshot,
)
from hexagent.correlations.flow import FlowPropertiesInput
from hexagent.correlations.geometry import CircularTubeGeometry, ConcentricAnnulusGeometry
from hexagent.correlations.service import CalculationContext as CorrCalculationContext
from hexagent.correlations.service import evaluate_hx_correlation
from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity, ErrorCode
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.result import (
    RatingRequestIdentity,
    RatingResult,
    RatingStatus,
    ResistanceBreakdownModel,
    SolverDetailsModel,
    _provenance_graph_digest,
    build_provenance,
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

# Large residual sentinel for property/correlation failures inside residual fn
_SENTINEL_RESIDUAL = 1e12


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
        bracket_width_w=solver_result.bracket_width_w,
        function_evaluations=solver_result.function_evaluations,
        termination_reason=solver_result.termination_reason.value,
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
        bracket_width_w=0.0,
        function_evaluations=0,
        termination_reason="not_started",
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
    )

    provenance_graph = build_provenance(
        flow_arrangement=flow_arrangement,
        property_calls=property_calls,
        iterations=0,
        converged=False,
        warnings=warnings,
        blockers=blockers,
        result_hash="pending",
        execution_context=ctx,
        request_identity=ri,
    )

    # Compute the result hash from what we have so far
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
        provenance_digest=_provenance_graph_digest(provenance_graph),
    )

    # Rebuild provenance with the real result_hash
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

    provenance_graph = build_provenance(
        flow_arrangement=flow_arrangement,
        property_calls=property_calls,
        iterations=solver_result.iterations,
        converged=False,
        warnings=warnings,
        blockers=blockers,
        result_hash="pending",
        execution_context=ctx,
        request_identity=ri,
    )

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
        provenance_digest=_provenance_graph_digest(provenance_graph),
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
    )


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
    # 5. COMPUTE Q_MAX FOR BRACKET
    # =====================================================================

    q_max_theoretical = C_min * (hot_inlet_temperature_k - cold_inlet_temperature_k)
    q_max = q_max_theoretical * params.max_q_fraction
    if q_max <= 0:
        blockers.append(
            _make_blocker(
                ErrorCode.SOLVER_BRACKET_NOT_FOUND,
                "Maximum feasible duty is non-positive",
                (("q_max_theoretical", q_max_theoretical),),
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

    def residual_fn(Q: float) -> float:
        """Evaluate residual Q - UA(Q) × LMTD(Q)."""
        nonlocal seq_idx

        if Q < 0:
            return _SENTINEL_RESIDUAL

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

        try:
            hot_outlet_state = provider.state_ph(
                hot_fluid,
                hot_inlet_pressure_pa,
                h_hot_out,
                reference_state=provider.reference_state_policy,
            )
            property_calls.append(
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
        except (PropertyServiceError, Exception):
            seq_idx += 1
            return _SENTINEL_RESIDUAL

        try:
            cold_outlet_state = provider.state_ph(
                cold_fluid,
                cold_inlet_pressure_pa,
                h_cold_out,
                reference_state=provider.reference_state_policy,
            )
            property_calls.append(
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
        except (PropertyServiceError, Exception):
            seq_idx += 1
            return _SENTINEL_RESIDUAL

        # --- 6c. Validate single-phase outlet states ---
        if hot_outlet_state.phase not in _SINGLE_PHASE:
            return _SENTINEL_RESIDUAL
        if cold_outlet_state.phase not in _SINGLE_PHASE:
            return _SENTINEL_RESIDUAL

        # --- 6d. Bulk temperatures ---
        T_bulk_hot = (hot_inlet_temperature_k + hot_outlet_state.temperature_k) / 2.0
        T_bulk_cold = (cold_inlet_temperature_k + cold_outlet_state.temperature_k) / 2.0

        # --- 6e. Assign tube and annulus flows based on tube_in_hot ---
        if tube_in_hot:
            tube_flow = FlowPropertiesInput(
                mass_flow_kg_s=hot_mass_flow_kg_s,
                density_kg_m3=hot_outlet_state.density_kg_m3,
                dynamic_viscosity_pa_s=hot_outlet_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=hot_outlet_state.conductivity_w_m_k,
                specific_heat_j_kg_k=hot_outlet_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_hot,
                heating=True,
            )
            annulus_flow = FlowPropertiesInput(
                mass_flow_kg_s=cold_mass_flow_kg_s,
                density_kg_m3=cold_outlet_state.density_kg_m3,
                dynamic_viscosity_pa_s=cold_outlet_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=cold_outlet_state.conductivity_w_m_k,
                specific_heat_j_kg_k=cold_outlet_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_cold,
                heating=False,
            )
        else:
            tube_flow = FlowPropertiesInput(
                mass_flow_kg_s=cold_mass_flow_kg_s,
                density_kg_m3=cold_outlet_state.density_kg_m3,
                dynamic_viscosity_pa_s=cold_outlet_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=cold_outlet_state.conductivity_w_m_k,
                specific_heat_j_kg_k=cold_outlet_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_cold,
                heating=False,
            )
            annulus_flow = FlowPropertiesInput(
                mass_flow_kg_s=hot_mass_flow_kg_s,
                density_kg_m3=hot_outlet_state.density_kg_m3,
                dynamic_viscosity_pa_s=hot_outlet_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=hot_outlet_state.conductivity_w_m_k,
                specific_heat_j_kg_k=hot_outlet_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_hot,
                heating=True,
            )

        # --- 6f-h. Evaluate correlations ---
        corr_ctx = CorrCalculationContext()

        tube_result = evaluate_hx_correlation(
            geometry=tube_geom,
            flow=tube_flow,
            boundary_condition="constant_wall_temperature",
            context=corr_ctx,
        )
        if tube_result.status.value == "blocked" or tube_result.heat_transfer_coefficient <= 0:
            # Correlation blocked: UA=0 effectively, residual = Q - 0 = Q
            # This is positive for Q>0, giving bracket-finding a clear signal
            # that this flow regime is unsupported.
            return Q if Q > 0 else _SENTINEL_RESIDUAL

        annulus_result = evaluate_hx_correlation(
            geometry=annulus_geom,
            flow=annulus_flow,
            boundary_condition="inner_wall_heated",
            context=corr_ctx,
        )
        is_annulus_blocked = annulus_result.status.value == "blocked"
        if is_annulus_blocked or annulus_result.heat_transfer_coefficient <= 0:
            return Q if Q > 0 else _SENTINEL_RESIDUAL

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
            return _SENTINEL_RESIDUAL

        # --- 6m. Residual ---
        residual = Q - UA * lmtd
        return residual

    # =====================================================================
    # 7. SOLVE
    # =====================================================================

    solver_result = solve_rating(
        residual_fn=residual_fn,
        q_max=q_max,
        params=params,
        c_hot=C_hot,
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

    # Compute final outlet states
    h_hot_out_sol = h_hot_in - Q_sol / hot_mass_flow_kg_s
    h_cold_out_sol = h_cold_in + Q_sol / cold_mass_flow_kg_s

    hot_outlet_final = provider.state_ph(
        hot_fluid,
        hot_inlet_pressure_pa,
        h_hot_out_sol,
        reference_state=provider.reference_state_policy,
    )
    property_calls.append(
        _build_provider_call_record(
            hot_outlet_final,
            query_type="PH",
            inputs=(("pressure_pa", hot_inlet_pressure_pa), ("enthalpy_j_kg", h_hot_out_sol)),
            provider=provider,
            stage="final_state",
            stream_role="hot_outlet",
            sequence_index=seq_idx,
        )
    )
    seq_idx += 1

    cold_outlet_final = provider.state_ph(
        cold_fluid,
        cold_inlet_pressure_pa,
        h_cold_out_sol,
        reference_state=provider.reference_state_policy,
    )
    property_calls.append(
        _build_provider_call_record(
            cold_outlet_final,
            query_type="PH",
            inputs=(("pressure_pa", cold_inlet_pressure_pa), ("enthalpy_j_kg", h_cold_out_sol)),
            provider=provider,
            stage="final_state",
            stream_role="cold_outlet",
            sequence_index=seq_idx,
        )
    )
    seq_idx += 1

    # --- Energy balance ---
    Q_hot = hot_mass_flow_kg_s * (h_hot_in - h_hot_out_sol)
    Q_cold = cold_mass_flow_kg_s * (h_cold_out_sol - h_cold_in)
    energy_residual = abs(Q_hot - Q_cold)
    max_q = max(abs(Q_hot), abs(Q_cold))
    energy_residual / max_q if max_q > 1.0 else energy_residual

    # --- Final thermal diagnostics ---
    T_h_out_sol = hot_outlet_final.temperature_k
    T_c_out_sol = cold_outlet_final.temperature_k
    T_bulk_hot_final = (hot_inlet_temperature_k + T_h_out_sol) / 2.0
    T_bulk_cold_final = (cold_inlet_temperature_k + T_c_out_sol) / 2.0

    # Rebuild final correlation evaluations for diagnostics
    if tube_in_hot:
        tube_flow_final = FlowPropertiesInput(
            mass_flow_kg_s=hot_mass_flow_kg_s,
            density_kg_m3=hot_outlet_final.density_kg_m3,
            dynamic_viscosity_pa_s=hot_outlet_final.viscosity_pa_s,
            thermal_conductivity_w_m_k=hot_outlet_final.conductivity_w_m_k,
            specific_heat_j_kg_k=hot_outlet_final.cp_j_kg_k,
            bulk_temperature_k=T_bulk_hot_final,
            heating=True,
        )
        annulus_flow_final = FlowPropertiesInput(
            mass_flow_kg_s=cold_mass_flow_kg_s,
            density_kg_m3=cold_outlet_final.density_kg_m3,
            dynamic_viscosity_pa_s=cold_outlet_final.viscosity_pa_s,
            thermal_conductivity_w_m_k=cold_outlet_final.conductivity_w_m_k,
            specific_heat_j_kg_k=cold_outlet_final.cp_j_kg_k,
            bulk_temperature_k=T_bulk_cold_final,
            heating=False,
        )
    else:
        tube_flow_final = FlowPropertiesInput(
            mass_flow_kg_s=cold_mass_flow_kg_s,
            density_kg_m3=cold_outlet_final.density_kg_m3,
            dynamic_viscosity_pa_s=cold_outlet_final.viscosity_pa_s,
            thermal_conductivity_w_m_k=cold_outlet_final.conductivity_w_m_k,
            specific_heat_j_kg_k=cold_outlet_final.cp_j_kg_k,
            bulk_temperature_k=T_bulk_cold_final,
            heating=False,
        )
        annulus_flow_final = FlowPropertiesInput(
            mass_flow_kg_s=hot_mass_flow_kg_s,
            density_kg_m3=hot_outlet_final.density_kg_m3,
            dynamic_viscosity_pa_s=hot_outlet_final.viscosity_pa_s,
            thermal_conductivity_w_m_k=hot_outlet_final.conductivity_w_m_k,
            specific_heat_j_kg_k=hot_outlet_final.cp_j_kg_k,
            bulk_temperature_k=T_bulk_hot_final,
            heating=True,
        )

    corr_ctx_final = CorrCalculationContext()
    tube_result_final = evaluate_hx_correlation(
        geometry=tube_geom,
        flow=tube_flow_final,
        boundary_condition="constant_wall_temperature",
        context=corr_ctx_final,
    )
    annulus_result_final = evaluate_hx_correlation(
        geometry=annulus_geom,
        flow=annulus_flow_final,
        boundary_condition="inner_wall_heated",
        context=corr_ctx_final,
    )

    tube_h_val = (
        tube_result_final.heat_transfer_coefficient
        if tube_result_final.status.value != "blocked"
        else 0.0
    )
    annulus_h_val = (
        annulus_result_final.heat_transfer_coefficient
        if annulus_result_final.status.value != "blocked"
        else 0.0
    )

    # Correlation info
    tube_sel_corr = tube_result_final.selected_correlation
    tube_corr_id = tube_sel_corr.correlation_id if tube_sel_corr else None
    tube_corr_ver = tube_sel_corr.version if tube_sel_corr else None
    tube_app_status = tube_result_final.applicability_status or None
    annulus_sel_corr = annulus_result_final.selected_correlation
    annulus_corr_id = annulus_sel_corr.correlation_id if annulus_sel_corr else None
    annulus_corr_ver = annulus_sel_corr.version if annulus_sel_corr else None
    annulus_app_status = annulus_result_final.applicability_status or None

    # Add warnings from correlation results
    for w in tube_result_final.warnings:
        warnings.append(w)
    for w in annulus_result_final.warnings:
        warnings.append(w)

    # Final resistance breakdown
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

    # LMTD at solution
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
    if not math.isfinite(lmtd_final):
        lmtd_final = 0.0

    # ε-NTU diagnostics
    NTU_final = UA_final / C_min if C_min > 0 else 0.0
    if flow_arrangement == FlowArrangement.COUNTERFLOW:
        eps_calc = effectiveness_counterflow(NTU_final, capacity_ratio)
    else:
        eps_calc = effectiveness_parallel(NTU_final, capacity_ratio)

    # Overall U values
    U_inner = UA_final / area_inner_m2 if area_inner_m2 > 0 else 0.0
    U_outer = UA_final / area_outer_m2 if area_outer_m2 > 0 else 0.0

    # ua_lmtd residual
    ua_lmtd_residual = (
        abs(Q_sol - UA_final * lmtd_final) if UA_final > 0 and lmtd_final > 0 else 0.0
    )

    solver_details = _make_solver_details(solver_result)

    # =====================================================================
    # 9. BUILD PROVENANCE AND HASH
    # =====================================================================

    # Compute result hash first (needed for provenance RESULT node)
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
        energy_residual_w=energy_residual,
        ua_lmtd_residual_w=ua_lmtd_residual,
        iterations=solver_result.iterations,
        converged=True,
        solver_termination_reason=solver_result.termination_reason.value,
        solver_details=solver_details,
        property_calls=tuple(property_calls),
        warnings=tuple(warnings),
        blockers=(),
        status=RatingStatus.SUCCEEDED,
        provenance_digest="",  # placeholder
    )

    # Build provenance with the real result_hash
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
    provenance_digest = _provenance_graph_digest(provenance_graph)

    # =====================================================================
    # 10. BUILD RESULT
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
        energy_residual_w=energy_residual,
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
    )

    return result
