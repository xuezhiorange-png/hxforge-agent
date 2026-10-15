"""Hard wall-clock bounded live mesh worker (spawn + terminate on timeout)."""

from __future__ import annotations

import multiprocessing as mp
import time
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_live_rating_ladder_r13.request_snapshot import (
    load_rating_request_by_id,
)
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import solve_fast_outer_boundary
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_cell_closure,
    verify_energy_balance,
)


def _worker_entry(queue: mp.Queue, payload: dict[str, Any]) -> None:
    subdivisions = int(payload["subdivisions"])
    budget_s = float(payload["budget_s"])
    t0 = time.perf_counter()
    try:
        request = load_rating_request_by_id(str(payload["candidate_id"]))
        if candidate_rating_request_hash(request) != str(payload["rating_request_hash"]):
            raise ValueError("worker request hash gate failed")
        context = t173._candidate_context(request)
        token = t173._CANDIDATE_RATING_CONTEXT.set(context)
        provider = CoolPropProvider(cache_size=2048)
        try:
            deadline = time.perf_counter() + budget_s
            outer = solve_fast_outer_boundary(
                subdivisions,
                provider,
                context.shell_authority,
                deadline_monotonic=deadline,
            )
            run = outer.mesh_run
            obs = run.observables if run is not None else None
            receipt: dict[str, Any] = {
                "worker_status": outer.status,
                "blocked_code": outer.blocked_code,
                "blocked_diagnostics": list(outer.blocked_diagnostics),
                "shooting_enthalpy_j_kg": outer.shooting_enthalpy_j_kg,
                "mesh_result_hash": run.mesh_result_hash if run is not None else None,
                "rating_request_hash": candidate_rating_request_hash(request),
                "candidate_id": request.candidate_id,
                "mesh_n": subdivisions,
                "worker_wall_seconds": outer.stats.worker_wall_seconds,
                "terminal_boundary_residual_k": (
                    str(obs.terminal_boundary_residual_k) if obs is not None else None
                ),
                "energy_balance_residual_w": (
                    str(obs.energy_balance_residual_w) if obs is not None else None
                ),
                "cell_closure_pass": verify_cell_closure(run) if run is not None else False,
                "energy_balance_pass": verify_energy_balance(run) if run is not None else False,
                "terminal_tolerance_pass": (
                    t173._terminal_tolerance_pass(run) if run is not None else False
                ),
                "shooting_enthalpy_for_rehydrate": (
                    str(run.shooting_enthalpy) if run is not None else None
                ),
                "outer_iterations_for_rehydrate": (
                    int(run.bisection_iterations) if run is not None else 0
                ),
            }
            queue.put(receipt)
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)
    except Exception as exc:  # noqa: BLE001 — worker boundary must surface failure
        queue.put(
            {
                "worker_status": "BLOCKED",
                "blocked_code": "WORKER_EXCEPTION",
                "blocked_diagnostics": [repr(exc)],
                "mesh_n": subdivisions,
                "worker_wall_seconds": time.perf_counter() - t0,
            }
        )


def run_live_mesh_worker(
    request: CandidateRatingRequest,
    mesh_n: int,
    budget_s: float,
    *,
    join_grace_s: float = 15.0,
) -> dict[str, Any]:
    """Run one live outer-boundary solve in an isolated worker with hard parent timeout."""
    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue()
    payload = {
        "candidate_id": request.candidate_id,
        "rating_request_hash": candidate_rating_request_hash(request),
        "subdivisions": mesh_n,
        "budget_s": budget_s,
    }
    process = ctx.Process(target=_worker_entry, args=(queue, payload))
    process.start()
    process.join(timeout=budget_s + join_grace_s)
    if process.is_alive():
        process.terminate()
        process.join(5.0)
        return {
            "worker_status": "TIMEOUT",
            "blocked_code": "LIVE_WORKER_HARD_TIMEOUT",
            "blocked_diagnostics": (f"mesh_n={mesh_n}", f"budget_s={budget_s}"),
            "mesh_n": mesh_n,
            "worker_wall_seconds": budget_s,
        }
    if queue.empty():
        return {
            "worker_status": "BLOCKED",
            "blocked_code": "WORKER_EMPTY_RECEIPT",
            "mesh_n": mesh_n,
        }
    return queue.get()


def rehydrate_mesh_run_for_compare(
    request: CandidateRatingRequest,
    shooting_enthalpy_j_kg: str,
    mesh_n: int,
    outer_iterations: int = 0,
) -> Any:
    """Rebuild mesh run at live-discovered shooting enthalpy for mesh comparison."""
    from prototypes.v07_fast_solver_architecture_r1.mesh_march import fast_valid_trajectory

    context = t173._candidate_context(request)
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    try:
        run, _stats = fast_valid_trajectory(
            mesh_n,
            Decimal(shooting_enthalpy_j_kg),
            provider,
            context.shell_authority,
            outer_iterations,
            cell_solver="r2",
        )
        return run
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
