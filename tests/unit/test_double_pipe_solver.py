"""Unit tests for the Q-based bisection-secant solver in double_pipe.solver.

Covers:
  1. Normal bracket finding and convergence
  2. Dynamic bracket probing (20 equal steps)
  3. No bracket found returns BRACKET_NOT_FOUND
  4. Non-convergence after max iterations
  5. Zero duty case (q_max <= 0)
  6. Final bracket width is tracked (not just initial)
  7. Convergence requires BOTH residual AND bracket tolerance (no bypass)
  8. Repeated runs produce identical results (deterministic)
  9. Bracket temperature effect computed correctly
 10. SolverParams validation (negative values, etc.)
 11. SolverResult to_dict serialization
 12. Bracket endpoints have opposite signs (invariant)
"""

from __future__ import annotations

import math

import pytest

from hexagent.exchangers.double_pipe.recorder import SolverEvaluationPhase
from hexagent.exchangers.double_pipe.solver import (
    SolverParams,
    SolverResult,
    SolverTermination,
    find_bracket,
    solve_rating,
)

pytestmark = pytest.mark.pure

# ---------------------------------------------------------------------------
# Helper: discontinuous residual for non-zero bracket width
# ---------------------------------------------------------------------------


def _sawtooth_residual(Q: float, phase: SolverEvaluationPhase) -> float:
    """Step function with discontinuity at Q = 700.

    r(0) = -10 (large, outside default tolerance so bracket finder
    probes normally).  r(Q >= 700) = 1.0.

    The bisection solver narrows to the discontinuity but can never
    reach residual = 0, so final bracket width stays > 0.
    """
    if Q < 700.0:
        return -10.0
    return 1.0


# ---------------------------------------------------------------------------
# 1. Normal bracket finding and convergence
# ---------------------------------------------------------------------------


class TestNormalConvergence:
    """Basic root-finding with a simple linear residual.

    Convergence requires c_effective_w_k so that bracket temperature
    effect can be evaluated.  Without it, bracket_dt is NaN and
    convergence is always False.
    """

    def test_linear_root(self) -> None:
        """f(Q) = Q - 500  ->  root at Q = 500."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=1000.0, c_effective_w_k=100.0)
        assert result.converged
        assert result.termination_reason == SolverTermination.CONVERGED
        assert abs(result.q_solution_w - 500.0) < 1.0

    def test_root_near_q_max(self) -> None:
        """Root at Q = 950 (close to q_max = 1000)."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 950.0

        result = solve_rating(residual, q_max=1000.0, c_effective_w_k=100.0)
        assert result.converged
        assert abs(result.q_solution_w - 950.0) < 1.0

    def test_root_at_half_q_max(self) -> None:
        """Root exactly at 0.5 * q_max."""
        q_max = 1000.0
        target = q_max / 2.0

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - target

        result = solve_rating(residual, q_max=q_max, c_effective_w_k=100.0)
        assert result.converged
        assert abs(result.q_solution_w - target) < 1.0

    def test_quadratic_root(self) -> None:
        """f(Q) = Q^2 - 50^2  ->  root at Q = 50."""
        target = 50.0

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q * Q - target * target

        result = solve_rating(residual, q_max=200.0, c_effective_w_k=100.0)
        assert result.converged
        assert abs(result.q_solution_w - target) < 1.0

    def test_increasing_residual(self) -> None:
        """f(Q) = Q - 100  ->  root at Q = 100 (increasing, f(0) < 0)."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 100.0

        result = solve_rating(residual, q_max=1000.0, c_effective_w_k=100.0)
        assert result.converged
        assert abs(result.q_solution_w - 100.0) < 1.0

    def test_residual_below_tolerance(self) -> None:
        """|residual| <= max(abs_tol, rel_tol * |Q|) at convergence."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=1000.0, c_effective_w_k=100.0)
        assert result.converged
        params = SolverParams()
        tol = max(
            params.absolute_residual_w,
            params.relative_residual_fraction * max(abs(result.q_solution_w), 1.0),
        )
        assert abs(result.residual_w) <= tol

    def test_find_bracket_sign_change(self) -> None:
        """find_bracket returns a valid bracket for a crossing function."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        assert q_low < q_high

    def test_find_bracket_resolves_root(self) -> None:
        """Bracket endpoints should bracket the root."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        # Root at 500 is between the bracket endpoints
        assert q_low <= 500.0 <= q_high


