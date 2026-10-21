"""Profile property-provider TP calls on a representative native cell."""

# ruff: noqa: E501

from __future__ import annotations

import time
from collections import Counter
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.experimental_tp_cache import (
    EphemeralTpCacheStats,
    _tp_key,
    install_ephemeral_tp_cache,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import NativeCellContext


def _feasible_shell_physical_left(provider: CoolPropProvider) -> Any:
    from decimal import Decimal

    state = provider.state_tp(FluidIdentifier("Water", "HEOS"), 298.5, 101325.0)
    return t173._state_from_enthalpy(provider, Decimal(str(state.enthalpy_j_kg)))


def profile_representative_cell_tp_calls(
    native: NativeCellContext,
    *,
    q_trials_w: tuple[float, ...] = (0.0, 50.0, 500.0, 2000.0, 8000.0, 12000.0),
) -> dict[str, Any]:
    provider = CoolPropProvider()
    key_counter: Counter[tuple[Any, ...]] = Counter()
    call_times: list[float] = []
    original = provider.state_tp

    def instrumented_state_tp(fluid: Any, temperature_k: float, pressure_pa: float) -> Any:
        key = _tp_key(fluid, temperature_k, pressure_pa)
        key_counter[key] += 1
        t0 = time.perf_counter()
        result = original(fluid, temperature_k, pressure_pa)
        call_times.append(time.perf_counter() - t0)
        return result

    provider.state_tp = instrumented_state_tp  # type: ignore[method-assign]
    tube = t173._state_at_inlet(provider, t173.TUBE_INLET_T_K)
    shell = _feasible_shell_physical_left(provider)
    token = t173._CANDIDATE_RATING_CONTEXT.set(native.context)
    task172_evaluations = 0
    task172_hashes: list[str] = []
    try:
        for q in q_trials_w:
            try:
                evaluation = t173._cell_evaluation(
                    q,
                    support=native.support,
                    tube_upstream=tube,
                    shell_physical_left=shell,
                    provider=provider,
                    shell_authority=native.shell_authority,
                )
                task172_evaluations += 1
                task172_hashes.append(evaluation.task172_result.result_hash)
            except (t173._LowSideDomainInfeasible, t173._Stage3Failure, t173._Task172NumericalHole):
                continue
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)

    total_calls = sum(key_counter.values())
    unique_keys = len(key_counter)
    duplicate_calls = total_calls - unique_keys
    return {
        "schema_version": "hxforge.property-provider-call-profile.v1",
        "q_trials_w": list(q_trials_w),
        "property_provider_state_tp_calls": total_calls,
        "unique_tp_keys": unique_keys,
        "exact_duplicate_tp_queries": duplicate_calls,
        "exact_duplicate_rate": duplicate_calls / total_calls if total_calls else 0.0,
        "mean_state_tp_seconds": sum(call_times) / len(call_times) if call_times else 0.0,
        "task172_constitutive_evaluations": task172_evaluations,
        "task172_result_hashes_sampled": task172_hashes,
        "task172_request_hash_collection": "NOT_MEASURED",
    }


def run_tp_cache_ab_parity(
    native: NativeCellContext,
    *,
    q_trials_w: tuple[float, ...] = (50.0, 500.0, 2000.0, 8000.0),
) -> dict[str, Any]:
    def run_once(use_cache: bool) -> tuple[list[str], list[str], float, EphemeralTpCacheStats | None]:
        provider = CoolPropProvider()
        cache_stats: EphemeralTpCacheStats | None = None
        if use_cache:
            cache_stats, _ = install_ephemeral_tp_cache(provider)
        tube = t173._state_at_inlet(provider, t173.TUBE_INLET_T_K)
        shell = _feasible_shell_physical_left(provider)
        token = t173._CANDIDATE_RATING_CONTEXT.set(native.context)
        result_hashes: list[str] = []
        request_hashes: list[str] = []
        t0 = time.perf_counter()
        try:
            for q in q_trials_w:
                evaluation = t173._cell_evaluation(
                    q,
                    support=native.support,
                    tube_upstream=tube,
                    shell_physical_left=shell,
                    provider=provider,
                    shell_authority=native.shell_authority,
                )
                result_hashes.append(evaluation.task172_result.result_hash)
                request_hashes.append(evaluation.task172_result.request_hash)
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)
        return result_hashes, request_hashes, time.perf_counter() - t0, cache_stats

    baseline_hashes, baseline_request_hashes, baseline_wall, _ = run_once(False)
    cached_hashes, cached_request_hashes, cached_wall, cache_stats = run_once(True)
    parity = baseline_hashes == cached_hashes and baseline_request_hashes == cached_request_hashes
    reduction = (baseline_wall - cached_wall) / baseline_wall * 100.0 if baseline_wall > 0 else 0.0
    call_reduction = 0.0
    if cache_stats is not None and cache_stats.provider_calls > 0:
        call_reduction = cache_stats.cache_hits / cache_stats.provider_calls * 100.0
    return {
        "schema_version": "hxforge.tp-cache-ab-parity.v1",
        "numerical_parity": parity,
        "baseline_task172_result_hashes": baseline_hashes,
        "cached_task172_result_hashes": cached_hashes,
        "baseline_task172_request_hashes": baseline_request_hashes,
        "cached_task172_request_hashes": cached_request_hashes,
        "task172_request_hash_parity": baseline_request_hashes == cached_request_hashes,
        "baseline_wall_seconds": round(baseline_wall, 6),
        "cached_wall_seconds": round(cached_wall, 6),
        "wall_time_reduction_percent": reduction,
        "cache_stats": cache_stats.to_dict() if cache_stats else None,
        "provider_call_reduction_percent": call_reduction,
    }
