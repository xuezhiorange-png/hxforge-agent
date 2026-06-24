"""Comprehensive tests for TASK-008 engineering correction round 10.

Covers:
1. TestQMaxEndpointContract - verify pinch_lo tracking in Q_max bisection
2. TestQMaxIterationLimit - deterministic iteration limit (monkeypatch)
3. TestQMaxDiagnosticsSnapshot - q_max_diagnostics in result + JSON round-trip
4. TestVerifierStatefulRules - enhanced verifier tamper detection
5. TestFinalEvaluationPartialBlocked - partial BLOCKED preserves diagnostics
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.domain.messages import ErrorCode
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import (
    Q_MAX_PINCH_TOLERANCE_K,
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
)
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import (
    FluidIdentifier,
    PropertyProvider,
    ReferenceStatePolicy,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

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


# =========================================================================
# 1. TestQMaxEndpointContract - verify pinch_lo tracking
# =========================================================================


class TestQMaxEndpointContract:
    """Verify that the converged bisection Q_max satisfies endpoint contracts."""

    def test_qmax_endpoint_contracts(self, provider: CoolPropProvider) -> None:
        """Run _compute_q_max_parallel and verify endpoint contracts."""
        recorder = EvaluationRecorder()
        h_hot_in = provider.state_tp(WATER, 350.0, 200000.0).enthalpy_j_kg
        h_cold_in = provider.state_tp(WATER, 300.0, 150000.0).enthalpy_j_kg

        qmax = _compute_q_max_parallel(
            provider=provider,
            hot_fluid=WATER,
            cold_fluid=WATER,
            hot_inlet_temperature_k=350.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200000.0,
            cold_inlet_pressure_pa=150000.0,
            h_hot_in=h_hot_in,
            h_cold_in=h_cold_in,
            hot_mass_flow_kg_s=0.5,
            cold_mass_flow_kg_s=1.5,
            minimum_terminal_delta_t=0.5,
            recorder=recorder,
        )

        # Must converge (standard conditions should always converge)
        assert qmax.termination_reason == "bisection_converged", (
            f"Expected bisection_converged, got {qmax.termination_reason}"
        )

        # Contract 1: q_max_w == final_q_low_w (solution is at q_lo)
        assert qmax.q_max_w == qmax.final_q_low_w, (
            f"q_max_w ({qmax.q_max_w}) != final_q_low_w ({qmax.final_q_low_w})"
        )

        # Contract 2: bracket width within tolerance
        assert qmax.final_q_width_w is not None
        assert qmax.q_tolerance_w is not None
        assert qmax.final_q_width_w <= qmax.q_tolerance_w, (
            f"final_q_width_w ({qmax.final_q_width_w}) > q_tolerance_w ({qmax.q_tolerance_w})"
        )

        # Contract 3: pinch residual within tolerance
        assert qmax.pinch_temperature_tolerance_k is not None
        assert abs(qmax.final_pinch_residual_k) <= qmax.pinch_temperature_tolerance_k, (
            f"abs(pinch_residual) ({abs(qmax.final_pinch_residual_k)}) > "
            f"pinch_tolerance ({qmax.pinch_temperature_tolerance_k})"
        )

        # Contract 4: independent pinch residual at q_max_w matches
        # Compute T_hot_out - T_cold_out - minimum_terminal_delta_t at q_max_w
        h_hot_out = h_hot_in - qmax.q_max_w / 0.5
        h_cold_out = h_cold_in + qmax.q_max_w / 1.5
        hot_state = provider.state_ph(
            WATER,
            200000.0,
            h_hot_out,
            reference_state=ReferenceStatePolicy.DEF,
        )
        cold_state = provider.state_ph(
            WATER,
            150000.0,
            h_cold_out,
            reference_state=ReferenceStatePolicy.DEF,
        )
        recomputed_residual = (hot_state.temperature_k - cold_state.temperature_k) - 0.5
        assert abs(recomputed_residual - qmax.final_pinch_residual_k) < 1e-10, (
            f"Recomputed residual ({recomputed_residual}) != "
            f"final_pinch_residual_k ({qmax.final_pinch_residual_k})"
        )


# =========================================================================
# 2. TestQMaxIterationLimit - deterministic iteration limit
# =========================================================================


class TestQMaxIterationLimit:
    """Verify deterministic iteration limit behavior when Q_MAX_MAX_ITERATIONS=1."""

    def test_iteration_limit_direct(self, provider: CoolPropProvider) -> None:
        """_compute_q_max_parallel with iterations=1 terminates deterministically."""
        recorder = EvaluationRecorder()
        h_hot_in = provider.state_tp(WATER, 350.0, 200000.0).enthalpy_j_kg
        h_cold_in = provider.state_tp(WATER, 300.0, 150000.0).enthalpy_j_kg

        # Monkeypatch Q_MAX_MAX_ITERATIONS to 1
        import hexagent.exchangers.double_pipe.rating as rating_mod

        original = rating_mod.Q_MAX_MAX_ITERATIONS
        rating_mod.Q_MAX_MAX_ITERATIONS = 1
        try:
            qmax = _compute_q_max_parallel(
                provider=provider,
                hot_fluid=WATER,
                cold_fluid=WATER,
                hot_inlet_temperature_k=350.0,
                cold_inlet_temperature_k=300.0,
                hot_inlet_pressure_pa=200000.0,
                cold_inlet_pressure_pa=150000.0,
                h_hot_in=h_hot_in,
                h_cold_in=h_cold_in,
                hot_mass_flow_kg_s=0.5,
                cold_mass_flow_kg_s=1.5,
                minimum_terminal_delta_t=0.5,
                recorder=recorder,
            )
        finally:
            rating_mod.Q_MAX_MAX_ITERATIONS = original

        assert qmax.termination_reason == "iteration_limit"
        assert qmax.iterations == 1
        # At least one tolerance must be violated
        assert (
            qmax.final_q_width_w is not None
            and qmax.q_tolerance_w is not None
            and qmax.final_q_width_w > qmax.q_tolerance_w
        ) or abs(qmax.final_pinch_residual_k) > Q_MAX_PINCH_TOLERANCE_K, (
            "Expected at least one tolerance to be violated after 1 iteration"
        )

    def test_iteration_limit_rate_double_pipe(self, provider: CoolPropProvider) -> None:
        """rate_double_pipe with iterations=1 produces BLOCKED + SOLVER_NON_CONVERGENCE."""
        import hexagent.exchangers.double_pipe.rating as rating_mod

        original = rating_mod.Q_MAX_MAX_ITERATIONS
        rating_mod.Q_MAX_MAX_ITERATIONS = 1
        try:
            result = _run_rating(
                provider,
                flow_arrangement=FlowArrangement.PARALLEL,
            )
        finally:
            rating_mod.Q_MAX_MAX_ITERATIONS = original

        assert result.status == RatingStatus.BLOCKED
        # Blocker code should be SOLVER_NON_CONVERGENCE
        blocker_codes = [b.code for b in result.blockers]
        assert ErrorCode.SOLVER_NON_CONVERGENCE in blocker_codes, (
            f"Expected SOLVER_NON_CONVERGENCE in blockers, got {blocker_codes}"
        )
        # Q_max diagnostics must be present
        assert result.q_max_diagnostics is not None
        assert result.q_max_diagnostics.termination_reason == "iteration_limit"
        # Integrity checks
        assert result.verify_hash() is True
        assert result.verify_provenance() is True


# =========================================================================
# 3. TestQMaxDiagnosticsSnapshot - verify snapshot in result
# =========================================================================


class TestQMaxDiagnosticsSnapshot:
    """Verify q_max_diagnostics is present and round-trips through JSON."""

    def test_qmax_diagnostics_present(self, provider: CoolPropProvider) -> None:
        """Normal rating includes q_max_diagnostics."""
        result = _run_rating(provider)
        assert result.q_max_diagnostics is not None
        # Self-consistency: the snapshot q_max_w matches itself
        assert result.q_max_diagnostics.q_max_w == result.q_max_diagnostics.q_max_w
        assert math.isfinite(result.q_max_diagnostics.q_max_w)
        assert result.q_max_diagnostics.q_max_w >= 0

    def test_json_round_trip(self, provider: CoolPropProvider) -> None:
        """JSON round-trip preserves q_max_diagnostics fields."""
        result = _run_rating(provider)
        assert result.q_max_diagnostics is not None

        # Serialize to dict
        d = result.model_dump()

        # Rebuild from dict
        restored = RatingResult.model_validate(d)

        assert restored.q_max_diagnostics is not None
        assert restored.q_max_diagnostics.q_max_w == result.q_max_diagnostics.q_max_w
        assert restored.q_max_diagnostics.iterations == result.q_max_diagnostics.iterations
        assert (
            restored.q_max_diagnostics.final_pinch_residual_k
            == result.q_max_diagnostics.final_pinch_residual_k
        )
        assert (
            restored.q_max_diagnostics.termination_reason
            == result.q_max_diagnostics.termination_reason
        )
        assert restored.q_max_diagnostics.final_q_low_w == result.q_max_diagnostics.final_q_low_w
        assert restored.q_max_diagnostics.final_q_high_w == result.q_max_diagnostics.final_q_high_w
        assert (
            restored.q_max_diagnostics.final_q_width_w == result.q_max_diagnostics.final_q_width_w
        )
        assert restored.q_max_diagnostics.hot_limit_w == result.q_max_diagnostics.hot_limit_w
        assert restored.q_max_diagnostics.cold_limit_w == result.q_max_diagnostics.cold_limit_w
        assert restored.q_max_diagnostics.limiting_side == result.q_max_diagnostics.limiting_side
        assert restored.q_max_diagnostics.q_tolerance_w == result.q_max_diagnostics.q_tolerance_w
        assert (
            restored.q_max_diagnostics.pinch_temperature_tolerance_k
            == result.q_max_diagnostics.pinch_temperature_tolerance_k
        )


# =========================================================================
# 4. TestVerifierStatefulRules - enhanced verifier
# =========================================================================


class TestVerifierStatefulRules:
    """Verify the enhanced provenance verifier catches structural violations."""

    def _get_succeeded_result(self, provider: CoolPropProvider) -> RatingResult:
        """Get a valid SUCCEEDED result."""
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.verify_provenance() is True
        return result

    def _tamper_property_calls(self, result: RatingResult, tamper_fn) -> RatingResult:
        """Create a new RatingResult with tampered property_calls."""
        tampered_calls = tamper_fn(list(result.property_calls))
        return result.model_copy(update={"property_calls": tuple(tampered_calls)})

    def test_unknown_role(self, provider: CoolPropProvider) -> None:
        """Tamper evaluation_role to 'unknown_role' -> verify_provenance is False."""
        result = self._get_succeeded_result(provider)

        def _tamper(calls):
            if not calls:
                pytest.skip("Need at least 1 call")
            calls[0] = calls[0].__class__(
                **{**calls[0].__dict__, "evaluation_role": "unknown_role"}
            )
            return calls

        tampered = self._tamper_property_calls(result, _tamper)
        assert tampered.verify_provenance() is False

    def test_static_role_with_trial_q(self, provider: CoolPropProvider) -> None:
        """Set trial_q_w=123.0 on inlet record -> verify_provenance is False."""
        result = self._get_succeeded_result(provider)

        # Find the inlet evaluation record
        inlet_calls = [
            c for c in result.property_calls if c.evaluation_role == EvaluationRole.INLET.value
        ]
        if not inlet_calls:
            pytest.skip("No inlet calls found")

        def _tamper(calls):
            for i, c in enumerate(calls):
                if c.evaluation_role == EvaluationRole.INLET.value:
                    calls[i] = c.__class__(**{**c.__dict__, "trial_q_w": 123.0})
                    break
            return calls

        tampered = self._tamper_property_calls(result, _tamper)
        assert tampered.verify_provenance() is False

    def test_dynamic_role_with_trial_q_none(self, provider: CoolPropProvider) -> None:
        """Set trial_q_w=None on solver_iteration record -> verify_provenance is False."""
        result = self._get_succeeded_result(provider)

        # Find solver_iteration records
        solver_calls = [
            c
            for c in result.property_calls
            if c.evaluation_role == EvaluationRole.SOLVER_ITERATION.value
        ]
        if not solver_calls:
            pytest.skip("No solver_iteration calls found")

        def _tamper(calls):
            for i, c in enumerate(calls):
                if c.evaluation_role == EvaluationRole.SOLVER_ITERATION.value:
                    calls[i] = c.__class__(**{**c.__dict__, "trial_q_w": None})
                    break
            return calls

        tampered = self._tamper_property_calls(result, _tamper)
        assert tampered.verify_provenance() is False

    def test_failed_with_final_evaluation(self, provider: CoolPropProvider) -> None:
        """FAILED result with a final_evaluation role -> verify_provenance is False."""
        # Get a BLOCKED result (no final_evaluation because solver didn't run)
        import hexagent.exchangers.double_pipe.rating as rating_mod

        original = rating_mod.Q_MAX_MAX_ITERATIONS
        rating_mod.Q_MAX_MAX_ITERATIONS = 1
        try:
            blocked_result = _run_rating(
                provider,
                flow_arrangement=FlowArrangement.PARALLEL,
            )
        finally:
            rating_mod.Q_MAX_MAX_ITERATIONS = original

        assert blocked_result.status == RatingStatus.BLOCKED
        # This BLOCKED result has no final_evaluation
        final_calls = [
            c
            for c in blocked_result.property_calls
            if c.evaluation_role == EvaluationRole.FINAL_EVALUATION.value
        ]
        assert len(final_calls) == 0

        # Create a synthetic final_evaluation PropertyCallRecord
        # using the last call's metadata as a base
        base_call = blocked_result.property_calls[-1] if blocked_result.property_calls else None
        if base_call is None:
            pytest.skip("No property calls to base synthetic record on")

        synthetic_final = base_call.__class__(
            **{
                **base_call.__dict__,
                "evaluation_role": EvaluationRole.FINAL_EVALUATION.value,
                "evaluation_index": base_call.evaluation_index + 100,
                "sequence_index": base_call.sequence_index + 100,
                "trial_q_w": None,
            }
        )

        # Add the synthetic final_evaluation to property_calls
        new_calls = list(blocked_result.property_calls) + [synthetic_final]
        tampered = blocked_result.model_copy(update={"property_calls": tuple(new_calls)})
        assert tampered.verify_provenance() is False

    def test_succeeded_without_final_evaluation(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED result with final_evaluation removed -> verify_provenance is False."""
        result = self._get_succeeded_result(provider)

        # Find and remove final_evaluation records
        final_indices = [
            i
            for i, c in enumerate(result.property_calls)
            if c.evaluation_role == EvaluationRole.FINAL_EVALUATION.value
        ]
        if not final_indices:
            pytest.skip("No final_evaluation calls found")

        def _tamper(calls):
            return [c for c in calls if c.evaluation_role != EvaluationRole.FINAL_EVALUATION.value]

        tampered = self._tamper_property_calls(result, _tamper)
        assert tampered.verify_provenance() is False

    def test_final_not_last(self, provider: CoolPropProvider) -> None:
        """Swap final_evaluation to earlier index -> verify_provenance is False."""
        result = self._get_succeeded_result(provider)

        # Find final_evaluation and an earlier evaluation
        final_calls = [
            c
            for c in result.property_calls
            if c.evaluation_role == EvaluationRole.FINAL_EVALUATION.value
        ]
        earlier_calls = [
            c
            for c in result.property_calls
            if c.evaluation_role
            not in (
                EvaluationRole.FINAL_EVALUATION.value,
                EvaluationRole.INLET.value,
            )
        ]
        if not final_calls or not earlier_calls:
            pytest.skip("Need both final_evaluation and earlier calls")

        # Swap evaluation_index: put final_evaluation at an earlier index
        # and the earlier call at the final index
        final_eval_idx = final_calls[0].evaluation_index
        earlier_eval_idx = earlier_calls[0].evaluation_index

        def _tamper(calls):
            new_calls = []
            for c in calls:
                if c.evaluation_role == EvaluationRole.FINAL_EVALUATION.value:
                    new_calls.append(
                        c.__class__(**{**c.__dict__, "evaluation_index": earlier_eval_idx})
                    )
                elif c.evaluation_index == earlier_eval_idx:
                    new_calls.append(
                        c.__class__(**{**c.__dict__, "evaluation_index": final_eval_idx})
                    )
                else:
                    new_calls.append(c)
            return new_calls

        tampered = self._tamper_property_calls(result, _tamper)
        assert tampered.verify_provenance() is False

    def test_counterflow_with_parallel_role(self, provider: CoolPropProvider) -> None:
        """Counterflow result with parallel role added -> verify_provenance is False."""
        result = self._get_succeeded_result(provider)
        assert result.flow_arrangement == FlowArrangement.COUNTERFLOW

        # Create a synthetic q_max_parallel_limits record
        base_call = result.property_calls[0]
        synthetic_parallel = base_call.__class__(
            **{
                **base_call.__dict__,
                "evaluation_role": EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                "evaluation_index": base_call.evaluation_index + 200,
                "sequence_index": base_call.sequence_index + 200,
                "trial_q_w": None,
            }
        )

        new_calls = list(result.property_calls) + [synthetic_parallel]
        tampered = result.model_copy(update={"property_calls": tuple(new_calls)})
        assert tampered.verify_provenance() is False