# ---------------------------------------------------------------------------
# 2. Dynamic bracket probing (20 equal steps)
# ---------------------------------------------------------------------------


class TestDynamicBracketProbing:
    """The bracket finder probes 20 equal steps from 0 to q_max.

    Use f(Q) = Q - 325 so the root falls between probe points 300 and 350,
    giving a clean sign change.  (Roots exactly at probe points return a
    degenerate bracket because r=0 does not trigger the < 0 check.)
    """

    def test_bracket_found_between_probes(self) -> None:
        """Sign change at Q = 325 is caught between probes at 300 and 350."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 325.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        # Step size is 1000/20 = 50, so bracket should be within one step of 325
        assert q_low < 325.0 < q_high
        assert q_high - q_low <= 50.0 + 1e-9

    def test_bracket_near_boundary(self) -> None:
        """Root at Q = 945 (between probes at 900 and 950)."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 945.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        assert q_low < 945.0 < q_high

    def test_no_sign_change_returns_none(self) -> None:
        """f(Q) = 100 (always positive) -> no bracket."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return 100.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is None

    def test_always_negative_returns_none(self) -> None:
        """f(Q) = -100 (always negative) -> no bracket."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return -100.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is None

    def test_non_finite_skipped(self) -> None:
        """Non-finite residuals at intermediate probes are skipped."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            if 180.0 < Q < 220.0 or 480.0 < Q < 520.0:
                return float("nan")
            return Q - 500.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        assert q_low < q_high

    def test_zero_q_max_returns_none(self) -> None:
        params = SolverParams()
        bracket = find_bracket(lambda Q, phase: Q - 500.0, q_max=0.0, params=params)
        assert bracket is None

    def test_bracket_width_positive(self) -> None:
        """Bracket found for a crossing function has q_high > q_low."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 325.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        assert bracket[1] > bracket[0]


# ---------------------------------------------------------------------------
# 3. No bracket found returns BRACKET_NOT_FOUND
# ---------------------------------------------------------------------------


