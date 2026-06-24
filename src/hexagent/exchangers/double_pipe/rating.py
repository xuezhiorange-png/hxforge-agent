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
from hexagent.exchangers.double_pipe.recorder import (
    EvaluationContext,
    EvaluationRecorder,
    EvaluationRole,
    SolverEvaluationPhase,
)
from hexagent.exchangers.double_pipe.result import (
    ApplicabilitySnapshot,
    FluidStateSnapshot,
    PropertyProvenanceSnapshot,
    QMaxDiagnosticsSnapshot,
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

# Q_max dual tolerance (parallel-flow pinch search)
Q_MAX_Q_TOLERANCE_W = 1e-6
Q_MAX_PINCH_TOLERANCE_K = 1e-6
Q_MAX_MAX_ITERATIONS = 100


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


class TrialEvaluationAbort(Exception):
    """Raised to abort solver iteration when trial is infeasible.

    Carries the full TrialEvaluation so the solver can terminate
    gracefully without converting domain errors to numeric residuals.
    """

    def __init__(self, trial: TrialEvaluation):
        self.trial = trial
        super().__init__(f"Trial Q={trial.q_w} is not feasible")


# ---------------------------------------------------------------------------
# Trial evaluator class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrialEvaluator:
    """Encapsulates trial Q evaluation logic for double-pipe rating.

    Extracted from the nested ``_evaluate_trial`` closure inside
    ``rate_double_pipe`` so that the evaluation logic is reusable and
    testable in isolation.  All dependencies are injected at
    construction time; ``evaluate()`` is the only mutable entry point
    (via the recorder).
    """

    provider: PropertyProvider
    recorder: EvaluationRecorder
    hot_fluid: FluidIdentifier
    cold_fluid: FluidIdentifier
    hot_mass_flow_kg_s: float
    cold_mass_flow_kg_s: float
    hot_inlet_pressure_pa: float
    cold_inlet_pressure_pa: float
    hot_inlet_temperature_k: float
    cold_inlet_temperature_k: float
    h_hot_in: float
    h_cold_in: float
    tube_in_hot: bool
    flow_arrangement: FlowArrangement
    tube_geom: CircularTubeGeometry
    annulus_geom: ConcentricAnnulusGeometry
    tube_boundary_condition: ThermalBoundaryCondition
    annulus_boundary_condition: ThermalBoundaryCondition
    area_inner_m2: float
    area_outer_m2: float
    wall_resistance: float
    geometry: DoublePipeGeometry

    def evaluate(
        self,
        Q: float,
        *,
        ctx: EvaluationContext,
    ) -> TrialEvaluation:
        """Evaluate a single trial Q and return a TrialEvaluation."""
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
        h_hot_out = self.h_hot_in - Q / self.hot_mass_flow_kg_s
        h_cold_out = self.h_cold_in + Q / self.cold_mass_flow_kg_s

        # --- 6b. Back-calculate outlet states via PH query ---
        hot_outlet_inputs = (
            ("pressure_pa", self.hot_inlet_pressure_pa),
            ("enthalpy_j_kg", h_hot_out),
        )
        cold_outlet_inputs = (
            ("pressure_pa", self.cold_inlet_pressure_pa),
            ("enthalpy_j_kg", h_cold_out),
        )

        hot_outlet_state: FluidState | None = None
        cold_outlet_state: FluidState | None = None

        try:
            hot_outlet_state = self.provider.state_ph(
                self.hot_fluid,
                self.hot_inlet_pressure_pa,
                h_hot_out,
                reference_state=self.provider.reference_state_policy,
            )
            self.recorder.record_success(
                ctx,
                hot_outlet_state,
                query_type="PH",
                inputs=hot_outlet_inputs,
                provider=self.provider,
                stage="brent_evaluation",
                stream_role="hot_solver",
            )
        except PropertyServiceError as exc:
            self.recorder.record_failure(
                ctx,
                fluid_name=self.hot_fluid.name,
                query_type="PH",
                inputs=hot_outlet_inputs,
                provider=self.provider,
                stage="brent_evaluation",
                stream_role="hot_solver",
                error_code=(exc.code.value if hasattr(exc, "code") else "property_unavailable"),
                error_message=str(exc),
            )
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
                        ErrorCode.PROPERTY_EVALUATION_FAILED,
                        f"Hot-side outlet property evaluation failed: {exc}",
                        (("fluid", self.hot_fluid.name), ("stage", "brent_evaluation")),
                    ),
                ),
            )

        try:
            cold_outlet_state = self.provider.state_ph(
                self.cold_fluid,
                self.cold_inlet_pressure_pa,
                h_cold_out,
                reference_state=self.provider.reference_state_policy,
            )
            self.recorder.record_success(
                ctx,
                cold_outlet_state,
                query_type="PH",
                inputs=cold_outlet_inputs,
                provider=self.provider,
                stage="brent_evaluation",
                stream_role="cold_solver",
            )
        except PropertyServiceError as exc:
            self.recorder.record_failure(
                ctx,
                fluid_name=self.cold_fluid.name,
                query_type="PH",
                inputs=cold_outlet_inputs,
                provider=self.provider,
                stage="brent_evaluation",
                stream_role="cold_solver",
                error_code=(exc.code.value if hasattr(exc, "code") else "property_unavailable"),
                error_message=str(exc),
            )
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
                property_calls=(),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PROPERTY_EVALUATION_FAILED,
                        f"Cold-side outlet property evaluation failed: {exc}",
                        (("fluid", self.cold_fluid.name), ("stage", "brent_evaluation")),
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
                property_calls=(),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PHASE_NOT_SUPPORTED,
                        f"Hot-side outlet phase {hot_outlet_state.phase.value} is not single-phase",
                        (("phase", hot_outlet_state.phase.value), ("fluid", self.hot_fluid.name)),
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
                property_calls=(),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PHASE_NOT_SUPPORTED,
                        f"Cold-side outlet phase {cold_outlet_state.phase.value}"
                        " is not single-phase",
                        (("phase", cold_outlet_state.phase.value), ("fluid", self.cold_fluid.name)),
                    ),
                ),
            )

        # --- 6d. Bulk temperatures and PropertyProvider queries ---
        T_bulk_hot = (self.hot_inlet_temperature_k + hot_outlet_state.temperature_k) / 2.0
        T_bulk_cold = (self.cold_inlet_temperature_k + cold_outlet_state.temperature_k) / 2.0
        P_bulk_hot = self.hot_inlet_pressure_pa  # no pressure drop
        P_bulk_cold = self.cold_inlet_pressure_pa  # no pressure drop

        # Query bulk states via PropertyProvider at T_bulk
        hot_bulk_state: FluidState | None = None
        cold_bulk_state: FluidState | None = None

        try:
            hot_bulk_state = self.provider.state_tp(self.hot_fluid, T_bulk_hot, P_bulk_hot)
            self.recorder.record_success(
                ctx,
                hot_bulk_state,
                query_type="TP",
                inputs=(("temperature_k", T_bulk_hot), ("pressure_pa", P_bulk_hot)),
                provider=self.provider,
                stage="bulk",
                stream_role="hot_bulk",
            )
        except PropertyServiceError as exc:
            self.recorder.record_failure(
                ctx,
                fluid_name=self.hot_fluid.name,
                query_type="TP",
                inputs=(("temperature_k", T_bulk_hot), ("pressure_pa", P_bulk_hot)),
                provider=self.provider,
                stage="bulk",
                stream_role="hot_bulk",
                error_code=(exc.code.value if hasattr(exc, "code") else "property_unavailable"),
                error_message=str(exc),
            )
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
                property_calls=(),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PROPERTY_EVALUATION_FAILED,
                        f"Hot-side bulk property evaluation failed: {exc}",
                        (("fluid", self.hot_fluid.name), ("stage", "bulk")),
                    ),
                ),
            )

        try:
            cold_bulk_state = self.provider.state_tp(self.cold_fluid, T_bulk_cold, P_bulk_cold)
            self.recorder.record_success(
                ctx,
                cold_bulk_state,
                query_type="TP",
                inputs=(("temperature_k", T_bulk_cold), ("pressure_pa", P_bulk_cold)),
                provider=self.provider,
                stage="bulk",
                stream_role="cold_bulk",
            )
        except PropertyServiceError as exc:
            self.recorder.record_failure(
                ctx,
                fluid_name=self.cold_fluid.name,
                query_type="TP",
                inputs=(("temperature_k", T_bulk_cold), ("pressure_pa", P_bulk_cold)),
                provider=self.provider,
                stage="bulk",
                stream_role="cold_bulk",
                error_code=(exc.code.value if hasattr(exc, "code") else "property_unavailable"),
                error_message=str(exc),
            )
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
                property_calls=(),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PROPERTY_EVALUATION_FAILED,
                        f"Cold-side bulk property evaluation failed: {exc}",
                        (("fluid", self.cold_fluid.name), ("stage", "bulk")),
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
                property_calls=(),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PHASE_NOT_SUPPORTED,
                        f"Hot-side bulk phase {hot_bulk_state.phase.value} is not single-phase",
                        (("phase", hot_bulk_state.phase.value), ("fluid", self.hot_fluid.name)),
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
                property_calls=(),
                warnings=(),
                blockers=(
                    _make_blocker(
                        ErrorCode.PHASE_NOT_SUPPORTED,
                        f"Cold-side bulk phase {cold_bulk_state.phase.value} is not single-phase",
                        (("phase", cold_bulk_state.phase.value), ("fluid", self.cold_fluid.name)),
                    ),
                ),
            )

        # --- 6f. Assign tube and annulus flows based on tube_in_hot ---
        # Hot stream: heating=False (being cooled)
        # Cold stream: heating=True (being heated)
        if self.tube_in_hot:
            tube_flow = FlowPropertiesInput(
                mass_flow_kg_s=self.hot_mass_flow_kg_s,
                density_kg_m3=hot_bulk_state.density_kg_m3,
                dynamic_viscosity_pa_s=hot_bulk_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=hot_bulk_state.conductivity_w_m_k,
                specific_heat_j_kg_k=hot_bulk_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_hot,
                heating=False,  # hot stream is being cooled
            )
            annulus_flow = FlowPropertiesInput(
                mass_flow_kg_s=self.cold_mass_flow_kg_s,
                density_kg_m3=cold_bulk_state.density_kg_m3,
                dynamic_viscosity_pa_s=cold_bulk_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=cold_bulk_state.conductivity_w_m_k,
                specific_heat_j_kg_k=cold_bulk_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_cold,
                heating=True,  # cold stream is being heated
            )
        else:
            tube_flow = FlowPropertiesInput(
                mass_flow_kg_s=self.cold_mass_flow_kg_s,
                density_kg_m3=cold_bulk_state.density_kg_m3,
                dynamic_viscosity_pa_s=cold_bulk_state.viscosity_pa_s,
                thermal_conductivity_w_m_k=cold_bulk_state.conductivity_w_m_k,
                specific_heat_j_kg_k=cold_bulk_state.cp_j_kg_k,
                bulk_temperature_k=T_bulk_cold,
                heating=True,  # cold stream is being heated
            )
            annulus_flow = FlowPropertiesInput(
                mass_flow_kg_s=self.hot_mass_flow_kg_s,
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
            geometry=self.tube_geom,
            flow=tube_flow,
            boundary_condition=self.tube_boundary_condition,
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
                property_calls=(),
                warnings=tuple(trial_warnings),
                blockers=tuple(trial_blockers),
            )

        # --- 6h. Evaluate annulus correlation ---
        annulus_result = evaluate_hx_correlation(
            geometry=self.annulus_geom,
            flow=annulus_flow,
            boundary_condition=self.annulus_boundary_condition,
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
                property_calls=(),
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
            area_inner_m2=self.area_inner_m2,
            area_outer_m2=self.area_outer_m2,
            wall_resistance_kw=self.wall_resistance,
            fouling_inner_m2k_w=self.geometry.inner_fouling_resistance_m2k_w,
            fouling_outer_m2k_w=self.geometry.outer_fouling_resistance_m2k_w,
        )
        UA = R_breakdown.ua_w_k

        # --- 6k. Compute outlet temperatures ---
        T_h_out = hot_outlet_state.temperature_k
        T_c_out = cold_outlet_state.temperature_k

        # --- 6l. Compute LMTD ---
        if self.flow_arrangement == FlowArrangement.COUNTERFLOW:
            lmtd = lmtd_counterflow(
                self.hot_inlet_temperature_k,
                T_h_out,
                self.cold_inlet_temperature_k,
                T_c_out,
            )
        else:
            lmtd = lmtd_parallel(
                self.hot_inlet_temperature_k,
                T_h_out,
                self.cold_inlet_temperature_k,
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
                property_calls=(),
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
            property_calls=(),
            warnings=tuple(trial_warnings),
            blockers=(),
        )


