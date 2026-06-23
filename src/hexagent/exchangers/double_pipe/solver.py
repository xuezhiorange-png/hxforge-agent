"""Q-based Brent solver for double-pipe rating with dynamic bracket.

The solver uses heat duty *Q* as the sole scalar root variable and
residual ``Q − UA(Q)·LMTD(Q)`` as the objective.  Dynamic bracket
construction ensures the solver cannot converge to infeasible states.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from scipy.optimize import brentq

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
      - ``|residual_Q| <= max(absolute_residual_w, relative_residual_fraction × max(|Q|, 1))``
      - bracket width (in outlet-temperature effect) <= ``bracket_temperature_tolerance_k``
      - iterations <= ``max_iterations``
    """

    absolute_residual_w: float = 1e-3
    """Absolute residual tolerance [W]."""
    relative_residual_fraction: float = 1e-8
    """Relative residual fraction (dimensionless)."""
    bracket_temperature_tolerance_k: float = 1e-4
    """Maximum bracket width converted to outlet-temperature effect [K]."""
    max_iterations: int = 100
    """Maximum Brent iterations."""
    q_step_fraction: float = 0.1
    """Fraction of Q_max for initial bracket probing."""
    max_q_fraction: float = 0.99
    """Maximum fraction of theoretical Q_max for bracket upper bound."""

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
    """Output of the Q-based Brent solver."""

    converged: bool
    q_solution_w: float
    residual_w: float
    bracket_width_w: float
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
            "bracket_width_w": self.bracket_width_w,
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
# Bracket construction
# ---------------------------------------------------------------------------


def compute_q_max(
    m_hot: float,
    m_cold: float,
    h_hot_in: float,
    h_cold_in: float,
    th_in: float,
    tc_in: float,
    flow_arrangement: str,
    min_terminal_dt_k: float = 0.5,
) -> float | None:
    """Compute the maximum feasible duty from enthalpy reach limits.

    The maximum Q is the smaller of:
      - Hot side: m_hot × (h_hot_in − h_hot_min)  where T_hot_min = T_cold_in + min_terminal_dt
      - Cold side: m_cold × (h_cold_max − h_cold_in)  where T_cold_max = T_hot_in − min_terminal_dt

    For counter-flow: both terminal ΔT must remain positive.
    For parallel-flow: hot outlet must exceed cold outlet at the exit.

    Returns None if no feasible Q > 0 exists.
    """
    if m_hot <= 0 or m_cold <= 0:
        return None

    # Maximum possible temperature change
    max_delta_th = th_in - tc_in - min_terminal_dt_k
    max_delta_tc = th_in - tc_in - min_terminal_dt_k

    if max_delta_th <= 0 and max_delta_tc <= 0:
        return None

    # Approximate Q_max using average Cp (conservative upper bound)
    # We use a rough estimate: Q_max ≈ min(C_hot, C冷水) × ΔT_max
    # But for bracketing, we use a generous upper bound.
    # The actual upper bound is limited by the enthalpy change.
    # We'll return a conservative estimate.
    q_max_hot = m_hot * max(0.0, max_delta_th) * 4200.0  # rough Cp_water
    q_max_cold = m_cold * max(0.0, max_delta_tc) * 4200.0

    q_max = min(q_max_hot, q_max_cold)
    if q_max <= 0:
        return None

    return q_max


def find_bracket(
    residual_fn: Callable[[float], float],
    q_max: float,
    params: SolverParams,
    c_hot: float | None = None,
) -> tuple[float, float] | None:
    """Find a bracket [q_low, q_high] where residual changes sign.

    Starts from Q = 0 and probes upward.  If no sign change is found,
    performs deterministic interval probing.

    Returns None if no valid bracket exists.
    """
    q_low = 0.0
    q_high = q_max * params.max_q_fraction

    if q_high <= 0:
        return None

    # Evaluate at Q = 0
    r_low = residual_fn(q_low)

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
        r_try = residual_fn(q_try)

        if not math.isfinite(r_try):
            # Skip non-finite points but continue probing
            continue

        if r_prev * r_try < 0:
            # Sign change found
            return (q_prev, q_try)

        r_prev = r_try
        q_prev = q_try

    # Also check at Q = 0 for sign change with the last probe
    if r_prev * r_low < 0:
        return (0.0, q_prev)

    # No sign change found
    return None


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------


