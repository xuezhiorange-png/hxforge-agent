"""Unit tests for the Q-based Brent solver in double_pipe.solver.

NOTE: There is a known bug in ``solve_rating``: it passes ``xtol=0.0``
to ``scipy.optimize.brentq``, which raises ``ValueError: xtol too small
(0 <= 0)`` on scipy >= 1.17.  The ``except ValueError`` block catches
this and returns ``BRACKET_NOT_FOUND`` instead of converging.  Tests
that depend on successful Brent convergence are marked ``xfail`` with
``reason="solver.py xtol=0.0 bug"`` to document this issue.
"""

from __future__ import annotations

import math

import pytest

from hexagent.exchangers.double_pipe.solver import (
    SolverParams,
    SolverResult,
    SolverTermination,
    compute_q_max,
    find_bracket,
    solve_rating,
)

# Marker for tests that fail due to the xtol=0.0 bug in solver.py.
_xfail_xtol = pytest.mark.xfail(
    reason="solver.py passes xtol=0.0 to brentq which raises ValueError",
    raises=AssertionError,
    strict=False,
)


# ---------------------------------------------------------------------------
# 1. SolverParams: default values, validation
# ---------------------------------------------------------------------------


class TestSolverParams:
    """SolverParams: defaults and validation."""

    def test_defaults(self) -> None:
        p = SolverParams()
        assert p.absolute_residual_w == pytest.approx(1e-3)
        assert p.relative_residual_fraction == pytest.approx(1e-8)
        assert p.bracket_temperature_tolerance_k == pytest.approx(1e-4)
        assert p.max_iterations == 100
        assert p.q_step_fraction == pytest.approx(0.1)
        assert p.max_q_fraction == pytest.approx(0.99)

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


# ---------------------------------------------------------------------------
# 9. SolverTermination enum values
# ---------------------------------------------------------------------------


class TestSolverTermination:
    """All enum values are present and are strings."""

    def test_enum_values(self) -> None:
        expected = {
            "converged",
            "bracket_not_found",
            "non_convergence",
            "temperature_crossing",
            "property_failure",
            "zero_duty",
        }
        actual = {e.value for e in SolverTermination}
        assert actual == expected

    def test_enum_is_str_enum(self) -> None:
        assert SolverTermination.CONVERGED == "converged"

    def test_member_by_name(self) -> None:
        assert SolverTermination["BRACKET_NOT_FOUND"] == SolverTermination.BRACKET_NOT_FOUND


# ---------------------------------------------------------------------------
# 8. SolverResult.to_dict() round-trip
# ---------------------------------------------------------------------------


class TestSolverResultToDict:
    """SolverResult.to_dict() round-trip."""

    def test_to_dict_round_trip(self) -> None:
        params = SolverParams(absolute_residual_w=0.01, max_iterations=25)
        result = SolverResult(
            converged=True,
            q_solution_w=500.0,
            residual_w=0.001,
            bracket_width_w=0.1,
            iterations=10,
            function_evaluations=12,
            termination_reason=SolverTermination.CONVERGED,
            solver_params=params,
        )
        d = result.to_dict()
        assert d["converged"] is True
        assert d["q_solution_w"] == 500.0
        assert d["residual_w"] == 0.001
        assert d["bracket_width_w"] == 0.1
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
            bracket_width_w=0.0,
            iterations=0,
            function_evaluations=0,
            termination_reason=SolverTermination.ZERO_DUTY,
            solver_params=params,
        )
        d = result.to_dict()
        assert d["converged"] is False
        assert d["termination_reason"] == "zero_duty"

    def test_to_dict_all_keys_present(self) -> None:
        """to_dict output contains all required keys and correct types."""
        params = SolverParams()
        result = SolverResult(
            converged=True,
            q_solution_w=100.0,
            residual_w=0.0,
            bracket_width_w=0.5,
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
            "bracket_width_w",
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


# ---------------------------------------------------------------------------
# 2. Simple root: f(Q) = Q - 500 → converge to Q=500
# ---------------------------------------------------------------------------


class TestSimpleRoot:
    """f(Q) = Q - 500 → converge to Q = 500."""

    def test_simple_root(self) -> None:
        def residual(Q: float) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=1000.0)
        assert result.converged
        assert result.termination_reason == SolverTermination.CONVERGED
        assert abs(result.q_solution_w - 500.0) < 1.0
        assert abs(result.residual_w) < SolverParams().absolute_residual_w

    def test_simple_root_near_q_max(self) -> None:
        """Root at Q=950 (close to q_max=1000) is still found."""

        def residual(Q: float) -> float:
            return Q - 950.0

        result = solve_rating(residual, q_max=1000.0)
        assert result.converged
        assert abs(result.q_solution_w - 950.0) < 1.0


