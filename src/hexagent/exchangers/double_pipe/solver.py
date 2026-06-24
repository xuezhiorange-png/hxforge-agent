"""Q-based solver for double-pipe rating with dynamic bracket.

The solver uses heat duty *Q* as the sole scalar root variable and
residual ``Q − UA(Q)·LMTD(Q)`` as the objective.  Dynamic bracket
construction via PropertyProvider enthalpy limits ensures the solver
cannot converge to infeasible states.

Implements a bisection-secant hybrid that tracks the final bracket
for rigorous convergence verification.

Phase tracking is explicit: the residual function receives a
SolverEvaluationPhase argument on every call, eliminating shared
mutable state in the closure.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from hexagent.exchangers.double_pipe.recorder import SolverEvaluationPhase

# ---------------------------------------------------------------------------
# Solver status
# ---------------------------------------------------------------------------


class SolverTermination(StrEnum):
    """Why the solver stopped."""

    CONVERGED = "converged"
    BRACKET_NOT_FOUND = "bracket_not_found"
    NON_CONVERGENCE = "non_convergence"
    TEMPERATURE_CROSSING = "temperature_crossing"
    PROPERTY_FAILURE = "property_failure"
    ZERO_DUTY = "zero_duty"


# ---------------------------------------------------------------------------
# Solver parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SolverParams:
    """Control parameters for the Q-based root-finding solver.

    Convergence requires ALL of:
      - ``|residual_Q| <= max(absolute_residual_w, relative_residual_fraction × max(|Q|, 1 W))``
      - bracket width converted to outlet-temperature effect <= ``bracket_temperature_tolerance_k``
      - iterations <= ``max_iterations``

    No bypass conditions are permitted.
    """

    absolute_residual_w: float = 1e-3
    """Absolute residual tolerance [W]."""
    relative_residual_fraction: float = 1e-8
    """Relative residual fraction (dimensionless)."""
    bracket_temperature_tolerance_k: float = 1e-4
    """Maximum bracket width converted to outlet-temperature effect [K]."""
    max_iterations: int = 100
    """Maximum Brent iterations."""

    def __post_init__(self) -> None:
        if not math.isfinite(self.absolute_residual_w) or self.absolute_residual_w < 0:
            raise ValueError(f"absolute_residual_w must be >= 0, got {self.absolute_residual_w}")
        if (
            not math.isfinite(self.relative_residual_fraction)
            or self.relative_residual_fraction < 0
        ):
            raise ValueError(
                f"relative_residual_fraction must be >= 0, got {self.relative_residual_fraction}"
            )
        if (
            not math.isfinite(self.bracket_temperature_tolerance_k)
            or self.bracket_temperature_tolerance_k <= 0
        ):
            raise ValueError(
                "bracket_temperature_tolerance_k must be > 0,"
                f" got {self.bracket_temperature_tolerance_k}"
            )
        if not isinstance(self.max_iterations, int) or self.max_iterations < 1:
            raise ValueError(f"max_iterations must be an integer >= 1, got {self.max_iterations}")


# ---------------------------------------------------------------------------
# Solver result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SolverResult:
    """Output of the Q-based solver.

    Records both initial and final bracket for rigorous convergence
    verification.  The final bracket is the actual bracket at termination,
    not the initial probe bracket.
    """

    converged: bool
    q_solution_w: float
    residual_w: float

    # Bracket tracking
    initial_bracket_low_w: float
    initial_bracket_high_w: float
    final_bracket_low_w: float
    final_bracket_high_w: float
    final_bracket_width_w: float
    final_bracket_temperature_effect_k: float

    iterations: int
    function_evaluations: int
    termination_reason: SolverTermination
    solver_params: SolverParams

    def to_dict(self) -> dict[str, object]:
        """Serialize to plain dict."""
        return {
            "converged": self.converged,
            "q_solution_w": self.q_solution_w,
            "residual_w": self.residual_w,
            "initial_bracket_low_w": self.initial_bracket_low_w,
            "initial_bracket_high_w": self.initial_bracket_high_w,
            "final_bracket_low_w": self.final_bracket_low_w,
            "final_bracket_high_w": self.final_bracket_high_w,
            "final_bracket_width_w": self.final_bracket_width_w,
            "final_bracket_temperature_effect_k": self.final_bracket_temperature_effect_k,
            "iterations": self.iterations,
            "function_evaluations": self.function_evaluations,
            "termination_reason": self.termination_reason.value,
            "solver_params": {
                "absolute_residual_w": self.solver_params.absolute_residual_w,
                "relative_residual_fraction": self.solver_params.relative_residual_fraction,
                "bracket_temperature_tolerance_k": (
                    self.solver_params.bracket_temperature_tolerance_k
                ),
                "max_iterations": self.solver_params.max_iterations,
            },
        }


# ---------------------------------------------------------------------------
# Bisection-secant hybrid with bracket tracking
# ---------------------------------------------------------------------------


def _bisect_secant(
    f: object,
    xa: float,
    xb: float,
    xtol: float,
    rtol: float,
    maxiter: int,
) -> tuple[float, float, int, int, float, float]:
    """Bisection-secant hybrid root-finding with final bracket tracking.

    Returns (x_sol, f_sol, n_iter, n_func, final_a, final_b).

    Maintains the invariant f(a)*f(b) <= 0 at all times.  Uses secant
    method for acceleration when safe, falls back to bisection otherwise.
    The final bracket [final_a, final_b] is the actual bracket at
    termination.
    """
    assert callable(f)

    a = xa
    b = xb
    fa = f(a)
    fb = f(b)

    if fa * fb > 0:
        raise ValueError("f(a) and f(b) must have opposite signs")

    # Ensure fa <= 0 <= fb
    if fa > 0:
        a, b = b, a
        fa, fb = fb, fa

    n_func = 2
    n_iter = 0

    for _ in range(maxiter):
        n_iter += 1

        # Convergence check: bracket narrow enough
        tol = xtol + rtol * max(abs(a), abs(b))
        if b - a <= 2 * tol:
            break

        # Bisection midpoint
        m = 0.5 * (a + b)
        fm = f(m)
        n_func += 1

        if fm == 0:
            a, b = m, m
            fa, fb = fm, fm
            break

        if fa * fm < 0:
            # Root in [a, m]
            b, fb = m, fm
        elif fm * fb < 0:
            # Root in [m, b]
            a, fa = m, fm
        else:
            # fm has same sign as both fa and fb — shouldn't happen
            # with a valid bracket, but handle gracefully
            break

        # Try secant acceleration: extrapolate from a and b
        if abs(fa) > 0 and abs(fb) > 0 and a != b:
            # Secant step: x_new = b - fb * (b - a) / (fb - fa)
            denom = fb - fa
            if abs(denom) > 1e-30:
                x_sec = b - fb * (b - a) / denom
                # Only use secant if it lands inside the bracket
                if a < x_sec < b:
                    fs = f(x_sec)
                    n_func += 1
                    if fs == 0:
                        a, b = x_sec, x_sec
                        fa, fb = fs, fs
                        break
                    if fa * fs < 0:
                        b, fb = x_sec, fs
                    elif fs * fb < 0:
                        a, fa = x_sec, fs
                    # If fs has same sign as both, secant didn't help — keep bracket

    # Return the bracket endpoints and the point closest to zero
    if abs(fa) <= abs(fb):
        x_sol, f_sol = a, fa
    else:
        x_sol, f_sol = b, fb

    return x_sol, f_sol, n_iter, n_func, a, b


# ---------------------------------------------------------------------------
# Bracket construction (property-based)
# ---------------------------------------------------------------------------


def find_bracket(
    residual_fn: Callable[[float, SolverEvaluationPhase], float],
    q_max: float,
    params: SolverParams,
    on_probe: Callable[[], None] | None = None,
) -> tuple[float, float] | None:
    """Find a bracket [q_low, q_high] where residual changes sign.

    Starts from Q = 0 and probes upward in 20 equal steps.
    If no sign change is found, returns None.

    Parameters
    ----------
    residual_fn :
        Function ``f(Q, phase) -> residual_w``.  The phase argument
        is SolverEvaluationPhase.BRACKET_PROBE for all calls in this
        function.
    on_probe :
        Optional callback invoked before each residual evaluation during
        bracket probing (after the explicit phase is set).
    """
    assert callable(residual_fn)

    q_low = 0.0
    q_high = q_max

    if q_high <= 0:
        return None

    # Evaluate at Q = 0
    if on_probe:
        on_probe()
    r_low = residual_fn(q_low, SolverEvaluationPhase.BRACKET_PROBE)

    if not math.isfinite(r_low):
        return None

    # Quick check: if r_low is already very small, we're at zero duty
    if abs(r_low) <= params.absolute_residual_w:
        return (0.0, 0.0)

    # Probe upward to find sign change
    n_probes = 20
    step = q_high / n_probes

    r_prev = r_low
    q_prev = q_low

    for i in range(1, n_probes + 1):
        q_try = min(q_low + i * step, q_high)
        if on_probe:
            on_probe()
        r_try = residual_fn(q_try, SolverEvaluationPhase.BRACKET_PROBE)

        if not math.isfinite(r_try):
            continue

        if r_prev * r_try < 0:
            return (q_prev, q_try)

        r_prev = r_try
        q_prev = q_try

    # Also check at Q = 0 for sign change with the last probe
    if r_prev * r_low < 0:
        return (0.0, q_prev)

    return None


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------


def solve_rating(
    residual_fn: Callable[[float, SolverEvaluationPhase], float],
    q_max: float,
    params: SolverParams | None = None,
    c_effective_w_k: float | None = None,
    on_probe: Callable[[], None] | None = None,
) -> SolverResult:
    """Solve for Q using bisection-secant hybrid with dynamic bracket.

    Parameters
    ----------
    residual_fn :
        Function ``f(Q, phase) -> residual_w``.  Must be finite at the
        bracket endpoints.  ``phase`` is BRACKET_PROBE during bracket
        construction and SOLVER_ITERATION during bisection-secant.
    q_max :
        Maximum feasible duty from enthalpy reach limits [W].
    params :
        Solver control parameters.
    c_effective_w_k :
        Effective capacity rate [W/K] for bracket-width-to-temperature
        conversion.  Typically min(C_hot, C_cold).
    on_probe :
        Optional callback for bracket-probe provenance tracking.
    """
    if params is None:
        params = SolverParams()

    if q_max <= 0:
        return SolverResult(
            converged=False,
            q_solution_w=0.0,
            residual_w=float("nan"),
            initial_bracket_low_w=0.0,
            initial_bracket_high_w=0.0,
            final_bracket_low_w=0.0,
            final_bracket_high_w=0.0,
            final_bracket_width_w=0.0,
            final_bracket_temperature_effect_k=float("nan"),
            iterations=0,
            function_evaluations=0,
            termination_reason=SolverTermination.ZERO_DUTY,
            solver_params=params,
        )

    # Find bracket — all calls use BRACKET_PROBE phase
    bracket = find_bracket(residual_fn, q_max, params, on_probe=on_probe)
    if bracket is None:
        return SolverResult(
            converged=False,
            q_solution_w=0.0,
            residual_w=float("nan"),
            initial_bracket_low_w=0.0,
            initial_bracket_high_w=q_max,
            final_bracket_low_w=0.0,
            final_bracket_high_w=q_max,
            final_bracket_width_w=q_max,
            final_bracket_temperature_effect_k=float("nan"),
            iterations=0,
            function_evaluations=0,
            termination_reason=SolverTermination.BRACKET_NOT_FOUND,
            solver_params=params,
        )

    q_low, q_high = bracket
    initial_bracket_low = q_low
    initial_bracket_high = q_high

    # Handle zero-duty case
    if q_low == 0.0 and q_high == 0.0:
        r = residual_fn(0.0, SolverEvaluationPhase.SOLVER_ITERATION)
        return SolverResult(
            converged=True,
            q_solution_w=0.0,
            residual_w=r,
            initial_bracket_low_w=0.0,
            initial_bracket_high_w=0.0,
            final_bracket_low_w=0.0,
            final_bracket_high_w=0.0,
            final_bracket_width_w=0.0,
            final_bracket_temperature_effect_k=0.0,
            iterations=0,
            function_evaluations=1,
            termination_reason=SolverTermination.ZERO_DUTY,
            solver_params=params,
        )

    # Run bisection-secant hybrid — all calls use SOLVER_ITERATION phase
    def _iteration_residual(Q: float) -> float:
        return residual_fn(Q, SolverEvaluationPhase.SOLVER_ITERATION)

    try:
        q_sol, r_sol, n_iter, n_func, final_a, final_b = _bisect_secant(
            _iteration_residual,
            q_low,
            q_high,
            xtol=1e-12,
            rtol=1e-12,
            maxiter=params.max_iterations,
        )
    except (ValueError, AssertionError):
        return SolverResult(
            converged=False,
            q_solution_w=0.0,
            residual_w=float("nan"),
            initial_bracket_low_w=initial_bracket_low,
            initial_bracket_high_w=initial_bracket_high,
            final_bracket_low_w=q_low,
            final_bracket_high_w=q_high,
            final_bracket_width_w=q_high - q_low,
            final_bracket_temperature_effect_k=float("nan"),
            iterations=0,
            function_evaluations=0,
            termination_reason=SolverTermination.BRACKET_NOT_FOUND,
            solver_params=params,
        )

    # Compute final bracket width
    final_bracket_width = abs(final_b - final_a)

    # Compute bracket temperature effect
    bracket_dt = float("nan")
    if c_effective_w_k is not None and c_effective_w_k > 0:
        bracket_dt = final_bracket_width / c_effective_w_k

    # Check convergence — ALL conditions must be satisfied
    residual_tol = max(
        params.absolute_residual_w,
        params.relative_residual_fraction * max(abs(q_sol), 1.0),
    )
    residual_ok = abs(r_sol) <= residual_tol

    bracket_ok = math.isfinite(bracket_dt) and bracket_dt <= params.bracket_temperature_tolerance_k

    converged = residual_ok and bracket_ok and n_iter <= params.max_iterations

    termination = SolverTermination.CONVERGED if converged else SolverTermination.NON_CONVERGENCE

    return SolverResult(
        converged=converged,
        q_solution_w=q_sol,
        residual_w=r_sol,
        initial_bracket_low_w=initial_bracket_low,
        initial_bracket_high_w=initial_bracket_high,
        final_bracket_low_w=final_a,
        final_bracket_high_w=final_b,
        final_bracket_width_w=final_bracket_width,
        final_bracket_temperature_effect_k=bracket_dt,
        iterations=n_iter,
        function_evaluations=n_func,
        termination_reason=termination,
        solver_params=params,
    )