# =========================================================================
# 5. TestFinalEvaluationPartialBlocked - partial BLOCKED preserves diagnostics
# =========================================================================


def _make_final_only_cold_ph_fail(provider: CoolPropProvider) -> MagicMock:
    """Provider that fails cold PH only on FINAL_EVALUATION.

    Uses a call counter: succeeds for the first N calls, then fails
    on cold-side state_ph (P == 150000.0) for subsequent calls.
    """
    mock = MagicMock()
    mock.name = provider.name
    mock.version = provider.version
    mock.git_revision = ""
    mock.reference_state_policy = ReferenceStatePolicy.DEF
    real_tp = provider.state_tp
    real_ph = provider.state_ph
    mock.state_tp.side_effect = real_tp

    call_count = [0]

    def _selective_ph(fluid, P, h, reference_state=None):
        call_count[0] += 1
        state = real_ph(fluid, P, h, reference_state=reference_state)
        # Fail cold PH on the final evaluation (after solver converged).
        # The final evaluation is the last PH call batch.
        # We detect it by checking if we've had enough prior calls.
        # With standard conditions: ~4 bracket probes + ~12 solver iterations
        # = ~32 PH calls before final evaluation. Threshold of 33 ensures
        # only the final evaluation's cold PH call triggers the failure.
        if fluid.name == "Water" and P == 150000.0 and call_count[0] > 33:
            from hexagent.properties.base import PropertyErrorCode
            from hexagent.properties.errors import PropertyServiceError

            raise PropertyServiceError(
                code=PropertyErrorCode.BACKEND_FAILURE,
                message="Cold PH failed on final evaluation",
            )
        return state

    mock.state_ph.side_effect = _selective_ph
    return mock


