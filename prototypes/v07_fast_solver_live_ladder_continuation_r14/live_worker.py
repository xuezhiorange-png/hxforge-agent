"""Spawn-safe live mesh worker driven by request snapshot file (no Q13 reload)."""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    load_request_from_snapshot_file,
    verify_snapshot_integrity,
)
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import solve_fast_outer_boundary
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_cell_closure,
    verify_energy_balance,
)


def _worker_entry(conn: mp.connection.Connection, payload: dict[str, Any]) -> None:
    subdivisions = int(payload["subdivisions"])
    budget_s = float(payload["budget_s"])
    t0 = time.perf_counter()
    exit_code = 0
    try:
        snapshot_path = Path(str(payload["snapshot_path"]))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        verify_snapshot_integrity(snapshot)
        if snapshot.get("snapshot_sha256") != payload.get("expected_snapshot_sha256"):
            raise ValueError("snapshot sha256 gate failed")
        request = load_request_from_snapshot_file(snapshot_path)
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
                "request_snapshot_sha256": snapshot.get("snapshot_sha256"),
            }
            conn.send(receipt)
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)
    except Exception as exc:  # noqa: BLE001 — worker boundary must surface failure
        exit_code = 1
        conn.send(
            {
                "worker_status": "BLOCKED",
                "blocked_code": "WORKER_EXCEPTION",
                "blocked_diagnostics": [repr(exc)],
                "mesh_n": subdivisions,
                "worker_wall_seconds": time.perf_counter() - t0,
            }
        )
    finally:
        conn.close()
    sys.exit(exit_code)


def run_live_mesh_worker_from_snapshot(
    snapshot_path: Path,
    *,
    snapshot_sha256: str,
    rating_request_hash: str,
    mesh_n: int,
    budget_s: float,
    join_grace_s: float = 15.0,
) -> dict[str, Any]:
    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    payload = {
        "snapshot_path": str(snapshot_path),
        "expected_snapshot_sha256": snapshot_sha256,
        "rating_request_hash": rating_request_hash,
        "subdivisions": mesh_n,
        "budget_s": budget_s,
    }
    process = ctx.Process(target=_worker_entry, args=(child_conn, payload))
    process.start()
    child_conn.close()
    process.join(timeout=budget_s + join_grace_s)
    timed_out = process.is_alive()
    if timed_out:
        process.terminate()
        process.join(5.0)
        parent_conn.close()
        return {
            "worker_status": "TIMEOUT",
            "blocked_code": "WORKER_HARD_TIMEOUT",
            "blocked_diagnostics": (f"mesh_n={mesh_n}", f"budget_s={budget_s}"),
            "mesh_n": mesh_n,
            "worker_wall_seconds": budget_s,
        }
    exit_code = process.exitcode
    receipt: dict[str, Any] | None = None
    if parent_conn.poll(timeout=1.0):
        receipt = parent_conn.recv()
    parent_conn.close()
    if exit_code not in (0, None) and receipt is None:
        return {
            "worker_status": "BLOCKED",
            "blocked_code": "WORKER_NONZERO_EXIT",
            "blocked_diagnostics": (f"exitcode={exit_code}", f"mesh_n={mesh_n}"),
            "mesh_n": mesh_n,
        }
    if receipt is None:
        return {
            "worker_status": "BLOCKED",
            "blocked_code": "WORKER_EMPTY_RECEIPT",
            "mesh_n": mesh_n,
            "worker_exitcode": exit_code,
        }
    if exit_code not in (0, None):
        receipt = dict(receipt)
        receipt.setdefault("blocked_code", "WORKER_NONZERO_EXIT")
        receipt.setdefault("worker_exitcode", exit_code)
    return receipt


def rehydrate_mesh_run_for_compare(
    request: Any,
    shooting_enthalpy_j_kg: str,
    mesh_n: int,
    outer_iterations: int = 0,
    *,
    budget_s: float = 120.0,
) -> Any:
    """Rebuild mesh run at live-discovered shooting enthalpy (time-bounded)."""
    from prototypes.v07_fast_solver_architecture_r1.mesh_march import fast_valid_trajectory

    t0 = time.perf_counter()
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
        if time.perf_counter() - t0 > budget_s:
            raise TimeoutError("MESH_REHYDRATE_BUDGET_EXCEEDED")
        return run
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
