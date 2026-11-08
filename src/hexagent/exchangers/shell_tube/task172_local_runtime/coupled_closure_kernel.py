"""Coupled wall-temperature local thermal closure for Task172 (reference kernel)."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Any, Literal

import numpy as np
from scipy.optimize import brentq, least_squares

from .coupled_closure_accounting import CoupledClosureAccounting

TrialEvaluator = Callable[[float, float, float], dict[str, Any]]
AcceptSolution = Callable[
    [tuple[float, float, float], Any],
    tuple[dict[str, Any], tuple[float, float, float]],
]

CoupledLeastSquaresMethod = Literal["trf", "dogbox"]
_Q_TS_LATTICE_MAX_STEPS = 16
_Q_TS_BRENT_MAXITER = 24
_Q_TS_MIN_RESERVE = 12


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


def _remaining_callback_budget(callback_budget: int, callback_counter: list[int]) -> int:
    return max(0, int(callback_budget) - int(callback_counter[0]))


def _max_residual_ratio_from_evaluated(evaluated: dict[str, Any]) -> float:
    residuals = evaluated["residuals"]
    bounds = evaluated["bounds"]
    ratios: list[float] = []
    for residual, bound in zip(residuals, bounds, strict=True):
        if bound <= 0.0 or not math.isfinite(bound):
            return math.inf
        ratios.append(abs(float(residual)) / float(bound))
    return max(ratios)


def _max_residual_ratio(
    q_ts: float,
    twi: float,
    two: float,
    evaluate_trial: TrialEvaluator,
) -> float:
    evaluated = evaluate_trial(float(q_ts), twi, two)
    return _max_residual_ratio_from_evaluated(evaluated)


def _ratio_minus_one(
    q_ts: float,
    twi: float,
    two: float,
    evaluate_trial: TrialEvaluator,
) -> float:
    return _max_residual_ratio(q_ts, twi, two, evaluate_trial) - 1.0


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


def _distinct_q(*values: float) -> tuple[float, ...]:
    seen: set[float] = set()
    ordered: list[float] = []
    for item in values:
        key = float(item)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return tuple(ordered)


def _search_q_ts_for_acceptance(
    twi: float,
    two: float,
    *,
    tube_bulk_k: float,
    shell_bulk_k: float,
    evaluate_trial: TrialEvaluator,
    q_anchor: float,
    callback_budget: int,
    callback_counter: list[int],
    accounting: CoupledClosureAccounting | None = None,
    probe_evaluated: dict[str, Any] | None = None,
    q_ts_evaluate: TrialEvaluator | None = None,
) -> tuple[float, bool]:
    """Deterministic bounded search; returns (q_ts, accepted). Raises on budget exhaustion."""
    ratio_eval = q_ts_evaluate or evaluate_trial

    def budget_guard() -> None:
        if _remaining_callback_budget(callback_budget, callback_counter) <= 0:
            raise ClosureResourceExhausted("solver.callback_cap")

    remaining = _remaining_callback_budget(callback_budget, callback_counter)
    if remaining <= 0:
        raise ClosureResourceExhausted("solver.callback_cap")

    lattice_steps = min(_Q_TS_LATTICE_MAX_STEPS, max(3, remaining // 3))
    if probe_evaluated is not None:
        probe = probe_evaluated
    else:
        budget_guard()
        probe = ratio_eval(float(q_anchor), twi, two)
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
        raise ValueError("non-finite branch heat rates")

    # Branch-rate anchors (bounds depend on q_ts — search hint only, not a proof interval).
    for candidate_q in _distinct_q(q_wall, q_inner, q_outer):
        if probe_evaluated is not None and float(candidate_q) == float(q_anchor):
            ratio_anchor = _max_residual_ratio_from_evaluated(probe)
        else:
            budget_guard()
            ratio_anchor = _max_residual_ratio(candidate_q, twi, two, ratio_eval)
        if accounting is not None:
            accounting.q_ts_branch_precheck += 1
        if ratio_anchor <= 1.0:
            if accounting is not None:
                accounting.max_residual_ratio = ratio_anchor
                accounting.accepted = True
            return float(candidate_q), True

    if high - low <= max(math.ulp(high), 1e-18):
        budget_guard()
        ratio = _max_residual_ratio(low, twi, two, ratio_eval)
        return float(low), ratio <= 1.0

    lattice_ratios: list[tuple[float, float]] = []

    for step in range(lattice_steps + 1):
        budget_guard()
        fraction = float(step) / float(lattice_steps)
        q_point = low + fraction * (high - low)
        ratio_m1 = _ratio_minus_one(q_point, twi, two, ratio_eval)
        lattice_ratios.append((q_point, ratio_m1))
        if accounting is not None:
            accounting.q_ts_lattice_points += 1
        if ratio_m1 <= 0.0:
            if accounting is not None:
                accounting.max_residual_ratio = ratio_m1 + 1.0
                accounting.accepted = True
            return q_point, True

    for left_index in range(lattice_steps):
        q_left, r_left = lattice_ratios[left_index]
        q_right, r_right = lattice_ratios[left_index + 1]
        if r_left <= 0.0:
            return q_left, True
        if r_right <= 0.0:
            return q_right, True
        if r_left * r_right > 0.0:
            continue
        try:
            budget_guard()

            def _brent_target(q_ts: float) -> float:
                if accounting is not None:
                    accounting.q_ts_brent_iterations += 1
                return _ratio_minus_one(q_ts, twi, two, ratio_eval)

            root = brentq(
                _brent_target,
                q_left,
                q_right,
                maxiter=_Q_TS_BRENT_MAXITER,
                xtol=max(math.ulp(q_left), math.ulp(q_right), 1e-18),
                rtol=1e-12,
            )
            ratio_root = _ratio_minus_one(float(root), twi, two, ratio_eval)
            if ratio_root <= 0.0:
                if accounting is not None:
                    accounting.max_residual_ratio = ratio_root + 1.0
                    accounting.accepted = True
                return float(root), True
        except (ValueError, RuntimeError):
            continue

    best_q, best_ratio_m1 = min(lattice_ratios, key=lambda item: item[1])
    for direction in (-1.0, 1.0):
        neighbor = best_q
        toward = math.inf if direction > 0.0 else -math.inf
        for _ in range(8):
            budget_guard()
            neighbor = math.nextafter(neighbor, toward)
            if neighbor < low or neighbor > high:
                break
            if accounting is not None:
                accounting.q_ts_ulp_neighbors += 1
            ratio_m1 = _ratio_minus_one(neighbor, twi, two, ratio_eval)
            if ratio_m1 <= 0.0:
                if accounting is not None:
                    accounting.accepted = True
                    accounting.max_residual_ratio = ratio_m1 + 1.0
                return neighbor, True
            if ratio_m1 < best_ratio_m1:
                best_ratio_m1 = ratio_m1
                best_q = neighbor

    if accounting is not None:
        accounting.max_residual_ratio = best_ratio_m1 + 1.0
        accounting.accepted = best_ratio_m1 <= 0.0
    return float(best_q), best_ratio_m1 <= 0.0


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
    least_squares_method: CoupledLeastSquaresMethod,
    accounting: CoupledClosureAccounting | None = None,
) -> tuple[dict[str, Any], tuple[float, float, float], int, str]:
    """Solve coupled closure; raise ``ClosureResourceExhausted`` on budget exceed."""
    started = time.perf_counter()
    if accounting is not None:
        accounting.callback_cap = callback_budget

    if callback_counter[0] >= callback_budget:
        raise ClosureResourceExhausted("solver.callback_cap")

    span = tube_bulk_k - shell_bulk_k
    if span <= 0.0:
        raise ValueError("invalid bulk span")

    two0 = min(max(wall_outer_seed, shell_bulk_k), tube_bulk_k)
    twi0 = min(max(wall_inner_seed, two0), tube_bulk_k)
    u1_0 = (two0 - shell_bulk_k) / span
    u2_0 = (twi0 - two0) / max(tube_bulk_k - two0, 1e-30)

    evaluations_before = callback_counter[0]
    remaining_budget = _remaining_callback_budget(callback_budget, callback_counter)
    reserve_q = min(_Q_TS_MIN_RESERVE, max(8, remaining_budget // 3))
    max_nfev = min(120, max(remaining_budget - reserve_q, 4))
    if max_nfev < 4:
        raise ClosureResourceExhausted("solver.callback_cap")

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
        method=least_squares_method,
        bounds=([0.0, 0.0], [1.0, 1.0]),
        ftol=1e-12,
        xtol=1e-14,
        gtol=1e-12,
        max_nfev=max_nfev,
    )
    if accounting is not None:
        accounting.least_squares_reported_nfev = int(result.nfev)

    twi_root, two_root = _temperatures_from_u(
        float(result.x[0]),
        float(result.x[1]),
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
    )
    imbalance, probe_eval = _flux_imbalance_at_wall_temperatures(
        twi_root,
        two_root,
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
        evaluate_trial=evaluate_trial,
    )
    del imbalance
    q_inner, q_wall, _q_outer = _branch_heat_rates_w(
        probe_eval,
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
        twi_value=twi_root,
        two_value=two_root,
    )

    q_eval_trial = evaluate_trial

    def q_ts_eval(q: float, twi: float, two: float) -> dict[str, Any]:
        if accounting is not None:
            accounting.eval_trial_q_ts_search += 1
        return q_eval_trial(q, twi, two)

    q_ts, _accepted = _search_q_ts_for_acceptance(
        twi_root,
        two_root,
        tube_bulk_k=tube_bulk_k,
        shell_bulk_k=shell_bulk_k,
        evaluate_trial=evaluate_trial,
        q_anchor=q_wall,
        callback_budget=callback_budget,
        callback_counter=callback_counter,
        accounting=accounting,
        probe_evaluated=probe_eval,
        q_ts_evaluate=q_ts_eval,
    )

    evaluated, solution = accept_solution((q_ts, twi_root, two_root), accept_context)
    if accounting is not None:
        accounting.callback_used = callback_counter[0] - evaluations_before
        accounting.eval_trial_2d_flux = int(result.nfev) + 1
        accounting.eval_trial_total = accounting.callback_used
        accounting.eval_trial_accept = max(
            0,
            accounting.callback_used
            - accounting.eval_trial_2d_flux
            - accounting.eval_trial_q_ts_search,
        )
        accounting.wall_seconds = time.perf_counter() - started
        accounting.property_evaluations_estimated = accounting.callback_used
        if accounting.max_residual_ratio is None:
            accounting.max_residual_ratio = _max_residual_ratio_from_evaluated(evaluated)
    nfev = callback_counter[0] - evaluations_before
    solver_status = f"V08_03_COUPLED_WALL_CLOSURE_{least_squares_method.upper()}"
    if accounting is not None:
        accounting.solver_status = solver_status
    return evaluated, solution, nfev, solver_status
