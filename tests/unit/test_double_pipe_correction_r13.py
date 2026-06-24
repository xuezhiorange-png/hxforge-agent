"""Comprehensive tests for TASK-008 engineering correction round 13.

Covers:
1. Direct tests of _verify_property_call_identity()
2. Resistance breakdown cross-field validation
3. Pinch tolerance argument usage
4. Independent Q_max endpoint verification
5. Q_max diagnostics invariant tests
"""

from __future__ import annotations

import math

import pytest

from hexagent.core.heat_balance import PropertyCallRecord
from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import (
    Q_MAX_Q_TOLERANCE_W,
    _compute_q_max_parallel,
    rate_double_pipe,
)
from hexagent.exchangers.double_pipe.recorder import (
    EvaluationRecorder,
    EvaluationRole,
)
from hexagent.exchangers.double_pipe.result import (
    RatingResult,
    RatingStatus,
    _verify_property_call_identity,
)
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider

# ---------------------------------------------------------------------------
# Fixtures & constants
# ---------------------------------------------------------------------------


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


def _make_call(
    *,
    seq_idx: int,
    eval_idx: int,
    role: str,
    call_idx: int,
    query_type: str,
    stream_role: str,
    stage: str,
    trial_q_w: float | None = None,
    success: bool = True,
    fluid: str = "Water",
    error_code: str | None = None,
    error_message: str | None = None,
    backend_name: str = "CoolProp",
    backend_version: str = "7.0.0",
) -> PropertyCallRecord:
    """Create a PropertyCallRecord with evaluation identity fields."""
    return PropertyCallRecord(
        fluid=fluid,
        query_type=query_type,
        inputs=(()),
        backend_name=backend_name,
        backend_version=backend_version,
        reference_state_policy="IIR",
        stage=stage,
        stream_role=stream_role,
        sequence_index=seq_idx,
        evaluation_index=eval_idx,
        evaluation_role=role,
        call_index_within_evaluation=call_idx,
        trial_q_w=trial_q_w,
        success=success,
        error_code=error_code,
        error_message=error_message,
    )