@dataclass(frozen=True)
class QMaxResult:
    """Structured result from Q_max computation.

    Property calls are owned by the EvaluationRecorder; the recorder
    is the single source of truth for all property call records.
    """

    q_max_w: float
    iterations: int
    final_pinch_residual_k: float
    termination_reason: str
    final_q_low_w: float | None = None
    final_q_high_w: float | None = None
    final_q_width_w: float | None = None
    # Counter-flow: explicit limit fields
    hot_limit_w: float | None = None
    cold_limit_w: float | None = None
    limiting_side: str | None = None
    # Parallel-flow: bracket and pinch diagnostics
    q_tolerance_w: float | None = None
    pinch_temperature_tolerance_k: float | None = None


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
    prov = state.provenance
    property_provenance = PropertyProvenanceSnapshot(
        fluid_identifier=(
            prov.fluid_identifier
            if isinstance(prov.fluid_identifier, str)
            else str(prov.fluid_identifier)
        ),
        backend_name=prov.backend_name,
        backend_version=prov.backend_version,
        backend_git_revision=getattr(prov, "backend_git_revision", ""),
        reference_state_policy=(
            prov.reference_state_policy.value
            if hasattr(prov.reference_state_policy, "value")
            else str(prov.reference_state_policy)
        ),
        configuration_fingerprint=getattr(prov, "configuration_fingerprint", ""),
        validation_level=(
            prov.validation_level.value
            if hasattr(prov.validation_level, "value")
            else str(prov.validation_level)
        ),
        cache_policy_version=getattr(prov, "cache_policy_version", ""),
    )
    return FluidStateSnapshot(
        temperature_k=state.temperature_k,
        pressure_pa=state.pressure_pa,
        enthalpy_j_kg=state.enthalpy_j_kg,
        density_kg_m3=state.density_kg_m3,
        cp_j_kg_k=state.cp_j_kg_k,
        viscosity_pa_s=state.viscosity_pa_s,
        conductivity_w_m_k=state.conductivity_w_m_k,
        phase=state.phase.value,
        quality=state.quality,
        property_provenance=property_provenance,
    )


def _make_selected_correlation_snapshot(
    corr_result: CorrelationResult,
) -> SelectedCorrelationSnapshot | None:
    """Build a full SelectedCorrelationSnapshot from a CorrelationResult."""
    sc = corr_result.selected_correlation
    if sc is None:
        return None
    return SelectedCorrelationSnapshot(
        correlation_id=sc.correlation_id,
        version=sc.version,
        definition_hash=sc.definition_hash,
        source_title=sc.source_title,
        source_authors=sc.source_authors,
        source_year=sc.source_year,
        source_reference=sc.source_reference,
        source_verification_status=sc.source_verification_status,
        nusselt_basis=sc.nusselt_basis,
        is_adaptation=sc.is_adaptation,
        adaptation_limitation=sc.adaptation_limitation,
    )


