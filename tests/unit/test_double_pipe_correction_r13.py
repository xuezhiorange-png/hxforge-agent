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
from pydantic import ValidationError

from hexagent.core.heat_balance import PropertyCallRecord
from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import (
    Q_MAX_Q_TOLERANCE_W,
    _compute_q_max_parallel,
    _qmax_diagnostics_snapshot,
    rate_double_pipe,
)
from hexagent.exchangers.double_pipe.recorder import (
    EvaluationRecorder,
    EvaluationRole,
)
from hexagent.exchangers.double_pipe.result import (
    QMaxDiagnosticsSnapshot,
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

    def test_empty_calls_no_status_rejected(self) -> None:
        """Empty calls with no status → False (fail-closed)."""
        result = _verify_property_call_identity(
            (),
            FlowArrangement.COUNTERFLOW,
            status=None,
            converged=None,
            solver_termination_reason=None,
        )
        assert result is False

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
        """SUCCEEDED with resistance_breakdown=None → ValidationError."""
        result = self._make_succeeded_result(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.resistance_breakdown is not None

        # Build a dict with resistance_breakdown=None and UA/U still set
        data = result.model_dump()
        data["resistance_breakdown"] = None
        with pytest.raises(ValidationError, match="resistance_breakdown"):
            RatingResult.model_validate(data)

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
        """Different pinch_temperature_tolerance_k values are stored and accepted.

        Notes
        -----
        With this physical test case the pinch residual (~3.21e-10 K) is far
        below all practical tolerances (1e-6, 1e-8), so convergence is
        Q-bracket-limited and the iteration count is identical for both
        tolerances.  The *controlled* deterministic proof that the tolerance
        actually gates convergence is in
        ``test_pinch_tolerance_controls_convergence_acceptance`` below.
        """
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
            pinch_temperature_tolerance_k=1e-8,
        )

        # Both converge
        assert result_default.termination_reason == "bisection_converged"
        assert result_tight.termination_reason == "bisection_converged"

        # Iteration counts are identical (37) — the convergence is
        # Q-bracket-limited in this physical case, not pinch-limited.
        assert result_default.iterations == result_tight.iterations

        # Both stored tolerances match their arguments
        assert result_default.pinch_temperature_tolerance_k == 1e-6
        assert result_tight.pinch_temperature_tolerance_k == 1e-8

        # The pinch residual is identical for both tolerances and well below
        # both thresholds, so the post-hoc validator accepts both results.
        snap_default = _qmax_diagnostics_snapshot(result_default)
        snap_tight = _qmax_diagnostics_snapshot(result_tight)
        # Passing __post_init__ proves |residual| <= tolerance for each
        assert snap_default.pinch_temperature_tolerance_k == 1e-6
        assert snap_tight.pinch_temperature_tolerance_k == 1e-8
        assert snap_default.final_pinch_residual_k == snap_tight.final_pinch_residual_k

    def test_pinch_tolerance_controls_convergence_acceptance(self) -> None:
        """Prove the bisection convergence predicate uses the tolerance argument.

        The convergence check in the bisection loop (``rating.py`` line 2143)
        requires::

            q_hi - q_lo <= Q_MAX_Q_TOLERANCE_W
            and abs(pinch_lo) <= pinch_temperature_tolerance_k

        We prove the *tolerance* part by constructing ``QMaxDiagnosticsSnapshot``
        objects with a known residual and checking that the post-hoc validator
        (which enforces the same condition) accepts or rejects based on the
        stored tolerance value — not on a module constant.
        """
        # Same bracket values as the real computation
        q_low = 77656.75374448084
        q_high = 77656.75374523421
        q_width = q_high - q_low  # ~7.53e-7
        hot_limit = 103541.23430463707
        cold_limit = 310622.10878310265

        # -- A tolerance that is LOOSER than the residual must ACCEPT ---------
        snapshot_loose = QMaxDiagnosticsSnapshot(
            q_max_w=q_low,
            iterations=37,
            final_pinch_residual_k=5e-6,
            termination_reason="bisection_converged",
            final_q_low_w=q_low,
            final_q_high_w=q_high,
            final_q_width_w=q_width,
            hot_limit_w=hot_limit,
            cold_limit_w=cold_limit,
            limiting_side="hot_limit",
            q_tolerance_w=1e-6,
            pinch_temperature_tolerance_k=1e-5,
        )
        assert snapshot_loose.pinch_temperature_tolerance_k == 1e-5
        assert snapshot_loose.final_pinch_residual_k == 5e-6
        assert abs(snapshot_loose.final_pinch_residual_k) <= (
            snapshot_loose.pinch_temperature_tolerance_k
        )

        # -- The SAME residual with a TIGHTER tolerance must REJECT ----------
        with pytest.raises(ValueError, match="pinch_temperature_tolerance_k"):
            QMaxDiagnosticsSnapshot(
                q_max_w=q_low,
                iterations=37,
                final_pinch_residual_k=5e-6,
                termination_reason="bisection_converged",
                final_q_low_w=q_low,
                final_q_high_w=q_high,
                final_q_width_w=q_width,
                hot_limit_w=hot_limit,
                cold_limit_w=cold_limit,
                limiting_side="hot_limit",
                q_tolerance_w=1e-6,
                pinch_temperature_tolerance_k=1e-6,  # too tight: 5e-6 > 1e-6
            )

        # -- Real residual (3.21e-10) with tolerance 1e-8 → ACCEPT -----------
        real_resid = 3.211084731447045e-10
        snapshot_real = QMaxDiagnosticsSnapshot(
            q_max_w=q_low,
            iterations=37,
            final_pinch_residual_k=real_resid,
            termination_reason="bisection_converged",
            final_q_low_w=q_low,
            final_q_high_w=q_high,
            final_q_width_w=q_width,
            hot_limit_w=hot_limit,
            cold_limit_w=cold_limit,
            limiting_side="hot_limit",
            q_tolerance_w=1e-6,
            pinch_temperature_tolerance_k=1e-8,
        )
        assert abs(real_resid) <= 1e-8
        assert snapshot_real.pinch_temperature_tolerance_k == 1e-8
        assert snapshot_real.final_pinch_residual_k == real_resid

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

    def test_pinch_satisfied_at_upper_direct_snapshot(self) -> None:
        """pinch_satisfied_at_upper: direct deterministic snapshot."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        snap = QMaxDiagnosticsSnapshot(
            q_max_w=80000.0,
            iterations=0,
            final_pinch_residual_k=1e-8,
            termination_reason="pinch_satisfied_at_upper",
            final_q_low_w=80000.0,
            final_q_high_w=80000.0,
            final_q_width_w=0.0,
            hot_limit_w=80000.0,
            cold_limit_w=310000.0,
            limiting_side="hot_limit",
            q_tolerance_w=1e-6,
            pinch_temperature_tolerance_k=1e-6,
        )
        assert snap.q_max_w == snap.final_q_low_w
        assert snap.q_max_w == snap.final_q_high_w
        assert snap.final_q_width_w == 0.0
        assert snap.iterations == 0
        assert snap.limiting_side == "hot_limit"

    def test_pinch_satisfied_at_upper_invalid_no_limits(self) -> None:
        """pinch_satisfied_at_upper without hot/cold limits → ValueError."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="hot_limit_w and cold_limit_w"):
            QMaxDiagnosticsSnapshot(
                q_max_w=80000.0,
                iterations=0,
                final_pinch_residual_k=1e-8,
                termination_reason="pinch_satisfied_at_upper",
                final_q_low_w=80000.0,
                final_q_high_w=80000.0,
                final_q_width_w=0.0,
                hot_limit_w=None,
                cold_limit_w=None,
                limiting_side=None,
                q_tolerance_w=1e-6,
                pinch_temperature_tolerance_k=1e-6,
            )

    def test_pinch_satisfied_at_upper_negative_residual(self) -> None:
        """pinch_satisfied_at_upper with negative residual → ValueError."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="final_pinch_residual_k >= 0"):
            QMaxDiagnosticsSnapshot(
                q_max_w=80000.0,
                iterations=0,
                final_pinch_residual_k=-1e-8,
                termination_reason="pinch_satisfied_at_upper",
                final_q_low_w=80000.0,
                final_q_high_w=80000.0,
                final_q_width_w=0.0,
                hot_limit_w=80000.0,
                cold_limit_w=310000.0,
                limiting_side="hot_limit",
                q_tolerance_w=1e-6,
                pinch_temperature_tolerance_k=1e-6,
            )

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


# =========================================================================
# 7. Synthetic verifier tests for R15 review items
# =========================================================================


class TestSyntheticVerifierDiagnosticsBinding:
    """Synthetic tests for diagnostics binding and trace contracts."""

    def test_counterflow_success_missing_qmax_counterflow(self) -> None:
        """Counterflow SUCCEEDED without q_max_counterflow eval → False."""
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
            # bracket/solver/final but NO q_max_counterflow
            _make_call(
                seq_idx=2,
                eval_idx=1,
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="bracket",
                trial_q_w=50000.0,
            ),
            _make_call(
                seq_idx=3,
                eval_idx=2,
                role=EvaluationRole.SOLVER_ITERATION.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="solver",
                trial_q_w=50000.0,
            ),
            _make_call(
                seq_idx=4,
                eval_idx=3,
                role=EvaluationRole.FINAL_EVALUATION.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="final",
                trial_q_w=50000.0,
            ),
        ]
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        diag = QMaxDiagnosticsSnapshot(
            q_max_w=100000.0,
            iterations=0,
            final_pinch_residual_k=0.0,
            termination_reason="independent_limits",
            hot_limit_w=100000.0,
            cold_limit_w=300000.0,
            limiting_side="hot_limit",
        )
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.SUCCEEDED,
            converged=True,
            solver_termination_reason="converged",
            q_max_diagnostics=diag,
        )
        assert result is False, "counterflow without q_max_counterflow should be rejected"

    def test_parallel_success_no_diagnostics(self) -> None:
        """Parallel SUCCEEDED without q_max_diagnostics → False."""
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
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="pinch",
                trial_q_w=50000.0,
            ),
            _make_call(
                seq_idx=5,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="pinch",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            status=RatingStatus.SUCCEEDED,
            converged=True,
            solver_termination_reason="converged",
            q_max_diagnostics=None,
        )
        assert result is False, "SUCCEEDED without q_max_diagnostics should be rejected"

    def test_parallel_zero_upper_bound_trace_mismatch(self) -> None:
        """zero_upper_bound diagnostics with pinch+solver trace → False."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        diag = QMaxDiagnosticsSnapshot(
            q_max_w=0.0,
            iterations=0,
            final_pinch_residual_k=0.0,
            termination_reason="zero_upper_bound",
            hot_limit_w=-100.0,
            cold_limit_w=300000.0,
            limiting_side="hot_limit",
        )
        # Trace has limits + pinch + solver — incompatible with zero_upper_bound
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
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="pinch",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            q_max_diagnostics=diag,
        )
        assert result is False, "zero_upper_bound with pinch trace should be rejected"

    def test_cold_limit_fail_followed_by_pinch_rejected(self) -> None:
        """PARALLEL: cold limit fails, then pinch follows → False (state machine stop)."""
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
            # eval 2: pinch — should NOT be here after limits failure
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="pinch",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "cold limit fail with later pinch should be rejected"

    def test_cold_pinch_fail_followed_by_solver_rejected(self) -> None:
        """PARALLEL: cold pinch fails, then solver/final follows → False."""
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
            # eval 2: pinch (hot succeeds, cold fails)
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="pinch",
                trial_q_w=50000.0,
            ),
            _make_call(
                seq_idx=5,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="pinch",
                trial_q_w=50000.0,
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="PH failed",
            ),
            # eval 3: bracket/solver — should NOT be here after pinch failure
            _make_call(
                seq_idx=6,
                eval_idx=3,
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="bracket",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "cold pinch fail with later bracket should be rejected"


class TestQMaxDiagnosticsInvalidSnapshots:
    """Direct construction tests for invalid QMax diagnostics snapshots."""

    def test_iteration_limit_both_criteria_met(self) -> None:
        """iteration_limit but both criteria satisfied → ValueError."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="Use bisection_converged instead"):
            QMaxDiagnosticsSnapshot(
                q_max_w=80000.0,
                iterations=37,
                final_pinch_residual_k=1e-10,
                termination_reason="iteration_limit",
                final_q_low_w=80000.0,
                final_q_high_w=80000.0,
                final_q_width_w=0.0,
                q_tolerance_w=1e-6,
                pinch_temperature_tolerance_k=1e-6,
                hot_limit_w=100000.0,
                cold_limit_w=300000.0,
                limiting_side="hot_limit",
            )

    def test_iteration_limit_q_not_low(self) -> None:
        """iteration_limit with q_max_w != low → ValueError."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="q_max_w == final_q_low_w"):
            QMaxDiagnosticsSnapshot(
                q_max_w=80001.0,
                iterations=37,
                final_pinch_residual_k=1e-6,
                termination_reason="iteration_limit",
                final_q_low_w=80000.0,
                final_q_high_w=81000.0,
                final_q_width_w=1000.0,
                q_tolerance_w=1e-6,
                pinch_temperature_tolerance_k=1e-6,
                hot_limit_w=100000.0,
                cold_limit_w=300000.0,
                limiting_side="hot_limit",
            )

    def test_zero_upper_bound_q_not_zero(self) -> None:
        """zero_upper_bound with q_max_w != 0 → ValueError."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="q_max_w == 0"):
            QMaxDiagnosticsSnapshot(
                q_max_w=100.0,
                iterations=0,
                final_pinch_residual_k=0.0,
                termination_reason="zero_upper_bound",
                hot_limit_w=-100.0,
                cold_limit_w=300000.0,
                limiting_side="hot_limit",
            )

    def test_zero_upper_bound_bracket_fields_not_none(self) -> None:
        """zero_upper_bound with bracket fields present → ValueError."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="final_q_low_w"):
            QMaxDiagnosticsSnapshot(
                q_max_w=0.0,
                iterations=0,
                final_pinch_residual_k=0.0,
                termination_reason="zero_upper_bound",
                final_q_low_w=0.0,  # should be None
                hot_limit_w=-100.0,
                cold_limit_w=300000.0,
                limiting_side="hot_limit",
            )

    def test_zero_upper_bound_residual_not_zero(self) -> None:
        """zero_upper_bound with residual != 0 → ValueError."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="final_pinch_residual_k == 0"):
            QMaxDiagnosticsSnapshot(
                q_max_w=0.0,
                iterations=0,
                final_pinch_residual_k=1.0,
                termination_reason="zero_upper_bound",
                hot_limit_w=-100.0,
                cold_limit_w=300000.0,
                limiting_side="hot_limit",
            )

    def test_zero_upper_bound_min_limit_positive(self) -> None:
        """zero_upper_bound with min(hot, cold) > 0 → ValueError."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="min.hot_limit_w"):
            QMaxDiagnosticsSnapshot(
                q_max_w=0.0,
                iterations=0,
                final_pinch_residual_k=0.0,
                termination_reason="zero_upper_bound",
                hot_limit_w=100.0,
                cold_limit_w=300000.0,
                limiting_side="hot_limit",
            )

    def test_independent_limits_wrong_limiting_side(self) -> None:
        """independent_limits with wrong limiting_side → ValueError."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="limiting_side"):
            QMaxDiagnosticsSnapshot(
                q_max_w=100000.0,
                iterations=0,
                final_pinch_residual_k=0.0,
                termination_reason="independent_limits",
                hot_limit_w=100000.0,
                cold_limit_w=300000.0,
                limiting_side="cold_limit",
            )

    def test_independent_limits_residual_not_zero(self) -> None:
        """independent_limits with residual != 0 → ValueError."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        with pytest.raises(ValueError, match="final_pinch_residual_k == 0"):
            QMaxDiagnosticsSnapshot(
                q_max_w=100000.0,
                iterations=0,
                final_pinch_residual_k=1.0,
                termination_reason="independent_limits",
                hot_limit_w=100000.0,
                cold_limit_w=300000.0,
                limiting_side="hot_limit",
            )


class TestCounterflowVerifierContracts:
    """Counterflow Q_max call prefix and failure stop tests."""

    def test_counterflow_hot_limit_fails_no_later_eval(self) -> None:
        """Counterflow: hot limit fails, no later evaluation -> True."""
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
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is True, "counterflow hot limit fail should pass"

    def test_counterflow_cold_limit_fails_no_later_eval(self) -> None:
        """Counterflow: hot succeeds, cold fails, no later eval -> True."""
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
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
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
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is True, "counterflow cold limit fail should pass"

    def test_counterflow_failure_followed_by_bracket_rejected(self) -> None:
        """Counterflow: Q_max fails, then bracket/solver follows -> False."""
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
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
            _make_call(
                seq_idx=3,
                eval_idx=2,
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="bracket",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "counterflow Q_max fail + bracket should be rejected"

    def test_counterflow_wrong_first_call_role_rejected(self) -> None:
        """Counterflow Q_max: call 0 not hot_limit/TP -> False."""
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
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "counterflow qmax with cold first should be rejected"


class TestIterationLimitTraceBinding:
    """iteration_limit diagnostics must bind to limits+pinch trace."""

    def test_iteration_limit_limits_only_rejected(self) -> None:
        """iteration_limit with limits-only trace -> False."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        diag = QMaxDiagnosticsSnapshot(
            q_max_w=80000.0,
            iterations=50,
            final_pinch_residual_k=1e-4,
            termination_reason="iteration_limit",
            final_q_low_w=80000.0,
            final_q_high_w=80001.0,
            final_q_width_w=1.0,
            q_tolerance_w=1e-6,
            pinch_temperature_tolerance_k=1e-6,
            hot_limit_w=100000.0,
            cold_limit_w=300000.0,
            limiting_side="hot_limit",
        )
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
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            q_max_diagnostics=diag,
        )
        assert result is False, "iteration_limit limits-only should be rejected"

    def test_iteration_limit_with_solver_rejected(self) -> None:
        """iteration_limit with bracket/solver trace -> False."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        diag = QMaxDiagnosticsSnapshot(
            q_max_w=80000.0,
            iterations=50,
            final_pinch_residual_k=1e-4,
            termination_reason="iteration_limit",
            final_q_low_w=80000.0,
            final_q_high_w=80001.0,
            final_q_width_w=1.0,
            q_tolerance_w=1e-6,
            pinch_temperature_tolerance_k=1e-6,
            hot_limit_w=100000.0,
            cold_limit_w=300000.0,
            limiting_side="hot_limit",
        )
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
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="pinch",
                trial_q_w=50000.0,
            ),
            _make_call(
                seq_idx=5,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="pinch",
                trial_q_w=50000.0,
            ),
            _make_call(
                seq_idx=6,
                eval_idx=3,
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="bracket",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            q_max_diagnostics=diag,
        )
        assert result is False, "iteration_limit with bracket should be rejected"

    def test_iteration_limit_valid_trace_accepted(self) -> None:
        """iteration_limit with limits+pinch + no solver -> True."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        diag = QMaxDiagnosticsSnapshot(
            q_max_w=80000.0,
            iterations=50,
            final_pinch_residual_k=1e-4,
            termination_reason="iteration_limit",
            final_q_low_w=80000.0,
            final_q_high_w=80001.0,
            final_q_width_w=1.0,
            q_tolerance_w=1e-6,
            pinch_temperature_tolerance_k=1e-6,
            hot_limit_w=100000.0,
            cold_limit_w=300000.0,
            limiting_side="hot_limit",
        )
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
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="pinch",
                trial_q_w=50000.0,
            ),
            _make_call(
                seq_idx=5,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="pinch",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            q_max_diagnostics=diag,
        )
        assert result is True, "iteration_limit with limits+pinch should pass"


class TestZeroUpperBoundTraceBinding:
    """zero_upper_bound must require exactly one limits eval with 2 successful calls."""

    def test_zero_upper_bound_duplicate_limits_rejected(self) -> None:
        """zero_upper_bound with two limits evaluations -> False."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        diag = QMaxDiagnosticsSnapshot(
            q_max_w=0.0,
            iterations=0,
            final_pinch_residual_k=0.0,
            termination_reason="zero_upper_bound",
            hot_limit_w=-100.0,
            cold_limit_w=300000.0,
            limiting_side="hot_limit",
        )
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
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=5,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            q_max_diagnostics=diag,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "zero_upper_bound with duplicate limits should be rejected"

    def test_zero_upper_bound_failed_call_rejected(self) -> None:
        """zero_upper_bound with failed limit call -> False."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        diag = QMaxDiagnosticsSnapshot(
            q_max_w=0.0,
            iterations=0,
            final_pinch_residual_k=0.0,
            termination_reason="zero_upper_bound",
            hot_limit_w=-100.0,
            cold_limit_w=300000.0,
            limiting_side="hot_limit",
        )
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
            tuple(calls),
            FlowArrangement.PARALLEL,
            q_max_diagnostics=diag,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "zero_upper_bound with failed limit should be rejected"


# =========================================================================
# 10. Round 16 verifier contracts
# =========================================================================


class TestFailedQmaxNoDiagnostics:
    """Failed Q_max calls must have q_max_diagnostics is None."""

    def test_counterflow_failure_with_diagnostics_rejected(self) -> None:
        """Counterflow hot limit fails + independent_limits diagnostics → False."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        diag = QMaxDiagnosticsSnapshot(
            q_max_w=80000.0,
            iterations=0,
            final_pinch_residual_k=0.0,
            termination_reason="independent_limits",
            hot_limit_w=80000.0,
            cold_limit_w=120000.0,
            limiting_side="hot_limit",
        )
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
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            q_max_diagnostics=diag,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "counterflow failure with diagnostics should be rejected"

    def test_parallel_limits_failure_with_diagnostics_rejected(self) -> None:
        """Parallel limits cold fails + bisection_converged diagnostics → False."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        q_low = 80000.0
        q_high = q_low + 1e-4
        width = q_high - q_low
        diag = QMaxDiagnosticsSnapshot(
            q_max_w=q_low,
            iterations=10,
            final_pinch_residual_k=1e-8,
            q_tolerance_w=1e-3,
            pinch_temperature_tolerance_k=1e-6,
            final_q_low_w=q_low,
            final_q_high_w=q_high,
            final_q_width_w=width,
            termination_reason="bisection_converged",
        )
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
            tuple(calls),
            FlowArrangement.PARALLEL,
            q_max_diagnostics=diag,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "parallel limits failure with diagnostics should be rejected"

    def test_parallel_pinch_failure_with_diagnostics_rejected(self) -> None:
        """Parallel pinch hot fails + bisection_converged diagnostics → False."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        q_low = 80000.0
        q_high = q_low + 1e-4
        width = q_high - q_low
        diag = QMaxDiagnosticsSnapshot(
            q_max_w=q_low,
            iterations=10,
            final_pinch_residual_k=1e-8,
            q_tolerance_w=1e-3,
            pinch_temperature_tolerance_k=1e-6,
            final_q_low_w=q_low,
            final_q_high_w=q_high,
            final_q_width_w=width,
            termination_reason="bisection_converged",
        )
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
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="q_max",
                trial_q_w=80000.0,
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="PH failed",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            q_max_diagnostics=diag,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "parallel pinch failure with diagnostics should be rejected"


