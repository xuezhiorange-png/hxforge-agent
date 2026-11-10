"""V08_03_JOINT_BVP_FEASIBLE_DOMAIN_RECOVERY closeout runner."""
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
    joint_bvp_dof_audit_summary,
    solve_joint_boundary_value_mesh,
)
from prototypes.v08_thermal_rating.run_joint_bvp_proof import (
    CANDIDATES,
    _build_rating_request,
)

OUT = Path("/opt/cursor/artifacts/v08_03_joint_bvp_feasible_domain_proof.json")
PRE_TRF = Path("/opt/cursor/artifacts/v08_03_joint_bvp_pre_trf_diagnostics.json")
TASK_ID = "V08_03_JOINT_BVP_FEASIBLE_DOMAIN_RECOVERY"


def _git_head() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True)
        .strip()
    )


def _run_candidate(candidate_id: str, ctx_rating: Any) -> dict[str, Any]:
    provider = CoolPropProvider()
    normalized, _, enum, task168_digest = _enumerate_for_fixture()
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
        task172 = sum(1 for c in n1.cells if c.task172_gate_pass and c.production_validated)
        task173 = sum(1 for c in n1.cells if c.task173_root_validated)
        return {
            "cell0": {
                "task172": cell0.task172_gate_pass and cell0.production_validated,
                "task173_root": cell0.task173_root_validated,
                "domain_exit": cell0.domain_exit,
                "q_w": cell0.q_w,
            },
            "two_cell": {
                "status": two.get("status"),
                "domain_penalty_plateau": two.get("domain_penalty_plateau"),
                "task172_cells": sum(
                    1
                    for c in two.get("cells", [])
                    if getattr(c, "task172_gate_pass", False) and getattr(c, "production_validated", False)
                ),
            },
            "n1": {
                "status": n1.status,
                "physical_acceptance": n1.physical_acceptance,
                "energy_balance_residual_w": n1.energy_balance_residual_w,
                "total_q_w": n1.total_q_w,
                "task172_validated_cells": task172,
                "task173_validated_roots": task173,
                "optimizer_nfev": n1.optimizer_nfev,
                "domain_penalty_plateau": n1.extra.get("domain_penalty_plateau"),
            },
        }
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)


def main() -> int:
    from prototypes.v08_thermal_rating import export_joint_bvp_pre_trf_diagnostics as pre_trf

    pre_trf.main()
    normalized, _, enum, task168_digest = _enumerate_for_fixture()
    per_candidate: dict[str, Any] = {}
    for cid in CANDIDATES:
        ctx_rating = _build_rating_request(cid, enum, task168_digest)
        per_candidate[cid] = _run_candidate(cid, ctx_rating)

    c1 = per_candidate[CANDIDATES[0]]
    c2 = per_candidate[CANDIDATES[1]]
    pre = json.loads(PRE_TRF.read_text(encoding="utf-8")) if PRE_TRF.is_file() else {}

    bvp_dof = joint_bvp_dof_audit_summary()["audit"]
    initial_feas = "PASS" if pre.get("initial_axial_feasible") else "BLOCKED"
    phys_rank = pre.get("physical_jacobian_rank")
    pen_rank = pre.get("penalty_jacobian_rank")
    perturb = pre.get("perturbation_audit", [])
    domain_elim = pre.get("domain_plateau_cells", 5) == 0 and all(
        p.get("physical_finite", True) for p in perturb
    )

    cell1_pass = c1["cell0"]["task172"] and c1["cell0"]["task173_root"]
    two_pass = c1["two_cell"]["status"] == "PASS"
    n1_pass = c1["n1"]["physical_acceptance"]
    n2_n4 = "not_run"
    if n1_pass:
        n2_n4 = "not_run_this_round"

    distinct = 0
    if n1_pass:
        distinct = 1

    engineering = "PASS" if n1_pass else "BLOCKED"
    blocker = "none"
    if not cell1_pass:
        blocker = f"real_cell_0: {c1['cell0'].get('domain_exit')}"
    elif not two_pass:
        blocker = "two_cell_coupling"
    elif not n1_pass:
        blocker = "full_n1_physical_acceptance"

    closeout = {
        "TASK_ID": TASK_ID,
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": "pending_local",
        "BVP_DOF_AUDIT": bvp_dof,
        "INITIAL_FEASIBLE_STATE": initial_feas,
        "PHYSICAL_JACOBIAN_RANK": phys_rank,
        "PENALTY_JACOBIAN_RANK": pen_rank,
        "DOMAIN_PLATEAU_ELIMINATED": domain_elim,
        "REAL_CELL_1_TASK172": "PASS" if cell1_pass else "BLOCKED",
        "REAL_TWO_CELL_COUPLING": "PASS" if two_pass else "BLOCKED",
        "CANDIDATE_1_N1": "PASS" if n1_pass else "BLOCKED",
        "CANDIDATE_2_N1": "PASS" if c2["n1"]["physical_acceptance"] else "BLOCKED",
        "TASK172_VALIDATED_CELLS": c1["n1"]["task172_validated_cells"],
        "TASK173_VALIDATED_ROOTS": c1["n1"]["task173_validated_roots"],
        "ENERGY_BALANCE": c1["n1"]["energy_balance_residual_w"],
        "N2_N4": n2_n4,
        "DISTINCT_FULLY_CONVERGED": distinct,
        "ENGINEERING_ACCEPTANCE": engineering,
        "REMAINING_BLOCKER": blocker,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "candidates": per_candidate,
        "pre_trf": pre,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(closeout, indent=2) + "\n", encoding="utf-8")
    print(OUT)
    print(json.dumps({k: closeout[k] for k in closeout if k not in ("candidates", "pre_trf")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
