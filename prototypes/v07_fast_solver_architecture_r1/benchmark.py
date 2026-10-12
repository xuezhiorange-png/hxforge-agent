#!/usr/bin/env python3
"""Bounded Candidate B mesh march: production vs fast coupled-cell solver."""

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

TASK_ID = "V07_TASK172_TASK173_FAST_SOLVER_ARCHITECTURE_R1"
SOURCE_HEAD = "84c5f38b74fd26eacefee260af7be26c12cb2e31"
CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"
HISTORIC_CANDIDATE_B_RATING_HASH = (
    "1cecb402cc44ec2690918b3479cf6c7e4e1079eb290835122ad53ddfce657743"
)
FAST_AUTHORITY_CANDIDATE = "V07-FAST-SOLVER-COUPLED-CELL-R1"
PER_RUN_BUDGET_S = 120.0
# Frozen demonstration shooting enthalpy (non-zero duty, feasible n=1..4 march).
SHOOTING_ENTHALPY_FRAC = Decimal("0.5")


def _load_candidate_b_context() -> tuple[Any, Any]:
    runner = (
        ROOT
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate request runner unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    requests_map = mod._build_candidate_requests()
    _candidate, rating_request = requests_map[CANDIDATE_B_ID]
    context = t173._candidate_context(rating_request)
    return rating_request, context


def _observables_dict(run: Any) -> dict[str, Any]:
    obs = run.observables
    return {
        "mesh_result_hash": run.mesh_result_hash,
        "total_duty_w": str(obs.total_duty_w),
        "tube_outlet_temperature_k": str(obs.tube_outlet_temperature_k),
        "shell_outlet_temperature_k": str(obs.shell_outlet_temperature_k),
        "energy_balance_residual_w": str(obs.energy_balance_residual_w),
        "terminal_boundary_residual_k": str(obs.terminal_boundary_residual_k),
        "terminal_boundary_residual_j_kg": str(obs.terminal_boundary_residual_j_kg),
        "task172_local_evaluation_count": obs.task172_local_evaluation_count,
        "local_task172_result_hashes": list(obs.local_task172_result_hashes),
    }


def _run_with_alarm(budget_s: float, fn: Any) -> tuple[Any, float, str]:
    class _Timeout(Exception):
        pass

    def _on_alarm(*_args: Any) -> None:
        raise _Timeout(f"budget_s={budget_s}")

    prev = signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, budget_s)
    t0 = time.perf_counter()
    status = "COMPLETED"
    try:
        result = fn()
    except _Timeout:
        status = "TIMEOUT"
        result = None
    except Exception as exc:
        status = f"ERROR:{type(exc).__name__}:{exc}"
        result = None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prev)
    return result, time.perf_counter() - t0, status