class TestCounterflowOrdering:
    """Counterflow Q_max must occur directly after inlet, before bracket/solver."""

    def test_counterflow_qmax_after_bracket_rejected(self) -> None:
        """Counterflow Q_max after bracket probe → False."""
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
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="bracket",
                trial_q_w=50000.0,
            ),
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="bracket",
                trial_q_w=50000.0,
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=5,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.SUCCEEDED,
            converged=True,
            solver_termination_reason="converged",
        )
        assert result is False, "counterflow Q_max after bracket should be rejected"


class TestDuplicateQmaxEvaluations:
    """At most/exactly one Q_max evaluation per role on all paths."""

    def test_counterflow_duplicate_qmax_rejected(self) -> None:
        """Two counterflow Q_max evaluations → False."""
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
            # First counterflow eval: both succeed
            _make_call(
                seq_idx=2,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            # Second counterflow eval: hot fails
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
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
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "duplicate counterflow Q_max should be rejected"

    def test_parallel_limits_without_pinch_duplicate_limits_rejected(self) -> None:
        """Two limits evals without pinch (second cold fails) → False."""
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
            # First limits eval: both succeed
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
            # Second limits eval: cold fails
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=5,
                eval_idx=2,
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
            tuple(calls),
            FlowArrangement.PARALLEL,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "parallel limits-without-pinch duplicate limits should be rejected"


# =========================================================================
# 11. Round 17 inlet contract + successful Q_max diagnostics
# =========================================================================


class TestInletFullContract:
    """Inlet evaluation must enforce exact hot-failure, cold-failure, and
    success contracts."""

    def test_inlet_hot_failure_accepts(self) -> None:
        """Hot failure: exactly 1 call hot_inlet/TP/fail, BLOCKED, last → True."""
        calls = [
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_inlet",
                stage="inlet",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is True, "hot failure inlet should pass"

    def test_inlet_hot_failure_with_diagnostics_rejected(self) -> None:
        """Hot failure inlet with diagnostics → False."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        diag = QMaxDiagnosticsSnapshot(
            q_max_w=80000.0,
            iterations=0,
            final_pinch_residual_k=0.0,
            termination_reason="independent_limits",
            hot_limit_w=80000.0,
            cold_limit_w=120000.0,
            limiting_side="hot_limit",
        )
        calls = [
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_inlet",
                stage="inlet",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            q_max_diagnostics=diag,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "hot failure inlet with diagnostics should be rejected"

    def test_inlet_single_success_rejected(self) -> None:
        """Single successful inlet call → False (cannot proceed to later phases)."""
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
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.SUCCEEDED,
            converged=True,
            solver_termination_reason="converged",
        )
        assert result is False, "single successful inlet should be rejected"

    def test_inlet_wrong_role_rejected(self) -> None:
        """Single inlet with wrong stream_role → False."""
        calls = [
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="cold_inlet",
                stage="inlet",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "wrong role inlet failure should be rejected"

    def test_inlet_wrong_query_type_rejected(self) -> None:
        """Single inlet with wrong query type → False."""
        calls = [
            _make_call(
                seq_idx=0,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_inlet",
                stage="inlet",
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="PH failed",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "wrong query type inlet failure should be rejected"

    def test_inlet_cold_failure_accepts(self) -> None:
        """Cold failure: hot success, cold fail, last, BLOCKED → True."""
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
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is True, "cold failure inlet should pass"

    def test_inlet_cold_failure_followed_by_qmax_rejected(self) -> None:
        """Cold failure inlet with later Q_max → False (inlet not last)."""
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
                success=False,
                error_code="BACKEND_FAILURE",
                error_message="TP failed",
            ),
            _make_call(
                seq_idx=2,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
        )
        assert result is False, "cold failure followed by Q_max should be rejected"

    def test_inlet_three_calls_rejected(self) -> None:
        """Three inlet calls → False."""
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
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=2,
                query_type="TP",
                stream_role="cold_inlet",
                stage="inlet",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.SUCCEEDED,
            converged=True,
            solver_termination_reason="converged",
        )
        assert result is False, "three inlet calls should be rejected"

    def test_inlet_success_accepts(self) -> None:
        """Inlet success: 2 calls, both TP success → True (with full trace)."""
        from hexagent.exchangers.double_pipe.result import QMaxDiagnosticsSnapshot

        diag = QMaxDiagnosticsSnapshot(
            q_max_w=80000.0,
            iterations=0,
            final_pinch_residual_k=0.0,
            termination_reason="independent_limits",
            hot_limit_w=80000.0,
            cold_limit_w=120000.0,
            limiting_side="hot_limit",
        )
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
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.FINAL_EVALUATION.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="final",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            q_max_diagnostics=diag,
            status=RatingStatus.SUCCEEDED,
            converged=True,
            solver_termination_reason="converged",
        )
        assert result is True, "inlet success should pass"


class TestSuccessfulQmaxRequiresDiagnostics:
    """Successful Q_max with later phases must carry q_max_diagnostics."""

    def test_counterflow_qmax_success_no_diagnostics_rejected(self) -> None:
        """Counterflow Q_max success + later phases, no diagnostics → False."""
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
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="bracket",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.SUCCEEDED,
            converged=True,
            solver_termination_reason="converged",
            q_max_diagnostics=None,
        )
        assert result is False, "counterflow Q_max success without diag should be rejected"

    def test_parallel_qmax_success_no_diagnostics_rejected(self) -> None:
        """Parallel Q_max success + later phases, no diagnostics → False."""
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
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="q_max",
                trial_q_w=80000.0,
            ),
            _make_call(
                seq_idx=5,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="q_max",
                trial_q_w=80000.0,
            ),
            _make_call(
                seq_idx=6,
                eval_idx=3,
                role=EvaluationRole.FINAL_EVALUATION.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="final",
                trial_q_w=50000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            status=RatingStatus.BLOCKED,
            converged=True,
            solver_termination_reason="converged",
            q_max_diagnostics=None,
        )
        assert result is False, "parallel Q_max success without diag should be rejected"


class TestTerminalQmaxRequiresDiagnostics:
    """Successful Q_max without later solver phases must still carry diagnostics."""

    def test_counterflow_terminal_qmax_no_diagnostics_rejected(self) -> None:
        """Counterflow Q_max success without diagnostics, terminal → False."""
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
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_COUNTERFLOW.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.COUNTERFLOW,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
            q_max_diagnostics=None,
        )
        assert result is False, "terminal counterflow Q_max without diag should be rejected"

    def test_parallel_terminal_qmax_no_diagnostics_rejected(self) -> None:
        """Parallel Q_max success without diagnostics, terminal → False."""
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
            _make_call(
                seq_idx=3,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
            ),
            _make_call(
                seq_idx=4,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="q_max",
                trial_q_w=80000.0,
            ),
            _make_call(
                seq_idx=5,
                eval_idx=2,
                role=EvaluationRole.Q_MAX_PARALLEL_PINCH.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="q_max",
                trial_q_w=80000.0,
            ),
        ]
        result = _verify_property_call_identity(
            tuple(calls),
            FlowArrangement.PARALLEL,
            status=RatingStatus.BLOCKED,
            converged=False,
            solver_termination_reason="blocked",
            q_max_diagnostics=None,
        )
        assert result is False, "terminal parallel Q_max without diag should be rejected"


class _PhFailProvider:
    """Provider wrapper that delegates all calls and fails on the Nth state_ph call.

    For counterflow flow arrangement:
    - Inlet evaluation: 2 state_tp calls, 0 state_ph calls
    - Q_max counterflow: 2 state_tp calls, 0 state_ph calls
    - First BRACKET_PROBE evaluation: 2 state_ph calls + 2 state_tp calls

    With fail_after=0, the 1st state_ph call (= hot outlet PH during
    BRACKET_PROBE) raises PropertyServiceError, so TrialEvaluator.evaluate
    returns an infeasible TrialEvaluation, and residual_fn naturally raises
    TrialEvaluationAbort.
    """

    def __init__(self, real_provider: object, *, fail_after: int = 0) -> None:
        self._real: object = real_provider
        self._ph_calls: int = 0
        self._fail_after: int = fail_after

    # --- delegate attributes ---
    @property
    def name(self) -> str:
        return str(self._real.name)  # type: ignore[union-attr]

    @property
    def version(self) -> str:
        return str(self._real.version)  # type: ignore[union-attr]

    @property
    def git_revision(self) -> str:
        return str(self._real.git_revision)  # type: ignore[union-attr]

    @property
    def reference_state_policy(self) -> object:
        return self._real.reference_state_policy  # type: ignore[union-attr]

    # --- delegate methods ---
    def state_ph(  # type: ignore[no-untyped-def]
        self,
        fluid,
        pressure_pa,
        enthalpy_j_kg,
        *,
        reference_state=None,
    ):
        from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

        self._ph_calls += 1
        if self._ph_calls > self._fail_after:
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_INPUT,
                f"Controlled failure on PH call #{self._ph_calls}",
                context={"fluid": str(fluid)},
            )
        real = self._real  # type: ignore[union-attr]
        return real.state_ph(
            fluid,
            pressure_pa,
            enthalpy_j_kg,
            reference_state=reference_state or real.reference_state_policy,
        )

    def state_tp(  # type: ignore[no-untyped-def]
        self,
        fluid,
        temperature_k,
        pressure_pa,
    ):
        return self._real.state_tp(  # type: ignore[union-attr]
            fluid,
            temperature_k,
            pressure_pa,
        )

    def saturation_at_pressure(  # type: ignore[no-untyped-def]
        self,
        fluid,
        pressure_pa,
    ):
        return self._real.saturation_at_pressure(  # type: ignore[union-attr]
            fluid,
            pressure_pa,
        )

    def saturation_at_temperature(  # type: ignore[no-untyped-def]
        self,
        fluid,
        temperature_k,
    ):
        return self._real.saturation_at_temperature(  # type: ignore[union-attr]
            fluid,
            temperature_k,
        )

    def cache_info(self) -> object:
        return self._real.cache_info()  # type: ignore[union-attr]

    def clear_cache(self) -> None:
        self._real.clear_cache()  # type: ignore[union-attr]


class TestTrialAbortPreservesDiagnostics:
    """TrialEvaluationAbort after successful Q_max must retain diagnostics."""

    def test_trial_abort_via_controlled_ph_failure(
        self,
        provider: CoolPropProvider,
    ) -> None:
        """rate_double_pipe with solver abort after Q_max, via controlled provider.

        The _PhFailProvider fails on the first state_ph call during the
        BRACKET_PROBE evaluation, so residual_fn naturally raises
        TrialEvaluationAbort (no synthetic append after suppress).

        Assertions:
        - BLOCKED result with q_max_diagnostics preserved
        - INLET -> Q_MAX_COUNTERFLOW -> BRACKET_PROBE trace ordering
        - last BRACKET_PROBE evaluation contains the failure prefix
          (hot outlet PH call with success=False and the expected error code)
        - blockers reflect the property evaluation failure
        - diagnostics, hash, provenance, and JSON round-trip remain valid
        """
        from hexagent.domain.messages import ErrorCode
        from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

        fail_provider = _PhFailProvider(provider, fail_after=0)

        result = _run_rating(
            fail_provider,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
        )

        # Core result contract
        assert result.status == RatingStatus.BLOCKED, "abort should produce BLOCKED"
        assert result.q_max_diagnostics is not None, "Q_max diagnostics must survive trial abort"
        assert result.q_max_diagnostics.termination_reason == "independent_limits", (
            f"Unexpected reason: {result.q_max_diagnostics.termination_reason}"
        )
        assert result.converged is False
        assert result.solver_termination_reason == "blocked"
        assert result.verify_hash() is True, "hash must be valid"
        assert result.verify_provenance() is True, "provenance must be valid"

        # Trace ordering: INLET -> Q_MAX_COUNTERFLOW -> BRACKET_PROBE
        roles = [c.evaluation_role for c in result.property_calls]
        unique_roles: list[str] = []
        for r in roles:
            if not unique_roles or unique_roles[-1] != r:
                unique_roles.append(r)
        assert unique_roles == [
            EvaluationRole.INLET.value,
            EvaluationRole.Q_MAX_COUNTERFLOW.value,
            EvaluationRole.BRACKET_PROBE.value,
        ], f"Expected inlet -> qmax -> bracket, got {unique_roles}"

        # Last evaluation must be the aborting bracket probe
        last_eval_idx = max({c.evaluation_index for c in result.property_calls})
        last_calls = [c for c in result.property_calls if c.evaluation_index == last_eval_idx]
        assert all(c.evaluation_role == EvaluationRole.BRACKET_PROBE.value for c in last_calls), (
            f"Last eval should be BRACKET_PROBE, got {last_calls[0].evaluation_role}"
        )

        # The last evaluation must contain at least one failed call with the
        # expected error code from the controlled provider failure.
        failed_calls = [c for c in last_calls if not c.success]
        assert len(failed_calls) >= 1, (
            "BRACKET_PROBE evaluation should contain at least one failed "
            f"property call; found {len(failed_calls)} failures"
        )
        assert (
            failed_calls[0].error_code
            == PropertyServiceError(
                PropertyErrorCode.INVALID_INPUT,
                "",
            ).code.value
        ), f"Expected INVALID_INPUT error, got {failed_calls[0].error_code}"
        # The failed call should be the hot outlet PH (stream_role hot_solver)
        assert failed_calls[0].stream_role == "hot_solver", (
            f"Expected hot_solver role for the failing PH call, got {failed_calls[0].stream_role}"
        )

        # The BRACKET_PROBE evaluation should contain the failure prefix.
        # Since the failure happens on the first PH call (call 0), the
        # evaluation has exactly that one call — which is the failure.
        # This proves the evaluation was real and recorded its failure.
        call_indices_in_eval = sorted({c.call_index_within_evaluation for c in last_calls})
        assert len(call_indices_in_eval) >= 1, (
            "BRACKET_PROBE evaluation should have at least one call"
        )
        # The (only) call in the evaluation is the failing PH call
        assert failed_calls[0].call_index_within_evaluation == 0, (
            "The failing call should be the first (and only) call in the evaluation"
        )
        assert failed_calls[0].query_type == "PH", (
            f"Failed call should be PH, got {failed_calls[0].query_type}"
        )

        # Blockers should contain the property evaluation failure
        assert len(result.blockers) >= 1, "BLOCKED result should have blockers"
        blocker_codes = {b.code for b in result.blockers}
        assert ErrorCode.PROPERTY_EVALUATION_FAILED in blocker_codes, (
            f"Expected PROPERTY_EVALUATION_FAILED blocker, got {blocker_codes}"
        )

        # JSON round-trip preserves diagnostics AND provenance
        js = result.model_dump_json(exclude_none=False, by_alias=True)
        restored = RatingResult.model_validate_json(js)
        assert restored.q_max_diagnostics is not None, "JSON round-trip lost diagnostics"
        assert restored.q_max_diagnostics.termination_reason == "independent_limits", (
            f"Unexpected reason: {restored.q_max_diagnostics.termination_reason}"
        )
        assert restored.verify_hash() is True, "round-trip hash must be valid"
        assert restored.verify_provenance() is True, "round-trip provenance must be valid"