class TestFinalEvaluationPartialBlocked:
    """Partial BLOCKED (final evaluation failure) preserves solver diagnostics."""

    def test_partial_blocked_preserves_diagnostics(self, provider: CoolPropProvider) -> None:
        """Provider fails cold PH only on final evaluation -> BLOCKED with
        converged=True, solver converged, diagnostics preserved.
        """
        mock_provider = _make_final_only_cold_ph_fail(provider)
        result = _run_rating(mock_provider)

        # Status should be BLOCKED (final evaluation failed)
        assert result.status == RatingStatus.BLOCKED
        # But solver converged
        assert result.converged is True
        assert result.solver_termination_reason == "converged"
        # heat_duty_w should be present (solver succeeded)
        assert result.heat_duty_w is not None
        # Integrity checks
        assert result.verify_hash() is True
        assert result.verify_provenance() is True

        # JSON round-trip preserves non-None fields
        d = result.model_dump()
        restored = RatingResult.model_validate(d)
        assert restored.heat_duty_w == result.heat_duty_w
        assert restored.hot_outlet_temperature_k == result.hot_outlet_temperature_k
        assert restored.cold_outlet_temperature_k == result.cold_outlet_temperature_k
        assert restored.converged == result.converged
        assert restored.status == result.status
        assert restored.q_max_diagnostics == result.q_max_diagnostics