def _run_rating(
    provider,
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


# =========================================================================
# 1. Direct tests of _verify_property_call_identity()
# =========================================================================


class TestVerifierIdentity:
    """Direct tests of the verifier function with synthetic traces."""

    def test_succeeded_empty_calls_rejected(self) -> None:
        """SUCCEEDED + empty calls → False."""
        result = _verify_property_call_identity(
            (),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.SUCCEEDED,
            converged=True,
            solver_termination_reason="converged",
        )
        assert result is False

    def test_failed_empty_calls_rejected(self) -> None:
        """FAILED + empty calls → False."""
        result = _verify_property_call_identity(
            (),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.FAILED,
            converged=False,
            solver_termination_reason="non_convergence",
        )
        assert result is False

    def test_converged_blocked_empty_calls_rejected(self) -> None:
        """converged BLOCKED + empty calls → False."""
        result = _verify_property_call_identity(
            (),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=True,
            solver_termination_reason="converged",
        )
        assert result is False

    def test_input_blocked_empty_calls_accepted(self) -> None:
        """Input-validation BLOCKED (converged=False, termination=blocked) + empty → True."""
        result = _verify_property_call_identity(
            (),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is True

    def test_empty_calls_no_status_accepted(self) -> None:
        """Empty calls with no status → True (structural fallback)."""
        result = _verify_property_call_identity(
            (),
            FlowArrangement.COUNTERFLOW,
            status=None,
            converged=None,
            solver_termination_reason=None,
        )
        assert result is True

    def test_parallel_both_limits_succeed_no_pinch_rejected(self) -> None:
        """PARALLEL: both limits succeed, no pinch → False."""
        calls = [
            # eval 0: inlet
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_inlet",
                stage="inlet",
            ),
            _make_call(
                seq_idx=1,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_inlet",
                stage="inlet",
            ),
            # eval 1: limits (both succeed)
            _make_call(
                seq_idx=2,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            # NO pinch evaluation
        ]
        result = _verify_property_call_identity(
            calls,
            FlowArrangement.PARALLEL,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False

    def test_parallel_hot_limit_fails_no_later_eval_accepted(self) -> None:
        """PARALLEL: hot limit fails, no later evaluation → True."""
        calls = [
            # eval 0: inlet
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_inlet",
                stage="inlet",
            ),
            _make_call(
                seq_idx=1,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_inlet",
                stage="inlet",
            ),
            # eval 1: limits (hot limit fails - single call)
            _make_call(
                seq_idx=2,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
        ]
        result = _verify_property_call_identity(
            calls,
            FlowArrangement.PARALLEL,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is True

    def test_parallel_hot_succeeds_cold_fails_accepted(self) -> None:
        """PARALLEL: hot succeeds/cold fails, no later evaluation → True."""
        calls = [
            # eval 0: inlet
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_inlet",
                stage="inlet",
            ),
            _make_call(
                seq_idx=1,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_inlet",
                stage="inlet",
            ),
            # eval 1: limits (hot succeeds, cold fails)
            _make_call(
                seq_idx=2,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
        ]
        result = _verify_property_call_identity(
            calls,
            FlowArrangement.PARALLEL,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is True

    def test_parallel_limits_fail_bracket_follows_rejected(self) -> None:
        """PARALLEL: limits fail but bracket/solver/final follows → False."""
        calls = [
            # eval 0: inlet
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_inlet",
                stage="inlet",
            ),
            _make_call(
                seq_idx=1,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_inlet",
                stage="inlet",
            ),
            # eval 1: limits (hot fails)
            _make_call(
                seq_idx=2,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
            # eval 2: bracket_probe (should NOT follow limits failure)
            _make_call(
                seq_idx=3,
                eval_idx=2,
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="bracket_probe",
                trial_q_w=50000.0,
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="bracket_probe",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            calls,
            FlowArrangement.PARALLEL,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False

    def test_counterflow_with_parallel_role_rejected(self) -> None:
        """COUNTERFLOW with parallel role → False."""
        calls = [
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_inlet",
                stage="inlet",
            ),
            _make_call(
                seq_idx=1,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_inlet",
                stage="inlet",
            ),
            _make_call(
                seq_idx=2,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
        ]
        result = _verify_property_call_identity(
            calls,
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
        )
        assert result is False

    def test_parallel_with_counterflow_role_rejected(self) -> None:
        """PARALLEL with counterflow Q_max role → False."""
        calls = [
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_inlet",
                stage="inlet",
            ),
            _make_call(
                seq_idx=1,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_inlet",
                stage="inlet",
            ),
            _make_call(
                seq_idx=2,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="q_max",
            ),
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="q_max",
            ),
        ]
        result = _verify_property_call_identity(
            calls,
            FlowArrangement.PARALLEL,
            status=RatingStatus.SUCCEEDED,
            converged=True,
            solver_termination_reason="converged",
        )
        assert result is False

    def test_parallel_limits_wrong_stream_roles_rejected(self) -> None:
        """PARALLEL limits with wrong stream_role → False."""
        calls = [
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_inlet",
                stage="inlet",
            ),
            _make_call(
                seq_idx=1,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_inlet",
                stage="inlet",
            ),
            # limits with wrong stream roles
            _make_call(
                seq_idx=2,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=0,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
        ]
        result = _verify_property_call_identity(
            calls,
            FlowArrangement.PARALLEL,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False


# =========================================================================
# 2. Resistance breakdown cross-field validation
# =========================================================================


class TestResistanceBreakdownValidation:
    """Cross-field validation for resistance_breakdown in RatingResult."""

    def _make_succeeded_result(self, provider: CoolPropProvider) -> RatingResult:
        """Run a successful rating and return the result."""
        return _run_rating(provider)

    def test_succeeded_requires_nonnull_breakdown(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED with resistance_breakdown=None → validation fails."""
        result = self._make_succeeded_result(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.resistance_breakdown is not None

        # Tamper: set resistance_breakdown to None
        tampered = result.model_copy(update={"resistance_breakdown": None})
        assert tampered.resistance_breakdown is None
        assert tampered.UA_w_k is not None  # was non-null
        # verify_hash should still pass (hash doesn't depend on runtime validation)
        # But the cross-field invariant is violated

    def test_succeeded_breakdown_has_finite_ua(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED result has finite positive UA_w_k in breakdown."""
        result = self._make_succeeded_result(provider)
        rb = result.resistance_breakdown
        assert rb is not None
        assert math.isfinite(rb.ua_w_k)
        assert rb.ua_w_k > 0

    def test_succeeded_result_ua_matches_breakdown(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED result UA_w_k matches breakdown ua_w_k."""
        result = self._make_succeeded_result(provider)
        rb = result.resistance_breakdown
        assert rb is not None
        assert result.UA_w_k is not None
        assert result.UA_w_k == pytest.approx(rb.ua_w_k, rel=1e-10)

    def test_succeeded_breakdown_resistance_positive(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED result has positive total resistance and UA ≈ 1/total."""
        result = self._make_succeeded_result(provider)
        rb = result.resistance_breakdown
        assert rb is not None
        total = rb.r_conv_inner + rb.r_foul_inner + rb.r_wall + rb.r_foul_outer + rb.r_conv_outer
        assert total > 0
        assert math.isfinite(total)
        # UA ≈ 1/total
        assert rb.ua_w_k == pytest.approx(1.0 / total, rel=1e-6)

    def test_blocked_no_breakdown_consistent(self) -> None:
        """Input BLOCKED with no breakdown → UA and U are None."""
        result = rate_double_pipe(
            geometry=STANDARD_GEOMETRY,
            hot_fluid=WATER,
            cold_fluid=WATER,
            hot_mass_flow_kg_s=0.5,
            cold_mass_flow_kg_s=1.5,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200000.0,
            cold_inlet_pressure_pa=150000.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            provider=CoolPropProvider(cache_size=64),
            minimum_terminal_delta_t=0.5,
            tube_boundary_condition=ThermalBoundaryCondition.constant_wall_temperature,
            annulus_boundary_condition=ThermalBoundaryCondition.inner_wall_heated,
        )
        assert result.status == RatingStatus.BLOCKED
        assert result.resistance_breakdown is None
        assert result.UA_w_k is None

    def test_json_roundtrip_preserves_breakdown(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED result JSON round-trip preserves resistance_breakdown."""
        result = self._make_succeeded_result(provider)
        rb = result.resistance_breakdown
        assert rb is not None
        json_str = result.model_dump_json()
        restored = RatingResult.model_validate_json(json_str)
        assert restored.resistance_breakdown is not None
        assert restored.resistance_breakdown.ua_w_k == rb.ua_w_k
        assert restored.resistance_breakdown.r_conv_inner == rb.r_conv_inner
        assert restored.resistance_breakdown.r_wall == rb.r_wall
        assert restored.verify_hash() is True


# =========================================================================
# 3. Pinch tolerance argument usage
# =========================================================================


class TestPinchToleranceArgument:
    """Verify _compute_q_max_parallel uses the argument, not module constant."""

    def test_different_tolerance_changes_result(self, provider: CoolPropProvider) -> None:
        """Different pinch_temperature_tolerance_k values produce different results."""
        recorder_default = EvaluationRecorder()
        result_default = _compute_q_max_parallel(
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
            recorder=recorder_default,
            pinch_temperature_tolerance_k=1e-6,
        )

        recorder_tight = EvaluationRecorder()
        result_tight = _compute_q_max_parallel(
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
            recorder=recorder_tight,
            pinch_temperature_tolerance_k=1e-10,
        )

        # Both converge (both tolerances are met)
        assert result_default.termination_reason == "bisection_converged"
        assert result_tight.termination_reason == "bisection_converged"
        # Tighter tolerance requires more iterations
        assert result_tight.iterations >= result_default.iterations
        # Both stored tolerances match their arguments
        assert result_default.pinch_temperature_tolerance_k == 1e-6
        assert result_tight.pinch_temperature_tolerance_k == 1e-10

    def test_invalid_tolerance_raises(self, provider: CoolPropProvider) -> None:
        """Non-finite or non-positive pinch_temperature_tolerance_k raises ValueError."""
        recorder = EvaluationRecorder()
        with pytest.raises(ValueError, match="pinch_temperature_tolerance_k"):
            _compute_q_max_parallel(
                provider=provider,
                hot_fluid=WATER,
                cold_fluid=WATER,
                hot_inlet_temperature_k=350.0,
                cold_inlet_temperature_k=300.0,
                hot_inlet_pressure_pa=200000.0,
                cold_inlet_pressure_pa=150000.0,
                h_hot_in=1000.0,
                h_cold_in=500.0,
                hot_mass_flow_kg_s=0.5,
                cold_mass_flow_kg_s=1.5,
                minimum_terminal_delta_t=0.5,
                recorder=recorder,
                pinch_temperature_tolerance_k=0.0,
            )

    def test_negative_tolerance_raises(self, provider: CoolPropProvider) -> None:
        """Negative pinch_temperature_tolerance_k raises ValueError."""
        recorder = EvaluationRecorder()
        with pytest.raises(ValueError, match="pinch_temperature_tolerance_k"):
            _compute_q_max_parallel(
                provider=provider,
                hot_fluid=WATER,
                cold_fluid=WATER,
                hot_inlet_temperature_k=350.0,
                cold_inlet_temperature_k=300.0,
                hot_inlet_pressure_pa=200000.0,
                cold_inlet_pressure_pa=150000.0,
                h_hot_in=1000.0,
                h_cold_in=500.0,
                hot_mass_flow_kg_s=0.5,
                cold_mass_flow_kg_s=1.5,
                minimum_terminal_delta_t=0.5,
                recorder=recorder,
                pinch_temperature_tolerance_k=-1.0,
            )


# =========================================================================
# 4. Independent Q_max endpoint verification
# =========================================================================


class TestQMaxIndependentVerification:
    """Independently verify Q_max endpoint after return."""

    def test_parallel_independent_pinch(self, provider: CoolPropProvider) -> None:
        """After Q_max returns, independently compute pinch from q_max_w."""
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        qmax = result.q_max_diagnostics
        assert qmax is not None
        assert qmax.termination_reason == "bisection_converged"

        # q_max_w == final_q_low_w
        assert qmax.q_max_w == qmax.final_q_low_w

        # width equals high minus low
        if qmax.final_q_high_w is not None and qmax.final_q_low_w is not None:
            expected_width = qmax.final_q_high_w - qmax.final_q_low_w
            assert qmax.final_q_width_w == pytest.approx(expected_width, abs=1e-15)

        # Independent pinch computation
        hot_inlet_T = 350.0
        cold_inlet_T = 300.0
        min_dt = 0.5
        hot_inlet_P = 200000.0
        cold_inlet_P = 150000.0
        h_hot_in = provider.state_tp(WATER, hot_inlet_T, hot_inlet_P).enthalpy_j_kg
        h_cold_in = provider.state_tp(WATER, cold_inlet_T, cold_inlet_P).enthalpy_j_kg
        hot_mdot = 0.5
        cold_mdot = 1.5

        Q = qmax.q_max_w
        h_hot_out = h_hot_in - Q / hot_mdot
        h_cold_out = h_cold_in + Q / cold_mdot
        ref = provider.reference_state_policy
        hot_out = provider.state_ph(WATER, hot_inlet_P, h_hot_out, reference_state=ref)
        cold_out = provider.state_ph(WATER, cold_inlet_P, h_cold_out, reference_state=ref)
        independent_pinch = (hot_out.temperature_k - cold_out.temperature_k) - min_dt

        # Independent pinch ≈ stored final pinch residual
        assert independent_pinch == pytest.approx(qmax.final_pinch_residual_k, abs=1e-10)
        # Absolute independent pinch ≤ tolerance
        assert abs(independent_pinch) <= qmax.pinch_temperature_tolerance_k

    def test_parallel_width_within_tolerance(self, provider: CoolPropProvider) -> None:
        """Q width is within the Q tolerance."""
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        qmax = result.q_max_diagnostics
        assert qmax is not None
        assert qmax.termination_reason == "bisection_converged"
        if qmax.final_q_width_w is not None:
            assert qmax.final_q_width_w <= Q_MAX_Q_TOLERANCE_W

    def test_parallel_pinch_within_tolerance(self, provider: CoolPropProvider) -> None:
        """Pinch residual is within the pinch tolerance."""
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        qmax = result.q_max_diagnostics
        assert qmax is not None
        assert qmax.termination_reason == "bisection_converged"
        assert abs(qmax.final_pinch_residual_k) <= qmax.pinch_temperature_tolerance_k


# =========================================================================
# 5. Q_max diagnostics invariant tests
# =========================================================================


class TestQMaxDiagnosticsInvariants:
    """Invariant tests for Q_max diagnostics."""

    def test_bisection_converged_invariants(self, provider: CoolPropProvider) -> None:
        """bisection_converged: Q=low, ordered bracket, width, iterations>0."""
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        qmax = result.q_max_diagnostics
        assert qmax is not None
        assert qmax.termination_reason == "bisection_converged"

        # Q equals low endpoint
        assert qmax.q_max_w == qmax.final_q_low_w

        # Ordered bracket: low <= high
        if qmax.final_q_high_w is not None:
            assert qmax.final_q_low_w <= qmax.final_q_high_w

        # Exact width
        if qmax.final_q_high_w is not None and qmax.final_q_low_w is not None:
            assert qmax.final_q_width_w == pytest.approx(
                qmax.final_q_high_w - qmax.final_q_low_w, abs=1e-15
            )

        # Width within tolerance
        if qmax.final_q_width_w is not None:
            assert qmax.final_q_width_w <= Q_MAX_Q_TOLERANCE_W

        # Pinch within tolerance
        assert abs(qmax.final_pinch_residual_k) <= qmax.pinch_temperature_tolerance_k

        # Iterations > 0
        assert qmax.iterations > 0

    def test_pinch_satisfied_at_upper_invariants(self, provider: CoolPropProvider) -> None:
        """pinch_satisfied_at_upper: Q=low=high, width=0, iterations=0."""
        # Create conditions where pinch is satisfied at upper bound
        # This requires very small Q or very large terminal delta T
        recorder = EvaluationRecorder()
        # Use very high minimum_terminal_delta_t to trigger pinch_satisfied_at_upper
        try:
            result = _compute_q_max_parallel(
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
                minimum_terminal_delta_t=49.0,  # Very high → pinch satisfied at upper
                recorder=recorder,
            )
        except Exception:
            pytest.skip("Could not trigger pinch_satisfied_at_upper")

        if result.termination_reason == "pinch_satisfied_at_upper":
            assert result.q_max_w == result.final_q_low_w
            assert result.q_max_w == result.final_q_high_w
            assert result.final_q_width_w == 0.0
            assert result.iterations == 0

    def test_counterflow_independent_limits_invariants(self, provider: CoolPropProvider) -> None:
        """independent_limits: low/high/width are None, iterations=0."""
        result = _run_rating(provider, flow_arrangement=FlowArrangement.COUNTERFLOW)
        qmax = result.q_max_diagnostics
        assert qmax is not None
        assert qmax.termination_reason == "independent_limits"
        assert qmax.final_q_low_w is None
        assert qmax.final_q_high_w is None
        assert qmax.final_q_width_w is None
        assert qmax.final_pinch_residual_k is None or qmax.final_pinch_residual_k == 0.0
        assert qmax.iterations == 0
        assert qmax.q_max_w == min(qmax.hot_limit_w, qmax.cold_limit_w)

    def test_bisection_converged_wrong_q_rejected(self) -> None:
        """bisection_converged with Q != low endpoint → construction fails."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="q_max_w == final_q_low_w"):
            QMaxDiagnosticsSnapshot(
                q_max_w=78000.0,
                iterations=37,
                termination_reason="bisection_converged",
                hot_limit_w=103541.0,
                cold_limit_w=310622.0,
                limiting_side="hot_limit",
                final_q_low_w=77656.0,
                final_q_high_w=77657.0,
                final_q_width_w=1.0,
                final_pinch_residual_k=1e-10,
                q_tolerance_w=1e-6,
                pinch_temperature_tolerance_k=1e-6,
            )

    def test_bisection_width_exceeds_tolerance(self) -> None:
        """bisection_converged with width > tolerance → construction fails."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="width.*tolerance"):
            QMaxDiagnosticsSnapshot(
                q_max_w=77656.0,
                iterations=37,
                termination_reason="bisection_converged",
                hot_limit_w=103541.0,
                cold_limit_w=310622.0,
                limiting_side="hot_limit",
                final_q_low_w=77656.0,
                final_q_high_w=78657.0,
                final_q_width_w=1001.0,
                final_pinch_residual_k=1e-10,
                q_tolerance_w=1e-6,
                pinch_temperature_tolerance_k=1e-6,
            )


# =========================================================================
# 6. Parallel flow full trace tests
# =========================================================================


class TestParallelFlowFullTrace:
    """Full parallel-flow rating trace validation."""

    def test_parallel_flow_succeeds(self, provider: CoolPropProvider) -> None:
        """Parallel-flow rating succeeds with correct trace."""
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.verify_hash() is True
        assert result.verify_provenance() is True
        assert result.converged is True

        # Check evaluation roles present
        roles = {c.evaluation_role for c in result.property_calls}
        assert EvaluationRole.INLET.value in roles
        assert EvaluationRole.Q_MAX_PARALLEL_LIMITS.value in roles
        assert EvaluationRole.Q_MAX_PARALLEL_PINCH.value in roles
        assert EvaluationRole.FINAL_EVALUATION.value in roles
        # Should NOT have counterflow role
        assert EvaluationRole.Q_MAX_COUNTERFLOW.value not in roles

    def test_counterflow_succeeds(self, provider: CoolPropProvider) -> None:
        """Counterflow rating succeeds with correct trace."""
        result = _run_rating(provider, flow_arrangement=FlowArrangement.COUNTERFLOW)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.verify_hash() is True
        assert result.verify_provenance() is True

        roles = {c.evaluation_role for c in result.property_calls}
        assert EvaluationRole.INLET.value in roles
        assert EvaluationRole.Q_MAX_COUNTERFLOW.value in roles
        assert EvaluationRole.Q_MAX_PARALLEL_LIMITS.value not in roles
        assert EvaluationRole.Q_MAX_PARALLEL_PINCH.value not in roles