def _canonical_value(v: Any) -> str | int | float | bool | None | tuple[Any, ...]:
    """Recursively convert a value to a canonical immutable type."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, dict):
        return tuple((str(k), _canonical_value(v[k])) for k in sorted(v.keys()))
    if isinstance(v, (list, tuple)):
        return tuple(_canonical_value(item) for item in v)
    return str(v)


def _make_applicability_snapshot(
    corr_result: CorrelationResult,
) -> ApplicabilitySnapshot | None:
    """Build a full ApplicabilitySnapshot from a CorrelationResult."""
    aa = corr_result.applicability_assessment
    if aa is None:
        return ApplicabilitySnapshot(status=corr_result.applicability_status or "")
    # Extract reynolds/prandtl ranges from variable_results if available
    reyn_min: float | None = None
    reyn_max: float | None = None
    pran_min: float | None = None
    pran_max: float | None = None
    for vr in aa.variable_results:
        vr_var = vr.variable.value if hasattr(vr.variable, "value") else str(vr.variable)
        if vr_var == "reynolds":
            reyn_min = vr.absolute_minimum
            reyn_max = vr.absolute_maximum
        elif vr_var == "prandtl":
            pran_min = vr.absolute_minimum
            pran_max = vr.absolute_maximum
    status_str = aa.status.value if hasattr(aa.status, "value") else str(aa.status)
    # Convert assessment to canonical typed immutable value tree
    raw_dict = aa.model_dump() if hasattr(aa, "model_dump") else {}
    raw_assessment: tuple[tuple[str, Any], ...] = tuple(
        (str(k), _canonical_value(v)) for k, v in sorted(raw_dict.items())
    )
    return ApplicabilitySnapshot(
        status=status_str,
        assessment_hash=aa.assessment_hash,
        reynolds_min=reyn_min,
        reynolds_max=reyn_max,
        prandtl_min=pran_min,
        prandtl_max=pran_max,
        geometry_type=getattr(aa, "geometry_type", ""),
        notes=getattr(aa, "notes", ""),
        raw_assessment=raw_assessment,
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
    evaluation_index: int = 0,
    evaluation_role: str = "inlet",
    call_index_within_evaluation: int = 0,
    trial_q_w: float | None = None,
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
        evaluation_index=evaluation_index,
        evaluation_role=evaluation_role,
        call_index_within_evaluation=call_index_within_evaluation,
        trial_q_w=trial_q_w,
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
    evaluation_index: int = 0,
    evaluation_role: str = "inlet",
    call_index_within_evaluation: int = 0,
    trial_q_w: float | None = None,
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
        evaluation_index=evaluation_index,
        evaluation_role=evaluation_role,
        call_index_within_evaluation=call_index_within_evaluation,
        trial_q_w=trial_q_w,
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
    """Build a valid minimal resistance breakdown (non-zero for validation)."""
    return ResistanceBreakdownModel(
        r_conv_inner=1e-4,
        r_foul_inner=0.0,
        r_wall=1e-4,
        r_foul_outer=0.0,
        r_conv_outer=1e-4,
        total_resistance=3e-4,
        ua_w_k=1.0 / 3e-4,
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


def _build_final_evaluation_blocked_result(
    *,
    final_trial: TrialEvaluation,
    solver_result: SolverResult,
    blockers: list[EngineeringMessage],
    warnings: list[EngineeringMessage],
    recorder: EvaluationRecorder,
    request_identity: RatingRequestIdentity,
    provider_identity: ProviderIdentitySnapshot,
    ctx_snapshot: ExecutionContextSnapshot,
    flow_arrangement: FlowArrangement,
    area_inner_m2: float,
    area_outer_m2: float,
    hot_inlet_state_snapshot: FluidStateSnapshot,
    cold_inlet_state_snapshot: FluidStateSnapshot,
    hot_inlet_temperature_k: float,
    cold_inlet_temperature_k: float,
    tube_in_hot: bool,
    geometry: DoublePipeGeometry,
    hot_mass_flow_kg_s: float,
    cold_mass_flow_kg_s: float,
    q_max_diagnostics: QMaxDiagnosticsSnapshot | None = None,
) -> RatingResult:
    """Build a BLOCKED result when the final evaluation at Q_sol is infeasible.

    Unlike ``_blocked_result`` (which zeros all thermal quantities), this
    function preserves whatever diagnostics were computed during the
    partially-completed final trial evaluation — solver results, available
    state snapshots, correlation data, and provenance — so downstream
    consumers can inspect what was computed before the blocker was hit.
    """
    # Extract whatever partial data is available from the final trial
    tube_result_final = final_trial.tube_result
    annulus_result_final = final_trial.annulus_result

    # Build state snapshots from whatever the trial provided
    hot_outlet_snapshot = (
        _make_fluid_state_snapshot(final_trial.hot_outlet_state)
        if final_trial.hot_outlet_state is not None
        else None
    )
    cold_outlet_snapshot = (
        _make_fluid_state_snapshot(final_trial.cold_outlet_state)
        if final_trial.cold_outlet_state is not None
        else None
    )
    hot_bulk_snapshot = (
        _make_fluid_state_snapshot(final_trial.hot_bulk_state)
        if final_trial.hot_bulk_state is not None
        else None
    )
    cold_bulk_snapshot = (
        _make_fluid_state_snapshot(final_trial.cold_bulk_state)
        if final_trial.cold_bulk_state is not None
        else None
    )

    # Correlation snapshots (may be None if trial didn't reach correlation step)
    tube_sc = (
        _make_selected_correlation_snapshot(tube_result_final)
        if tube_result_final is not None
        else None
    )
    annulus_sc = (
        _make_selected_correlation_snapshot(annulus_result_final)
        if annulus_result_final is not None
        else None
    )
    tube_ap = (
        _make_applicability_snapshot(tube_result_final) if tube_result_final is not None else None
    )
    annulus_ap = (
        _make_applicability_snapshot(annulus_result_final)
        if annulus_result_final is not None
        else None
    )

    tube_cid = tube_sc.correlation_id if tube_sc else None
    tube_cver = tube_sc.version if tube_sc else None
    tube_ast = (tube_result_final.applicability_status or None) if tube_result_final else None
    annulus_cid = annulus_sc.correlation_id if annulus_sc else None
    annulus_cver = annulus_sc.version if annulus_sc else None
    annulus_ast = (
        (annulus_result_final.applicability_status or None) if annulus_result_final else None
    )

    # Extract h values if available
    tube_h_val = (
        tube_result_final.heat_transfer_coefficient if tube_result_final is not None else None
    )
    annulus_h_val = (
        annulus_result_final.heat_transfer_coefficient if annulus_result_final is not None else None
    )

    # Build thermal resistance if both h values are available
    if (
        tube_h_val is not None
        and annulus_h_val is not None
        and tube_h_val > 0
        and annulus_h_val > 0
    ):
        R_breakdown_final = build_thermal_resistance(
            h_inner=tube_h_val,
            h_outer=annulus_h_val,
            area_inner_m2=area_inner_m2,
            area_outer_m2=area_outer_m2,
            wall_resistance_kw=compute_wall_resistance(
                geometry.inner_tube_inner_diameter_m,
                geometry.inner_tube_outer_diameter_m,
                geometry.effective_length_m,
                geometry.wall_thermal_conductivity_w_m_k,
            ),
            fouling_inner_m2k_w=geometry.inner_fouling_resistance_m2k_w,
            fouling_outer_m2k_w=geometry.outer_fouling_resistance_m2k_w,
        )
        UA_final = R_breakdown_final.ua_w_k
        rb_model = _make_resistance_breakdown(R_breakdown_final)
        U_inner = UA_final / area_inner_m2 if area_inner_m2 > 0 else None
        U_outer = UA_final / area_outer_m2 if area_outer_m2 > 0 else None
    else:
        UA_final = None
        rb_model = None
        U_inner = None
        U_outer = None

    # Outlet temperatures (may be None)
    T_h_out_sol = (
        final_trial.hot_outlet_state.temperature_k
        if final_trial.hot_outlet_state is not None
        else None
    )
    T_c_out_sol = (
        final_trial.cold_outlet_state.temperature_k
        if final_trial.cold_outlet_state is not None
        else None
    )

    # Capacity rates from inlet states (always available since we passed validation)
    C_hot = (
        hot_mass_flow_kg_s * hot_inlet_state_snapshot.cp_j_kg_k
        if hot_inlet_state_snapshot and hot_inlet_state_snapshot.cp_j_kg_k is not None
        else None
    )
    C_cold = (
        cold_mass_flow_kg_s * cold_inlet_state_snapshot.cp_j_kg_k
        if cold_inlet_state_snapshot and cold_inlet_state_snapshot.cp_j_kg_k is not None
        else None
    )
    C_min = min(C_hot, C_cold) if C_hot is not None and C_cold is not None else None
    C_max = max(C_hot, C_cold) if C_hot is not None and C_cold is not None else None
    capacity_ratio = (
        C_min / C_max if C_min is not None and C_max is not None and C_max > 0 else None
    )

    # ε-NTU diagnostics
    if (
        UA_final is not None
        and UA_final > 0
        and C_min is not None
        and C_min > 0
        and capacity_ratio is not None
    ):
        NTU_final = UA_final / C_min
        if flow_arrangement == FlowArrangement.COUNTERFLOW:
            eps_calc = effectiveness_counterflow(NTU_final, capacity_ratio)
        else:
            eps_calc = effectiveness_parallel(NTU_final, capacity_ratio)
    else:
        NTU_final = None
        eps_calc = None

    # LMTD (may be None)
    lmtd_final = None
    if T_h_out_sol is not None and T_c_out_sol is not None:
        if flow_arrangement == FlowArrangement.COUNTERFLOW:
            lmtd_val = lmtd_counterflow(
                hot_inlet_temperature_k,
                T_h_out_sol,
                cold_inlet_temperature_k,
                T_c_out_sol,
            )
        else:
            lmtd_val = lmtd_parallel(
                hot_inlet_temperature_k,
                T_h_out_sol,
                cold_inlet_temperature_k,
                T_c_out_sol,
            )
        if math.isfinite(lmtd_val):
            lmtd_final = lmtd_val

    # Map tube/annulus sides
    if tube_in_hot:
        tsi = hot_inlet_state_snapshot
        tso = hot_outlet_snapshot
        tbu = hot_bulk_snapshot
        asi = cold_inlet_state_snapshot
        aso = cold_outlet_snapshot
        abu = cold_bulk_snapshot
    else:
        tsi = cold_inlet_state_snapshot
        tso = cold_outlet_snapshot
        tbu = cold_bulk_snapshot
        asi = hot_inlet_state_snapshot
        aso = hot_outlet_snapshot
        abu = hot_bulk_snapshot

    solver_details = _make_solver_details(solver_result)

    core_graph, core_nodes, core_edges = build_provenance_core(
        flow_arrangement=flow_arrangement,
        property_calls=recorder.records,
        iterations=solver_result.iterations,
        converged=solver_result.converged,
        warnings=warnings,
        blockers=blockers,
        execution_context=ctx_snapshot,
        request_identity=request_identity,
        tube_correlation_info=tube_sc,
        annulus_correlation_info=annulus_sc,
        tube_applicability=tube_ap,
        annulus_applicability=annulus_ap,
        q_max_diagnostics=q_max_diagnostics,
    )
    core_provenance_digest = _provenance_graph_digest(core_graph)

    result_hash = compute_result_hash(
        request_identity=request_identity,
        provider_identity=provider_identity,
        flow_arrangement=flow_arrangement,
        heat_duty_w=final_trial.q_w,
        hot_outlet_temperature_k=T_h_out_sol,
        cold_outlet_temperature_k=T_c_out_sol,
        tube_reynolds=(tube_result_final.reynolds_number if tube_result_final else None),
        tube_prandtl=(tube_result_final.prandtl_number if tube_result_final else None),
        tube_nusselt=(tube_result_final.nusselt_number if tube_result_final else None),
        tube_h=tube_h_val,
        tube_selected_correlation_id=tube_cid,
        tube_selected_correlation_version=tube_cver,
        tube_applicability_status=tube_ast,
        annulus_reynolds=(annulus_result_final.reynolds_number if annulus_result_final else None),
        annulus_prandtl=(annulus_result_final.prandtl_number if annulus_result_final else None),
        annulus_nusselt=(annulus_result_final.nusselt_number if annulus_result_final else None),
        annulus_h=annulus_h_val,
        annulus_selected_correlation_id=annulus_cid,
        annulus_selected_correlation_version=annulus_cver,
        annulus_applicability_status=annulus_ast,
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
        energy_residual_w=None,
        ua_lmtd_residual_w=None,
        iterations=solver_result.iterations,
        converged=solver_result.converged,
        solver_termination_reason=solver_result.termination_reason.value,
        solver_details=solver_details,
        property_calls=recorder.records,
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        status=RatingStatus.BLOCKED,
        hot_inlet_state=hot_inlet_state_snapshot,
        cold_inlet_state=cold_inlet_state_snapshot,
        hot_outlet_state=hot_outlet_snapshot,
        cold_outlet_state=cold_outlet_snapshot,
        tube_side_inlet_state=tsi,
        tube_side_outlet_state=tso,
        annulus_side_inlet_state=asi,
        annulus_side_outlet_state=aso,
        tube_bulk_state=tbu,
        annulus_bulk_state=abu,
        tube_selected_correlation_snap=tube_sc,
        annulus_selected_correlation_snap=annulus_sc,
        tube_applicability_snap=tube_ap,
        annulus_applicability_snap=annulus_ap,
        core_provenance_digest=core_provenance_digest,
        Q_hot_w=None,
        Q_cold_w=None,
        relative_energy_residual=None,
        energy_tolerance_w=None,
        relative_ua_lmtd_residual=None,
        ua_lmtd_tolerance_w=None,
        q_max_diagnostics=q_max_diagnostics,
    )

    provenance_graph = build_provenance(
        flow_arrangement=flow_arrangement,
        property_calls=recorder.records,
        iterations=solver_result.iterations,
        converged=solver_result.converged,
        warnings=warnings,
        blockers=blockers,
        result_hash=result_hash,
        execution_context=ctx_snapshot,
        request_identity=request_identity,
        tube_correlation_info=tube_sc,
        annulus_correlation_info=annulus_sc,
        tube_applicability=tube_ap,
        annulus_applicability=annulus_ap,
        q_max_diagnostics=q_max_diagnostics,
    )
    provenance_digest = _provenance_graph_digest(provenance_graph)

    return RatingResult(
        status=RatingStatus.BLOCKED,
        flow_arrangement=flow_arrangement,
        heat_duty_w=final_trial.q_w,
        hot_outlet_temperature_k=T_h_out_sol,
        cold_outlet_temperature_k=T_c_out_sol,
        tube_reynolds=(tube_result_final.reynolds_number if tube_result_final else None),
        tube_prandtl=(tube_result_final.prandtl_number if tube_result_final else None),
        tube_nusselt=(tube_result_final.nusselt_number if tube_result_final else None),
        tube_h=tube_h_val,
        tube_selected_correlation_id=tube_cid,
        tube_selected_correlation_version=tube_cver,
        tube_applicability_status=tube_ast,
        annulus_reynolds=(annulus_result_final.reynolds_number if annulus_result_final else None),
        annulus_prandtl=(annulus_result_final.prandtl_number if annulus_result_final else None),
        annulus_nusselt=(annulus_result_final.nusselt_number if annulus_result_final else None),
        annulus_h=annulus_h_val,
        annulus_selected_correlation_id=annulus_cid,
        annulus_selected_correlation_version=annulus_cver,
        annulus_applicability_status=annulus_ast,
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
        energy_residual_w=None,
        ua_lmtd_residual_w=None,
        iterations=solver_result.iterations,
        converged=solver_result.converged,
        solver_termination_reason=solver_result.termination_reason.value,
        solver_details=solver_details,
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        property_calls=recorder.records,
        provider_identity=provider_identity,
        request_identity=request_identity,
        execution_context=ctx_snapshot,
        result_hash=result_hash,
        provenance_graph=provenance_graph,
        provenance_digest=provenance_digest,
        core_provenance_digest=core_provenance_digest,
        hot_inlet_state=hot_inlet_state_snapshot,
        cold_inlet_state=cold_inlet_state_snapshot,
        hot_outlet_state=hot_outlet_snapshot,
        cold_outlet_state=cold_outlet_snapshot,
        tube_side_inlet_state=tsi,
        tube_side_outlet_state=tso,
        annulus_side_inlet_state=asi,
        annulus_side_outlet_state=aso,
        tube_bulk_state=tbu,
        annulus_bulk_state=abu,
        tube_selected_correlation=tube_sc,
        annulus_selected_correlation=annulus_sc,
        tube_applicability=tube_ap,
        annulus_applicability=annulus_ap,
        Q_hot_w=None,
        Q_cold_w=None,
        relative_energy_residual=None,
        energy_tolerance_w=None,
        relative_ua_lmtd_residual=None,
        ua_lmtd_tolerance_w=None,
        q_max_diagnostics=q_max_diagnostics,
    )


def _qmax_diagnostics_snapshot(qmax: QMaxResult) -> QMaxDiagnosticsSnapshot:
    """Build a QMaxDiagnosticsSnapshot from a QMaxResult."""
    return QMaxDiagnosticsSnapshot(
        q_max_w=qmax.q_max_w,
        iterations=qmax.iterations,
        final_pinch_residual_k=qmax.final_pinch_residual_k,
        termination_reason=qmax.termination_reason,
        final_q_low_w=qmax.final_q_low_w,
        final_q_high_w=qmax.final_q_high_w,
        final_q_width_w=qmax.final_q_width_w,
        hot_limit_w=qmax.hot_limit_w,
        cold_limit_w=qmax.cold_limit_w,
        limiting_side=qmax.limiting_side,
        q_tolerance_w=qmax.q_tolerance_w,
        pinch_temperature_tolerance_k=qmax.pinch_temperature_tolerance_k,
    )


def _blocked_result(
    *,
    blockers: list[EngineeringMessage],
    warnings: list[EngineeringMessage] | None = None,
    property_calls: list[PropertyCallRecord] | tuple[PropertyCallRecord, ...] | None = None,
    request_identity: RatingRequestIdentity | None = None,
    provider_identity: ProviderIdentitySnapshot | None = None,
    execution_context: ExecutionContextSnapshot | None = None,
    flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW,
    q_max_diagnostics: QMaxDiagnosticsSnapshot | None = None,
) -> RatingResult:
    """Build a BLOCKED RatingResult with full provenance."""
    ctx = execution_context or ExecutionContextSnapshot()
    warnings = warnings or []
    property_calls = list(property_calls) if property_calls else []
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
        q_max_diagnostics=q_max_diagnostics,
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
        resistance_breakdown=None,
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
        core_provenance_digest=core_provenance_digest,
        q_max_diagnostics=q_max_diagnostics,
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
        q_max_diagnostics=q_max_diagnostics,
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
        resistance_breakdown=None,
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
        q_max_diagnostics=q_max_diagnostics,
    )


def _failed_result(
    *,
    solver_result: SolverResult,
    warnings: list[EngineeringMessage] | None = None,
    property_calls: list[PropertyCallRecord] | tuple[PropertyCallRecord, ...] | None = None,
    request_identity: RatingRequestIdentity | None = None,
    provider_identity: ProviderIdentitySnapshot | None = None,
    execution_context: ExecutionContextSnapshot | None = None,
    flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW,
    q_max_diagnostics: QMaxDiagnosticsSnapshot | None = None,
) -> RatingResult:
    """Build a FAILED RatingResult with full provenance."""
    from hexagent.domain.messages import RunFailure

    ctx = execution_context or ExecutionContextSnapshot()
    warnings = warnings or []
    property_calls = list(property_calls) if property_calls else []
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
        q_max_diagnostics=q_max_diagnostics,
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
        resistance_breakdown=None,
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
        core_provenance_digest=core_provenance_digest,
        q_max_diagnostics=q_max_diagnostics,
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
        q_max_diagnostics=q_max_diagnostics,
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
        resistance_breakdown=None,
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
        q_max_diagnostics=q_max_diagnostics,
    )


# ---------------------------------------------------------------------------
# Q_max computation via PropertyProvider
# ---------------------------------------------------------------------------


def _compute_q_max_counterflow(
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
    recorder: EvaluationRecorder,
) -> QMaxResult:
    """Counter-flow Q_max: independent terminal pinch at each end.

    All property calls are recorded atomically by the EvaluationRecorder.
    """
    ctx = recorder.begin(EvaluationRole.Q_MAX_COUNTERFLOW)

    # Hot stream: T_hot_out_min = T_cold_in + minimum_terminal_delta_t
    T_hot_out_min = cold_inlet_temperature_k + minimum_terminal_delta_t
    try:
        hot_limit_state = provider.state_tp(hot_fluid, T_hot_out_min, hot_inlet_pressure_pa)
    except PropertyServiceError as exc:
        recorder.record_failure(
            ctx,
            fluid_name=hot_fluid.name,
            query_type="TP",
            inputs=((("temperature_k", T_hot_out_min), ("pressure_pa", hot_inlet_pressure_pa))),
            provider=provider,
            stage="q_max",
            stream_role="hot_limit",
            error_code=exc.code.value,
            error_message=str(exc),
        )
        raise
    recorder.record_success(
        ctx,
        hot_limit_state,
        query_type="TP",
        inputs=(("temperature_k", T_hot_out_min), ("pressure_pa", hot_inlet_pressure_pa)),
        provider=provider,
        stage="q_max",
        stream_role="hot_limit",
    )

    # Cold stream: T_cold_out_max = T_hot_in - minimum_terminal_delta_t
    T_cold_out_max = hot_inlet_temperature_k - minimum_terminal_delta_t
    try:
        cold_limit_state = provider.state_tp(cold_fluid, T_cold_out_max, cold_inlet_pressure_pa)
    except PropertyServiceError as exc:
        recorder.record_failure(
            ctx,
            fluid_name=cold_fluid.name,
            query_type="TP",
            inputs=(("temperature_k", T_cold_out_max), ("pressure_pa", cold_inlet_pressure_pa)),
            provider=provider,
            stage="q_max",
            stream_role="cold_limit",
            error_code=exc.code.value,
            error_message=str(exc),
        )
        raise
    recorder.record_success(
        ctx,
        cold_limit_state,
        query_type="TP",
        inputs=(("temperature_k", T_cold_out_max), ("pressure_pa", cold_inlet_pressure_pa)),
        provider=provider,
        stage="q_max",
        stream_role="cold_limit",
    )

    Q_hot_limit = hot_mass_flow_kg_s * (h_hot_in - hot_limit_state.enthalpy_j_kg)
    Q_cold_limit = cold_mass_flow_kg_s * (cold_limit_state.enthalpy_j_kg - h_cold_in)
    q_max = min(Q_hot_limit, Q_cold_limit)
    limiting_side = "hot_limit" if Q_hot_limit <= Q_cold_limit else "cold_limit"

    return QMaxResult(
        q_max_w=q_max,
        iterations=0,
        final_q_low_w=None,
        final_q_high_w=None,
        final_q_width_w=None,
        final_pinch_residual_k=0.0,
        termination_reason="independent_limits",
        hot_limit_w=Q_hot_limit,
        cold_limit_w=Q_cold_limit,
        limiting_side=limiting_side,
    )


def _compute_q_max_parallel(
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
    recorder: EvaluationRecorder,
    pinch_temperature_tolerance_k: float = 1e-6,
) -> QMaxResult:
    """Parallel-flow Q_max: coupled outlet pinch by scalar search.

    For parallel-flow, T_hot_out and T_cold_out approach each other.
    The exit pinch constraint is:
        T_hot_out(Q) - T_cold_out(Q) >= minimum_terminal_delta_t

    We use enthalpy back-calculation (no fixed Cp) with bracket search.
    All property calls are recorded atomically by the EvaluationRecorder.

    The pinch_temperature_tolerance_k argument must be finite and > 0.
    """
    if not math.isfinite(pinch_temperature_tolerance_k) or pinch_temperature_tolerance_k <= 0:
        raise ValueError(
            "pinch_temperature_tolerance_k must be finite and > 0, "
            f"got {pinch_temperature_tolerance_k}"
        )

    # Upper bound: min of independent enthalpy limits
    ctx_limits = recorder.begin(EvaluationRole.Q_MAX_PARALLEL_LIMITS)

    T_hot_out_min_ind = cold_inlet_temperature_k + minimum_terminal_delta_t
    try:
        hot_limit_state = provider.state_tp(hot_fluid, T_hot_out_min_ind, hot_inlet_pressure_pa)
    except PropertyServiceError as exc:
        recorder.record_failure(
            ctx_limits,
            fluid_name=hot_fluid.name,
            query_type="TP",
            inputs=(("temperature_k", T_hot_out_min_ind), ("pressure_pa", hot_inlet_pressure_pa)),
            provider=provider,
            stage="q_max",
            stream_role="hot_limit",
            error_code=exc.code.value,
            error_message=str(exc),
        )
        raise
    recorder.record_success(
        ctx_limits,
        hot_limit_state,
        query_type="TP",
        inputs=(("temperature_k", T_hot_out_min_ind), ("pressure_pa", hot_inlet_pressure_pa)),
        provider=provider,
        stage="q_max",
        stream_role="hot_limit",
    )

    T_cold_out_max_ind = hot_inlet_temperature_k - minimum_terminal_delta_t
    try:
        cold_limit_state = provider.state_tp(cold_fluid, T_cold_out_max_ind, cold_inlet_pressure_pa)
    except PropertyServiceError as exc:
        recorder.record_failure(
            ctx_limits,
            fluid_name=cold_fluid.name,
            query_type="TP",
            inputs=(("temperature_k", T_cold_out_max_ind), ("pressure_pa", cold_inlet_pressure_pa)),
            provider=provider,
            stage="q_max",
            stream_role="cold_limit",
            error_code=exc.code.value,
            error_message=str(exc),
        )
        raise
    recorder.record_success(
        ctx_limits,
        cold_limit_state,
        query_type="TP",
        inputs=(("temperature_k", T_cold_out_max_ind), ("pressure_pa", cold_inlet_pressure_pa)),
        provider=provider,
        stage="q_max",
        stream_role="cold_limit",
    )

    Q_hot_limit = hot_mass_flow_kg_s * (h_hot_in - hot_limit_state.enthalpy_j_kg)
    Q_cold_limit = cold_mass_flow_kg_s * (cold_limit_state.enthalpy_j_kg - h_cold_in)
    q_upper = min(Q_hot_limit, Q_cold_limit)

    _parallel_limiting_side = "hot_limit" if Q_hot_limit <= Q_cold_limit else "cold_limit"

    if q_upper <= 0:
        return QMaxResult(
            q_max_w=0.0,
            iterations=0,
            final_q_low_w=None,
            final_q_high_w=None,
            final_q_width_w=None,
            final_pinch_residual_k=0.0,
            termination_reason="zero_upper_bound",
            hot_limit_w=Q_hot_limit,
            cold_limit_w=Q_cold_limit,
            limiting_side=_parallel_limiting_side,
        )

    def _exit_pinch_residual(Q: float) -> float:
        """Returns T_hot_out - T_cold_out - minimum_terminal_delta_t."""
        pinch_ctx = recorder.begin(EvaluationRole.Q_MAX_PARALLEL_PINCH, trial_q_w=Q)
        h_hot_out = h_hot_in - Q / hot_mass_flow_kg_s
        h_cold_out = h_cold_in + Q / cold_mass_flow_kg_s

        # Hot PH call (call_index=0)
        try:
            hot_state = provider.state_ph(
                hot_fluid,
                hot_inlet_pressure_pa,
                h_hot_out,
                reference_state=provider.reference_state_policy,
            )
        except PropertyServiceError as exc:
            recorder.record_failure(
                pinch_ctx,
                fluid_name=hot_fluid.name,
                query_type="PH",
                inputs=(("pressure_pa", hot_inlet_pressure_pa), ("enthalpy_j_kg", h_hot_out)),
                provider=provider,
                stage="q_max_pinch",
                stream_role="hot_solver",
                error_code=exc.code.value,
                error_message=str(exc),
            )
            raise
        recorder.record_success(
            pinch_ctx,
            hot_state,
            query_type="PH",
            inputs=(("pressure_pa", hot_inlet_pressure_pa), ("enthalpy_j_kg", h_hot_out)),
            provider=provider,
            stage="q_max_pinch",
            stream_role="hot_solver",
        )

        # Cold PH call (call_index=1)
        try:
            cold_state = provider.state_ph(
                cold_fluid,
                cold_inlet_pressure_pa,
                h_cold_out,
                reference_state=provider.reference_state_policy,
            )
        except PropertyServiceError as exc:
            recorder.record_failure(
                pinch_ctx,
                fluid_name=cold_fluid.name,
                query_type="PH",
                inputs=(("pressure_pa", cold_inlet_pressure_pa), ("enthalpy_j_kg", h_cold_out)),
                provider=provider,
                stage="q_max_pinch",
                stream_role="cold_solver",
                error_code=exc.code.value,
                error_message=str(exc),
            )
            raise
        recorder.record_success(
            pinch_ctx,
            cold_state,
            query_type="PH",
            inputs=(("pressure_pa", cold_inlet_pressure_pa), ("enthalpy_j_kg", h_cold_out)),
            provider=provider,
            stage="q_max_pinch",
            stream_role="cold_solver",
        )

        return (hot_state.temperature_k - cold_state.temperature_k) - minimum_terminal_delta_t

    # Check if q_upper itself satisfies the pinch
    pinch_at_upper = _exit_pinch_residual(q_upper)
    if pinch_at_upper >= 0:
        return QMaxResult(
            q_max_w=q_upper,
            iterations=0,
            final_q_low_w=q_upper,
            final_q_high_w=q_upper,
            final_q_width_w=0.0,
            final_pinch_residual_k=pinch_at_upper,
            termination_reason="pinch_satisfied_at_upper",
            q_tolerance_w=Q_MAX_Q_TOLERANCE_W,
            pinch_temperature_tolerance_k=pinch_temperature_tolerance_k,
            hot_limit_w=Q_hot_limit,
            cold_limit_w=Q_cold_limit,
            limiting_side=_parallel_limiting_side,
        )

    # Bisection to find the Q where pinch = 0
    q_lo, q_hi = 0.0, q_upper
    # pinch at Q=0: feasible end (hot in > cold in + min_dt)
    pinch_lo = hot_inlet_temperature_k - cold_inlet_temperature_k - minimum_terminal_delta_t
    pinch_hi = pinch_at_upper  # infeasible end (Q=q_upper)
    iterations = 0

    for _ in range(Q_MAX_MAX_ITERATIONS):
        iterations += 1
        q_mid = 0.5 * (q_lo + q_hi)
        pinch_mid = _exit_pinch_residual(q_mid)
        if pinch_mid >= 0.0:
            q_lo = q_mid
            pinch_lo = pinch_mid
        else:
            q_hi = q_mid
            pinch_hi = pinch_mid  # noqa: F841

        # Check dual tolerance using tracked endpoint residuals
        if q_hi - q_lo <= Q_MAX_Q_TOLERANCE_W and abs(pinch_lo) <= pinch_temperature_tolerance_k:
            break
    else:
        # Max iterations reached without convergence
        return QMaxResult(
            q_max_w=q_lo,
            iterations=iterations,
            final_q_low_w=q_lo,
            final_q_high_w=q_hi,
            final_q_width_w=q_hi - q_lo,
            final_pinch_residual_k=pinch_lo,
            termination_reason="iteration_limit",
            q_tolerance_w=Q_MAX_Q_TOLERANCE_W,
            pinch_temperature_tolerance_k=pinch_temperature_tolerance_k,
            hot_limit_w=Q_hot_limit,
            cold_limit_w=Q_cold_limit,
            limiting_side=_parallel_limiting_side,
        )

    return QMaxResult(
        q_max_w=q_lo,
        iterations=iterations,
        final_q_low_w=q_lo,
        final_q_high_w=q_hi,
        final_q_width_w=q_hi - q_lo,
        final_pinch_residual_k=pinch_lo,
        termination_reason="bisection_converged",
        q_tolerance_w=Q_MAX_Q_TOLERANCE_W,
        pinch_temperature_tolerance_k=pinch_temperature_tolerance_k,
        hot_limit_w=Q_hot_limit,
        cold_limit_w=Q_cold_limit,
        limiting_side=_parallel_limiting_side,
    )


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
    recorder: EvaluationRecorder,
) -> QMaxResult:
    """Compute Q_max using PropertyProvider enthalpy limits.

    Counter-flow: independent terminal pinch at each end.
    Parallel-flow: coupled outlet pinch solved by scalar search.
    """
    if flow_arrangement == FlowArrangement.COUNTERFLOW:
        return _compute_q_max_counterflow(
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
            recorder=recorder,
        )
    else:
        return _compute_q_max_parallel(
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
            recorder=recorder,
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
    minimum_terminal_delta_t: float,
    tube_boundary_condition: ThermalBoundaryCondition,
    annulus_boundary_condition: ThermalBoundaryCondition,
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

    recorder = EvaluationRecorder()

    # Hot inlet state via TP query
    hot_inlet_inputs = (
        ("temperature_k", hot_inlet_temperature_k),
        ("pressure_pa", hot_inlet_pressure_pa),
    )
    inlet_ctx = recorder.begin(EvaluationRole.INLET)
    try:
        hot_inlet_state = provider.state_tp(
            hot_fluid, hot_inlet_temperature_k, hot_inlet_pressure_pa
        )
        recorder.record_success(
            inlet_ctx,
            hot_inlet_state,
            query_type="TP",
            inputs=hot_inlet_inputs,
            provider=provider,
            stage="inlet",
            stream_role="hot_inlet",
        )
    except PropertyServiceError as exc:
        recorder.record_failure(
            inlet_ctx,
            fluid_name=hot_fluid.name,
            query_type="TP",
            inputs=hot_inlet_inputs,
            provider=provider,
            stage="inlet",
            stream_role="hot_inlet",
            error_code=(exc.code.value if hasattr(exc, "code") else "property_unavailable"),
            error_message=str(exc),
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
            property_calls=recorder.records,
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
        recorder.record_success(
            inlet_ctx,
            cold_inlet_state,
            query_type="TP",
            inputs=cold_inlet_inputs,
            provider=provider,
            stage="inlet",
            stream_role="cold_inlet",
        )
    except PropertyServiceError as exc:
        recorder.record_failure(
            inlet_ctx,
            fluid_name=cold_fluid.name,
            query_type="TP",
            inputs=cold_inlet_inputs,
            provider=provider,
            stage="inlet",
            stream_role="cold_inlet",
            error_code=(exc.code.value if hasattr(exc, "code") else "property_unavailable"),
            error_message=str(exc),
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
            property_calls=recorder.records,
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
            property_calls=recorder.records,
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
            property_calls=recorder.records,
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
    capacity_ratio = C_min / C_max if C_max > 0 else None

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
        q_max_result = _compute_q_max(
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
            recorder=recorder,
        )
        q_max = q_max_result.q_max_w

        q_max_diag = _qmax_diagnostics_snapshot(q_max_result)

        # Handle Q_max non-convergence
        if q_max_result.termination_reason == "iteration_limit":
            blockers.append(
                _make_blocker(
                    ErrorCode.SOLVER_NON_CONVERGENCE,
                    f"Parallel-flow Q_max pinch search did not converge after "
                    f"{q_max_result.iterations} iterations",
                    (
                        ("iterations", q_max_result.iterations),
                        ("final_q_width_w", q_max_result.final_q_width_w),
                        ("final_pinch_residual_k", q_max_result.final_pinch_residual_k),
                    ),
                )
            )
            return _blocked_result(
                blockers=blockers,
                property_calls=recorder.records,
                request_identity=request_identity,
                provider_identity=provider_identity,
                execution_context=ctx_snapshot,
                flow_arrangement=flow_arrangement,
                q_max_diagnostics=q_max_diag,
            )
    except PropertyServiceError as exc:
        blockers.append(
            _make_blocker(
                ErrorCode.PROPERTY_EVALUATION_FAILED,
                f"Q_max property evaluation failed: {exc}",
                (("stage", "q_max"),),
            )
        )
        return _blocked_result(
            blockers=blockers,
            property_calls=recorder.records,
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
            property_calls=recorder.records,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
            q_max_diagnostics=q_max_diag,
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

    # Build the trial evaluator (extracted class replacing the nested closure)
    trial_evaluator = TrialEvaluator(
        provider=provider,
        recorder=recorder,
        hot_fluid=hot_fluid,
        cold_fluid=cold_fluid,
        hot_mass_flow_kg_s=hot_mass_flow_kg_s,
        cold_mass_flow_kg_s=cold_mass_flow_kg_s,
        hot_inlet_pressure_pa=hot_inlet_pressure_pa,
        cold_inlet_pressure_pa=cold_inlet_pressure_pa,
        hot_inlet_temperature_k=hot_inlet_temperature_k,
        cold_inlet_temperature_k=cold_inlet_temperature_k,
        h_hot_in=h_hot_in,
        h_cold_in=h_cold_in,
        tube_in_hot=tube_in_hot,
        flow_arrangement=flow_arrangement,
        tube_geom=tube_geom,
        annulus_geom=annulus_geom,
        tube_boundary_condition=tube_boundary_condition,
        annulus_boundary_condition=annulus_boundary_condition,
        area_inner_m2=area_inner_m2,
        area_outer_m2=area_outer_m2,
        wall_resistance=wall_resistance,
        geometry=geometry,
    )

    def residual_fn(Q: float, phase: SolverEvaluationPhase) -> float:
        """Evaluate residual Q - UA(Q) x LMTD(Q).

        The evaluation role is determined by the solver's phase parameter.
        """
        ctx = recorder.begin(phase, trial_q_w=Q)
        trial = trial_evaluator.evaluate(
            Q,
            ctx=ctx,
        )
        if not trial.feasible or trial.residual_w is None:
            raise TrialEvaluationAbort(trial)
        return trial.residual_w

    # =====================================================================
    # 7. SOLVE
    # =====================================================================

    # TrialEvaluationAbort propagates through find_bracket / _bisect_secant
    # and is caught at the rate_double_pipe boundary to build a BLOCKED result.
    try:
        solver_result = solve_rating(
            residual_fn=residual_fn,
            q_max=q_max,
            params=params,
            c_effective_w_k=C_min,
        )
    except TrialEvaluationAbort as abort:
        trial = abort.trial
        # Only propagate warnings and blockers from the abort trial.
        warnings.extend(trial.warnings)
        blockers.extend(trial.blockers)
        # Map abort to structured BLOCKED result
        abort_blockers = list(blockers)
        if not abort_blockers:
            # Determine error code from trial context
            abort_code = ErrorCode.PROPERTY_EVALUATION_FAILED
            for b in trial.blockers:
                abort_code = b.code
                break
            abort_blockers.append(
                _make_blocker(
                    abort_code,
                    f"Trial evaluation aborted at Q={trial.q_w:.6f} W",
                    (("q_w", trial.q_w),),
                )
            )
        return _blocked_result(
            blockers=abort_blockers,
            warnings=warnings,
            property_calls=recorder.records,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
        )

    # =====================================================================
    # 8. POST-PROCESS
    # =====================================================================

    if not solver_result.converged:
        return _failed_result(
            solver_result=solver_result,
            warnings=warnings,
            property_calls=recorder.records,
            request_identity=request_identity,
            provider_identity=provider_identity,
            execution_context=ctx_snapshot,
            flow_arrangement=flow_arrangement,
            q_max_diagnostics=q_max_diag,
        )

    Q_sol = solver_result.q_solution_w

    # =====================================================================
    # 9. FINAL STATE CONSISTENCY
    # =====================================================================

    # Re-evaluate at the solution Q for final diagnostics
    final_ctx = recorder.begin(EvaluationRole.FINAL_EVALUATION, trial_q_w=Q_sol)
    final_trial = trial_evaluator.evaluate(
        Q_sol,
        ctx=final_ctx,
    )

    # Propagate warnings only
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
        return _build_final_evaluation_blocked_result(
            final_trial=final_trial,
            solver_result=solver_result,
            blockers=blockers,
            warnings=warnings,
            recorder=recorder,
            request_identity=request_identity,
            provider_identity=provider_identity,
            ctx_snapshot=ctx_snapshot,
            flow_arrangement=flow_arrangement,
            area_inner_m2=area_inner_m2,
            area_outer_m2=area_outer_m2,
            hot_inlet_state_snapshot=hot_inlet_state_snapshot,
            cold_inlet_state_snapshot=cold_inlet_state_snapshot,
            hot_inlet_temperature_k=hot_inlet_temperature_k,
            cold_inlet_temperature_k=cold_inlet_temperature_k,
            tube_in_hot=tube_in_hot,
            geometry=geometry,
            hot_mass_flow_kg_s=hot_mass_flow_kg_s,
            cold_mass_flow_kg_s=cold_mass_flow_kg_s,
            q_max_diagnostics=q_max_diag,
        )

    # Extract final states
    hot_outlet_final = final_trial.hot_outlet_state
    cold_outlet_final = final_trial.cold_outlet_state
    hot_bulk_final = final_trial.hot_bulk_state
    cold_bulk_final = final_trial.cold_bulk_state
    tube_result_final = final_trial.tube_result
    annulus_result_final = final_trial.annulus_result

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
        dt_hot_in_cold_out = hot_inlet_temperature_k - T_c_out_sol
        dt_hot_out_cold_in = T_h_out_sol - cold_inlet_temperature_k
        _eps = 1e-12
        if (
            dt_hot_in_cold_out < minimum_terminal_delta_t - _eps
            or dt_hot_out_cold_in < minimum_terminal_delta_t - _eps
        ):
            blockers.append(
                _make_blocker(
                    ErrorCode.TEMPERATURE_CROSSING,
                    f"Terminal temperature differences must be >= minimum_terminal_delta_t "
                    f"({minimum_terminal_delta_t} K) for counter-flow "
                    f"(dt1={dt_hot_in_cold_out:.6f}, dt2={dt_hot_out_cold_in:.6f})",
                    (
                        ("dt_hot_in_cold_out", dt_hot_in_cold_out),
                        ("dt_hot_out_cold_in", dt_hot_out_cold_in),
                        ("minimum_terminal_delta_t", minimum_terminal_delta_t),
                    ),
                )
            )
    else:
        # Parallel-flow: T_hot_out - T_cold_out >= minimum_terminal_delta_t
        exit_dt = T_h_out_sol - T_c_out_sol
        _eps = 1e-12
        if exit_dt < minimum_terminal_delta_t - _eps:
            blockers.append(
                _make_blocker(
                    ErrorCode.TEMPERATURE_CROSSING,
                    f"Parallel-flow exit temperature difference must be >= "
                    f"minimum_terminal_delta_t ({minimum_terminal_delta_t} K), "
                    f"got {exit_dt:.6f} K",
                    (
                        ("exit_dt_k", exit_dt),
                        ("minimum_terminal_delta_t", minimum_terminal_delta_t),
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
        UA_final = None
        rb_model = None

    # --- Check UA ---
    if UA_final is None or not math.isfinite(UA_final) or UA_final <= 0:
        blockers.append(
            _make_blocker(
                ErrorCode.ENERGY_BALANCE_NOT_CLOSED,
                f"UA is not finite and > 0 at solution: {UA_final}",
                (("ua_w_k", UA_final),),
            )
        )

    # --- ε-NTU diagnostics ---
    if (
        UA_final is not None
        and UA_final > 0
        and C_min is not None
        and C_min > 0
        and capacity_ratio is not None
    ):
        NTU_final = UA_final / C_min
        if flow_arrangement == FlowArrangement.COUNTERFLOW:
            eps_calc = effectiveness_counterflow(NTU_final, capacity_ratio)
        else:
            eps_calc = effectiveness_parallel(NTU_final, capacity_ratio)
    else:
        NTU_final = None
        eps_calc = None

    # --- Overall U values ---
    if UA_final is not None and UA_final > 0:
        U_inner = UA_final / area_inner_m2 if area_inner_m2 > 0 else None
        U_outer = UA_final / area_outer_m2 if area_outer_m2 > 0 else None
    else:
        U_inner = None
        U_outer = None

    # =====================================================================
    # 10. ENERGY BALANCE CLOSURE
    # =====================================================================

    # Use final PropertyProvider returned states (not algebraic identity)
    Q_hot_w = hot_mass_flow_kg_s * (hot_inlet_state.enthalpy_j_kg - hot_outlet_final.enthalpy_j_kg)
    Q_cold_w = cold_mass_flow_kg_s * (
        cold_outlet_final.enthalpy_j_kg - cold_inlet_state.enthalpy_j_kg
    )

    energy_residual_w = abs(Q_hot_w - Q_cold_w)
    max_abs_q = max(abs(Q_hot_w), abs(Q_cold_w), 1.0)
    energy_tolerance_w = max(_ENERGY_RESIDUAL_ABS_TOL, _ENERGY_RESIDUAL_REL_TOL * max_abs_q)
    relative_energy_residual = energy_residual_w / max_abs_q if max_abs_q > 0 else 0.0

    if energy_residual_w > energy_tolerance_w:
        blockers.append(
            _make_blocker(
                ErrorCode.ENERGY_BALANCE_NOT_CLOSED,
                f"Energy balance not closed: Q_hot={Q_hot_w:.6f} W, Q_cold={Q_cold_w:.6f} W, "
                f"residual={energy_residual_w:.6e} W, tolerance={energy_tolerance_w:.6e} W",
                (
                    ("Q_hot_w", Q_hot_w),
                    ("Q_cold_w", Q_cold_w),
                    ("energy_residual_w", energy_residual_w),
                    ("relative_energy_residual", relative_energy_residual),
                    ("energy_tolerance_w", energy_tolerance_w),
                ),
            )
        )

    # --- UA-LMTD residual ---
    relative_ua_lmtd_residual: float | None = None
    ua_lmtd_tolerance_w_val: float | None = None
    if (
        UA_final is not None
        and lmtd_final is not None
        and UA_final > 0
        and lmtd_final > 0
        and math.isfinite(UA_final)
        and math.isfinite(lmtd_final)
    ):
        ua_lmtd_residual_w = abs(Q_sol - UA_final * lmtd_final)
        # Frozen tolerance: max(abs(Q), abs(UA*LMTD), 1.0) as base
        _ua_lmtd_base = max(abs(Q_sol), abs(UA_final * lmtd_final), 1.0)
        ua_lmtd_tolerance_w_val = max(
            _ENERGY_RESIDUAL_ABS_TOL, _ENERGY_RESIDUAL_REL_TOL * _ua_lmtd_base
        )
        relative_ua_lmtd_residual = ua_lmtd_residual_w / _ua_lmtd_base
        if ua_lmtd_residual_w > ua_lmtd_tolerance_w_val:
            blockers.append(
                _make_blocker(
                    ErrorCode.ENERGY_BALANCE_NOT_CLOSED,
                    f"UA-LMTD residual not closed: residual={ua_lmtd_residual_w:.6e} W, "
                    f"tolerance={ua_lmtd_tolerance_w_val:.6e} W",
                    (
                        ("ua_lmtd_residual_w", ua_lmtd_residual_w),
                        ("ua_lmtd_tolerance_w", ua_lmtd_tolerance_w_val),
                        ("relative_ua_lmtd_residual", relative_ua_lmtd_residual),
                    ),
                )
            )
    else:
        ua_lmtd_residual_w = None

    # --- Propagate correlation warnings to global ---
    for w in tube_result_final.warnings:
        warnings.append(w)
    for w in annulus_result_final.warnings:
        warnings.append(w)

    def _build_postcalculation_blocked_result(
        blkrs: list[EngineeringMessage],
        wrns: list[EngineeringMessage],
    ) -> RatingResult:
        """Build a BLOCKED RatingResult preserving all computed diagnostics.

        Unlike _blocked_result (which returns zeroed fields), this function
        preserves solver results, thermal diagnostics, correlation data,
        state snapshots, and provenance so downstream consumers can still
        inspect what was computed before the blocker was encountered.
        """
        # Correlation snapshots
        tube_sc = _make_selected_correlation_snapshot(tube_result_final)
        annulus_sc = _make_selected_correlation_snapshot(annulus_result_final)
        tube_ap = _make_applicability_snapshot(tube_result_final)
        annulus_ap = _make_applicability_snapshot(annulus_result_final)

        tube_cid = tube_sc.correlation_id if tube_sc else None
        tube_cver = tube_sc.version if tube_sc else None
        tube_ast = tube_result_final.applicability_status or None
        annulus_cid = annulus_sc.correlation_id if annulus_sc else None
        annulus_cver = annulus_sc.version if annulus_sc else None
        annulus_ast = annulus_result_final.applicability_status or None

        # Map tube/annulus sides
        if tube_in_hot:
            tsi = hot_inlet_state_snapshot
            tso = hot_outlet_snapshot
            tbu = hot_bulk_snapshot
            asi = cold_inlet_state_snapshot
            aso = cold_outlet_snapshot
            abu = cold_bulk_snapshot
        else:
            tsi = cold_inlet_state_snapshot
            tso = cold_outlet_snapshot
            tbu = cold_bulk_snapshot
            asi = hot_inlet_state_snapshot
            aso = hot_outlet_snapshot
            abu = hot_bulk_snapshot

        solver_details = _make_solver_details(solver_result)

        core_graph, core_nodes, core_edges = build_provenance_core(
            flow_arrangement=flow_arrangement,
            property_calls=recorder.records,
            iterations=solver_result.iterations,
            converged=solver_result.converged,
            warnings=wrns,
            blockers=blkrs,
            execution_context=ctx_snapshot,
            request_identity=request_identity,
            tube_correlation_info=tube_sc,
            annulus_correlation_info=annulus_sc,
            tube_applicability=tube_ap,
            annulus_applicability=annulus_ap,
            q_max_diagnostics=q_max_diag,
        )
        core_provenance_digest = _provenance_graph_digest(core_graph)

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
            tube_selected_correlation_id=tube_cid,
            tube_selected_correlation_version=tube_cver,
            tube_applicability_status=tube_ast,
            annulus_reynolds=annulus_result_final.reynolds_number,
            annulus_prandtl=annulus_result_final.prandtl_number,
            annulus_nusselt=annulus_result_final.nusselt_number,
            annulus_h=annulus_h_val,
            annulus_selected_correlation_id=annulus_cid,
            annulus_selected_correlation_version=annulus_cver,
            annulus_applicability_status=annulus_ast,
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
            ua_lmtd_residual_w=ua_lmtd_residual_w,
            iterations=solver_result.iterations,
            converged=solver_result.converged,
            solver_termination_reason=solver_result.termination_reason.value,
            solver_details=solver_details,
            property_calls=recorder.records,
            warnings=tuple(wrns),
            blockers=tuple(blkrs),
            status=RatingStatus.BLOCKED,
            hot_inlet_state=hot_inlet_state_snapshot,
            cold_inlet_state=cold_inlet_state_snapshot,
            hot_outlet_state=hot_outlet_snapshot,
            cold_outlet_state=cold_outlet_snapshot,
            tube_side_inlet_state=tsi,
            tube_side_outlet_state=tso,
            annulus_side_inlet_state=asi,
            annulus_side_outlet_state=aso,
            tube_bulk_state=tbu,
            annulus_bulk_state=abu,
            tube_selected_correlation_snap=tube_sc,
            annulus_selected_correlation_snap=annulus_sc,
            tube_applicability_snap=tube_ap,
            annulus_applicability_snap=annulus_ap,
            core_provenance_digest=core_provenance_digest,
            Q_hot_w=Q_hot_w,
            Q_cold_w=Q_cold_w,
            relative_energy_residual=relative_energy_residual,
            energy_tolerance_w=energy_tolerance_w,
            relative_ua_lmtd_residual=relative_ua_lmtd_residual,
            ua_lmtd_tolerance_w=ua_lmtd_tolerance_w_val,
            q_max_diagnostics=q_max_diag,
        )

        provenance_graph = build_provenance(
            flow_arrangement=flow_arrangement,
            property_calls=recorder.records,
            iterations=solver_result.iterations,
            converged=solver_result.converged,
            warnings=wrns,
            blockers=blkrs,
            result_hash=result_hash,
            execution_context=ctx_snapshot,
            request_identity=request_identity,
            tube_correlation_info=tube_sc,
            annulus_correlation_info=annulus_sc,
            tube_applicability=tube_ap,
            annulus_applicability=annulus_ap,
            q_max_diagnostics=q_max_diag,
        )
        provenance_digest = _provenance_graph_digest(provenance_graph)

        return RatingResult(
            status=RatingStatus.BLOCKED,
            flow_arrangement=flow_arrangement,
            heat_duty_w=Q_sol,
            hot_outlet_temperature_k=T_h_out_sol,
            cold_outlet_temperature_k=T_c_out_sol,
            tube_reynolds=tube_result_final.reynolds_number,
            tube_prandtl=tube_result_final.prandtl_number,
            tube_nusselt=tube_result_final.nusselt_number,
            tube_h=tube_h_val,
            tube_selected_correlation_id=tube_cid,
            tube_selected_correlation_version=tube_cver,
            tube_applicability_status=tube_ast,
            annulus_reynolds=annulus_result_final.reynolds_number,
            annulus_prandtl=annulus_result_final.prandtl_number,
            annulus_nusselt=annulus_result_final.nusselt_number,
            annulus_h=annulus_h_val,
            annulus_selected_correlation_id=annulus_cid,
            annulus_selected_correlation_version=annulus_cver,
            annulus_applicability_status=annulus_ast,
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
            ua_lmtd_residual_w=ua_lmtd_residual_w,
            iterations=solver_result.iterations,
            converged=solver_result.converged,
            solver_termination_reason=solver_result.termination_reason.value,
            solver_details=solver_details,
            warnings=tuple(wrns),
            blockers=tuple(blkrs),
            property_calls=recorder.records,
            provider_identity=provider_identity,
            request_identity=request_identity,
            execution_context=ctx_snapshot,
            result_hash=result_hash,
            provenance_graph=provenance_graph,
            provenance_digest=provenance_digest,
            core_provenance_digest=core_provenance_digest,
            hot_inlet_state=hot_inlet_state_snapshot,
            cold_inlet_state=cold_inlet_state_snapshot,
            hot_outlet_state=hot_outlet_snapshot,
            cold_outlet_state=cold_outlet_snapshot,
            tube_side_inlet_state=tsi,
            tube_side_outlet_state=tso,
            annulus_side_inlet_state=asi,
            annulus_side_outlet_state=aso,
            tube_bulk_state=tbu,
            annulus_bulk_state=abu,
            tube_selected_correlation=tube_sc,
            annulus_selected_correlation=annulus_sc,
            tube_applicability=tube_ap,
            annulus_applicability=annulus_ap,
            Q_hot_w=Q_hot_w,
            Q_cold_w=Q_cold_w,
            relative_energy_residual=relative_energy_residual,
            energy_tolerance_w=energy_tolerance_w,
            relative_ua_lmtd_residual=relative_ua_lmtd_residual,
            ua_lmtd_tolerance_w=ua_lmtd_tolerance_w_val,
            q_max_diagnostics=q_max_diag,
        )

    # --- Check if any blockers were found during final consistency ---
    if blockers:
        return _build_postcalculation_blocked_result(blockers, warnings)

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
        property_calls=recorder.records,
        iterations=solver_result.iterations,
        converged=True,
        warnings=warnings,
        blockers=[],
        execution_context=ctx_snapshot,
        request_identity=request_identity,
        tube_correlation_info=tube_sel_corr_snapshot,
        annulus_correlation_info=annulus_sel_corr_snapshot,
        tube_applicability=tube_app_snapshot,
        annulus_applicability=annulus_app_snapshot,
        q_max_diagnostics=q_max_diag,
    )

    # Step 2: Compute core_provenance_digest
    core_provenance_digest = _provenance_graph_digest(core_graph)

    # Step 3: Compute result_hash using core_provenance_digest
    # IMPORTANT: all snapshot fields MUST be passed here so that the
    # construction-time hash matches the verification-time recomputation.
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
        ua_lmtd_residual_w=ua_lmtd_residual_w,
        iterations=solver_result.iterations,
        converged=True,
        solver_termination_reason=solver_result.termination_reason.value,
        solver_details=solver_details,
        property_calls=recorder.records,
        warnings=tuple(warnings),
        blockers=(),
        status=RatingStatus.SUCCEEDED,
        # Snapshot fields — must match _recompute_result_hash
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
        tube_selected_correlation_snap=tube_sel_corr_snapshot,
        annulus_selected_correlation_snap=annulus_sel_corr_snapshot,
        tube_applicability_snap=tube_app_snapshot,
        annulus_applicability_snap=annulus_app_snapshot,
        core_provenance_digest=core_provenance_digest,
        # Closure diagnostics
        Q_hot_w=Q_hot_w,
        Q_cold_w=Q_cold_w,
        relative_energy_residual=relative_energy_residual,
        energy_tolerance_w=energy_tolerance_w,
        relative_ua_lmtd_residual=relative_ua_lmtd_residual,
        ua_lmtd_tolerance_w=ua_lmtd_tolerance_w_val,
        q_max_diagnostics=q_max_diag,
    )

    # Step 4: Add RESULT node via build_provenance
    provenance_graph = build_provenance(
        flow_arrangement=flow_arrangement,
        property_calls=recorder.records,
        iterations=solver_result.iterations,
        converged=True,
        warnings=warnings,
        blockers=[],
        result_hash=result_hash,
        execution_context=ctx_snapshot,
        request_identity=request_identity,
        tube_correlation_info=tube_sel_corr_snapshot,
        annulus_correlation_info=annulus_sel_corr_snapshot,
        tube_applicability=tube_app_snapshot,
        annulus_applicability=annulus_app_snapshot,
        q_max_diagnostics=q_max_diag,
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
        ua_lmtd_residual_w=ua_lmtd_residual_w,
        iterations=solver_result.iterations,
        converged=True,
        solver_termination_reason=solver_result.termination_reason.value,
        solver_details=solver_details,
        warnings=tuple(warnings),
        blockers=(),
        property_calls=recorder.records,
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
        # Closure diagnostics
        Q_hot_w=Q_hot_w,
        Q_cold_w=Q_cold_w,
        relative_energy_residual=relative_energy_residual,
        energy_tolerance_w=energy_tolerance_w,
        relative_ua_lmtd_residual=relative_ua_lmtd_residual,
        ua_lmtd_tolerance_w=ua_lmtd_tolerance_w_val,
        q_max_diagnostics=q_max_diag,
    )

    return result
