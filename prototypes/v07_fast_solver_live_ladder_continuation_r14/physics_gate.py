"""Fail-closed live mesh physics gate before mesh comparison."""

from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_accepted_cell_count,
    verify_cell_closure,
    verify_energy_balance,
)


def evaluate_live_physics_gate(
    receipt: dict[str, Any],
    request: CandidateRatingRequest,
    run: t173._MeshRun,
    *,
    expected_request_hash: str,
    expected_mesh_hash: str | None = None,
) -> tuple[bool, str | None, tuple[str, ...]]:
    diagnostics: list[str] = []
    if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
        return (
            False,
            "LIVE_PHYSICS_WORKER_NOT_TERMINAL_ACCEPTED",
            (f"worker_status={receipt.get('worker_status')}",),
        )
    if not receipt.get("terminal_tolerance_pass"):
        return False, "LIVE_PHYSICS_TERMINAL_TOLERANCE_FAIL", ()
    if not receipt.get("cell_closure_pass"):
        return False, "LIVE_PHYSICS_CELL_CLOSURE_FAIL", ()
    if not receipt.get("energy_balance_pass"):
        return False, "LIVE_PHYSICS_ENERGY_BALANCE_FAIL", ()
    if receipt.get("rating_request_hash") != expected_request_hash:
        return (
            False,
            "LIVE_PHYSICS_REQUEST_HASH_MISMATCH",
            (
                f"receipt={receipt.get('rating_request_hash')}",
                f"expected={expected_request_hash}",
            ),
        )
    if expected_mesh_hash is not None and run.mesh_result_hash != expected_mesh_hash:
        return (
            False,
            "LIVE_PHYSICS_MESH_HASH_REPLAY_MISMATCH",
            (
                f"rehydrate={run.mesh_result_hash}",
                f"expected={expected_mesh_hash}",
            ),
        )
    if run.mesh_result_hash != receipt.get("mesh_result_hash"):
        return (
            False,
            "REPLAY_MISMATCH",
            (
                f"receipt={receipt.get('mesh_result_hash')}",
                f"rehydrate={run.mesh_result_hash}",
            ),
        )
    context = t173._candidate_context(request)
    subdivisions = int(receipt.get("mesh_n", run.subdivisions))
    if not verify_accepted_cell_count(run, context, subdivisions):
        diagnostics.append(f"cell_count={len(run.cells)}")
        return False, "LIVE_PHYSICS_CELL_COUNT_FAIL", tuple(diagnostics)
    if not verify_cell_closure(run) or not verify_energy_balance(run):
        return False, "LIVE_PHYSICS_POST_REHYDRATE_VERIFY_FAIL", ()
    if not t173._terminal_tolerance_pass(run):
        return False, "LIVE_PHYSICS_POST_REHYDRATE_TERMINAL_FAIL", ()
    return True, None, ()
