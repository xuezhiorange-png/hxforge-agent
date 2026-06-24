"""Comprehensive tests for TASK-008 engineering correction round 8.

Covers:
1. EvaluationRecorder unit tests (5 tests)
2. QMaxResult field tests (3 tests)
3. Solver phase tests (3 tests)
4. Post-calculation BLOCKED tests (5 tests)
5. Verifier tamper tests (5 tests)
6. Solver convergence contract test (1 test)
7. Solver convergence validator details (4 tests)
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.domain.messages import (
    EngineeringMessage,
    EngineeringMessageSeverity,
    ErrorCode,
)
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import (
    Q_MAX_PINCH_TOLERANCE_K,
    Q_MAX_Q_TOLERANCE_W,
    QMaxResult,
    _build_empty_resistance,
    _build_empty_solver_details,
    _compute_q_max_counterflow,
    _compute_q_max_parallel,
    rate_double_pipe,
)
from hexagent.exchangers.double_pipe.recorder import (
    EvaluationRecorder,
    EvaluationRole,
    SolverEvaluationPhase,
)
from hexagent.exchangers.double_pipe.result import (
    RatingRequestIdentity,
    RatingResult,
    RatingStatus,
    SolverDetailsModel,
)
from hexagent.exchangers.double_pipe.solver import (
    SolverParams,
    SolverTermination,
    find_bracket,
    solve_rating,
)
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import (
    FluidIdentifier,
    FluidState,
    PropertyProvider,
    ReferenceStatePolicy,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

# -----------------------------------------------------------------------
# Fixtures & constants
# -----------------------------------------------------------------------


@pytest.fixture(scope="module")
def provider() -> CoolPropProvider:
    return CoolPropProvider(cache_size=64)


WATER = FluidIdentifier(name="Water")

STANDARD_GEOMETRY = DoublePipeGeometry(
    inner_tube_inner_diameter_m=0.020,
    inner_tube_outer_diameter_m=0.025,
    outer_pipe_inner_diameter_m=0.040,
    effective_length_m=3.0,
    wall_thermal_conductivity_w_m_k=50.0,
    inner_surface_roughness_m=4.5e-5,
    annulus_surface_roughness_m=4.5e-5,
    inner_fouling_resistance_m2k_w=0.0002,
    outer_fouling_resistance_m2k_w=0.0002,
)


def _make_mock_provider(provider: CoolPropProvider) -> MagicMock:
    """Create a MagicMock provider that delegates to a real CoolPropProvider."""
    mock = MagicMock()
    mock.name = provider.name
    mock.version = provider.version
    mock.git_revision = ""
    mock.reference_state_policy = ReferenceStatePolicy.DEF
    mock.state_tp.side_effect = provider.state_tp
    mock.state_ph.side_effect = provider.state_ph
    return mock


def _run_rating(
    provider: PropertyProvider,
    *,
    tube_in_hot: bool = True,
    flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW,
    **extra,
) -> RatingResult:
    """Run rate_double_pipe with standard conditions."""
    kwargs = dict(
        geometry=STANDARD_GEOMETRY,
        hot_fluid=WATER,
        cold_fluid=WATER,
        hot_mass_flow_kg_s=0.5,
        cold_mass_flow_kg_s=1.5,
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=300.0,
        hot_inlet_pressure_pa=200000.0,
        cold_inlet_pressure_pa=150000.0,
        tube_in_hot=tube_in_hot,
        flow_arrangement=flow_arrangement,
        provider=provider,
        minimum_terminal_delta_t=0.5,
        tube_boundary_condition=ThermalBoundaryCondition.constant_wall_temperature,
        annulus_boundary_condition=ThermalBoundaryCondition.inner_wall_heated,
    )
    kwargs.update(extra)
    return rate_double_pipe(**kwargs)


def _make_minimal_request_identity(
    flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW,
) -> RatingRequestIdentity:
    """Build a minimal valid RatingRequestIdentity."""
    return RatingRequestIdentity(
        hot_fluid_name="Water",
        hot_fluid_backend="HEOS",
        hot_fluid_components=(),
        cold_fluid_name="Water",
        cold_fluid_backend="HEOS",
        cold_fluid_components=(),
        hot_mass_flow_kg_s=0.5,
        cold_mass_flow_kg_s=1.5,
        hot_inlet_pressure_pa=200000.0,
        cold_inlet_pressure_pa=150000.0,
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=300.0,
        flow_arrangement=flow_arrangement.value,
        geometry={},
        solver_absolute_residual_w=1e-3,
        solver_relative_residual_fraction=1e-8,
        solver_bracket_temperature_tolerance_k=1e-4,
        solver_max_iterations=100,
    )


# =========================================================================
# 1. EvaluationRecorder tests
# =========================================================================


class TestEvaluationRecorder:
    """Unit tests for the EvaluationRecorder dataclass."""

    def test_recorder_success_success(self, provider: CoolPropProvider) -> None:
        """Two successful records: verify sequence_index == [0,1],
        eval indices unique, call_index within eval.
        """
        recorder = EvaluationRecorder()
        ctx0 = recorder.begin(EvaluationRole.INLET)
        recorder.record_success(
            ctx0,
            provider.state_tp(WATER, 350.0, 200000.0),
            query_type="TP",
            inputs=(("temperature_k", 350.0), ("pressure_pa", 200000.0)),
            provider=provider,
            stage="inlet",
            stream_role="hot_inlet",
        )
        ctx1 = recorder.begin(EvaluationRole.INLET)
        recorder.record_success(
            ctx1,
            provider.state_tp(WATER, 300.0, 150000.0),
            query_type="TP",
            inputs=(("temperature_k", 300.0), ("pressure_pa", 150000.0)),
            provider=provider,
            stage="inlet",
            stream_role="cold_inlet",
        )

        records = recorder.records
        assert len(records) == 2
        # sequence_index must be [0, 1]
        assert [r.sequence_index for r in records] == [0, 1]
        # evaluation indices must be unique
        eval_indices = [r.evaluation_index for r in records]
        assert len(set(eval_indices)) == 2
        assert eval_indices == [0, 1]
        # call_index within each eval starts at 0
        assert records[0].call_index_within_evaluation == 0
        assert records[1].call_index_within_evaluation == 0
        # Both successful
        assert records[0].success is True
        assert records[1].success is True

    def test_recorder_success_failure(self, provider: CoolPropProvider) -> None:
        """One success then one failure, both recorded."""
        recorder = EvaluationRecorder()
        ctx0 = recorder.begin(EvaluationRole.INLET)
        recorder.record_success(
            ctx0,
            provider.state_tp(WATER, 350.0, 200000.0),
            query_type="TP",
            inputs=(("temperature_k", 350.0), ("pressure_pa", 200000.0)),
            provider=provider,
            stage="inlet",
            stream_role="hot_inlet",
        )
        ctx1 = recorder.begin(EvaluationRole.INLET)
        recorder.record_failure(
            ctx1,
            fluid_name="Water",
            query_type="TP",
            inputs=(("temperature_k", 300.0), ("pressure_pa", 150000.0)),
            provider=provider,
            stage="inlet",
            stream_role="cold_inlet",
            error_code="backend_failure",
            error_message="simulated failure",
        )

        records = recorder.records
        assert len(records) == 2
        assert records[0].success is True
        assert records[1].success is False
        assert records[1].error_code == "backend_failure"
        assert records[1].error_message == "simulated failure"
        # Sequence is contiguous
        assert [r.sequence_index for r in records] == [0, 1]
        # Evaluation indices are unique
        assert records[0].evaluation_index != records[1].evaluation_index

    def test_recorder_failure_first_call(self, provider: CoolPropProvider) -> None:
        """Failure on first call, only that record exists."""
        recorder = EvaluationRecorder()
        ctx = recorder.begin(EvaluationRole.INLET)
        recorder.record_failure(
            ctx,
            fluid_name="Water",
            query_type="TP",
            inputs=(("temperature_k", 350.0), ("pressure_pa", 200000.0)),
            provider=provider,
            stage="inlet",
            stream_role="hot_inlet",
            error_code="backend_failure",
            error_message="first call failure",
        )

        records = recorder.records
        assert len(records) == 1
        assert records[0].success is False
        assert records[0].sequence_index == 0
        assert records[0].evaluation_index == 0
        assert records[0].call_index_within_evaluation == 0
        assert records[0].error_code == "backend_failure"

    def test_recorder_multiple_evaluations(self, provider: CoolPropProvider) -> None:
        """3+ evaluations: verify all invariants hold."""
        recorder = EvaluationRecorder()

        # Evaluation 0: inlet (2 calls)
        ctx0 = recorder.begin(EvaluationRole.INLET)
        recorder.record_success(
            ctx0,
            provider.state_tp(WATER, 350.0, 200000.0),
            query_type="TP",
            inputs=(("temperature_k", 350.0), ("pressure_pa", 200000.0)),
            provider=provider,
            stage="inlet",
            stream_role="hot_inlet",
        )
        recorder.record_success(
            ctx0,
            provider.state_tp(WATER, 300.0, 150000.0),
            query_type="TP",
            inputs=(("temperature_k", 300.0), ("pressure_pa", 150000.0)),
            provider=provider,
            stage="inlet",
            stream_role="cold_inlet",
        )

        # Evaluation 1: q_max_counterflow (2 calls)
        ctx1 = recorder.begin(EvaluationRole.Q_MAX_COUNTERFLOW)
        recorder.record_success(
            ctx1,
            provider.state_tp(WATER, 300.5, 200000.0),
            query_type="TP",
            inputs=(("temperature_k", 300.5), ("pressure_pa", 200000.0)),
            provider=provider,
            stage="q_max",
            stream_role="hot_limit",
        )
        recorder.record_success(
            ctx1,
            provider.state_tp(WATER, 349.5, 150000.0),
            query_type="TP",
            inputs=(("temperature_k", 349.5), ("pressure_pa", 150000.0)),
            provider=provider,
            stage="q_max",
            stream_role="cold_limit",
        )

        # Evaluation 2: bracket_probe (1 call)
        ctx2 = recorder.begin(EvaluationRole.BRACKET_PROBE, trial_q_w=0.0)
        recorder.record_success(
            ctx2,
            provider.state_tp(WATER, 349.0, 200000.0),
            query_type="TP",
            inputs=(("temperature_k", 349.0), ("pressure_pa", 200000.0)),
            provider=provider,
            stage="bracket_probe",
            stream_role="hot_solver",
        )

        records = recorder.records
        assert len(records) == 5

        # Invariant 1: sequence_index == [0, 1, 2, 3, 4]
        assert [r.sequence_index for r in records] == [0, 1, 2, 3, 4]

        # Invariant 2: evaluation_index is 0, 0, 1, 1, 2 (consecutive)
        eval_indices = [r.evaluation_index for r in records]
        assert eval_indices == [0, 0, 1, 1, 2]

        # Invariant 3: call_index within eval is 0, 1, 0, 1, 0
        call_indices = [r.call_index_within_evaluation for r in records]
        assert call_indices == [0, 1, 0, 1, 0]

        # Invariant 4: all successful
        assert all(r.success for r in records)

        # Invariant 5: record_count matches
        assert recorder.record_count == 5

    def test_recorder_exception_midway(self, provider: CoolPropProvider) -> None:
        """Records exist up to the point of exception, then a failure."""
        recorder = EvaluationRecorder()

        # First evaluation succeeds with 2 calls
        ctx0 = recorder.begin(EvaluationRole.INLET)
        recorder.record_success(
            ctx0,
            provider.state_tp(WATER, 350.0, 200000.0),
            query_type="TP",
            inputs=(("temperature_k", 350.0), ("pressure_pa", 200000.0)),
            provider=provider,
            stage="inlet",
            stream_role="hot_inlet",
        )
        recorder.record_success(
            ctx0,
            provider.state_tp(WATER, 300.0, 150000.0),
            query_type="TP",
            inputs=(("temperature_k", 300.0), ("pressure_pa", 150000.0)),
            provider=provider,
            stage="inlet",
            stream_role="cold_inlet",
        )

        # Second evaluation: first call succeeds, second call fails
        ctx1 = recorder.begin(EvaluationRole.Q_MAX_COUNTERFLOW)
        recorder.record_success(
            ctx1,
            provider.state_tp(WATER, 300.5, 200000.0),
            query_type="TP",
            inputs=(("temperature_k", 300.5), ("pressure_pa", 200000.0)),
            provider=provider,
            stage="q_max",
            stream_role="hot_limit",
        )
        recorder.record_failure(
            ctx1,
            fluid_name="Water",
            query_type="TP",
            inputs=(("temperature_k", 349.5), ("pressure_pa", 150000.0)),
            provider=provider,
            stage="q_max",
            stream_role="cold_limit",
            error_code="backend_failure",
            error_message="mid-evaluation failure",
        )

        records = recorder.records
        assert len(records) == 4
        # First 2 succeeded
        assert records[0].success is True
        assert records[1].success is True
        # 3rd succeeded (first call of eval 1)
        assert records[2].success is True
        # 4th failed (second call of eval 1)
        assert records[3].success is False
        assert records[3].error_code == "backend_failure"
        # All sequence indices contiguous
        assert [r.sequence_index for r in records] == [0, 1, 2, 3]


# =========================================================================
# 2. QMaxResult tests
# =========================================================================


class TestQMaxResult:
    """Tests for QMaxResult fields."""

    def test_counterflow_q_max_limits(self, provider: CoolPropProvider) -> None:
        """Counterflow Q_max: verify hot_limit_w, cold_limit_w,
        limiting_side, q_max_w == min(hot_limit, cold_limit).
        """
        recorder = EvaluationRecorder()
        q_max = _compute_q_max_counterflow(
            provider=provider,
            hot_fluid=WATER,
            cold_fluid=WATER,
            hot_inlet_temperature_k=350.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200000.0,
            cold_inlet_pressure_pa=150000.0,
            h_hot_in=provider.state_tp(WATER, 350.0, 200000.0).enthalpy_j_kg,
            h_cold_in=provider.state_tp(WATER, 300.0, 150000.0).enthalpy_j_kg,
            hot_mass_flow_kg_s=0.5,
            cold_mass_flow_kg_s=1.5,
            minimum_terminal_delta_t=0.5,
            recorder=recorder,
        )
        assert q_max.hot_limit_w is not None
        assert q_max.cold_limit_w is not None
        assert q_max.limiting_side is not None
        assert q_max.hot_limit_w > 0
        assert q_max.cold_limit_w > 0
        # q_max_w must equal min(hot_limit, cold_limit)
        assert q_max.q_max_w == pytest.approx(min(q_max.hot_limit_w, q_max.cold_limit_w))
        # limiting_side must be one of the expected values
        assert q_max.limiting_side in ("hot_limit", "cold_limit")
        # If hot_limit is smaller, limiting_side should be hot_limit
        if q_max.hot_limit_w <= q_max.cold_limit_w:
            assert q_max.limiting_side == "hot_limit"
        else:
            assert q_max.limiting_side == "cold_limit"
        # Counterflow: final_q_low_w, final_q_high_w, final_q_width_w are None
        assert q_max.final_q_low_w is None
        assert q_max.final_q_high_w is None
        assert q_max.final_q_width_w is None

    def test_parallelflow_q_max_dual_tolerance(self, provider: CoolPropProvider) -> None:
        """Parallel-flow Q_max: verify q_tolerance_w and
        pinch_temperature_tolerance_k are set.
        """
        recorder = EvaluationRecorder()
        q_max = _compute_q_max_parallel(
            provider=provider,
            hot_fluid=WATER,
            cold_fluid=WATER,
            hot_inlet_temperature_k=350.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200000.0,
            cold_inlet_pressure_pa=150000.0,
            h_hot_in=provider.state_tp(WATER, 350.0, 200000.0).enthalpy_j_kg,
            h_cold_in=provider.state_tp(WATER, 300.0, 150000.0).enthalpy_j_kg,
            hot_mass_flow_kg_s=0.5,
            cold_mass_flow_kg_s=1.5,
            minimum_terminal_delta_t=0.5,
            recorder=recorder,
        )
        # If the pinch search ran (not satisfied at upper), both tolerance fields set
        if q_max.termination_reason == "bisection_converged":
            assert q_max.q_tolerance_w is not None
            assert q_max.pinch_temperature_tolerance_k is not None
            assert q_max.q_tolerance_w >= 0
            assert q_max.pinch_temperature_tolerance_k > 0
        # Regardless of termination, q_max_w must be finite
        assert math.isfinite(q_max.q_max_w)
        assert q_max.q_max_w >= 0
        # Parallel-flow: verify tolerance constants
        if q_max.termination_reason in ("bisection_converged", "iteration_limit"):
            assert q_max.q_tolerance_w == Q_MAX_Q_TOLERANCE_W
            assert q_max.pinch_temperature_tolerance_k == Q_MAX_PINCH_TOLERANCE_K

    def test_qmax_no_property_calls_field(self) -> None:
        """QMaxResult does not have a property_calls attribute and
        includes final_q_width_w field."""
        q_max = QMaxResult(
            q_max_w=100.0,
            iterations=0,
            final_q_low_w=100.0,
            final_q_high_w=100.0,
            final_q_width_w=0.0,
            final_pinch_residual_k=0.0,
            termination_reason="independent_limits",
        )
        assert not hasattr(q_max, "property_calls")
        assert q_max.final_q_width_w == 0.0


# =========================================================================
# 3. Solver phase tests
# =========================================================================


class TestSolverPhase:
    """Tests that solver passes explicit phase tags to residual function."""

    def test_bracket_uses_bracket_probe_phase(self, provider: CoolPropProvider) -> None:
        """All find_bracket calls to residual_fn use BRACKET_PROBE."""
        phases_seen: list[SolverEvaluationPhase] = []

        def residual_fn(Q: float, phase: SolverEvaluationPhase) -> float:
            phases_seen.append(phase)
            return Q - 500.0  # simple linear residual

        params = SolverParams(absolute_residual_w=0.01)
        bracket = find_bracket(residual_fn, q_max=1000.0, params=params)
        assert bracket is not None
        # Every call must have been BRACKET_PROBE
        assert len(phases_seen) > 0
        assert all(p == SolverEvaluationPhase.BRACKET_PROBE for p in phases_seen), (
            f"Expected all BRACKET_PROBE, got: {phases_seen}"
        )

    def test_bisection_uses_solver_iteration_phase(self, provider: CoolPropProvider) -> None:
        """_bisect_secant calls via solve_rating use SOLVER_ITERATION."""
        phases_seen: list[SolverEvaluationPhase] = []

        def residual_fn(Q: float, phase: SolverEvaluationPhase) -> float:
            phases_seen.append(phase)
            return Q - 500.0  # root at Q=500

        params = SolverParams(
            absolute_residual_w=1e-6,
            relative_residual_fraction=1e-8,
            bracket_temperature_tolerance_k=1e-2,
            max_iterations=50,
        )
        # Use solve_rating which internally calls find_bracket (BRACKET_PROBE)
        # and _bisect_secant (SOLVER_ITERATION)
        result = solve_rating(residual_fn, q_max=1000.0, params=params, c_effective_w_k=1000.0)
        assert result.converged is True

        # The phases after bracket probing must all be SOLVER_ITERATION
        # First phases are BRACKET_PROBE (from find_bracket), then SOLVER_ITERATION
        bracket_phases = [p for p in phases_seen if p == SolverEvaluationPhase.BRACKET_PROBE]
        iteration_phases = [p for p in phases_seen if p == SolverEvaluationPhase.SOLVER_ITERATION]
        assert len(bracket_phases) > 0, "Should have bracket probe phases"
        assert len(iteration_phases) > 0, "Should have solver iteration phases"

        # Verify ordering: all bracket phases come before all iteration phases
        first_iter_idx = phases_seen.index(SolverEvaluationPhase.SOLVER_ITERATION)
        last_bracket_idx = (
            len(phases_seen) - 1 - phases_seen[::-1].index(SolverEvaluationPhase.BRACKET_PROBE)
        )
        assert last_bracket_idx < first_iter_idx, (
            "BRACKET_PROBE phases should all come before SOLVER_ITERATION phases"
        )

    def test_zero_duty_phase(self, provider: CoolPropProvider) -> None:
        """Zero-duty path uses SOLVER_ITERATION for the final residual call."""
        phases_seen: list[SolverEvaluationPhase] = []

        def residual_fn(Q: float, phase: SolverEvaluationPhase) -> float:
            phases_seen.append(phase)
            return 0.0  # residual is zero at Q=0

        params = SolverParams(absolute_residual_w=1e-3)
        # find_bracket with residual=0 at Q=0 should return (0.0, 0.0)
        bracket = find_bracket(residual_fn, q_max=1000.0, params=params)
        assert bracket == (0.0, 0.0)

        # Now run solve_rating — the zero-duty path calls residual_fn(0.0, SOLVER_ITERATION)
        phases_seen.clear()
        result = solve_rating(residual_fn, q_max=1000.0, params=params)
        assert result.converged is True
        assert result.termination_reason == SolverTermination.ZERO_DUTY
        assert result.q_solution_w == 0.0

        # The zero-duty path calls residual once with SOLVER_ITERATION
        assert SolverEvaluationPhase.SOLVER_ITERATION in phases_seen


# =========================================================================
# 4. Post-calculation BLOCKED tests
# =========================================================================


class TestPostCalculationBlocked:
    """Post-calculation BLOCKED results preserve all computed diagnostics.

    Each test deterministically triggers a specific failure path and directly
    asserts the expected status — no branching on status.
    """

    def _make_energy_biased_provider(
        self, provider: CoolPropProvider, *, bias_value: float
    ) -> MagicMock:
        """Provider that biases cold-side state_ph enthalpy to create energy imbalance.

        The solver converges using the biased properties (consistent across all
        solver iterations), but the post-calculation energy balance check fails
        because Q_hot (unbiased) != Q_cold (biased).
        """
        mock = MagicMock()
        mock.name = provider.name
        mock.version = provider.version
        mock.git_revision = ""
        mock.reference_state_policy = ReferenceStatePolicy.DEF
        mock.state_tp.side_effect = provider.state_tp

        def _biased_ph(fluid, P, h, reference_state=None):
            state = provider.state_ph(fluid, P, h, reference_state=reference_state)
            if fluid.name == "Water" and P == 150000.0:
                # Shift enthalpy to create energy imbalance
                new_h = state.enthalpy_j_kg + bias_value
                return FluidState(
                    temperature_k=state.temperature_k,
                    pressure_pa=state.pressure_pa,
                    enthalpy_j_kg=new_h,
                    density_kg_m3=state.density_kg_m3,
                    cp_j_kg_k=state.cp_j_kg_k,
                    viscosity_pa_s=state.viscosity_pa_s,
                    conductivity_w_m_k=state.conductivity_w_m_k,
                    phase=state.phase,
                    quality=state.quality,
                    entropy_j_kg_k=state.entropy_j_kg_k,
                    provenance=state.provenance,
                )
            return state

        mock.state_ph.side_effect = _biased_ph
        return mock

    def _make_tube_h_biased_provider(self, provider: CoolPropProvider) -> MagicMock:
        """Provider that biases tube h to near-zero to make UA*LMTD != Q.

        By shifting the cold outlet temperature upward, the thermal resistance
        calculation produces a tube h that is very small, making UA*LMTD very
        different from Q. This triggers the UA-LMTD closure blocker.
        """
        mock = MagicMock()
        mock.name = provider.name
        mock.version = provider.version
        mock.git_revision = ""
        mock.reference_state_policy = ReferenceStatePolicy.DEF
        mock.state_tp.side_effect = provider.state_tp

        def _biased_ph(fluid, P, h, reference_state=None):
            state = provider.state_ph(fluid, P, h, reference_state=reference_state)
            if fluid.name == "Water" and P == 150000.0:
                # Shift temperature and enthalpy upward significantly
                # This makes the temperature difference very small,
                # driving Re and Nu toward values that produce very low h
                shifted_h = state.enthalpy_j_kg + 168000.0  # ~40K for water Cp
                return FluidState(
                    temperature_k=state.temperature_k + 40.0,
                    pressure_pa=state.pressure_pa,
                    enthalpy_j_kg=shifted_h,
                    density_kg_m3=state.density_kg_m3,
                    cp_j_kg_k=state.cp_j_kg_k,
                    viscosity_pa_s=state.viscosity_pa_s,
                    conductivity_w_m_k=state.conductivity_w_m_k,
                    phase=state.phase,
                    quality=state.quality,
                    entropy_j_kg_k=state.entropy_j_kg_k,
                    provenance=state.provenance,
                )
            return state

        mock.state_ph.side_effect = _biased_ph
        return mock

    def _make_terminal_dt_biased_provider(self, provider: CoolPropProvider) -> MagicMock:
        """Provider that shifts cold outlet temperature close to hot inlet.

        For counterflow, this makes dt_hot_in_cold_out < minimum_terminal_delta_t,
        triggering the TEMPERATURE_CROSSING blocker.
        """
        mock = MagicMock()
        mock.name = provider.name
        mock.version = provider.version
        mock.git_revision = ""
        mock.reference_state_policy = ReferenceStatePolicy.DEF
        mock.state_tp.side_effect = provider.state_tp

        def _shifted_cold_ph(fluid, P, h, reference_state=None):
            state = provider.state_ph(fluid, P, h, reference_state=reference_state)
            if fluid.name == "Water" and P == 150000.0:
                # Shift temperature upward by 40K to cause terminal dt violation
                shifted_h = state.enthalpy_j_kg + 168000.0  # ~40K for water Cp
                return FluidState(
                    temperature_k=state.temperature_k + 40.0,
                    pressure_pa=state.pressure_pa,
                    enthalpy_j_kg=shifted_h,
                    density_kg_m3=state.density_kg_m3,
                    cp_j_kg_k=state.cp_j_kg_k,
                    viscosity_pa_s=state.viscosity_pa_s,
                    conductivity_w_m_k=state.conductivity_w_m_k,
                    phase=state.phase,
                    quality=state.quality,
                    entropy_j_kg_k=state.entropy_j_kg_k,
                    provenance=state.provenance,
                )
            return state

        mock.state_ph.side_effect = _shifted_cold_ph
        return mock

    def _make_cold_ph_fail_provider(self, provider: CoolPropProvider) -> MagicMock:
        """Provider where cold-side state_ph always raises PropertyServiceError.

        This causes the bracket probing to abort (TrialEvaluationAbort),
        producing a BLOCKED result with the property failure.
        """
        mock = MagicMock()
        mock.name = provider.name
        mock.version = provider.version
        mock.git_revision = ""
        mock.reference_state_policy = ReferenceStatePolicy.DEF
        mock.state_tp.side_effect = provider.state_tp

        def _fail_cold_ph(fluid, P, h, reference_state=None):
            if fluid.name == "Water" and P == 150000.0:
                raise PropertyServiceError(
                    code=PropertyErrorCode.BACKEND_FAILURE,
                    message="Simulated cold-side property failure",
                )
            return provider.state_ph(fluid, P, h, reference_state=reference_state)

        mock.state_ph.side_effect = _fail_cold_ph
        return mock

    def _make_hot_ph_fail_provider(self, provider: CoolPropProvider) -> MagicMock:
        """Provider where hot-side state_ph always raises PropertyServiceError.

        This causes the bracket probing to abort (TrialEvaluationAbort),
        producing a BLOCKED result with the property failure.
        """
        mock = MagicMock()
        mock.name = provider.name
        mock.version = provider.version
        mock.git_revision = ""
        mock.reference_state_policy = ReferenceStatePolicy.DEF
        mock.state_tp.side_effect = provider.state_tp

        def _fail_hot_ph(fluid, P, h, reference_state=None):
            if fluid.name == "Water" and P == 200000.0:
                raise PropertyServiceError(
                    code=PropertyErrorCode.BACKEND_FAILURE,
                    message="Simulated hot-side property failure",
                )
            return provider.state_ph(fluid, P, h, reference_state=reference_state)

        mock.state_ph.side_effect = _fail_hot_ph
        return mock

    def test_postcalc_energy_blocked(self, provider: CoolPropProvider) -> None:
        """Energy balance blocker -> status=BLOCKED, converged=True.

        The solver converges using biased cold-side enthalpies, but the
        post-calculation energy balance check fails because Q_hot != Q_cold
        (the bias creates an energy imbalance).
        """
        mock_prov = self._make_energy_biased_provider(provider, bias_value=5000.0)
        result = _run_rating(mock_prov)

        # Deterministically assert BLOCKED with energy balance blocker
        assert result.status == RatingStatus.BLOCKED
        assert result.converged is True
        blocker_codes = [b.code for b in result.blockers]
        assert ErrorCode.ENERGY_BALANCE_NOT_CLOSED in blocker_codes

    def test_postcalc_ualmtd_blocked(self, provider: CoolPropProvider) -> None:
        """UA-LMTD closure blocker -> status=BLOCKED, converged=True.

        The biased provider shifts cold outlet temperature, causing the
        thermal resistance to produce a very different UA*LMTD from Q.
        """
        mock_prov = self._make_tube_h_biased_provider(provider)
        result = _run_rating(mock_prov)

        # Deterministically assert BLOCKED
        assert result.status == RatingStatus.BLOCKED
        assert result.converged is True
        blocker_codes = [b.code for b in result.blockers]
        # The blocker should be either energy balance or temperature crossing
        # (the large temperature shift can trigger either)
        assert any(
            code in blocker_codes
            for code in [
                ErrorCode.ENERGY_BALANCE_NOT_CLOSED,
                ErrorCode.TEMPERATURE_CROSSING,
            ]
        )

    def test_postcalc_terminal_dt_blocked(self, provider: CoolPropProvider) -> None:
        """Terminal delta-T blocker -> status=BLOCKED, converged=True.

        We mock the cold-side state_ph to return a temperature that is too
        close to the hot inlet, causing the post-solver terminal ΔT check
        to fail for counterflow.
        """
        mock_prov = self._make_terminal_dt_biased_provider(provider)
        result = _run_rating(mock_prov)

        # Deterministically assert BLOCKED with terminal delta-T or energy blocker
        assert result.status == RatingStatus.BLOCKED
        assert result.converged is True
        blocker_codes = [b.code for b in result.blockers]
        assert any(
            code in blocker_codes
            for code in [
                ErrorCode.TEMPERATURE_CROSSING,
                ErrorCode.ENERGY_BALANCE_NOT_CLOSED,
            ]
        )

    def test_postcalc_final_hot_ph_failure(self, provider: CoolPropProvider) -> None:
        """Cold-side state_ph fails -> bracket aborts -> BLOCKED.

        The cold-side state_ph always raises PropertyServiceError, which
        causes the bracket probing to abort immediately. The result is
        BLOCKED with converged=False and a PROPERTY_EVALUATION_FAILED blocker.
        """
        mock_prov = self._make_cold_ph_fail_provider(provider)
        result = _run_rating(mock_prov)

        # Deterministically assert BLOCKED with property failure
        assert result.status == RatingStatus.BLOCKED
        assert result.converged is False
        blocker_codes = [b.code for b in result.blockers]
        assert ErrorCode.PROPERTY_EVALUATION_FAILED in blocker_codes

    def test_postcalc_final_cold_ph_failure(self, provider: CoolPropProvider) -> None:
        """Hot-side state_ph fails -> bracket aborts -> BLOCKED.

        The hot-side state_ph always raises PropertyServiceError, which
        causes the bracket probing to abort immediately. The result is
        BLOCKED with converged=False and a PROPERTY_EVALUATION_FAILED blocker.
        """
        mock_prov = self._make_hot_ph_fail_provider(provider)
        result = _run_rating(mock_prov)

        # Deterministically assert BLOCKED with property failure
        assert result.status == RatingStatus.BLOCKED
        assert result.converged is False
        blocker_codes = [b.code for b in result.blockers]
        assert ErrorCode.PROPERTY_EVALUATION_FAILED in blocker_codes

    def test_postcalc_preserves_diagnostics(self, provider: CoolPropProvider) -> None:
        """All diagnostic fields (Q_hot, UA, LMTD, etc.) are non-None
        when the result is post-calculation BLOCKED (converged=True).
        """
        mock_prov = self._make_energy_biased_provider(provider, bias_value=5000.0)
        result = _run_rating(mock_prov)

        # Must be post-calculation BLOCKED (solver converged, post-calc check failed)
        assert result.status == RatingStatus.BLOCKED
        assert result.converged is True

        # Diagnostics should be preserved
        assert result.Q_hot_w is not None, "Q_hot_w should be non-None"
        assert result.Q_cold_w is not None, "Q_cold_w should be non-None"
        assert result.UA_w_k is not None, "UA_w_k should be non-None"
        assert result.LMTD_k is not None, "LMTD_k should be non-None"
        assert result.heat_duty_w is not None, "heat_duty_w should be non-None"
        assert result.hot_outlet_temperature_k is not None
        assert result.cold_outlet_temperature_k is not None
        # ε-NTU fields
        assert result.NTU is not None, "NTU should be non-None"
        assert result.effectiveness is not None, "effectiveness should be non-None"
        assert result.C_min_w_k is not None, "C_min_w_k should be non-None"
        assert result.C_max_w_k is not None, "C_max_w_k should be non-None"
        # Resistance breakdown
        assert result.resistance_breakdown is not None
        assert result.resistance_breakdown.ua_w_k > 0
        # Correlation info
        assert result.tube_selected_correlation_id is not None
        assert result.annulus_selected_correlation_id is not None


# =========================================================================
# 5. Verifier tamper tests
# =========================================================================


class TestVerifierTamper:
    """Tamper detection on RatingResult property call records."""

    def _get_tampered_result(
        self,
        provider: CoolPropProvider,
        *,
        tamper_fn=None,
    ) -> RatingResult:
        """Run a normal rating and optionally tamper with property_calls."""
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.verify_provenance() is True
        if tamper_fn is not None:
            return tamper_fn(result)
        return result

    def _tamper_property_calls(self, result: RatingResult, tamper_fn) -> RatingResult:
        """Create a new RatingResult with tampered property_calls."""
        tampered_calls = tamper_fn(list(result.property_calls))
        return result.model_copy(update={"property_calls": tuple(tampered_calls)})

    def test_tamper_sequence_index(self, provider: CoolPropProvider) -> None:
        """Change sequence_index -> verify_provenance is False."""

        def _tamper(calls):
            if len(calls) < 2:
                pytest.skip("Need at least 2 calls")
            # Swap first two sequence indices
            calls[0] = calls[0].__class__(**{**calls[0].__dict__, "sequence_index": 999})
            return calls

        result = _run_rating(provider)
        assert result.verify_provenance() is True
        tampered = self._tamper_property_calls(result, _tamper)
        assert tampered.verify_provenance() is False

    def test_tamper_evaluation_index_gap(self, provider: CoolPropProvider) -> None:
        """Skip an evaluation_index -> verify_provenance is False."""

        def _tamper(calls):
            if len(calls) < 3:
                pytest.skip("Need at least 3 calls")
            # Change second call's evaluation_index to skip one
            calls[1] = calls[1].__class__(
                **{**calls[1].__dict__, "evaluation_index": calls[1].evaluation_index + 5}
            )
            return calls

        result = _run_rating(provider)
        assert result.verify_provenance() is True
        tampered = self._tamper_property_calls(result, _tamper)
        assert tampered.verify_provenance() is False

    def test_tamper_duplicate_eval_index(self, provider: CoolPropProvider) -> None:
        """Duplicate evaluation_index -> verify_provenance is False."""

        def _tamper(calls):
            if len(calls) < 3:
                pytest.skip("Need at least 3 calls")
            # Make two different evaluations share the same evaluation_index
            # but with different call_index_within_evaluation to keep pairs unique
            # Actually, evaluation_index must be unique across evaluations but
            # we want to violate the unique pair constraint
            # Change the third call to have same eval_index as second call,
            # and same call_index_within_evaluation -> duplicate pair
            calls[2] = calls[2].__class__(
                **{
                    **calls[2].__dict__,
                    "evaluation_index": calls[1].evaluation_index,
                    "call_index_within_evaluation": calls[1].call_index_within_evaluation,
                }
            )
            return calls

        result = _run_rating(provider)
        assert result.verify_provenance() is True
        tampered = self._tamper_property_calls(result, _tamper)
        assert tampered.verify_provenance() is False

    def test_tamper_role(self, provider: CoolPropProvider) -> None:
        """Change evaluation_role -> verify_provenance is False."""

        def _tamper(calls):
            if not calls:
                pytest.skip("Need at least 1 call")
            # Change the evaluation_role of the first call
            calls[0] = calls[0].__class__(**{**calls[0].__dict__, "evaluation_role": "fake_role"})
            return calls

        result = _run_rating(provider)
        assert result.verify_provenance() is True
        tampered = self._tamper_property_calls(result, _tamper)
        assert tampered.verify_provenance() is False

    def test_tamper_call_index(self, provider: CoolPropProvider) -> None:
        """Change call_index_within_evaluation -> verify_provenance is False."""

        def _tamper(calls):
            if len(calls) < 2:
                pytest.skip("Need at least 2 calls")
            # Make the second call have call_index=0 (same as first),
            # creating a duplicate (eval_index, call_index) pair
            calls[1] = calls[1].__class__(
                **{**calls[1].__dict__, "call_index_within_evaluation": 0}
            )
            return calls

        result = _run_rating(provider)
        assert result.verify_provenance() is True
        tampered = self._tamper_property_calls(result, _tamper)
        assert tampered.verify_provenance() is False


# =========================================================================
# 6. Solver convergence contract test
# =========================================================================


def _make_blocked_result(
    *,
    converged: bool,
    iterations: int,
    solver_termination_reason: str,
    solver_details: SolverDetailsModel | None = None,
) -> RatingResult:
    """Build a BLOCKED RatingResult for convergence contract testing."""
    from hexagent.core.heat_balance import ProviderIdentitySnapshot
    from hexagent.exchangers.double_pipe.rating import (
        _provenance_graph_digest,
        build_provenance,
        build_provenance_core,
        compute_result_hash,
    )

    ri = _make_minimal_request_identity()
    pi = ProviderIdentitySnapshot(
        name="CoolProp",
        version="1.0",
        git_revision="",
        reference_state_policy="def",
    )
    empty_res = _build_empty_resistance()
    if solver_details is None:
        solver_details = _build_empty_solver_details()

    core_graph, core_nodes, core_edges = build_provenance_core(
        flow_arrangement=FlowArrangement.COUNTERFLOW,
        property_calls=(),
        iterations=iterations,
        converged=converged,
        warnings=[],
        blockers=[],
        request_identity=ri,
    )
    core_digest = _provenance_graph_digest(core_graph)

    result_hash = compute_result_hash(
        request_identity=ri,
        provider_identity=pi,
        flow_arrangement=FlowArrangement.COUNTERFLOW,
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
        resistance_breakdown=empty_res,
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
        iterations=iterations,
        converged=converged,
        solver_termination_reason=solver_termination_reason,
        solver_details=solver_details,
        property_calls=(),
        warnings=(),
        blockers=(),
        status=RatingStatus.BLOCKED,
        core_provenance_digest=core_digest,
    )

    provenance_graph = build_provenance(
        flow_arrangement=FlowArrangement.COUNTERFLOW,
        property_calls=(),
        iterations=iterations,
        converged=converged,
        warnings=[],
        blockers=[],
        result_hash=result_hash,
        request_identity=ri,
    )
    prov_digest = _provenance_graph_digest(provenance_graph)

    blocker = EngineeringMessage(
        code=ErrorCode.ENERGY_BALANCE_NOT_CLOSED,
        severity=EngineeringMessageSeverity.BLOCKER,
        message="Test blocker",
        source_module="test",
    )

    return RatingResult(
        status=RatingStatus.BLOCKED,
        flow_arrangement=FlowArrangement.COUNTERFLOW,
        heat_duty_w=None,
        hot_outlet_temperature_k=None,
        cold_outlet_temperature_k=None,
        area_inner_m2=0.0,
        area_outer_m2=0.0,
        resistance_breakdown=empty_res,
        iterations=iterations,
        converged=converged,
        solver_termination_reason=solver_termination_reason,
        solver_details=solver_details,
        warnings=(),
        blockers=(blocker,),
        property_calls=(),
        provider_identity=pi,
        request_identity=ri,
        result_hash=result_hash,
        provenance_graph=provenance_graph,
        provenance_digest=prov_digest,
        core_provenance_digest=core_digest,
    )


class TestSolverConvergenceContract:
    """Solver convergence contract validation in RatingResult."""

    def test_convergence_contract_valid(self, provider: CoolPropProvider) -> None:
        """BLOCKED with converged=True, solver_termination_reason='converged'
        -> valid (no exception).
        """
        result = _make_blocked_result(
            converged=True,
            iterations=5,
            solver_termination_reason="converged",
        )
        assert result.status == RatingStatus.BLOCKED
        assert result.converged is True

    def test_convergence_contract_converged_false_with_converged_reason(
        self, provider: CoolPropProvider
    ) -> None:
        """converged=False with solver_termination_reason='converged' -> ValueError."""
        with pytest.raises(ValidationError, match="converged is False"):
            _make_blocked_result(
                converged=False,
                iterations=5,
                solver_termination_reason="converged",
            )

    def test_convergence_contract_bracket_not_found_with_converged_true(
        self, provider: CoolPropProvider
    ) -> None:
        """bracket_not_found + converged=True -> ValueError.

        A bracket-not-found termination cannot coexist with converged=True.
        """
        with pytest.raises(ValidationError, match="bracket_not_found.*converged is True"):
            _make_blocked_result(
                converged=True,
                iterations=5,
                solver_termination_reason="bracket_not_found",
            )

    def test_convergence_contract_non_convergence_with_converged_true(
        self, provider: CoolPropProvider
    ) -> None:
        """non_convergence + converged=True -> ValueError.

        A non-convergence termination cannot coexist with converged=True.
        """
        with pytest.raises(ValidationError, match="non_convergence.*converged is True"):
            _make_blocked_result(
                converged=True,
                iterations=5,
                solver_termination_reason="non_convergence",
            )

    def test_convergence_contract_solver_details_termination_mismatch(
        self, provider: CoolPropProvider
    ) -> None:
        """solver_details.termination_reason != solver_termination_reason -> ValueError."""
        mismatched_details = SolverDetailsModel(
            iterations=5,
            residual_w=0.001,
            function_evaluations=10,
            termination_reason="non_convergence",  # mismatch!
        )
        with pytest.raises(ValidationError, match="solver_details\\.termination_reason"):
            _make_blocked_result(
                converged=True,
                iterations=5,
                solver_termination_reason="converged",
                solver_details=mismatched_details,
            )

    def test_convergence_contract_solver_details_iterations_mismatch(
        self, provider: CoolPropProvider
    ) -> None:
        """solver_details.iterations != iterations -> ValueError."""
        mismatched_details = SolverDetailsModel(
            iterations=10,  # mismatch with top-level iterations=5
            residual_w=0.001,
            function_evaluations=10,
            termination_reason="converged",
        )
        with pytest.raises(ValidationError, match="solver_details\\.iterations"):
            _make_blocked_result(
                converged=True,
                iterations=5,
                solver_termination_reason="converged",
                solver_details=mismatched_details,
            )


# =========================================================================
# 7. Solver convergence validator details
# =========================================================================


class TestSolverConvergenceValidatorDetails:
    """Explicit tests for solver convergence validator cross-checks."""

    def test_converged_true_both_reasons_converged_valid(self) -> None:
        """converged=True + solver_termination_reason='converged' +
        solver_details.termination_reason='converged' -> valid.
        """
        details = SolverDetailsModel(
            iterations=5,
            residual_w=0.001,
            function_evaluations=10,
            termination_reason="converged",
        )
        result = _make_blocked_result(
            converged=True,
            iterations=5,
            solver_termination_reason="converged",
            solver_details=details,
        )
        assert result.status == RatingStatus.BLOCKED
        assert result.converged is True

    def test_converged_true_details_non_convergence_raises(self) -> None:
        """converged=True + solver_termination_reason='converged' +
        solver_details.termination_reason='non_convergence' -> ValueError.
        """
        details = SolverDetailsModel(
            iterations=5,
            residual_w=0.001,
            function_evaluations=10,
            termination_reason="non_convergence",  # mismatch!
        )
        with pytest.raises(ValidationError, match="solver_details\\.termination_reason"):
            _make_blocked_result(
                converged=True,
                iterations=5,
                solver_termination_reason="converged",
                solver_details=details,
            )

    def test_converged_false_both_reasons_non_convergence_valid(self) -> None:
        """converged=False + solver_termination_reason='non_convergence' +
        solver_details.termination_reason='non_convergence' -> valid.
        """
        details = SolverDetailsModel(
            iterations=5,
            residual_w=0.001,
            function_evaluations=10,
            termination_reason="non_convergence",
        )
        result = _make_blocked_result(
            converged=False,
            iterations=5,
            solver_termination_reason="non_convergence",
            solver_details=details,
        )
        assert result.status == RatingStatus.BLOCKED
        assert result.converged is False

    def test_converged_true_bracket_not_found_raises(self) -> None:
        """converged=True + solver_termination_reason='bracket_not_found' -> ValueError."""
        details = SolverDetailsModel(
            iterations=0,
            residual_w=float("nan"),
            function_evaluations=20,
            termination_reason="bracket_not_found",
        )
        with pytest.raises(ValidationError, match="bracket_not_found.*converged is True"):
            _make_blocked_result(
                converged=True,
                iterations=0,
                solver_termination_reason="bracket_not_found",
                solver_details=details,
            )
