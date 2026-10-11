"""Experimental Task172 local solve — memoized _eval_trial only (non-authoritative)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from hexagent.exchangers.shell_tube.task172_local_runtime import service as production
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172BlockedResult,
    Task172LocalOutcome,
    Task172LocalRequest,
    Task172LocalResult,
)
from hexagent.properties.base import PropertyProvider

Task172Request = Task172LocalRequest | CandidateTask172LocalRequest


@dataclass
class EvalTrialMemoStats:
    trial_invocations: int = 0
    production_eval_calls: int = 0
    cache_hits: int = 0
    unique_eval_keys: int = 0
    wall_seconds: float = 0.0


@dataclass
class ExperimentalSolveReport:
    outcome: Task172LocalOutcome
    stats: EvalTrialMemoStats
    solver_path: str = "production._solve_with_memoized_eval_trial"


def _quantize_key(q: float, twi: float, two: float) -> tuple[float, float, float]:
    """Match binary64 trial coordinates used in TASK173 cell search."""
    return (float(q), float(twi), float(two))


def solve_with_memoized_eval_trial(
    request: Task172Request,
    provider: PropertyProvider,
) -> ExperimentalSolveReport:
    """Run production TRF/Dogbox path with duplicate-safe _eval_trial memoization."""
    stats = EvalTrialMemoStats()
    cache: dict[tuple[float, float, float], dict[str, Any]] = {}
    original_eval: Callable[..., dict[str, Any]] = production._eval_trial

    def memo_eval(*args: Any, **kwargs: Any) -> dict[str, Any]:
        stats.trial_invocations += 1
        if len(args) < 10:
            return original_eval(*args, **kwargs)
        q_hc = float(args[7])
        wall_inner = float(args[8])
        wall_outer = float(args[9])
        key = _quantize_key(q_hc, wall_inner, wall_outer)
        cached = cache.get(key)
        if cached is not None:
            stats.cache_hits += 1
            return cached
        result = original_eval(*args, **kwargs)
        stats.production_eval_calls += 1
        cache[key] = result
        return result

    production._eval_trial = memo_eval  # type: ignore[method-assign]
    t0 = time.perf_counter()
    try:
        outcome = production._solve(request, provider)
    finally:
        production._eval_trial = original_eval  # type: ignore[method-assign]
        stats.wall_seconds = time.perf_counter() - t0
        stats.unique_eval_keys = len(cache)
    return ExperimentalSolveReport(outcome=outcome, stats=stats)


def compare_outcomes(
    baseline: Task172LocalOutcome,
    experimental: Task172LocalOutcome,
) -> dict[str, Any]:
    """Structured comparison without claiming authority equivalence."""
    same_type = type(baseline) is type(experimental)
    comparison: dict[str, Any] = {
        "same_outcome_type": same_type,
        "baseline_type": type(baseline).__name__,
        "experimental_type": type(experimental).__name__,
        "result_hash_parity": False,
        "signed_q_delta": None,
        "wall_temperature_delta": None,
        "authority_change_required": True,
    }
    if type(baseline) is Task172LocalResult and type(experimental) is Task172LocalResult:
        comparison["result_hash_parity"] = baseline.result_hash == experimental.result_hash
        comparison["signed_q_delta"] = float(experimental.signed_q_hot_to_cold_w) - float(
            baseline.signed_q_hot_to_cold_w
        )
        comparison["wall_temperature_delta"] = {
            "wall_inner_k": float(experimental.wall_temperature_inner_k)
            - float(baseline.wall_temperature_inner_k),
            "wall_outer_k": float(experimental.wall_temperature_outer_k)
            - float(baseline.wall_temperature_outer_k),
        }
        comparison["residual_acceptance_match"] = (
            baseline.residual_acceptance_state == experimental.residual_acceptance_state
        )
        comparison["solver_status_match"] = baseline.solver_status == experimental.solver_status
        comparison["authority_change_required"] = not comparison["result_hash_parity"]
    elif type(baseline) is Task172BlockedResult and type(experimental) is Task172BlockedResult:
        comparison["failure_code_match"] = baseline.failure_code == experimental.failure_code
        comparison["blocked_hash_parity"] = (
            baseline.blocked_result_hash == experimental.blocked_result_hash
        )
        comparison["authority_change_required"] = not comparison.get("blocked_hash_parity", False)
    return comparison