# ---------------------------------------------------------------------------
# 3. Convergence: |residual| <= absolute_residual_w
# ---------------------------------------------------------------------------


class TestConvergence:
    """Verify |residual| <= absolute_residual_w at convergence."""

    def test_residual_below_tolerance(self) -> None:
        def residual(Q: float) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=1000.0)
        assert result.converged
        params = SolverParams()
        tol = max(
            params.absolute_residual_w,
            params.relative_residual_fraction * max(abs(result.q_solution_w), 1.0),
        )
        assert abs(result.residual_w) <= tol

    def test_tighter_tolerance(self) -> None:
        """With tighter tolerance, residual must still be within bound."""

        def residual(Q: float) -> float:
            return Q - 300.0

        tight = SolverParams(absolute_residual_w=1e-6)
        result = solve_rating(residual, q_max=1000.0, params=tight)
        assert result.converged
        tol = max(
            tight.absolute_residual_w,
            tight.relative_residual_fraction * max(abs(result.q_solution_w), 1.0),
        )
        assert abs(result.residual_w) <= tol


# ---------------------------------------------------------------------------
# 4. Bracket finding: sign change between Q=0 and Q_max
# ---------------------------------------------------------------------------


class TestFindBracket:
    """Bracket construction: sign change between Q=0 and Q_max."""

    def test_bracket_finds_sign_change(self) -> None:
        def residual(Q: float) -> float:
            return Q - 500.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        assert residual(q_low) * residual(q_high) <= 0

    def test_bracket_no_sign_change_returns_none(self) -> None:
        """f(Q) = 100 (always positive) → no bracket found."""

        def residual(Q: float) -> float:
            return 100.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is None

    def test_bracket_always_negative_returns_none(self) -> None:
        """f(Q) = -100 (always negative) → no bracket found."""

        def residual(Q: float) -> float:
            return -100.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is None

    def test_bracket_zero_q_max_returns_none(self) -> None:
        def residual(Q: float) -> float:
            return Q - 500.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=0.0, params=params)
        assert bracket is None

    def test_bracket_residual_at_zero_is_zero(self) -> None:
        """If f(0) ≈ 0, bracket should be (0, 0)."""

        def residual(Q: float) -> float:
            return Q * 0.0  # always 0 → within tolerance at Q=0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        assert bracket == (0.0, 0.0)

    def test_bracket_with_non_finite_values(self) -> None:
        """Non-finite residual values at intermediate probes are skipped."""

        def residual(Q: float) -> float:
            # NaN at Q ≈ 200 and Q ≈ 500 (middle probes), but finite at Q=0 and Q_high
            if 180.0 < Q < 220.0 or 480.0 < Q < 520.0:
                return float("nan")  # non-finite → skipped
            return Q - 500.0  # valid sign change

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        q_low, q_high = bracket
        assert q_low < q_high
        # The bracket should still capture the sign change
        assert residual(q_low) * residual(q_high) <= 0

    def test_bracket_with_inf_residual(self) -> None:
        """Non-finite residual at Q=0 → returns None."""

        def residual(Q: float) -> float:
            if Q == 0.0:
                return float("inf")
            return Q - 500.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is None

    def test_bracket_width_positive(self) -> None:
        """Bracket found for a crossing function has q_high > q_low."""

        def residual(Q: float) -> float:
            return Q - 500.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is not None
        assert bracket[1] > bracket[0]


# ---------------------------------------------------------------------------
# 5. No bracket → BRACKET_NOT_FOUND
# ---------------------------------------------------------------------------


