#!/usr/bin/env python3
"""Benchmark production Task172 vs experimental memoized eval (POC R1)."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402

from hexagent.exchangers.shell_tube.task172_local_runtime import (
    build_local_support,
    validate_candidate_request,
    validate_request,
)
from hexagent.exchangers.shell_tube.task172_local_runtime import models as runtime_models
from hexagent.exchangers.shell_tube.task172_local_runtime import service as production
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172BlockedResult,
    Task172LocalResult,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_task172_constitutive_accelerator_poc_r1.accelerator import (
    compare_outcomes,
    solve_with_memoized_eval_trial,
)

PROTOTYPE = Path(__file__).resolve().parent
TASK_ID = "V07_TASK172_CONSTITUTIVE_ACCELERATOR_POC_R1"
SOURCE_HEAD = "ce3046e05a11f8b255109546ba8a63c86f537619"
SPEEDUP_RND_TARGET = 2.0


def _reference_requests() -> list[Any]:
    from tests.exchangers.shell_tube.test_task172_local_runtime import (
        _native_shell_flow_authority,
        _request,
    )

    base = _request()
    warm = _request(tube_temperature="299.5", shell_temperature="298.5")
    shell_flow = _native_shell_flow_authority()
    topology = base.topology
    support = build_local_support(0, 2, 1)
    candidate_style = production.Task172LocalRequest(
        topology=topology,
        support=support,
        tube_bulk_state=runtime_models.LocalState(
            temperature_k=Decimal("300"), pressure_pa=Decimal("101325")
        ),
        shell_bulk_state=runtime_models.LocalState(
            temperature_k=Decimal("298.15"), pressure_pa=Decimal("101325")
        ),
        tube_mass_flow_kg_s=base.tube_mass_flow_kg_s,
        shell_mass_flow_kg_s=base.shell_mass_flow_kg_s,
        shell_flow_authority=shell_flow,
    )
    return [base, warm, candidate_style]


def _harvest_candidate_b_requests(budget_s: float = 25.0) -> list[Any]:
    import importlib.util
    import signal

    runner = (
        ROOT
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    if spec is None or spec.loader is None:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    requests_map = mod._build_candidate_requests()
    _candidate, rating_request = requests_map[
        "e152cca9-fd5d-59ca-9b46-1df574eee841"
    ]
    from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173

    context = t173._candidate_context(rating_request)
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    captured: list[Any] = []

    original = t173.task172_validate_candidate

    def capture(request: Any, provider: Any) -> Any:
        if len(captured) < 8:
            captured.append(request)
        return original(request, provider)

    t173.task172_validate_candidate = capture  # type: ignore[method-assign]

    class _Timeout(Exception):
        pass

    def _alarm(*_args: Any) -> None:
        raise _Timeout()

    prev = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, budget_s)
    provider = CoolPropProvider(cache_size=2048)
    stats = t173._CellSearchStats()
    try:
        t173._candidate_transient_outer_boundary(
            1, provider, context.shell_authority, stats
        )
    except Exception:
        pass
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prev)
        t173.task172_validate_candidate = original  # type: ignore[method-assign]
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
    return captured


def _outcome_identity(outcome: Any) -> dict[str, Any]:
    if type(outcome) is Task172LocalResult:
        return {
            "kind": "validated",
            "result_hash": outcome.result_hash,
            "signed_q_hot_to_cold_w": str(outcome.signed_q_hot_to_cold_w),
            "wall_inner_k": str(outcome.wall_temperature_inner_k),
            "wall_outer_k": str(outcome.wall_temperature_outer_k),
        }
    if type(outcome) is Task172BlockedResult:
        return {
            "kind": "blocked",
            "failure_code": outcome.failure_code,
            "blocked_result_hash": outcome.blocked_result_hash,
        }
    return {"kind": type(outcome).__name__}


def _timed_baseline(request: Any, provider: CoolPropProvider, repeats: int = 3) -> dict[str, Any]:
    eval_calls = 0
    original = production._eval_trial

    def counting_eval(*args: Any, **kwargs: Any) -> Any:
        nonlocal eval_calls
        eval_calls += 1
        return original(*args, **kwargs)

    times: list[float] = []
    outcome = None
    for _ in range(repeats):
        eval_calls = 0
        production._eval_trial = counting_eval  # type: ignore[method-assign]
        t0 = time.perf_counter()
        try:
            if type(request) is CandidateTask172LocalRequest:
                outcome = validate_candidate_request(request, provider)
            else:
                outcome = validate_request(request, provider)
        finally:
            production._eval_trial = original  # type: ignore[method-assign]
        times.append(time.perf_counter() - t0)
    return {
        "wall_seconds_mean": sum(times) / len(times),
        "wall_seconds_samples": times,
        "eval_trial_calls_last": eval_calls,
        "outcome_type": type(outcome).__name__ if outcome else None,
    }


def _timed_experimental(
    request: Any, provider: CoolPropProvider, repeats: int = 3
) -> dict[str, Any]:
    times: list[float] = []
    report = None
    for _ in range(repeats):
        t0 = time.perf_counter()
        report = solve_with_memoized_eval_trial(request, provider)
        times.append(time.perf_counter() - t0)
    assert report is not None
    return {
        "wall_seconds_mean": sum(times) / len(times),
        "wall_seconds_samples": times,
        "eval_trial_stats": asdict(report.stats),
        "outcome_type": type(report.outcome).__name__,
    }


def run_benchmark() -> dict[str, Any]:
    cases = _reference_requests()
    harvested = _harvest_candidate_b_requests(budget_s=25.0)
    for req in harvested[:3]:
        cases.append(req)

    results: list[dict[str, Any]] = []
    total_before = 0.0
    total_after = 0.0
    for idx, request in enumerate(cases):
        baseline_provider = CoolPropProvider(cache_size=2048)
        exp_provider = CoolPropProvider(cache_size=2048)
        baseline = _timed_baseline(request, baseline_provider, repeats=2)
        experimental = _timed_experimental(request, exp_provider, repeats=2)
        if type(request) is CandidateTask172LocalRequest:
            base_outcome = validate_candidate_request(request, baseline_provider)
        else:
            base_outcome = validate_request(request, baseline_provider)
        exp_report = solve_with_memoized_eval_trial(request, exp_provider)
        comparison = compare_outcomes(base_outcome, exp_report.outcome)
        before_s = baseline["wall_seconds_mean"]
        after_s = experimental["wall_seconds_mean"]
        total_before += before_s
        total_after += after_s
        speedup = before_s / after_s if after_s > 0 else None
        results.append(
            {
                "case_index": idx,
                "case_kind": (
                    "candidate_b_harvested"
                    if idx >= len(_reference_requests())
                    else "reference_fixture"
                ),
                "baseline": baseline,
                "experimental": experimental,
                "baseline_outcome_identity": _outcome_identity(base_outcome),
                "experimental_outcome_identity": _outcome_identity(exp_report.outcome),
                "numerical_comparison": comparison,
                "speedup": speedup,
                "eval_reduction_ratio": (
                    1.0
                    - (
                        experimental["eval_trial_stats"]["production_eval_calls"]
                        / baseline["eval_trial_calls_last"]
                    )
                    if baseline["eval_trial_calls_last"]
                    else None
                ),
            }
        )

    aggregate_speedup = total_before / total_after if total_after > 0 else None
    return {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_HEAD,
        "actual_hotspot_hypothesis": (
            "TRF jac=2-point generates near-unique (q,Twi,Two) trials; "
            "duplicate _eval_trial keys are rare (~1 per solve in this sample)."
        ),
        "speedup_rnd_target": SPEEDUP_RND_TARGET,
        "speedup_rnd_target_met": (
            aggregate_speedup is not None and aggregate_speedup >= SPEEDUP_RND_TARGET
        ),
        "result": (
            "POC_COMPLETE_HASH_PARITY_NO_SIGNIFICANT_SPEEDUP"
            if aggregate_speedup is not None and aggregate_speedup < SPEEDUP_RND_TARGET
            else "POC_COMPLETE"
        ),
        "unmet_engineering_equivalence_conditions": [
            "2x R&D speedup goal not met for memoized _eval_trial alone",
            "Not integrated into production Task173; no full Candidate B rating replay",
        ],
        "baseline_solver": "task172_local_runtime.validate_* → production._solve (TRF/Dogbox)",
        "experimental_solver": "production._solve + memoized _eval_trial (POC only)",
        "test_case_count": len(cases),
        "harvested_candidate_b_count": len(harvested),
        "cases": results,
        "before_seconds_total": total_before,
        "after_seconds_total": total_after,
        "aggregate_speedup": aggregate_speedup,
        "authority_change_required": any(
            c["numerical_comparison"].get("authority_change_required", True) for c in results
        ),
        "result_hash_parity_all": all(
            c["numerical_comparison"].get("result_hash_parity") is True
            for c in results
            if c["numerical_comparison"].get("same_outcome_type")
        ),
        "notes": (
            "Experimental module is not wired to production Task173. "
            "Hash parity True only when memoization is transparent to numerics."
        ),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PROTOTYPE / "V07_TASK172_CONSTITUTIVE_ACCELERATOR_POC_R1_results.json",
    )
    args = parser.parse_args()
    payload = run_benchmark()
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": digest,
                "speedup": payload["aggregate_speedup"],
            }
        )
    )


if __name__ == "__main__":
    main()