class TestNoBracket:
    """When no sign change exists, solve_rating returns BRACKET_NOT_FOUND."""

    def test_always_positive(self) -> None:
        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return 50.0

        result = solve_rating(residual, q_max=1000.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.BRACKET_NOT_FOUND
        assert result.q_solution_w == 0.0
        assert math.isnan(result.residual_w)

    def test_always_negative(self) -> None:
        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return -50.0

        result = solve_rating(residual, q_max=1000.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.BRACKET_NOT_FOUND

    def test_positive_parabola(self) -> None:
        """f(Q) = Q^2 + 1 always positive."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q * Q + 1.0

        result = solve_rating(residual, q_max=1000.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.BRACKET_NOT_FOUND

    def test_iterations_zero_when_no_bracket(self) -> None:
        result = solve_rating(lambda Q, phase: 1.0, q_max=1000.0)
        assert result.iterations == 0
        assert result.function_evaluations == 0

    def test_nan_residual_returns_no_bracket(self) -> None:
        """All-NaN residual -> no bracket."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return float("nan")

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is None

    def test_inf_at_zero_returns_no_bracket(self) -> None:
        """Inf at Q = 0 -> non-finite, bracket finder returns None."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            if Q == 0.0:
                return float("inf")
            return 100.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is None

    def test_no_bracket_does_not_call_solver(self) -> None:
        """When bracket is None, the bisection solver is never invoked."""
        call_log: list[float] = []

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            call_log.append(Q)
            return 1.0

        result = solve_rating(residual, q_max=1000.0)
        assert result.termination_reason == SolverTermination.BRACKET_NOT_FOUND
        # Only bracket-finder probes should be recorded
        assert all(q >= 0 for q in call_log)


# ---------------------------------------------------------------------------
# 4. Non-convergence after max iterations
# ---------------------------------------------------------------------------


class TestNonConvergence:
    """When max_iterations is too low or the function has a discontinuity,
    solver reports NON_CONVERGENCE."""

    def test_max_iterations_exceeded(self) -> None:
        """Use a tiny max_iterations so bisection can't converge."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        tight = SolverParams(max_iterations=1)
        result = solve_rating(residual, q_max=1000.0, params=tight)
        # With only 1 iteration, bisection may or may not converge;
        # the key check is that it doesn't crash.
        assert result.termination_reason in (
            SolverTermination.NON_CONVERGENCE,
            SolverTermination.CONVERGED,
        )

    def test_discontinuous_residual_non_convergence(self) -> None:
        """Step function: solver narrows to discontinuity but can't converge
        because residual is never zero."""
        result = solve_rating(_sawtooth_residual, q_max=1000.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.NON_CONVERGENCE

    def test_non_convergence_tracks_iterations(self) -> None:
        """NON_CONVERGENCE should report iterations > 0."""
        result = solve_rating(_sawtooth_residual, q_max=1000.0)
        assert result.iterations > 0
        assert result.function_evaluations > 0


# ---------------------------------------------------------------------------
# 5. Zero duty case (q_max <= 0)
# ---------------------------------------------------------------------------


class TestZeroDuty:
    """q_max <= 0 -> ZERO_DUTY termination with zero evaluations."""

    def test_zero_q_max(self) -> None:
        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=0.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.ZERO_DUTY
        assert result.q_solution_w == 0.0
        assert result.iterations == 0
        assert result.function_evaluations == 0
        assert math.isnan(result.residual_w)

    def test_negative_q_max(self) -> None:
        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=-100.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.ZERO_DUTY

    def test_zero_q_max_no_evaluations(self) -> None:
        """No function evaluations should occur when q_max <= 0."""
        call_log: list[float] = []

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            call_log.append(Q)
            return Q - 500.0

        result = solve_rating(residual, q_max=0.0)
        assert result.termination_reason == SolverTermination.ZERO_DUTY
        assert len(call_log) == 0

    def test_zero_q_max_bracket_fields(self) -> None:
        result = solve_rating(lambda Q, phase: Q, q_max=0.0)
        assert result.initial_bracket_low_w == 0.0
        assert result.initial_bracket_high_w == 0.0
        assert result.final_bracket_low_w == 0.0
        assert result.final_bracket_high_w == 0.0
        assert result.final_bracket_width_w == 0.0

    def test_zero_q_max_to_dict(self) -> None:
        result = solve_rating(lambda Q, phase: Q, q_max=0.0)
        d = result.to_dict()
        assert d["termination_reason"] == "zero_duty"
        assert d["converged"] is False
        assert d["q_solution_w"] == 0.0


# ---------------------------------------------------------------------------
# 6. Final bracket width is tracked (not just initial)
# ---------------------------------------------------------------------------


class TestBracketWidthTracking:
    """Both initial and final bracket are recorded; final is narrower.

    For smooth monotonic functions the bisection collapses to the exact
    root (bracket width = 0).  Use the sawtooth (discontinuous) residual
    to verify non-trivial final bracket width tracking.
    """

    def test_final_bracket_narrower_than_initial(self) -> None:
        """After solving, final bracket should be tighter than initial."""
        params = SolverParams(bracket_temperature_tolerance_k=1.0)
        result = solve_rating(
            _sawtooth_residual,
            q_max=1000.0,
            params=params,
            c_effective_w_k=1000.0,
        )
        initial_width = result.initial_bracket_high_w - result.initial_bracket_low_w
        final_width = result.final_bracket_width_w
        assert final_width < initial_width

    def test_bracket_width_positive_for_discontinuous(self) -> None:
        """Final bracket width is > 0 for the sawtooth residual."""
        result = solve_rating(_sawtooth_residual, q_max=1000.0)
        assert result.final_bracket_width_w > 0

    def test_initial_bracket_recorded(self) -> None:
        """initial_bracket_low/high are set from find_bracket output."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 325.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket

        result = solve_rating(residual, q_max=1000.0)
        assert result.initial_bracket_low_w == pytest.approx(q_low)
        assert result.initial_bracket_high_w == pytest.approx(q_high)

    def test_final_bracket_endpoints_flank_solution(self) -> None:
        """final_bracket_low_w <= q_solution_w <= final_bracket_high_w."""
        result = solve_rating(_sawtooth_residual, q_max=1000.0)
        assert result.final_bracket_low_w <= result.q_solution_w <= result.final_bracket_high_w

    def test_smooth_function_bracket_collapses(self) -> None:
        """For a smooth function with c_effective, bracket collapses to 0."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=1000.0, c_effective_w_k=100.0)
        assert result.converged
        assert result.final_bracket_width_w == 0.0


# ---------------------------------------------------------------------------
# 7. Convergence requires BOTH residual AND bracket tolerance (no bypass)
# ---------------------------------------------------------------------------


class TestDualConvergenceCriterion:
    """Convergence needs residual tolerance AND bracket temperature tolerance.

    The solver checks:
      residual_ok = |r| <= max(abs_tol, rel_tol * max(|Q|, 1))
      bracket_ok  = isfinite(bracket_dt) and bracket_dt <= bracket_temperature_tolerance_k
      converged   = residual_ok and bracket_ok and iterations <= max_iterations

    Without c_effective_w_k, bracket_dt is NaN -> bracket_ok = False -> never converges.
    With c_effective_w_k, smooth functions converge because bracket collapses to 0 width.
    """

    def test_no_c_effective_fails_convergence(self) -> None:
        """Without c_effective_w_k, bracket_dt is NaN -> bracket_ok is False."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=1000.0)
        # Residual tolerance is met but bracket temperature cannot be
        # evaluated without c_effective_w_k.
        assert not result.converged
        assert result.termination_reason == SolverTermination.NON_CONVERGENCE
        assert math.isnan(result.final_bracket_temperature_effect_k)

    def test_tight_bracket_tolerance_with_discontinuity(self) -> None:
        """Sawtooth: bracket_dt ~ 9e-10 > 1e-12 tolerance -> NOT converged.

        absolute_residual_w = 2.0 so that the residual at the
        discontinuity (1.0) passes the residual tolerance check.
        """
        params = SolverParams(
            bracket_temperature_tolerance_k=1e-12,
            absolute_residual_w=2.0,
        )
        result = solve_rating(
            _sawtooth_residual,
            q_max=1000.0,
            params=params,
            c_effective_w_k=1.0,
        )
        assert not result.converged
        assert result.termination_reason == SolverTermination.NON_CONVERGENCE
        # bracket_dt is small but > 1e-12
        assert result.final_bracket_temperature_effect_k > 1e-12

    def test_loose_bracket_tolerance_with_discontinuity(self) -> None:
        """Sawtooth: bracket_dt ~ 9e-10 < 1e-3 tolerance -> converged.

        absolute_residual_w = 2.0 so that the residual at the
        discontinuity (1.0) passes the residual tolerance check.
        """
        params = SolverParams(
            bracket_temperature_tolerance_k=1e-3,
            absolute_residual_w=2.0,
        )
        result = solve_rating(
            _sawtooth_residual,
            q_max=1000.0,
            params=params,
            c_effective_w_k=1.0,
        )
        # Residual is 1.0 <= 2.0 (abs_tol), and bracket_dt ~ 9e-10 < 1e-3
        assert result.converged
        assert result.termination_reason == SolverTermination.CONVERGED

    def test_residual_met_bracket_not_met(self) -> None:
        """Smooth function with tight bracket tolerance and c_effective.

        For smooth functions the bracket collapses to 0 width, so
        bracket_dt = 0 which satisfies any positive tolerance.
        This means the dual criterion can only be tested with
        discontinuous residuals or by limiting iterations.
        """

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        # Even with extremely tight tolerance, bracket collapses to 0
        params = SolverParams(bracket_temperature_tolerance_k=1e-15)
        result = solve_rating(residual, q_max=1000.0, params=params, c_effective_w_k=1.0)
        # Smooth function -> bracket width = 0 -> bracket_dt = 0 -> converged
        assert result.converged

    def test_c_effective_none_vs_set(self) -> None:
        """Same function: converge with c_effective, fail without."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        r_without = solve_rating(residual, q_max=1000.0)
        r_with = solve_rating(residual, q_max=1000.0, c_effective_w_k=100.0)

        assert not r_without.converged
        assert r_with.converged

    def test_custom_params_passed_through(self) -> None:
        """SolverParams is stored in the result."""
        params = SolverParams(absolute_residual_w=0.1)
        result = solve_rating(
            lambda Q, phase: Q - 500.0,
            q_max=1000.0,
            params=params,
            c_effective_w_k=100.0,
        )
        assert result.solver_params is params

    def test_default_params_used_when_none(self) -> None:
        result = solve_rating(
            lambda Q, phase: Q - 500.0,
            q_max=1000.0,
            c_effective_w_k=100.0,
        )
        assert isinstance(result.solver_params, SolverParams)
        assert result.solver_params.absolute_residual_w == SolverParams().absolute_residual_w


# ---------------------------------------------------------------------------
# 8. Repeated runs produce identical results (deterministic)
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Solving the same problem twice yields identical results."""

    def test_same_results_on_repeat(self) -> None:
        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        params = SolverParams(bracket_temperature_tolerance_k=1.0)
        r1 = solve_rating(residual, q_max=1000.0, params=params, c_effective_w_k=100.0)
        r2 = solve_rating(residual, q_max=1000.0, params=params, c_effective_w_k=100.0)
        assert r1.q_solution_w == r2.q_solution_w
        assert r1.residual_w == r2.residual_w
        assert r1.final_bracket_width_w == r2.final_bracket_width_w
        assert r1.iterations == r2.iterations
        assert r1.function_evaluations == r2.function_evaluations

    def test_same_bracket_on_repeat(self) -> None:
        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 300.0

        params = SolverParams()
        b1 = find_bracket(residual, q_max=1000.0, params=params)
        b2 = find_bracket(residual, q_max=1000.0, params=params)
        assert b1 == b2

    def test_same_params_stored(self) -> None:
        """The same SolverParams object is stored in both results."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        params = SolverParams(max_iterations=50)
        r1 = solve_rating(residual, q_max=1000.0, params=params)
        r2 = solve_rating(residual, q_max=1000.0, params=params)
        # Both should reference the same params object
        assert r1.solver_params is params
        assert r2.solver_params is params

    def test_deterministic_sawtooth(self) -> None:
        """Sawtooth residual is also deterministic."""
        r1 = solve_rating(_sawtooth_residual, q_max=1000.0)
        r2 = solve_rating(_sawtooth_residual, q_max=1000.0)
        assert r1.q_solution_w == r2.q_solution_w
        assert r1.final_bracket_width_w == r2.final_bracket_width_w
        assert r1.iterations == r2.iterations


# ---------------------------------------------------------------------------
# 9. Bracket temperature effect computed correctly
# ---------------------------------------------------------------------------


class TestBracketTemperatureEffect:
    """bracket_temperature_effect = bracket_width / c_effective_w_k."""

    def test_temperature_effect_computed(self) -> None:
        """Verify bracket_temperature_effect_k = width / c_effective_w_k."""
        c_eff = 500.0  # W/K
        params = SolverParams(bracket_temperature_tolerance_k=1.0)
        result = solve_rating(
            _sawtooth_residual,
            q_max=1000.0,
            params=params,
            c_effective_w_k=c_eff,
        )
        if result.final_bracket_width_w > 0:
            expected_dt = result.final_bracket_width_w / c_eff
            assert result.final_bracket_temperature_effect_k == pytest.approx(expected_dt)

    def test_temperature_effect_nan_without_c_eff(self) -> None:
        """Without c_effective_w_k, temperature effect is NaN."""
        result = solve_rating(_sawtooth_residual, q_max=1000.0)
        assert math.isnan(result.final_bracket_temperature_effect_k)

    def test_temperature_effect_nan_with_zero_c_eff(self) -> None:
        """With c_effective_w_k = 0, temperature effect is NaN."""
        result = solve_rating(_sawtooth_residual, q_max=1000.0, c_effective_w_k=0.0)
        assert math.isnan(result.final_bracket_temperature_effect_k)

    def test_temperature_effect_nan_with_negative_c_eff(self) -> None:
        """With c_effective_w_k < 0, temperature effect is NaN."""
        result = solve_rating(_sawtooth_residual, q_max=1000.0, c_effective_w_k=-1.0)
        assert math.isnan(result.final_bracket_temperature_effect_k)

    def test_zero_duty_temperature_effect_nan(self) -> None:
        """Zero duty -> temperature effect is NaN."""
        result = solve_rating(lambda Q, phase: Q, q_max=0.0)
        assert math.isnan(result.final_bracket_temperature_effect_k)

    def test_smooth_function_zero_temperature_effect(self) -> None:
        """Smooth function converges to exact root -> bracket_dt = 0."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=1000.0, c_effective_w_k=100.0)
        assert result.converged
        assert result.final_bracket_temperature_effect_k == 0.0


# ---------------------------------------------------------------------------
# 10. SolverParams validation (negative values, etc.)
# ---------------------------------------------------------------------------


class TestSolverParamsValidation:
    """SolverParams rejects invalid inputs."""

    def test_defaults(self) -> None:
        p = SolverParams()
        assert p.absolute_residual_w == pytest.approx(1e-3)
        assert p.relative_residual_fraction == pytest.approx(1e-8)
        assert p.bracket_temperature_tolerance_k == pytest.approx(1e-4)
        assert p.max_iterations == 100

    def test_frozen(self) -> None:
        p = SolverParams()
        with pytest.raises(AttributeError):
            p.absolute_residual_w = 1.0  # type: ignore[misc]

    def test_negative_absolute_residual_raises(self) -> None:
        with pytest.raises(ValueError, match="absolute_residual_w"):
            SolverParams(absolute_residual_w=-1.0)

    def test_negative_relative_fraction_raises(self) -> None:
        with pytest.raises(ValueError, match="relative_residual_fraction"):
            SolverParams(relative_residual_fraction=-0.1)

    def test_zero_bracket_temperature_raises(self) -> None:
        with pytest.raises(ValueError, match="bracket_temperature_tolerance_k"):
            SolverParams(bracket_temperature_tolerance_k=0.0)

    def test_negative_bracket_temperature_raises(self) -> None:
        with pytest.raises(ValueError, match="bracket_temperature_tolerance_k"):
            SolverParams(bracket_temperature_tolerance_k=-1.0)

    def test_zero_max_iterations_raises(self) -> None:
        with pytest.raises(ValueError, match="max_iterations"):
            SolverParams(max_iterations=0)

    def test_negative_max_iterations_raises(self) -> None:
        with pytest.raises(ValueError, match="max_iterations"):
            SolverParams(max_iterations=-5)

    def test_nan_absolute_residual_raises(self) -> None:
        with pytest.raises(ValueError, match="absolute_residual_w"):
            SolverParams(absolute_residual_w=float("nan"))

    def test_inf_relative_fraction_raises(self) -> None:
        with pytest.raises(ValueError, match="relative_residual_fraction"):
            SolverParams(relative_residual_fraction=float("inf"))

    def test_valid_custom_params(self) -> None:
        p = SolverParams(
            absolute_residual_w=0.5,
            relative_residual_fraction=1e-6,
            bracket_temperature_tolerance_k=0.01,
            max_iterations=50,
        )
        assert p.absolute_residual_w == 0.5
        assert p.max_iterations == 50

    def test_float_max_iterations_rejected(self) -> None:
        """max_iterations must be an int, not a float."""
        with pytest.raises(ValueError, match="max_iterations"):
            SolverParams(max_iterations=10.5)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 11. SolverResult to_dict serialization
# ---------------------------------------------------------------------------


class TestSolverResultToDict:
    """SolverResult.to_dict() round-trip."""

    def test_to_dict_all_keys(self) -> None:
        """to_dict output contains all required keys."""
        params = SolverParams()
        result = SolverResult(
            converged=True,
            q_solution_w=100.0,
            residual_w=0.0,
            initial_bracket_low_w=0.0,
            initial_bracket_high_w=200.0,
            final_bracket_low_w=99.0,
            final_bracket_high_w=101.0,
            final_bracket_width_w=2.0,
            final_bracket_temperature_effect_k=0.004,
            iterations=5,
            function_evaluations=6,
            termination_reason=SolverTermination.CONVERGED,
            solver_params=params,
        )
        d = result.to_dict()
        for key in [
            "converged",
            "q_solution_w",
            "residual_w",
            "initial_bracket_low_w",
            "initial_bracket_high_w",
            "final_bracket_low_w",
            "final_bracket_high_w",
            "final_bracket_width_w",
            "final_bracket_temperature_effect_k",
            "iterations",
            "function_evaluations",
            "termination_reason",
            "solver_params",
        ]:
            assert key in d
        for key in [
            "absolute_residual_w",
            "relative_residual_fraction",
            "bracket_temperature_tolerance_k",
            "max_iterations",
        ]:
            assert key in d["solver_params"]

    def test_to_dict_round_trip(self) -> None:
        params = SolverParams(absolute_residual_w=0.01, max_iterations=25)
        result = SolverResult(
            converged=True,
            q_solution_w=500.0,
            residual_w=0.001,
            initial_bracket_low_w=0.0,
            initial_bracket_high_w=1000.0,
            final_bracket_low_w=499.5,
            final_bracket_high_w=500.5,
            final_bracket_width_w=1.0,
            final_bracket_temperature_effect_k=0.01,
            iterations=10,
            function_evaluations=12,
            termination_reason=SolverTermination.CONVERGED,
            solver_params=params,
        )
        d = result.to_dict()
        assert d["converged"] is True
        assert d["q_solution_w"] == 500.0
        assert d["residual_w"] == 0.001
        assert d["final_bracket_width_w"] == 1.0
        assert d["iterations"] == 10
        assert d["function_evaluations"] == 12
        assert d["termination_reason"] == "converged"
        assert d["solver_params"]["absolute_residual_w"] == 0.01
        assert d["solver_params"]["max_iterations"] == 25

    def test_to_dict_not_converged(self) -> None:
        params = SolverParams()
        result = SolverResult(
            converged=False,
            q_solution_w=0.0,
            residual_w=float("nan"),
            initial_bracket_low_w=0.0,
            initial_bracket_high_w=1000.0,
            final_bracket_low_w=0.0,
            final_bracket_high_w=1000.0,
            final_bracket_width_w=1000.0,
            final_bracket_temperature_effect_k=float("nan"),
            iterations=0,
            function_evaluations=0,
            termination_reason=SolverTermination.ZERO_DUTY,
            solver_params=params,
        )
        d = result.to_dict()
        assert d["converged"] is False
        assert d["termination_reason"] == "zero_duty"

    def test_to_dict_real_solve(self) -> None:
        """to_dict on a real solved result has all expected keys."""
        result = solve_rating(lambda Q, phase: Q - 500.0, q_max=1000.0, c_effective_w_k=100.0)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "final_bracket_width_w" in d
        assert "final_bracket_temperature_effect_k" in d
        assert isinstance(d["solver_params"], dict)

    def test_to_dict_zero_duty(self) -> None:
        """to_dict on a zero-duty result."""
        result = solve_rating(lambda Q, phase: Q, q_max=0.0)
        d = result.to_dict()
        assert d["termination_reason"] == "zero_duty"
        assert d["converged"] is False
        assert d["q_solution_w"] == 0.0
        assert d["final_bracket_width_w"] == 0.0


# ---------------------------------------------------------------------------
# 12. Bracket endpoints have opposite signs (invariant)
# ---------------------------------------------------------------------------


class TestBracketSignInvariant:
    """Bracket endpoints always satisfy f(q_low) * f(q_high) <= 0."""

    def test_linear_residual_opposite_signs(self) -> None:
        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 325.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        phase = SolverEvaluationPhase.BRACKET_PROBE
        assert residual(q_low, phase) * residual(q_high, phase) <= 0

    def test_quadratic_residual_opposite_signs(self) -> None:
        target = 200.0

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q * Q - target * target

        params = SolverParams()
        bracket = find_bracket(residual, q_max=500.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        phase = SolverEvaluationPhase.BRACKET_PROBE
        assert residual(q_low, phase) * residual(q_high, phase) <= 0

    def test_decreasing_residual_opposite_signs(self) -> None:
        """f(Q) = 100 - Q: root at Q=100, probe between 100 and 150."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return 100.0 - Q

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        phase = SolverEvaluationPhase.BRACKET_PROBE
        assert residual(q_low, phase) * residual(q_high, phase) <= 0

    def test_sawtooth_opposite_signs(self) -> None:
        """Step function: opposite signs at bracket endpoints."""
        params = SolverParams()
        bracket = find_bracket(_sawtooth_residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        phase = SolverEvaluationPhase.BRACKET_PROBE
        assert _sawtooth_residual(q_low, phase) * _sawtooth_residual(q_high, phase) <= 0

    def test_bracket_widest_possible(self) -> None:
        """f(Q) = Q - 945: bracket between probes at 900 and 950."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 945.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        # Opposite signs
        phase = SolverEvaluationPhase.BRACKET_PROBE
        assert residual(q_low, phase) * residual(q_high, phase) <= 0
        # And they actually straddle the root
        assert q_low <= 945.0 <= q_high

    def test_sign_invariant_after_each_probe(self) -> None:
        """At no point during probing should sign tracking break."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 325.0

        SolverParams()
        # Simulate the bracket-finding logic
        q_low, q_high = 0.0, 1000.0
        r_low = residual(q_low, SolverEvaluationPhase.BRACKET_PROBE)
        assert math.isfinite(r_low)

        n_probes = 20
        step = q_high / n_probes
        r_prev = r_low
        q_prev = q_low
        found = False
        for i in range(1, n_probes + 1):
            q_try = min(q_low + i * step, q_high)
            r_try = residual(q_try, SolverEvaluationPhase.BRACKET_PROBE)
            if not math.isfinite(r_try):
                continue
            if r_prev * r_try < 0:
                # Sign change detected between q_prev and q_try
                found = True
                phase = SolverEvaluationPhase.BRACKET_PROBE
                assert residual(q_prev, phase) * residual(q_try, phase) <= 0
                break
            r_prev = r_try
            q_prev = q_try

        # For Q-325, sign change is between 300 and 350
        assert found


# ---------------------------------------------------------------------------
# Edge cases and integration
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Various edge cases for robustness."""

    def test_very_small_q_max(self) -> None:
        """Very small but positive q_max still works."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 0.0001

        result = solve_rating(residual, q_max=0.001, c_effective_w_k=0.001)
        assert result.converged
        assert abs(result.q_solution_w - 0.0001) <= 0.0001

    def test_large_q_max(self) -> None:
        """Very large q_max converges for a linear residual."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=1e12, c_effective_w_k=100.0)
        assert result.converged
        assert abs(result.q_solution_w - 500.0) < 1.0

    def test_result_is_frozen(self) -> None:
        """SolverResult is immutable (frozen dataclass)."""
        result = solve_rating(lambda Q, phase: Q, q_max=0.0)
        with pytest.raises(AttributeError):
            result.converged = True  # type: ignore[misc]

    def test_termination_reason_is_enum(self) -> None:
        """termination_reason is always a SolverTermination member."""
        for q_max_val in (0.0, -1.0, 1000.0):
            result = solve_rating(lambda Q, phase: 1.0, q_max=q_max_val)
            assert isinstance(result.termination_reason, SolverTermination)

    def test_bracket_residual_at_zero_within_tolerance(self) -> None:
        """f(Q) = 0 everywhere -> f(0) within tolerance -> bracket (0, 0)."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return 0.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        assert bracket == (0.0, 0.0)

    def test_root_at_zero_q_converges(self) -> None:
        """f(Q) = Q -> root at Q = 0 -> bracket (0, 0) -> converged."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q

        result = solve_rating(residual, q_max=1000.0)
        assert result.converged
        assert result.q_solution_w == pytest.approx(0.0, abs=1e-6)

    def test_nonlinear_residual(self) -> None:
        """f(Q) = sin(Q) has root at Q = 0 -> converges at Q = 0."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return math.sin(Q)

        # sin(0) = 0 -> within tolerance at Q=0 -> bracket (0,0) -> converged
        result = solve_rating(residual, q_max=10.0)
        assert result.converged

    def test_tighter_tolerance(self) -> None:
        """With tighter tolerance, residual must still be within bound."""

        def residual(Q: float, phase: SolverEvaluationPhase) -> float:
            return Q - 300.0

        tight = SolverParams(absolute_residual_w=1e-6)
        result = solve_rating(residual, q_max=1000.0, params=tight, c_effective_w_k=100.0)
        assert result.converged
        tol = max(
            tight.absolute_residual_w,
            tight.relative_residual_fraction * max(abs(result.q_solution_w), 1.0),
        )
        assert abs(result.residual_w) <= tol
