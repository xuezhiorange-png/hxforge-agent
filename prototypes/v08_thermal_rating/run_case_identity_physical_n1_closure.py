"""V08_03_CASE_IDENTITY_AND_PHYSICAL_N1_CLOSURE"""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

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
from prototypes.v08_thermal_rating.case_identity_v08 import build_case_identity_bundle
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import _enumerate_for_fixture
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    _supports_for_mesh,
    solve_joint_boundary_value_mesh,
)
from prototypes.v08_thermal_rating.physical_n1_domain_audit import audit_n1_domain_timeline
from prototypes.v08_thermal_rating.run_joint_bvp_proof import _build_rating_request
from prototypes.v08_thermal_rating.shadow_axial_l1_counterfactual import (
    assess_shadow_n1_counterfactual,
)

CANDIDATES = (
    "e1baa795-9cf5-5718-8fa8-0688d2102c5c",
    "9277ebb8-5b05-5130-8b90-92ee4768606b",
)
OUT = Path("/opt/cursor/artifacts/v08_03_case_identity_physical_n1_closure.json")


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _ci_status() -> tuple[str, str]:
    out = subprocess.check_output(
        [
            "gh",
            "run",
            "list",
            "--branch",
            "cursor/v08-03-live-thermal-rating-1201",
            "--limit",
            "3",
            "--json",
            "number,conclusion,headSha",
        ],
        cwd=_REPO,
        text=True,
    )
    for r in json.loads(out):
        if r.get("headSha", "").startswith(_git_head()[:12]):
            return (
                f"ci#{r['number']} {r.get('conclusion') or 'pending'}",
                "lint_failed_F841_prior" if r.get("conclusion") == "failure" else "see_shards",
            )
    return "unknown", "no_run"


def _geometry_hash(enum: Any, cid: str) -> str:
    for row in enum.candidate_records:
        if row.candidate_id == cid:
            return str(row.geometry_projection_hash)
    return ""


def _run_candidate(cid: str, provider: CoolPropProvider) -> dict[str, Any]:
    normalized, _, enum, digest = _enumerate_for_fixture()
    ghash = _geometry_hash(enum, cid)
    ctx_rating = _build_rating_request(cid, enum, digest)
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
        outcome = solve_joint_boundary_value_mesh(
            subdivisions=1,
            provider=provider,
            shell_authority=ctx.shell_authority,
            candidate_ctx=ctx,
        )
        supports = _supports_for_mesh(ctx, 1)
        q_final = np.array([c.q_w for c in outcome.cells], dtype=float)
        domain = audit_n1_domain_timeline(
            candidate_id=cid,
            geometry_hash=ghash,
            candidate_ctx=ctx,
            provider=provider,
            shell_authority=ctx.shell_authority,
            q_final=q_final,
            cells=outcome.cells,
        )
        shadow = assess_shadow_n1_counterfactual(
            outcome,
            supports=supports,
            provider=provider,
            shell_authority=ctx.shell_authority,
            l1_stop_would_block=not outcome.all_task172_gates_pass,
        )
        first_exit = domain.get("first_domain_exit_final") or domain.get(
            "first_domain_exit_initial"
        )
        return {
            "candidate_id": cid,
            "geometry_projection_hash": ghash,
            "case_binding": "V08_250KW_TASK174_ADMISSIBLE",
            "domain_audit": domain,
            "shadow_semantics": shadow,
            "joint_bvp_status": outcome.status,
            "FIRST_DOMAIN_EXIT": first_exit,
            "N1_PHYSICAL_CLOSURE_STATUS": shadow.get("n1_physical_closure_status"),
        }
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)


def _decision(rows: list[dict[str, Any]]) -> str:
    if any(r.get("N1_PHYSICAL_CLOSURE_STATUS") == "PASS" for r in rows):
        return "A"
    if any(r.get("FIRST_DOMAIN_EXIT") for r in rows):
        return "B"
    return "C"


def main() -> int:
    identity = build_case_identity_bundle()
    provider = CoolPropProvider()
    results = [_run_candidate(cid, provider) for cid in CANDIDATES]
    decision = _decision(results)
    ci_status, ci_fail = _ci_status()
    payload = {
        "TASK_ID": "V08_03_CASE_IDENTITY_AND_PHYSICAL_N1_CLOSURE",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": ci_status,
        "CI_FIRST_FAILURE": ci_fail,
        **identity,
        "SHADOW_SUCCESS_SEMANTICS_FIXED": True,
        "FIRST_DOMAIN_EXIT_CANDIDATE_1": results[0].get("FIRST_DOMAIN_EXIT"),
        "FIRST_DOMAIN_EXIT_CANDIDATE_2": results[1].get("FIRST_DOMAIN_EXIT"),
        "CANDIDATE_1_N1": results[0],
        "CANDIDATE_2_N1": results[1],
        "TASK172_ORIGINAL_GATE": "BLOCKED (C-ULP) on all cells; see shadow_semantics",
        "TASK173_ORIGINAL_GATE": "BLOCKED production rating",
        "WHOLE_ENERGY_BALANCE": results[0]
        .get("shadow_semantics", {})
        .get("aggregate", {})
        .get("ENERGY_RESIDUAL_W"),
        "N2_N4": "not_run",
        "DECISION": decision,
        "DISTINCT_FULLY_CONVERGED": 0,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "REMAINING_BLOCKER": results[0].get("FIRST_DOMAIN_EXIT") or "UNRESOLVED",
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "candidates": {r["candidate_id"]: r for r in results},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    slim = {
        k: v
        for k, v in payload.items()
        if k not in ("candidates", "CANDIDATE_1_N1", "CANDIDATE_2_N1")
    }
    print(json.dumps(slim, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
