"""Replay fast mesh at fixed shooting enthalpy and production mesh convergence compare."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import ConvergenceComparison
from hexagent.properties.base import PropertyProvider
from prototypes.v07_fast_solver_architecture_r1.mesh_march import fast_valid_trajectory


def mesh_observables_payload(run: t173._MeshRun) -> dict[str, Any]:
    return run.observables.model_dump(mode="json")


def comparison_payload(comparison: ConvergenceComparison) -> dict[str, Any]:
    return json.loads(comparison.model_dump_json())


def replay_mesh_at_enthalpy(
    subdivisions: int,
    shooting_enthalpy_j_kg: str,
    provider: PropertyProvider,
    shell_authority: Any,
    *,
    outer_iterations: int,
    expected_mesh_hash: str | None,
    source_label: str,
) -> tuple[t173._MeshRun, dict[str, Any]]:
    enthalpy = Decimal(shooting_enthalpy_j_kg)
    run, mesh_stats = fast_valid_trajectory(
        subdivisions,
        enthalpy,
        provider,
        shell_authority,
        outer_iterations=outer_iterations,
        cell_solver="r2",
    )
    terminal_ok = t173._terminal_tolerance_pass(run)
    actual_hash = run.mesh_result_hash
    hash_ok = expected_mesh_hash is None or actual_hash == expected_mesh_hash
    status: Literal["OK", "REPLAY_MISMATCH"] = (
        "OK" if terminal_ok and hash_ok else "REPLAY_MISMATCH"
    )
    record = {
        "subdivisions": subdivisions,
        "source_label": source_label,
        "shooting_enthalpy_j_kg": shooting_enthalpy_j_kg,
        "outer_iterations": outer_iterations,
        "status": status,
        "terminal_tolerance_pass": terminal_ok,
        "expected_mesh_hash": expected_mesh_hash,
        "actual_mesh_hash": actual_hash,
        "mesh_march_wall_seconds": mesh_stats.wall_seconds,
        "mesh_observables": mesh_observables_payload(run),
    }
    return run, record


def compare_mesh_pair(
    coarse: t173._MeshRun,
    fine: t173._MeshRun,
) -> ConvergenceComparison:
    return t173._compare_meshes(coarse, fine)
