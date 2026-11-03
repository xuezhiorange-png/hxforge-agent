"""Strict mesh replay at VERIFIED_PRIOR_LIVE_STAGE shooting enthalpy (no outer search)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.base import PropertyProvider
from prototypes.v07_fast_solver_architecture_r1.mesh_march import fast_valid_trajectory


class LiveMeshReplayError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


def replay_verified_prior_stage_mesh(
    mesh_n: int,
    *,
    shooting_enthalpy_j_kg: str,
    outer_iterations: int,
    expected_mesh_hash: str,
    provider: PropertyProvider,
    shell_authority: Any,
) -> t173._MeshRun:
    run, _stats = fast_valid_trajectory(
        mesh_n,
        Decimal(shooting_enthalpy_j_kg),
        provider,
        shell_authority,
        outer_iterations,
        cell_solver="r2",
    )
    if run.mesh_result_hash != expected_mesh_hash:
        raise LiveMeshReplayError(
            "MESH_HASH_REPLAY_MISMATCH",
            f"mesh_n={mesh_n}",
            f"expected={expected_mesh_hash}",
            f"actual={run.mesh_result_hash}",
        )
    if not t173._terminal_tolerance_pass(run):
        raise LiveMeshReplayError("TERMINAL_TOLERANCE_FAIL", f"mesh_n={mesh_n}")
    return run