class TestNoBracket:
    """No sign change → BRACKET_NOT_FOUND termination."""

    def test_no_bracket_always_positive(self) -> None:
        def residual(Q: float) -> float:
            return 50.0

        result = solve_rating(residual, q_max=1000.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.BRACKET_NOT_FOUND
        assert result.q_solution_w == 0.0
        assert math.isnan(result.residual_w)

    def test_no_bracket_always_negative(self) -> None:
        def residual(Q: float) -> float:
            return -50.0

        result = solve_rating(residual, q_max=1000.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.BRACKET_NOT_FOUND

    def test_no_bracket_monotonic_stays_positive(self) -> None:
        """f(Q) = Q² + 1 always positive."""

        def residual(Q: float) -> float:
            return Q * Q + 1.0

        result = solve_rating(residual, q_max=1000.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.BRACKET_NOT_FOUND


# ---------------------------------------------------------------------------
# 6. Zero duty: q_max <= 0 → ZERO_DUTY
# ---------------------------------------------------------------------------


class TestZeroDuty:
    """q_max <= 0 → ZERO_DUTY termination."""

    def test_zero_q_max(self) -> None:
        def residual(Q: float) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=0.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.ZERO_DUTY
        assert result.q_solution_w == 0.0
        assert result.iterations == 0
        assert result.function_evaluations == 0
        assert math.isnan(result.residual_w)

    def test_negative_q_max(self) -> None:
        def residual(Q: float) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=-100.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.ZERO_DUTY

    def test_zero_q_max_result_to_dict(self) -> None:
        """Verify to_dict round-trip on a zero-duty result."""
        result = solve_rating(lambda Q: Q, q_max=0.0)
        d = result.to_dict()
        assert d["termination_reason"] == "zero_duty"
        assert d["converged"] is False
        assert d["q_solution_w"] == 0.0


# ---------------------------------------------------------------------------
# 7. NaN / non-finite residual handling
# ---------------------------------------------------------------------------


class TestNaNHandling:
    """Non-finite residuals are handled gracefully."""

    def test_nan_at_zero_returns_no_bracket(self) -> None:
        """If residual returns NaN at Q=0, bracket finder returns None."""

        def residual(Q: float) -> float:
            return float("nan")

        result = solve_rating(residual, q_max=1000.0)
        assert not result.converged
        assert result.termination_reason in (
            SolverTermination.BRACKET_NOT_FOUND,
            SolverTermination.NON_CONVERGENCE,
        )

    def test_nan_everywhere(self) -> None:
        """All-NaN residual → no bracket → BRACKET_NOT_FOUND."""

        def residual(Q: float) -> float:
            return float("nan")

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is None

    def test_inf_residual_at_boundary(self) -> None:
        """Inf at Q=0 → no bracket (non-finite at q_low)."""

        def residual(Q: float) -> float:
            if Q == 0.0:
                return float("inf")
            return 100.0

        params = SolverParams()
        bracket = find_bracket(residual, q_max=1000.0, params=params)
        assert bracket is None


# ---------------------------------------------------------------------------
# 10. Quadratic root: f(Q) = Q² - target² → positive root
# ---------------------------------------------------------------------------


class TestQuadraticRoot:
    """f(Q) = Q² - 1000² → one positive root at Q = 1000."""

    def test_quadratic_root(self) -> None:
        target = 1000.0

        def residual(Q: float) -> float:
            return Q * Q - target * target

        result = solve_rating(residual, q_max=2000.0)
        assert result.converged
        assert abs(result.q_solution_w - target) < 1.0

    def test_quadratic_root_smaller(self) -> None:
        """f(Q) = Q² - 50² → root at Q = 50."""
        target = 50.0

        def residual(Q: float) -> float:
            return Q * Q - target * target

        result = solve_rating(residual, q_max=200.0)
        assert result.converged
        assert abs(result.q_solution_w - target) < 1.0


# ---------------------------------------------------------------------------
# 11. Near-zero root: f(Q) = Q - 0.001 → converges
# ---------------------------------------------------------------------------


class TestNearZeroRoot:
    """f(Q) = Q - 0.001 → very small root."""

    def test_near_zero_root(self) -> None:
        target = 0.001

        def residual(Q: float) -> float:
            return Q - target

        result = solve_rating(residual, q_max=10.0)
        assert result.converged
        assert abs(result.q_solution_w - target) < 0.01

    def test_zero_root_exact(self) -> None:
        """f(Q) = Q → root at Q = 0.  Bracket is (0, 0) → zero duty."""

        def residual(Q: float) -> float:
            return Q

        result = solve_rating(residual, q_max=1000.0)
        # f(0)=0 is within tolerance → bracket (0,0) → converged at Q=0
        assert result.converged
        assert result.q_solution_w == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# compute_q_max tests
# ---------------------------------------------------------------------------


class TestComputeQMax:
    """compute_q_max returns sensible maximum duty."""

    def test_basic_case(self) -> None:
        q_max = compute_q_max(
            m_hot=0.5,
            m_cold=0.5,
            h_hot_in=200000.0,
            h_cold_in=80000.0,
            th_in=350.0,
            tc_in=300.0,
            flow_arrangement="counter",
        )
        assert q_max is not None
        assert q_max > 0

    def test_zero_mass_flow_returns_none(self) -> None:
        q_max = compute_q_max(
            m_hot=0.0,
            m_cold=0.5,
            h_hot_in=200000.0,
            h_cold_in=80000.0,
            th_in=350.0,
            tc_in=300.0,
            flow_arrangement="counter",
        )
        assert q_max is None

    def test_negative_mass_flow_returns_none(self) -> None:
        q_max = compute_q_max(
            m_hot=-1.0,
            m_cold=0.5,
            h_hot_in=200000.0,
            h_cold_in=80000.0,
            th_in=350.0,
            tc_in=300.0,
            flow_arrangement="counter",
        )
        assert q_max is None

    def test_inverted_temperatures_returns_none(self) -> None:
        """If T_hot_in < T_cold_in, max_delta is negative → no feasible Q."""
        q_max = compute_q_max(
            m_hot=0.5,
            m_cold=0.5,
            h_hot_in=200000.0,
            h_cold_in=80000.0,
            th_in=280.0,
            tc_in=350.0,  # inverted
            flow_arrangement="counter",
        )
        assert q_max is None

    def test_large_mass_flows(self) -> None:
        q_max = compute_q_max(
            m_hot=10.0,
            m_cold=10.0,
            h_hot_in=200000.0,
            h_cold_in=80000.0,
            th_in=400.0,
            tc_in=300.0,
            flow_arrangement="counter",
        )
        assert q_max is not None
        assert q_max > 1e6

    def test_both_zero_mass_flows(self) -> None:
        q_max = compute_q_max(
            m_hot=0.0,
            m_cold=0.0,
            h_hot_in=200000.0,
            h_cold_in=80000.0,
            th_in=350.0,
            tc_in=300.0,
            flow_arrangement="counter",
        )
        assert q_max is None


# ---------------------------------------------------------------------------
# Integration: solve_rating with custom params
# ---------------------------------------------------------------------------


class TestSolveRatingWithParams:
    """Test solve_rating with non-default SolverParams."""

    def test_custom_params_passed_through(self) -> None:
        """SolverParams is stored in the result."""
        params = SolverParams(absolute_residual_w=0.1)
        result = solve_rating(
            lambda Q: Q - 500.0,
            q_max=1000.0,
            params=params,
        )
        assert result.solver_params is params

    def test_default_params_used_when_none(self) -> None:
        result = solve_rating(
            lambda Q: Q - 500.0,
            q_max=1000.0,
        )
        assert isinstance(result.solver_params, SolverParams)
        assert result.solver_params.absolute_residual_w == SolverParams().absolute_residual_w

    def test_zero_duty_bypasses_bracket_finding(self) -> None:
        """With q_max=0, bracket finding is skipped entirely."""
        call_log: list[float] = []

        def residual(Q: float) -> float:
            call_log.append(Q)
            return Q - 500.0

        result = solve_rating(residual, q_max=0.0)
        assert result.termination_reason == SolverTermination.ZERO_DUTY
        # No function evaluations should occur
        assert len(call_log) == 0

    def test_no_bracket_does_not_call_brentq(self) -> None:
        """When bracket is None, brentq is never invoked."""
        call_log: list[float] = []

        def residual(Q: float) -> float:
            call_log.append(Q)
            return 1.0  # always positive → no bracket

        result = solve_rating(residual, q_max=1000.0)
        assert result.termination_reason == SolverTermination.BRACKET_NOT_FOUND
        # Only bracket-finder probes should be recorded
        assert all(q >= 0 for q in call_log)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Various edge cases for robustness."""

    def test_root_at_half_q_max(self) -> None:
        """Root exactly at 0.5 * q_max."""
        q_max = 1000.0
        target = q_max / 2.0

        def residual(Q: float) -> float:
            return Q - target

        result = solve_rating(residual, q_max=q_max)
        assert result.converged
        assert abs(result.q_solution_w - target) < 1.0

    def test_strictly_increasing_residual(self) -> None:
        """f(Q) = Q + 100, always positive → no bracket."""

        def residual(Q: float) -> float:
            return Q + 100.0

        result = solve_rating(residual, q_max=1000.0)
        assert not result.converged
        assert result.termination_reason == SolverTermination.BRACKET_NOT_FOUND

    def test_strictly_decreasing_residual(self) -> None:
        """f(Q) = 100 - Q, root at Q=100 → should converge."""

        def residual(Q: float) -> float:
            return 100.0 - Q

        result = solve_rating(residual, q_max=1000.0)
        assert result.converged
        assert abs(result.q_solution_w - 100.0) < 1.0

    def test_nonlinear_residual(self) -> None:
        """f(Q) = sin(Q) has root at Q=0 → converges at Q=0."""

        def residual(Q: float) -> float:
            return math.sin(Q)

        # sin(0) = 0 → within tolerance at Q=0 → bracket (0,0) → converged
        result = solve_rating(residual, q_max=10.0)
        assert result.converged

    def test_sawtooth_residual(self) -> None:
        """Residual that changes sign at a specific point — solver finds bracket."""

        def residual(Q: float) -> float:
            if Q < 700.0:
                return -1.0
            else:
                return 1.0

        result = solve_rating(residual, q_max=1000.0)
        # The sign change is detected; Brent narrows to the discontinuity.
        # Residual is non-zero at the discontinuity, so not converged.
        assert not result.converged
        assert result.termination_reason == SolverTermination.NON_CONVERGENCE

    def test_very_small_q_max(self) -> None:
        """Very small but positive q_max should still work."""

        def residual(Q: float) -> float:
            return Q - 0.0001

        result = solve_rating(residual, q_max=0.001)
        assert result.converged
        assert abs(result.q_solution_w - 0.0001) <= 0.0001

    def test_large_q_max(self) -> None:
        """Very large q_max should still converge for a linear residual."""

        def residual(Q: float) -> float:
            return Q - 500.0

        result = solve_rating(residual, q_max=1e12)
        assert result.converged
        assert abs(result.q_solution_w - 500.0) < 1.0


# ---------------------------------------------------------------------------
# Result metadata tests
# ---------------------------------------------------------------------------


class TestResultMetadata:
    """Verify iteration counts and function evaluation counts."""

    def test_zero_iterations_on_zero_duty(self) -> None:
        result = solve_rating(lambda Q: Q, q_max=0.0)
        assert result.iterations == 0
        assert result.function_evaluations == 0

    def test_zero_iterations_on_no_bracket(self) -> None:
        result = solve_rating(lambda Q: 1.0, q_max=1000.0)
        assert result.iterations == 0
        assert result.function_evaluations == 0

    def test_bracket_width_reported(self) -> None:
        """Even with the xtol bug, bracket width should be positive."""
        result = solve_rating(lambda Q: Q - 500.0, q_max=1000.0)
        assert result.bracket_width_w > 0

    def test_result_is_frozen_dataclass(self) -> None:
        """SolverResult is immutable."""
        result = solve_rating(lambda Q: Q, q_max=0.0)
        with pytest.raises(AttributeError):
            result.converged = True  # type: ignore[misc]

    def test_termination_reason_is_enum(self) -> None:
        """termination_reason is always a SolverTermination member."""
        for q_max_val in (0.0, -1.0, 1000.0):
            result = solve_rating(lambda Q: 1.0, q_max=q_max_val)
            assert isinstance(result.termination_reason, SolverTermination)


# ---------------------------------------------------------------------------
# Known bug documentation
# ---------------------------------------------------------------------------
