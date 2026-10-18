"""Live n=16 outer boundary via verified bracket (R16 experimental authority)."""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_live_ladder_continuation_r14.identity_gate import (
    IdentityGateError,
    assert_candidate_identity,
    assert_request_hash_triple,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    load_request_from_snapshot_file,
    verify_snapshot_integrity,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.trial_persistence import (
    OuterTrialJsonlWriter,
)
from prototypes.v07_fast_solver_n16_verified_bracket_r8.narrow_bracket_solver import (
    solve_verified_narrow_bracket_outer_boundary,
)
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import OuterBudgetExceeded
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_cell_closure,
    verify_energy_balance,
)
from prototypes.v07_fast_solver_verified_bracket.mesh_extrapolation_bracket import (
    establish_verified_bracket,
)

LIVE_N16_OUTER_AUTHORITY_ID = "V07-FAST-SOLVER-LIVE-N16-CONTINUATION-R16"


def _n16_worker_entry(conn: mp.connection.Connection, payload: dict[str, Any]) -> None:
    exit_code = 0
    subdivisions = 16
    t0 = time.perf_counter()
    trial_writer: OuterTrialJsonlWriter | None = None
    try:
        expected_request_hash = str(payload["expected_request_hash"])
        expected_candidate_id = str(payload["expected_candidate_id"])
        snapshot_path = Path(str(payload["snapshot_path"]))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        verify_snapshot_integrity(snapshot)
        request = load_request_from_snapshot_file(snapshot_path)
        reconstructed_hash = candidate_rating_request_hash(request)
        assert_request_hash_triple(
            expected_request_hash,
            str(snapshot["rating_request_hash"]),
            reconstructed_hash,
        )
        assert_candidate_identity(expected_candidate_id, str(snapshot["candidate_id"]))

        trials_path = Path(str(payload["trials_jsonl_path"]))
        trial_writer = OuterTrialJsonlWriter(
            trials_path,
            metadata={
                "authority_id": LIVE_N16_OUTER_AUTHORITY_ID,
                "rating_request_hash": expected_request_hash,
                "candidate_id": expected_candidate_id,
                "mesh_n": subdivisions,
            },
        )

        def on_trial(receipt: Any) -> None:
            row = receipt.to_dict() if hasattr(receipt, "to_dict") else dict(receipt)
            row["rating_request_hash"] = expected_request_hash
            row["numerical_authority_id"] = LIVE_N16_OUTER_AUTHORITY_ID
            trial_writer.append(row)

        budget_s = float(payload["budget_s"])
        deadline = time.perf_counter() + budget_s
        h_coarse = str(payload["h_coarse_j_kg"])
        h_fine = str(payload["h_fine_j_kg"])
        run_session_id = str(payload.get("run_session_id") or uuid.uuid4())

        context = t173._candidate_context(request)
        token = t173._CANDIDATE_RATING_CONTEXT.set(context)
        provider = CoolPropProvider(cache_size=2048)
        try:
            endpoints, bracket_meta = establish_verified_bracket(
                subdivisions,
                provider,
                context.shell_authority,
                h_coarse_j_kg=h_coarse,
                h_fine_j_kg=h_fine,
                authority_id=LIVE_N16_OUTER_AUTHORITY_ID,
                rating_request_hash=reconstructed_hash,
                run_session_id=run_session_id,
                deadline_monotonic=deadline,
                on_trial_receipt=on_trial,
            )
            result, revalidation = solve_verified_narrow_bracket_outer_boundary(
                subdivisions,
                provider,
                context.shell_authority,
                h_low_j_kg=endpoints.h_low_j_kg,
                h_high_j_kg=endpoints.h_high_j_kg,
                authority_id=LIVE_N16_OUTER_AUTHORITY_ID,
                rating_request_hash=reconstructed_hash,
                same_run_endpoints=endpoints,
                run_session_id=run_session_id,
                deadline_monotonic=deadline,
                on_trial_receipt=on_trial,
            )
            trial_writer.flush()
            run = result.mesh_run
            obs = run.observables if run is not None else None
            conn.send(
                {
                    "worker_status": result.status,
                    "blocked_code": result.blocked_code,
                    "blocked_diagnostics": list(result.blocked_diagnostics),
                    "shooting_enthalpy_j_kg": result.shooting_enthalpy_j_kg,
                    "mesh_result_hash": run.mesh_result_hash if run is not None else None,
                    "rating_request_hash": reconstructed_hash,
                    "candidate_id": request.candidate_id,
                    "mesh_n": subdivisions,
                    "worker_wall_seconds": result.stats.worker_wall_seconds,
                    "outer_trial_count": result.stats.outer_trial_count,
                    "terminal_boundary_residual_k": (
                        str(obs.terminal_boundary_residual_k) if obs is not None else None
                    ),
                    "terminal_boundary_residual_j_kg": (
                        str(obs.terminal_boundary_residual_j_kg) if obs is not None else None
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
                    "bracket_meta": bracket_meta,
                    "revalidation": revalidation,
                    "trials_jsonl_rel_path": str(payload.get("trials_jsonl_rel_path")),
                }
            )
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)
    except IdentityGateError as exc:
        conn.send(
            {
                "worker_status": "BLOCKED",
                "blocked_code": exc.blocked_code,
                "blocked_diagnostics": list(exc.diagnostics),
                "mesh_n": subdivisions,
                "worker_wall_seconds": time.perf_counter() - t0,
            }
        )
    except OuterBudgetExceeded:
        if trial_writer is not None:
            trial_writer.flush()
        conn.send(
            {
                "worker_status": "TIMEOUT",
                "blocked_code": "N16_OUTER_BUDGET_EXCEEDED",
                "mesh_n": subdivisions,
                "worker_wall_seconds": time.perf_counter() - t0,
            }
        )
    except Exception as exc:  # noqa: BLE001
        exit_code = 1
        if trial_writer is not None:
            trial_writer.flush()
        conn.send(
            {
                "worker_status": "BLOCKED",
                "blocked_code": "N16_WORKER_EXCEPTION",
                "blocked_diagnostics": [repr(exc)],
                "mesh_n": subdivisions,
                "worker_wall_seconds": time.perf_counter() - t0,
            }
        )
    finally:
        conn.close()
    sys.exit(exit_code)


