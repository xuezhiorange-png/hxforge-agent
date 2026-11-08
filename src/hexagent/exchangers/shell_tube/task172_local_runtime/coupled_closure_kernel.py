"""Coupled wall-temperature local thermal closure for Task172 (reference kernel).

Physics (hot tube / cold shell convention as in ``service._eval_trial``):

  Q_i    = G_i(Twi) * (T_hot - Twi)
  Q_wall = G_wall * (Twi - Two)
  Q_o    = G_o(Two) * (Two - T_cold)

Closure is a root in (Twi, Two) with shell_bulk <= Two <= Twi <= tube_bulk and Q_i = Q_wall = Q_o.
The reported DOF ``q_ts`` is recovered by a bounded 1-D feasibility search on the W residual
acceptance gate (not scipy ``success`` alone).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import numpy as np
from scipy.optimize import brentq, least_squares

TrialEvaluator = Callable[[float, float, float], dict[str, Any]]
AcceptSolution = Callable[
    [tuple[float, float, float], Any],
    tuple[dict[str, Any], tuple[float, float, float]],
]


class ClosureResourceExhausted(Exception):
    """Raised when callback budget is exhausted."""


def _branch_heat_rates_w(
    evaluated: dict[str, Any],
    *,
    tube_bulk_k: float,
    shell_bulk_k: float,
    twi_value: float,
    two_value: float,
) -> tuple[float, float, float]:
    g_i = float(evaluated["g_i"])
    g_wall = float(evaluated["g_wall"])
    g_o = float(evaluated["g_o"])
    q_inner = g_i * (tube_bulk_k - twi_value)
    q_wall = g_wall * (twi_value - two_value)
    q_outer = g_o * (two_value - shell_bulk_k)
    return q_inner, q_wall, q_outer


def _temperatures_from_u(
    u1: float,
    u2: float,
    *,
    tube_bulk_k: float,
    shell_bulk_k: float,
) -> tuple[float, float]:
    u1c = min(max(float(u1), 0.0), 1.0)
    u2c = min(max(float(u2), 0.0), 1.0)
    span = tube_bulk_k - shell_bulk_k
    if span <= 0.0:
        raise ValueError("non-positive bulk temperature span")
    two = shell_bulk_k + u1c * span
    twi = two + u2c * (tube_bulk_k - two)
    return twi, two


def _flux_imbalance_at_wall_temperatures(
    twi: float,
    two: float,
    *,
    tube_bulk_k: float,
    shell_bulk_k: float,
    evaluate_trial: TrialEvaluator,
) -> tuple[np.ndarray, dict[str, Any]]:
    if not shell_bulk_k <= two <= twi <= tube_bulk_k:
        return np.asarray([1.0, 1.0], dtype=float), {}
    evaluated = evaluate_trial(0.0, twi, two)
    q_inner, q_wall, q_outer = _branch_heat_rates_w(
        evaluated,
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
        twi_value=twi,
        two_value=two,
    )
    scale = max(abs(q_wall), 1.0)
    imbalance = np.asarray([(q_inner - q_wall) / scale, (q_wall - q_outer) / scale], dtype=float)
    return imbalance, evaluated


def _max_residual_ratio(
    q_ts: float,
    twi: float,
    two: float,
    evaluate_trial: TrialEvaluator,
) -> float:
    evaluated = evaluate_trial(float(q_ts), twi, two)
    residuals = evaluated["residuals"]
    bounds = evaluated["bounds"]
    ratios: list[float] = []
    for residual, bound in zip(residuals, bounds, strict=True):
        if bound <= 0.0 or not math.isfinite(bound):
            return math.inf
        ratios.append(abs(float(residual)) / float(bound))
    return max(ratios)


def _select_q_ts_for_acceptance(
    twi: float,
    two: float,
    *,
    tube_bulk_k: float,
    shell_bulk_k: float,
    evaluate_trial: TrialEvaluator,
    q_anchor: float,
) -> float:
    """Pick ``q_ts`` near branch rates; refine with a 1-D bracket on the acceptance ratio."""
    probe = evaluate_trial(float(q_anchor), twi, two)
    q_inner, q_wall, q_outer = _branch_heat_rates_w(
        probe,
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
        twi_value=twi,
        two_value=two,
    )
    low = min(q_inner, q_wall, q_outer)
    high = max(q_inner, q_wall, q_outer)
    if not math.isfinite(low) or not math.isfinite(high):
        return float(q_wall)
    if high - low <= max(math.ulp(high), 1e-18):
        return float(q_wall)

    def ratio_minus_one(q_ts: float) -> float:
        return _max_residual_ratio(q_ts, twi, two, evaluate_trial) - 1.0

    if ratio_minus_one(float(q_wall)) <= 0.0:
        return float(q_wall)

    try:
        r_lo = ratio_minus_one(low)
        r_hi = ratio_minus_one(high)
        if r_lo <= 0.0:
            return float(low)
        if r_hi <= 0.0:
            return float(high)
        if r_lo * r_hi > 0.0:
            return float(q_wall)
        root = brentq(ratio_minus_one, low, high, maxiter=64, xtol=1e-15, rtol=1e-12)
        return float(root)
    except (ValueError, RuntimeError):
        return float(q_wall)


def solve_coupled_local_closure(
    *,
    tube_bulk_k: float,
    shell_bulk_k: float,
    wall_inner_seed: float,
    wall_outer_seed: float,
    evaluate_trial: TrialEvaluator,
    accept_solution: AcceptSolution,
    accept_context: Any,
    callback_budget: int,
    callback_counter: list[int],
    method_label: str,
) -> tuple[dict[str, Any], tuple[float, float, float], int, str]:
    """Solve coupled closure; raise ``ClosureResourceExhausted`` on budget exceed."""
    if callback_counter[0] >= callback_budget:
        raise ClosureResourceExhausted("solver.callback_cap")

    span = tube_bulk_k - shell_bulk_k
    if span <= 0.0:
        raise ValueError("invalid bulk span")

    # Seeds in monotone (two, twi) parameterization
    two0 = min(max(wall_outer_seed, shell_bulk_k), tube_bulk_k)
    twi0 = min(max(wall_inner_seed, two0), tube_bulk_k)
    u1_0 = (two0 - shell_bulk_k) / span
    u2_0 = (twi0 - two0) / max(tube_bulk_k - two0, 1e-30)

    evaluations_before = callback_counter[0]

    def residual_u(values: np.ndarray) -> np.ndarray:
        if callback_counter[0] >= callback_budget:
            raise ClosureResourceExhausted("solver.callback_cap")
        twi, two = _temperatures_from_u(
            float(values[0]),
            float(values[1]),
            tube_bulk_k=tube_bulk_k,
            shell_bulk_k=shell_bulk_k,
        )
        imbalance, _ = _flux_imbalance_at_wall_temperatures(
            twi,
            two,
            tube_bulk_k=tube_bulk_k,
            shell_bulk_k=shell_bulk_k,
            evaluate_trial=evaluate_trial,
        )
        return imbalance

    result = least_squares(
        residual_u,
        np.asarray([u1_0, u2_0], dtype=float),
        method="trf",
        bounds=([0.0, 0.0], [1.0, 1.0]),
        ftol=1e-12,
        xtol=1e-14,
        gtol=1e-12,
        max_nfev=min(120, max(callback_budget - callback_counter[0], 8)),
    )
    twi_root, two_root = _temperatures_from_u(
        float(result.x[0]),
        float(result.x[1]),
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
    )
    _, probe_eval = _flux_imbalance_at_wall_temperatures(
        twi_root,
        two_root,
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
        evaluate_trial=evaluate_trial,
    )
    q_inner, q_wall, q_outer = _branch_heat_rates_w(
        probe_eval,
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
        twi_value=twi_root,
        two_value=two_root,
    )
    q_ts = _select_q_ts_for_acceptance(
        twi_root,
        two_root,
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
        evaluate_trial=evaluate_trial,
        q_anchor=q_wall,
    )
    evaluated, solution = accept_solution((q_ts, twi_root, two_root), accept_context)
    nfev = callback_counter[0] - evaluations_before
    solver_status = f"V08_03_COUPLED_WALL_CLOSURE_{method_label.upper()}"
    return evaluated, solution, nfev, solver_status


def residual_acceptance_feasible_at_walls(
    twi: float,
    two: float,
    *,
    tube_bulk_k: float,
    shell_bulk_k: float,
    evaluate_trial: TrialEvaluator,
    q_anchor: float,
) -> tuple[bool, float, float]:
    """Return whether some ``q_ts`` passes the original W acceptance gate (ratio <= 1)."""
    q_ts = _select_q_ts_for_acceptance(
        twi,
        two,
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
        evaluate_trial=evaluate_trial,
        q_anchor=q_anchor,
    )
    ratio = _max_residual_ratio(q_ts, twi, two, evaluate_trial)
    return ratio <= 1.0, q_ts, ratio
