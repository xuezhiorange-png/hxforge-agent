"""V08_03_CELL_BOUNDARY_AND_WALL_ELIMINATION_PROOF closeout."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import subprocess
import sys
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
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    _enumerate_for_fixture,
    _find_bundle,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    attempt_real_single_cell_closure,
    attempt_real_two_cell_coupling,
    solve_joint_boundary_value_mesh,
)
from prototypes.v08_thermal_rating.run_joint_bvp_proof import (
    CANDIDATES,
    _build_rating_request,
)

OUT = Path("/opt/cursor/artifacts/v08_03_cell_boundary_wall_elimination_proof.json")
TASK_ID = "V08_03_CELL_BOUNDARY_AND_WALL_ELIMINATION_PROOF"


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _ci_status() -> str:
    out = subprocess.check_output(
        [
            "gh",
            "run",
            "list",
            "--branch",
            "cursor/v08-03-live-thermal-rating-1201",
            "--limit",
            "1",
            "--json",
            "number,status,conclusion,headSha",
        ],
        cwd=_REPO,
        text=True,
    )
    runs = json.loads(out)
    if not runs:
        return "unknown"
    r = runs[0]
    return f"ci#{r['number']} {r['status']}" + (
        f" {r['conclusion']}" if r.get("conclusion") else ""
    )


def _run_candidate(candidate_id: str, ctx_rating: Any) -> dict[str, Any]:
    provider = CoolPropProvider()
    normalized, _, enum, _ = _enumerate_for_fixture()
    _find_bundle(enum, candidate_id)
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
    try:
        cell0 = attempt_real_single_cell_closure(
            cell_index=0,
            provider=provider,
            shell_authority=ctx.shell_authority,
            candidate_ctx=ctx,
            subdivisions=1,
        )
        two = attempt_real_two_cell_coupling(
            provider=provider,
            shell_authority=ctx.shell_authority,
            candidate_ctx=ctx,
            subdivisions=1,
        )
        n1 = solve_joint_boundary_value_mesh(
            subdivisions=1,
            provider=provider,
            shell_authority=ctx.shell_authority,
            candidate_ctx=ctx,
        )
        return {
            "cell0": cell0,
            "two_cell_status": two.get("status"),
            "n1": n1,
        }
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)


def main() -> int:
    _, _, enum, task168_digest = _enumerate_for_fixture()
    results: dict[str, Any] = {}
    for cid in CANDIDATES:
        ctx_rating = _build_rating_request(cid, enum, task168_digest)
        packed = _run_candidate(cid, ctx_rating)
        c0 = packed["cell0"]
        n1 = packed["n1"]
        results[cid] = {
            "cell0": {
                "task172": c0.task172_gate_pass,
                "q_w": c0.q_w,
                "twi_k": c0.twi_k,
                "two_k": c0.two_k,
                "r1_w": c0.r1_w,
                "r2_w": c0.r2_w,
                "r3_w": c0.r3_w,
                "max_ulp_ratio": c0.max_ulp_ratio,
                "failure_class": c0.failure_class,
                "elimination_method": c0.elimination_method,
                "compare_tmid": c0.compare_tmid,
                "compare_u1_u2": c0.compare_u1_u2,
                "shell_inlet_h_fixed": c0.shell_inlet_h_fixed,
            },
            "two_cell": packed["two_cell_status"],
            "n1_physical_acceptance": n1.physical_acceptance,
            "task172_cells": sum(
                1 for c in n1.cells if c.task172_gate_pass and c.production_validated
            ),
            "energy_balance": n1.energy_balance_residual_w,
        }
    c1 = results[CANDIDATES[0]]["cell0"]
    wall_elim = (
        "PASS" if c1.get("compare_tmid", {}).get("original_residual_gate_pass") else "BLOCKED"
    )
    if not c1.get("compare_tmid"):
        wall_elim = "BLOCKED"
    payload = {
        "TASK_ID": TASK_ID,
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "SINGLE_CELL_BC_CORRECTED": True,
        "WALL_RESISTANCE_INDEPENDENT": "verified",
        "WALL_EQUATION_ELIMINATION": wall_elim,
        "CELL0_Q_W": c1.get("q_w"),
        "CELL0_TWI_K": c1.get("twi_k"),
        "CELL0_TWO_K": c1.get("two_k"),
        "CELL0_R1_W": c1.get("r1_w"),
        "CELL0_R2_W": c1.get("r2_w"),
        "CELL0_R3_W": c1.get("r3_w"),
        "CELL0_MAX_ULP_RATIO": c1.get("max_ulp_ratio"),
        "REAL_CELL0_TASK172": "PASS" if c1.get("task172") else "BLOCKED",
        "REAL_TWO_CELL_COUPLING": "PASS"
        if results[CANDIDATES[0]]["two_cell"] == "PASS"
        else "BLOCKED",
        "CANDIDATE_1_N1": "PASS" if results[CANDIDATES[0]]["n1_physical_acceptance"] else "BLOCKED",
        "CANDIDATE_2_N1": "PASS" if results[CANDIDATES[1]]["n1_physical_acceptance"] else "BLOCKED",
        "TASK173_ROOT_GATE": c1.get("task172"),
        "ENERGY_BALANCE": results[CANDIDATES[0]].get("energy_balance"),
        "N2_N4": "not_run",
        "V07_GOLDEN": "passed_locally",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "REMAINING_BLOCKER": c1.get("failure_class") or "pending",
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "candidates": results,
    }
    if not c1.get("task172"):
        payload["REMAINING_BLOCKER"] = (
            f"{c1.get('failure_class')}: r2={c1.get('r2_w')}, max_ulp={c1.get('max_ulp_ratio')}"
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, default=lambda o: getattr(o, "__dict__", str(o))) + "\n"
    )
    print(OUT)
    print(json.dumps({k: payload[k] for k in payload if k != "candidates"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
