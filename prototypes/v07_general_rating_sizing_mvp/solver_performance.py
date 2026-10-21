"""Aggregate Task173 mesh-run performance from native stats and provider counters."""

from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173


def build_solver_performance_profile(
    *,
    stats: t173._CellSearchStats,
    mesh_run: t173._MeshRun | None,
    property_provider_state_lookup_count: int,
    total_wall_seconds: float,
    subdivisions: int,
) -> dict[str, Any]:
    request_hashes = [
        receipt.task172_request_hash
        for receipt in stats.trial_receipts
        if receipt.task172_request_hash
    ]
    unique_hashes = {value for value in request_hashes if value}
    duplicate_request_count = len(request_hashes) - len(unique_hashes)
    outer_wall = max(
        0.0,
        total_wall_seconds - stats.task172_evaluation_wall_seconds,
    )
    cell_root_trials = len(stats.trial_receipts)
    return {
        "schema_version": "hxforge.solver-performance-profile.v1",
        "mesh_subdivisions": subdivisions,
        "outer_trial_count": stats.outer_trial_count,
        "cell_root_trial_receipt_count": cell_root_trials,
        "task172_local_evaluation_count": stats.task172_local_evaluation_count,
        "task172_request_hash_total": len(request_hashes),
        "task172_request_hash_unique": len(unique_hashes),
        "task172_request_hash_duplicate": duplicate_request_count,
        "property_provider_state_lookup_count": property_provider_state_lookup_count,
        "timing_seconds": {
            "total_wall": round(total_wall_seconds, 3),
            "task172_evaluations": round(stats.task172_evaluation_wall_seconds, 3),
            "outer_solver_estimated": round(outer_wall, 3),
        },
        "mesh_run_metadata": (
            {
                "mesh_result_hash": mesh_run.mesh_result_hash,
                "bisection_iterations": mesh_run.bisection_iterations,
                "outer_action_count": len(mesh_run.outer_decision_action_sequence),
            }
            if mesh_run is not None
            else None
        ),
    }