def run_live_n16_worker(
    snapshot_path: Path,
    *,
    snapshot_sha256: str,
    rating_request_hash: str,
    candidate_id: str,
    h_coarse_j_kg: str,
    h_fine_j_kg: str,
    trials_jsonl_path: Path,
    trials_jsonl_rel_path: str,
    budget_s: float,
    join_grace_s: float = 20.0,
) -> dict[str, Any]:
    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    payload = {
        "snapshot_path": str(snapshot_path),
        "expected_snapshot_sha256": snapshot_sha256,
        "expected_request_hash": rating_request_hash,
        "expected_candidate_id": candidate_id,
        "h_coarse_j_kg": h_coarse_j_kg,
        "h_fine_j_kg": h_fine_j_kg,
        "trials_jsonl_path": str(trials_jsonl_path),
        "trials_jsonl_rel_path": trials_jsonl_rel_path,
        "budget_s": budget_s,
    }
    process = ctx.Process(target=_n16_worker_entry, args=(child_conn, payload))
    process.start()
    child_conn.close()
    process.join(timeout=budget_s + join_grace_s)
    if process.is_alive():
        process.terminate()
        process.join(5.0)
        parent_conn.close()
        return {
            "worker_status": "TIMEOUT",
            "blocked_code": "N16_WORKER_HARD_TIMEOUT",
            "mesh_n": 16,
            "worker_wall_seconds": budget_s,
        }
    exit_code = process.exitcode
    receipt: dict[str, Any] | None = None
    if parent_conn.poll(timeout=2.0):
        receipt = parent_conn.recv()
    parent_conn.close()
    if receipt is None:
        return {
            "worker_status": "BLOCKED",
            "blocked_code": "WORKER_EMPTY_RECEIPT",
            "worker_exitcode": exit_code,
            "mesh_n": 16,
        }
    if exit_code not in (0, None) and receipt.get("worker_status") == "TERMINAL_ACCEPTED":
        receipt = dict(receipt)
        receipt["blocked_code"] = "WORKER_NONZERO_EXIT"
        receipt["worker_status"] = "BLOCKED"
    return receipt
