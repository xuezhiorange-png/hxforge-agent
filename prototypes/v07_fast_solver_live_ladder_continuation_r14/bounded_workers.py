"""Hard wall-clock bounded rehydrate and mesh-compare workers (spawn + terminate)."""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    load_request_from_snapshot_file,
    verify_snapshot_integrity,
)
from prototypes.v07_fast_solver_n4_mesh_convergence_r5.mesh_replay import (
    compare_mesh_pair,
    comparison_payload,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_cell_closure,
    verify_energy_balance,
)


def _rehydrate_worker_entry(conn: mp.connection.Connection, payload: dict[str, Any]) -> None:
    exit_code = 0
    try:
        from hexagent.properties.coolprop_provider import CoolPropProvider
        from prototypes.v07_fast_solver_architecture_r1.mesh_march import fast_valid_trajectory

        snapshot_path = Path(str(payload["snapshot_path"]))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        verify_snapshot_integrity(snapshot)
        request = load_request_from_snapshot_file(snapshot_path)
        from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
            candidate_rating_request_hash,
        )

        mesh_n = int(payload["mesh_n"])
        payload["rating_request_hash"] = candidate_rating_request_hash(request)
        shooting = str(payload["shooting_enthalpy_j_kg"])
        outer_iters = int(payload["outer_iterations"])
        context = t173._candidate_context(request)
        token = t173._CANDIDATE_RATING_CONTEXT.set(context)
        provider = CoolPropProvider(cache_size=2048)
        try:
            run, _stats = fast_valid_trajectory(
                mesh_n,
                Decimal(shooting),
                provider,
                context.shell_authority,
                outer_iters,
                cell_solver="r2",
            )
            obs = run.observables
            from prototypes.v07_fast_solver_live_ladder_continuation_r14.physics_gate import (
                evaluate_live_physics_gate,
            )

            gate_ok, gate_code, gate_diag = evaluate_live_physics_gate(
                receipt={
                    "worker_status": "TERMINAL_ACCEPTED",
                    "terminal_tolerance_pass": t173._terminal_tolerance_pass(run),
                    "cell_closure_pass": verify_cell_closure(run),
                    "energy_balance_pass": verify_energy_balance(run),
                    "rating_request_hash": payload.get("rating_request_hash"),
                    "mesh_result_hash": payload.get("expected_mesh_hash"),
                    "mesh_n": mesh_n,
                },
                request=request,
                run=run,
                expected_request_hash=str(payload["rating_request_hash"]),
                expected_mesh_hash=payload.get("expected_mesh_hash"),
            )
            conn.send(
                {
                    "status": "OK" if gate_ok else "GATE_FAIL",
                    "blocked_code": gate_code,
                    "blocked_diagnostics": list(gate_diag),
                    "mesh_result_hash": run.mesh_result_hash,
                    "subdivisions": run.subdivisions,
                    "total_duty_w": str(obs.total_duty_w),
                    "terminal_boundary_residual_k": str(obs.terminal_boundary_residual_k),
                    "energy_balance_residual_w": str(obs.energy_balance_residual_w),
                    "cell_closure_pass": verify_cell_closure(run),
                    "energy_balance_pass": verify_energy_balance(run),
                    "terminal_tolerance_pass": t173._terminal_tolerance_pass(run),
                }
            )
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)
    except Exception as exc:  # noqa: BLE001
        exit_code = 1
        conn.send(
            {
                "status": "WORKER_EXCEPTION",
                "blocked_code": "REHYDRATE_WORKER_EXCEPTION",
                "blocked_diagnostics": [repr(exc)],
            }
        )
    finally:
        conn.close()
    sys.exit(exit_code)


