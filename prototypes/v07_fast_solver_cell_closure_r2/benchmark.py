#!/usr/bin/env python3
"""R2: R1 baseline vs R2 coupled cell — two replicates, full cell receipts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import signal
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    H_MAX_J_KG,
    H_MIN_J_KG,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_architecture_r1.mesh_march import fast_valid_trajectory

TASK_ID = "V07_FAST_SOLVER_CELL_CLOSURE_R2"
SOURCE_HEAD = "a392cd10858b9d9d21185c744e33d7f07ccb8b6a"
SHOOTING_ENTHALPY_FRAC = Decimal("0.5")
PER_RUN_BUDGET_S = 90.0
REPLICATE_COUNT = 2
MESH_LEVELS = (1, 2, 4)
RND_SPEEDUP_TARGET = 1.5


def _load_candidate_b_context() -> Any:
    runner = (
        ROOT
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate request runner unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _candidate, rating_request = mod._build_candidate_requests()[
        "e152cca9-fd5d-59ca-9b46-1df574eee841"
    ]
    return t173._candidate_context(rating_request)


def _observables(run: Any) -> dict[str, Any]:
    obs = run.observables
    return {
        "mesh_result_hash": run.mesh_result_hash,
        "total_duty_w": str(obs.total_duty_w),
        "tube_outlet_temperature_k": str(obs.tube_outlet_temperature_k),
        "shell_outlet_temperature_k": str(obs.shell_outlet_temperature_k),
        "energy_balance_residual_w": str(obs.energy_balance_residual_w),
        "production_canonical_task172_local_evaluation_count": obs.task172_local_evaluation_count,
    }


def _run_timed(budget_s: float, fn: Any) -> tuple[Any, float, str]:
    class _Timeout(Exception):
        pass

    def _alarm(*_a: Any) -> None:
        raise _Timeout()

    prev = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, budget_s)
    t0 = time.perf_counter()
    status = "COMPLETED"
    try:
        out = fn()
    except _Timeout:
        status = "TIMEOUT"
        out = None
    except Exception as exc:
        status = f"ERROR:{type(exc).__name__}"
        out = None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prev)
    return out, time.perf_counter() - t0, status


def _mesh_case(
    *,
    subdivisions: int,
    shooting: Decimal,
    context: Any,
    cell_solver: str,
    replicate: int,
) -> dict[str, Any]:
    provider_prod = CoolPropProvider(cache_size=2048)
    provider_fast = CoolPropProvider(cache_size=2048)

    def production_march() -> Any:
        return t173._valid_trajectory(
            subdivisions, shooting, provider_prod, context.shell_authority, 0
        )

    def fast_march() -> Any:
        return fast_valid_trajectory(
            subdivisions,
            shooting,
            provider_fast,
            context.shell_authority,
            0,
            cell_solver=cell_solver,
        )

    prod_run, prod_s, prod_status = _run_timed(PER_RUN_BUDGET_S, production_march)
    fast_out, fast_s, fast_status = _run_timed(PER_RUN_BUDGET_S, fast_march)
    fast_run = fast_out[0] if fast_out is not None else None
    fast_stats = fast_out[1] if fast_out is not None else None
    comparison: dict[str, Any] = {}
    if prod_run is not None and fast_run is not None:
        comparison = {
            "duty_delta_w": float(
                fast_run.observables.total_duty_w - prod_run.observables.total_duty_w
            ),
            "tube_outlet_delta_k": float(
                fast_run.observables.tube_outlet_temperature_k
                - prod_run.observables.tube_outlet_temperature_k
            ),
            "mesh_hash_parity": fast_run.mesh_result_hash == prod_run.mesh_result_hash,
            "local_task172_hash_parity": (
                fast_run.observables.local_task172_result_hashes
                == prod_run.observables.local_task172_result_hashes
            ),
        }
    speedup = prod_s / fast_s if fast_s > 0 and prod_status == "COMPLETED" else None
    fallback_reasons: dict[str, int] = {}
    if fast_stats is not None:
        for receipt in fast_stats.cell_receipts:
            code = receipt.get("fallback_reason_code")
            if code:
                fallback_reasons[code] = fallback_reasons.get(code, 0) + 1
    return {
        "replicate": replicate,
        "subdivisions": subdivisions,
        "production": {
            "status": prod_status,
            "wall_seconds": prod_s,
            "observables": _observables(prod_run) if prod_run else None,
        },
        "fast_solver": {
            "variant": cell_solver,
            "status": fast_status,
            "wall_seconds": fast_s,
            "experimental_total_production_task172_calls": (
                fast_stats.experimental_total_production_task172_calls if fast_stats else None
            ),
            "experimental_total_eval_trial_calls": (
                fast_stats.total_eval_trial_calls if fast_stats else None
            ),
            "coupled_fallback_count": (fast_stats.coupled_fallback_count if fast_stats else None),
            "fallback_reason_histogram": fallback_reasons,
            "cell_receipts": fast_stats.cell_receipts if fast_stats else None,
            "observables": _observables(fast_run) if fast_run else None,
        },
        "comparison": comparison,
        "speedup_vs_production_march": speedup,
    }


def run_benchmark() -> dict[str, Any]:
    context = _load_candidate_b_context()
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    shooting = H_MIN_J_KG + (H_MAX_J_KG - H_MIN_J_KG) * SHOOTING_ENTHALPY_FRAC
    try:
        r1_cases: list[dict[str, Any]] = []
        r2_cases: list[dict[str, Any]] = []
        for replicate in range(1, REPLICATE_COUNT + 1):
            for n in MESH_LEVELS:
                r1_cases.append(
                    _mesh_case(
                        subdivisions=n,
                        shooting=shooting,
                        context=context,
                        cell_solver="r1",
                        replicate=replicate,
                    )
                )
                r2_cases.append(
                    _mesh_case(
                        subdivisions=n,
                        shooting=shooting,
                        context=context,
                        cell_solver="r2",
                        replicate=replicate,
                    )
                )
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)

    def speedups(cases: list[dict[str, Any]], n: int) -> list[float]:
        return [
            c["speedup_vs_production_march"]
            for c in cases
            if c["subdivisions"] == n and c["speedup_vs_production_march"] is not None
        ]

    def mean(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    r2_n1 = mean(speedups(r2_cases, 1))
    r2_n2 = mean(speedups(r2_cases, 2))
    r2_n4 = mean(speedups(r2_cases, 4))
    n2_fb = max(
        c["fast_solver"]["coupled_fallback_count"] or 0 for c in r2_cases if c["subdivisions"] == 2
    )
    n4_fb = max(
        c["fast_solver"]["coupled_fallback_count"] or 0 for c in r2_cases if c["subdivisions"] == 4
    )
    rnd_ok = (
        r2_n2 is not None
        and r2_n4 is not None
        and r2_n2 >= RND_SPEEDUP_TARGET
        and r2_n4 >= RND_SPEEDUP_TARGET
        and n2_fb <= 2
        and n4_fb <= 3
    )
    return {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_HEAD,
        "result": (
            "FAST_SOLVER_CELL_CLOSURE_R2_GOAL_MET"
            if rnd_ok
            else "CELL_LEVEL_ARCHITECTURE_SPEEDUP_INSUFFICIENT"
        ),
        "fallback_root_causes_r1": {
            "primary": "BLOCKED_COUPLED_NONCONVERGENCE",
            "note": "R1 TRF max_nfev=8 without mesh continuation; coarse algebraic seed only",
        },
        "r2_improvement": (
            "Mesh continuation warm-start (q,Twi,Two) + production-aligned TRF then Dogbox "
            f"(max_nfev={12})"
        ),
        "shooting_enthalpy_j_kg": str(shooting),
        "replicate_count": REPLICATE_COUNT,
        "r1_baseline_cases": r1_cases,
        "r2_improved_cases": r2_cases,
        "summary": {
            "r2_mean_speedup_n1": r2_n1,
            "r2_mean_speedup_n2": r2_n2,
            "r2_mean_speedup_n4": r2_n4,
            "r2_max_fallback_n2": n2_fb,
            "r2_max_fallback_n4": n4_fb,
            "rnd_speedup_target": RND_SPEEDUP_TARGET,
        },
        "cell_level_architecture_decision": (
            "CONTINUE_CELL_COUPLING_WITH_R2_AUTHORITY_CANDIDATE"
            if rnd_ok
            else "PIVOT_TO_GLOBAL_COUPLING_OR_ALGEBRAIC_REDUCTION"
        ),
        "authority_status": "CANDIDATE_V07_FAST_SOLVER_COUPLED_CELL_R2",
        "production_integration": False,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-cell-closure-r2.json",
    )
    args = parser.parse_args()
    payload = run_benchmark()
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(json.dumps({"output": str(args.output), "sha256": digest, "result": payload["result"]}))


if __name__ == "__main__":
    main()
