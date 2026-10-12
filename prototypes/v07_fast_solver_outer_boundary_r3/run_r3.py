#!/usr/bin/env python3
"""R3 outer boundary runner (subprocess-friendly, bounded wall clock)."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import (
    OUTER_BOUNDARY_AUTHORITY_ID,
    observables_summary,
    solve_fast_outer_boundary,
)

TASK_ID = "V07_FAST_SOLVER_OUTER_BOUNDARY_R3"
SOURCE_SHA = "aa835b7f439684e5d49fd0bc2994020819bcdd6c"
CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"


def _load_candidate_context() -> Any:
    runner = (
        ROOT
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate request runner unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _candidate, rating_request = mod._build_candidate_requests()[CANDIDATE_B_ID]
    return t173._candidate_context(rating_request), rating_request


def _solve_worker(payload: dict[str, Any]) -> dict[str, Any]:
    subdivisions = int(payload["subdivisions"])
    budget_s = float(payload["budget_s"])
    deadline = time.perf_counter() + budget_s
    context, rating_request = _load_candidate_context()
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    t0 = time.perf_counter()
    try:
        if time.perf_counter() > deadline:
            return {"status": "TIMEOUT", "reason": "budget_before_start"}
        result = solve_fast_outer_boundary(
            subdivisions, provider, context.shell_authority
        )
        if time.perf_counter() > deadline:
            return {
                "status": "TIMEOUT",
                "partial": _result_payload(result, subdivisions, rating_request),
                "elapsed_s": time.perf_counter() - t0,
            }
        return {
            "status": "COMPLETED",
            "result": _result_payload(result, subdivisions, rating_request),
            "elapsed_s": time.perf_counter() - t0,
        }
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def _result_payload(result: Any, subdivisions: int, rating_request: Any) -> dict[str, Any]:
    run = result.mesh_run
    summary = observables_summary(run) if run is not None else {}
    return {
        "subdivisions": subdivisions,
        "outer_boundary_status": result.status,
        "blocked_code": result.blocked_code,
        "blocked_diagnostics": list(result.blocked_diagnostics),
        "shooting_enthalpy_j_kg": result.shooting_enthalpy_j_kg,
        "observables": summary,
        "outer_trial_count": result.stats.outer_trial_count,
        "mesh_march_count": result.stats.mesh_march_count,
        "experimental_total_eval_trial_calls": result.stats.total_eval_trial_calls,
        "experimental_total_production_task172_calls": (
            result.stats.experimental_total_production_task172_calls
        ),
        "bisection_iterations": result.stats.bisection_iterations,
        "total_wall_seconds": result.stats.total_wall_seconds,
        "trial_receipts": [r.to_dict() for r in result.stats.trial_receipts],
        "authority_id": OUTER_BOUNDARY_AUTHORITY_ID,
        "candidate_id": rating_request.candidate_id,
        "rating_request_hash": t173.candidate_rating_request_hash(rating_request),
    }


def run_bounded(subdivisions: int, budget_s: float) -> dict[str, Any]:
    ctx = mp.get_context("spawn")
    with ctx.Pool(1) as pool:
        async_result = pool.apply_async(
            _solve_worker,
            ({"subdivisions": subdivisions, "budget_s": budget_s},),
        )
        try:
            return async_result.get(timeout=budget_s + 5.0)
        except mp.TimeoutError:
            pool.terminate()
            return {
                "status": "TIMEOUT",
                "reason": "worker_join_timeout",
                "subdivisions": subdivisions,
            }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget-s", type=float, default=480.0)
    parser.add_argument("--n1-budget-s", type=float, default=420.0)
    parser.add_argument("--n2-budget-s", type=float, default=90.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-outer-boundary-r3.json",
    )
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "candidate_b_id": CANDIDATE_B_ID,
        "runs": [],
    }
    n1 = run_bounded(1, min(args.n1_budget_s, args.budget_s))
    payload["runs"].append({"mesh_n": 1, **n1})
    n1_accepted = (
        n1.get("status") == "COMPLETED"
        and n1.get("result", {}).get("outer_boundary_status") == "TERMINAL_ACCEPTED"
        and n1.get("result", {}).get("observables", {}).get("terminal_tolerance_pass") == "True"
    )
    remaining = args.budget_s - (time.perf_counter() - wall_t0)
    n2_result: dict[str, Any] | None = None
    if n1_accepted and remaining > 30.0:
        n2_budget = min(args.n2_budget_s, remaining - 5.0)
        n2_result = run_bounded(2, n2_budget)
        payload["runs"].append({"mesh_n": 2, **n2_result})
    else:
        payload["n2_skipped_reason"] = (
            "N1_NOT_TERMINAL_ACCEPTED" if not n1_accepted else "BUDGET_EXHAUSTED"
        )

    if n1.get("status") == "TIMEOUT":
        payload["result"] = "TIMEOUT"
    elif n1_accepted:
        payload["result"] = "N1_OUTER_BOUNDARY_TERMINAL_ACCEPTED"
    else:
        payload["result"] = n1.get("result", {}).get("outer_boundary_status", "BLOCKED")

    payload["total_wall_seconds"] = time.perf_counter() - wall_t0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(json.dumps({"output": str(args.output), "sha256": digest, "result": payload["result"]}))


if __name__ == "__main__":
    main()