def _compare_worker_entry(conn: mp.connection.Connection, payload: dict[str, Any]) -> None:
    exit_code = 0
    try:
        from hexagent.properties.coolprop_provider import CoolPropProvider
        from prototypes.v07_fast_solver_architecture_r1.mesh_march import fast_valid_trajectory

        snapshot_path = Path(str(payload["snapshot_path"]))
        request = load_request_from_snapshot_file(snapshot_path)
        context = t173._candidate_context(request)
        token = t173._CANDIDATE_RATING_CONTEXT.set(context)
        provider = CoolPropProvider(cache_size=2048)
        try:

            def _run(spec: dict[str, Any]) -> Any:
                return fast_valid_trajectory(
                    int(spec["mesh_n"]),
                    Decimal(str(spec["shooting_enthalpy_j_kg"])),
                    provider,
                    context.shell_authority,
                    int(spec["outer_iterations"]),
                    cell_solver="r2",
                )[0]

            coarse = _run(payload["coarse"])
            fine = _run(payload["fine"])
            cmp_payload = comparison_payload(compare_mesh_pair(coarse, fine))
            conn.send({"status": "OK", "comparison": cmp_payload})
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)
    except Exception as exc:  # noqa: BLE001
        exit_code = 1
        conn.send(
            {
                "status": "WORKER_EXCEPTION",
                "blocked_code": "COMPARE_WORKER_EXCEPTION",
                "blocked_diagnostics": [repr(exc)],
            }
        )
    finally:
        conn.close()
    sys.exit(exit_code)


def _spawn_bounded_worker(
    target: Any,
    payload: dict[str, Any],
    *,
    budget_s: float,
    join_grace_s: float,
    timeout_blocked_code: str,
) -> dict[str, Any]:
    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(target=target, args=(child_conn, payload))
    process.start()
    child_conn.close()
    process.join(timeout=budget_s + join_grace_s)
    if process.is_alive():
        process.terminate()
        process.join(5.0)
        parent_conn.close()
        return {
            "status": "TIMEOUT",
            "blocked_code": timeout_blocked_code,
            "blocked_diagnostics": (f"budget_s={budget_s}",),
        }
    exit_code = process.exitcode
    message: dict[str, Any] | None = None
    if parent_conn.poll(timeout=1.0):
        message = parent_conn.recv()
    parent_conn.close()
    if message is None:
        return {
            "status": "BLOCKED",
            "blocked_code": "WORKER_EMPTY_RECEIPT",
            "blocked_diagnostics": (f"exitcode={exit_code}",),
        }
    if exit_code not in (0, None) and message.get("status") != "OK":
        message.setdefault("blocked_code", "WORKER_NONZERO_EXIT")
    return message


def run_bounded_rehydrate(
    snapshot_path: Path,
    *,
    shooting_enthalpy_j_kg: str,
    mesh_n: int,
    outer_iterations: int,
    expected_mesh_hash: str | None,
    rating_request_hash: str,
    budget_s: float,
    join_grace_s: float = 10.0,
) -> dict[str, Any]:
    return _spawn_bounded_worker(
        _rehydrate_worker_entry,
        {
            "snapshot_path": str(snapshot_path),
            "shooting_enthalpy_j_kg": shooting_enthalpy_j_kg,
            "mesh_n": mesh_n,
            "outer_iterations": outer_iterations,
            "expected_mesh_hash": expected_mesh_hash,
            "rating_request_hash": rating_request_hash,
        },
        budget_s=budget_s,
        join_grace_s=join_grace_s,
        timeout_blocked_code="REHYDRATE_HARD_TIMEOUT",
    )


def run_bounded_compare(
    snapshot_path: Path,
    *,
    coarse: dict[str, Any],
    fine: dict[str, Any],
    budget_s: float,
    join_grace_s: float = 10.0,
) -> dict[str, Any]:
    return _spawn_bounded_worker(
        _compare_worker_entry,
        {
            "snapshot_path": str(snapshot_path),
            "coarse": coarse,
            "fine": fine,
        },
        budget_s=budget_s,
        join_grace_s=join_grace_s,
        timeout_blocked_code="COMPARE_HARD_TIMEOUT",
    )