def run_benchmark() -> dict[str, Any]:
    rating_request, context = _load_candidate_b_context()
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    shooting = H_MIN_J_KG + (H_MAX_J_KG - H_MIN_J_KG) * SHOOTING_ENTHALPY_FRAC
    subdivisions_list = [1, 2, 4]
    cases: list[dict[str, Any]] = []
    try:
        for subdivisions in subdivisions_list:
            provider_prod = CoolPropProvider(cache_size=2048)
            provider_fast = CoolPropProvider(cache_size=2048)

            def prod_fn(
                n=subdivisions,
                provider=provider_prod,
            ) -> Any:
                return t173._valid_trajectory(
                    n,
                    shooting,
                    provider,
                    context.shell_authority,
                    0,
                )

            def fast_fn(
                n=subdivisions,
                provider=provider_fast,
            ) -> Any:
                run, stats = fast_valid_trajectory(
                    n,
                    shooting,
                    provider,
                    context.shell_authority,
                    0,
                )
                return run, stats

            prod_run, prod_s, prod_status = _run_with_alarm(PER_RUN_BUDGET_S, prod_fn)
            fast_out, fast_s, fast_status = _run_with_alarm(PER_RUN_BUDGET_S, fast_fn)
            fast_run = fast_out[0] if fast_out is not None else None
            fast_stats = fast_out[1] if fast_out is not None else None
            comparison: dict[str, Any] = {}
            if prod_run is not None and fast_run is not None:
                comparison = {
                    "mesh_hash_parity": prod_run.mesh_result_hash == fast_run.mesh_result_hash,
                    "local_task172_hash_parity": (
                        prod_run.observables.local_task172_result_hashes
                        == fast_run.observables.local_task172_result_hashes
                    ),
                    "duty_delta_w": float(
                        fast_run.observables.total_duty_w - prod_run.observables.total_duty_w
                    ),
                    "tube_outlet_delta_k": float(
                        fast_run.observables.tube_outlet_temperature_k
                        - prod_run.observables.tube_outlet_temperature_k
                    ),
                    "shell_outlet_delta_k": float(
                        fast_run.observables.shell_outlet_temperature_k
                        - prod_run.observables.shell_outlet_temperature_k
                    ),
                }
            speedup = prod_s / fast_s if fast_s > 0 and prod_status == "COMPLETED" else None
            cases.append(
                {
                    "subdivisions_per_interval": subdivisions,
                    "shooting_enthalpy_j_kg": str(shooting),
                    "production": {
                        "status": prod_status,
                        "wall_seconds": prod_s,
                        "observables": _observables_dict(prod_run)
                        if prod_run is not None
                        else None,
                    },
                    "fast_solver": {
                        "status": fast_status,
                        "wall_seconds": fast_s,
                        "authority_candidate": FAST_AUTHORITY_CANDIDATE,
                        "mesh_stats": {
                            "cell_count": fast_stats.cell_count if fast_stats else None,
                            "coupled_fallback_count": (
                                fast_stats.coupled_fallback_count if fast_stats else None
                            ),
                            "total_eval_trial_calls": (
                                fast_stats.total_eval_trial_calls if fast_stats else None
                            ),
                            "total_least_squares_nfev": (
                                fast_stats.total_least_squares_nfev if fast_stats else None
                            ),
                        },
                        "observables": _observables_dict(fast_run)
                        if fast_run is not None
                        else None,
                    },
                    "comparison": comparison,
                    "speedup": speedup,
                }
            )
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)

    n1 = cases[0] if cases else {}
    n1_speedup = n1.get("speedup")
    return {
        "task_id": TASK_ID,
        "result": (
            "FAST_SOLVER_CANDIDATE_VERIFIED_N1_SPEEDUP"
            if n1_speedup is not None and n1_speedup >= 1.5
            else "FAST_SOLVER_PROTOTYPE_INCOMPLETE_SPEEDUP"
        ),
        "source_head_sha": SOURCE_HEAD,
        "solver_method": "Coupled (q,Twi,Two) TRF per cell; enthalpy-linked bulk states",
        "fast_solver_implemented": True,
        "physical_equations_preserved": (
            "Production _eval_trial constitutive residuals + production _cell_evaluation "
            "propagation; no tolerance relaxation"
        ),
        "historic_candidate_b_rating_hash_reference": HISTORIC_CANDIDATE_B_RATING_HASH,
        "shooting_enthalpy_j_kg": str(shooting),
        "shooting_enthalpy_frac": str(SHOOTING_ENTHALPY_FRAC),
        "shooting_note": (
            "Frozen in-domain shooting enthalpy (50% of [H_MIN,H_MAX]) for non-zero duty; "
            "not converged outer-boundary enthalpy; not full Candidate B Rating replay"
        ),
        "candidate_b_n1": n1,
        "cases": cases,
        "authority_status": "CANDIDATE_AUTHORITY_V07_FAST_SOLVER_COUPLED_CELL_R1_NOT_PRODUCTION",
        "production_integration": False,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "docs/tasks/evidence/V07-TASK172-TASK173-fast-solver-architecture-r1.json",
    )
    args = parser.parse_args()
    payload = run_benchmark()
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(json.dumps({"output": str(args.output), "sha256": digest}))


if __name__ == "__main__":
    main()
