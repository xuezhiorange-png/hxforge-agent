"""Run joint BVP PoC for V08_03_JOINT_BOUNDARY_VALUE_SOLVER_PROOF."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    _candidate_context,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    _candidate_request_for_task174,
    v08_thermal_rating_request,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174NativeOutputs,
    Task174SuccessResult,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    validate_candidate_request as validate_task174_candidate,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    _enumerate_for_fixture,
    _find_bundle,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    solve_joint_boundary_value_mesh,
)

CANDIDATES = (
    "e1baa795-9cf5-5718-8fa8-0688d2102c5c",
    "9277ebb8-5b05-5130-8b90-92ee4768606b",
)
MESH_LEVELS = (1, 2, 4)
OUT_DIR = Path("/opt/cursor/artifacts")


def _build_rating_request(candidate_id: str, enum: Any, task168_digest: str) -> Any:
    bundle_row = _find_bundle(enum, candidate_id)
    candidate = bundle_row.candidate
    b = bundle_row.bundle
    topology = materialize_candidate_task171(
        candidate=candidate,
        configuration=b.task020_configuration,
        layout=b.task021_layout,
        bundle_geometry=b.task022_geometry,
        baffle_geometry=b.task024_geometry,
        task025_result=b.task025_result,
        task024_request=b.task024_request,
        task025_request=b.task025_request,
    )
    t174_req = _candidate_request_for_task174(candidate, b, topology)
    t174 = validate_task174_candidate(
        t174_req,
        Task174NativeOutputs(
            task029=b.task029_result,
            task034=None,
            task166=b.task166_result,
        ),
    )
    if type(t174) is not Task174SuccessResult:
        raise RuntimeError(f"TASK174 not validated for {candidate_id}: {type(t174).__name__}")
    space_hash = enum.space_hash
    return v08_thermal_rating_request(
        candidate,
        space_hash,
        b,
        topology,
        t174,
        task168_digest,
    )


def _run_candidate(candidate_id: str) -> dict[str, object]:
    provider = CoolPropProvider()
    normalized, _, enum, task168_digest = _enumerate_for_fixture()
    ctx_rating = _build_rating_request(candidate_id, enum, task168_digest)
    exp = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=normalized.tube_side.inlet_temperature_k,
        shell_inlet_temperature_k=normalized.shell_side.inlet_temperature_k,
        tube_mass_flow_kg_s=normalized.tube_side.mass_flow_kg_s,
        shell_mass_flow_kg_s=normalized.shell_side.mass_flow_kg_s,
        tube_property_evaluation_pressure_pa=normalized.tube_side.inlet_pressure_pa,
        shell_property_evaluation_pressure_pa=normalized.shell_side.inlet_pressure_pa,
        allow_live_variable_tube_mass_flow=True,
        allow_live_variable_shell_mass_flow=True,
        allow_variable_water_temperature=True,
    )
    tok = bind_experimental_thermal_boundary_v1(exp)
    ctx = _candidate_context(ctx_rating)
    ct = _CANDIDATE_RATING_CONTEXT.set(ctx)
    meshes: dict[str, object] = {}
    try:
        for subdivisions in MESH_LEVELS:
            if subdivisions > 1 and meshes.get("1", {}).get("status") != "PASS":  # type: ignore[union-attr]
                meshes[str(subdivisions)] = {
                    "status": "SKIPPED",
                    "reason": "N1 did not pass",
                }
                continue
            try:
                outcome = solve_joint_boundary_value_mesh(
                    subdivisions=subdivisions,
                    provider=provider,
                    shell_authority=ctx.shell_authority,
                    candidate_ctx=ctx,
                )
                meshes[str(subdivisions)] = {
                    **asdict(outcome),
                    "cells": [asdict(c) for c in outcome.cells],
                }
            except Exception as exc:  # noqa: BLE001 — proof harness captures hard failures
                meshes[str(subdivisions)] = {
                    "status": "BLOCKED",
                    "error": type(exc).__name__,
                    "message": str(exc)[:500],
                }
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)
    return {"candidate_id": candidate_id, "meshes": meshes}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = [_run_candidate(cid) for cid in CANDIDATES]
    n1 = [c["meshes"].get("1", {}) for c in candidates]  # type: ignore[union-attr]
    payload = {
        "TASK_ID": "V08_03_JOINT_BVP_WALL_CLOSURE_RECOVERY",
        "ENERGY_CONSERVING_FORMULATION": True,
        "candidates": candidates,
        "summary": {
            "candidate_1_n1_status": n1[0].get("status"),
            "candidate_2_n1_status": n1[1].get("status") if len(n1) > 1 else None,
            "candidate_1_energy_residual_w": n1[0].get("energy_balance_residual_w"),
            "candidate_2_energy_residual_w": n1[1].get("energy_balance_residual_w")
            if len(n1) > 1
            else None,
        },
    }
    out = OUT_DIR / "v08_03_joint_bvp_proof.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