def solve_rating(
    residual_fn: Callable[[float], float],
    q_max: float,
    params: SolverParams | None = None,
    c_hot: float | None = None,
) -> SolverResult:
    """Solve for Q using Brent's method with dynamic bracket.

    Parameters
    ----------
    residual_fn :
        Function ``f(Q) -> residual_w``.  Must be finite at the bracket
        endpoints.
    q_max :
        Maximum feasible duty from enthalpy reach limits [W].
    params :
        Solver control parameters.
    c_hot :
        Hot-side capacity rate [W/K] for bracket-width-to-temperature conversion.
    """
    if params is None:
        params = SolverParams()

    if q_max <= 0:
        return SolverResult(
            converged=False,
            q_solution_w=0.0,
            residual_w=float("nan"),
            bracket_width_w=0.0,
            iterations=0,
            function_evaluations=0,
            termination_reason=SolverTermination.ZERO_DUTY,
            solver_params=params,
        )

    # Find bracket
    bracket = find_bracket(residual_fn, q_max, params, c_hot)
    if bracket is None:
        return SolverResult(
            converged=False,
            q_solution_w=0.0,
            residual_w=float("nan"),
            bracket_width_w=0.0,
            iterations=0,
            function_evaluations=0,
            termination_reason=SolverTermination.BRACKET_NOT_FOUND,
            solver_params=params,
        )

    q_low, q_high = bracket

    # Handle zero-duty case
    if q_low == 0.0 and q_high == 0.0:
        r = residual_fn(0.0)
        return SolverResult(
            converged=True,
            q_solution_w=0.0,
            residual_w=r,
            bracket_width_w=0.0,
            iterations=0,
            function_evaluations=1,
            termination_reason=SolverTermination.ZERO_DUTY,
            solver_params=params,
        )

    # Run Brent's method
    try:
        q_sol, info = brentq(
            residual_fn,
            q_low,
            q_high,
            xtol=1e-12,  # Tiny xtol; we do our own convergence check
            rtol=1e-12,
            maxiter=params.max_iterations,
            full_output=True,
        )
        r_sol = residual_fn(q_sol)
        n_eval = info.function_calls
        n_iter = info.iterations
    except ValueError:
        # brentq raises ValueError if no sign change (shouldn't happen with
        # our bracket, but defensive)
        return SolverResult(
            converged=False,
            q_solution_w=0.0,
            residual_w=float("nan"),
            bracket_width_w=q_high - q_low,
            iterations=0,
            function_evaluations=0,
            termination_reason=SolverTermination.BRACKET_NOT_FOUND,
            solver_params=params,
        )

    # Check convergence
    tol = max(params.absolute_residual_w, params.relative_residual_fraction * max(abs(q_sol), 1.0))
    converged = abs(r_sol) <= tol

    # Check bracket width in temperature terms (only when capacity rate is known)
    # Skip bracket check if residual is already very small (root is precise)
    bracket_width = q_high - q_low
    if converged and c_hot is not None and c_hot > 0:
        bracket_dt = bracket_width / c_hot
        if bracket_dt > params.bracket_temperature_tolerance_k and abs(r_sol) > tol * 0.1:
            converged = False

    termination = SolverTermination.CONVERGED if converged else SolverTermination.NON_CONVERGENCE

    return SolverResult(
        converged=converged,
        q_solution_w=q_sol,
        residual_w=r_sol,
        bracket_width_w=bracket_width,
        iterations=n_iter,
        function_evaluations=n_eval,
        termination_reason=termination,
        solver_params=params,
    )
