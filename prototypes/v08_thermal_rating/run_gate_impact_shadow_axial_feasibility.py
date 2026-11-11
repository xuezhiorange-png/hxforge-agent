"""V08_03_GATE_IMPACT_AND_SHADOW_AXIAL_FEASIBILITY closeout."""
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
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import Task173BlockedResult
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    _candidate_context,
    validate_candidate_rating,
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
from prototypes.v08_thermal_rating.run_joint_bvp_proof import _build_rating_request
from prototypes.v08_thermal_rating.shadow_axial_l1_counterfactual import (
    decide_gate_impact,
    run_shadow_n1_mesh,
)

CANDIDATES = (
    "e1baa795-9cf5-5718-8fa8-0688d2102c5c",
    "9277ebb8-5b05-5130-8b90-92ee4768606b",
)
OUT = Path("/opt/cursor/artifacts/v08_03_gate_impact_shadow_axial_feasibility.json")


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _ci_first_failure() -> tuple[str, str]:
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
            "number,status,conclusion,headSha",
        ],
        cwd=_REPO,
        text=True,
    )
    rows = json.loads(out)
    for r in rows:
        if r.get("headSha", "").startswith(_git_head()[:12]):
            st = f"ci#{r['number']} {r['status']} {r.get('conclusion') or ''}"
            detail = "pending" if not r.get("conclusion") else "see_pr_checks"
            return st, detail
    return "unknown", "no_run_for_head"


def _geometry_hash(candidate_id: str, enum: Any) -> str:
    for row in enum.candidate_records:
        if row.candidate_id == candidate_id:
            return str(row.geometry_projection_hash)
    return ""


def _original_rating(candidate_id: str, provider: CoolPropProvider) -> dict[str, Any]:
    normalized, _, enum, task168_digest = _enumerate_for_fixture()
    _find_bundle(enum, candidate_id)
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
        return {"status": "BLOCKED", "reason": f"task174_{type(t174).__name__}"}
    rating_req = v08_thermal_rating_request(
        candidate, enum.space_hash, b, topology, t174, task168_digest
    )
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
    try:
        outcome = validate_candidate_rating(rating_req, provider)
    finally:
        reset_experimental_thermal_boundary(tok)
    row: dict[str, Any] = {
        "path": "ORIGINAL_PRODUCTION_ACCEPTANCE",
        "task173_status": getattr(outcome, "status", type(outcome).__name__),
    }
    if type(outcome) is Task173BlockedResult:
        row["failure_code"] = outcome.failure_code
        row["failed_mesh_subdivisions"] = outcome.failed_mesh_subdivisions
        row["result_hash"] = outcome.result_hash
        diag = list(outcome.diagnostics)
        row["diagnostics_sample"] = diag[:12]
        for item in diag:
            if item.startswith("task172") or "task172" in item.lower():
                row["first_task172_hint"] = item
                break
    return row


def _shadow_path(candidate_id: str, provider: CoolPropProvider) -> dict[str, Any]:
    normalized, _, enum, digest = _enumerate_for_fixture()
    ctx_rating = _build_rating_request(candidate_id, enum, digest)
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
        _, shadow_n1 = run_shadow_n1_mesh(
            subdivisions=1,
            provider=provider,
            shell_authority=ctx.shell_authority,
            candidate_ctx=ctx,
        )
        shadow_n2_n4: dict[str, Any] = {"status": "not_run"}
        if shadow_n1.get("shadow_physical_profile_without_l1_stop"):
            meshes = {}
            for sub in (2, 4):
                try:
                    _, sh = run_shadow_n1_mesh(
                        subdivisions=sub,
                        provider=provider,
                        shell_authority=ctx.shell_authority,
                        candidate_ctx=ctx,
                    )
                    meshes[str(sub)] = {
                        "shadow_physical": sh.get("shadow_physical_profile_without_l1_stop"),
                        "blockers": sh.get("independent_remaining_blockers"),
                        "aggregate": sh.get("aggregate"),
                    }
                except Exception as exc:  # noqa: BLE001
                    meshes[str(sub)] = {"status": "BLOCKED", "error": type(exc).__name__}
            shadow_n2_n4 = meshes
        return {
            "path": "SHADOW_L1_COUNTERFACTUAL",
            "shadow_n1": shadow_n1,
            "shadow_n2_n4": shadow_n2_n4,
        }
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)


def main() -> int:
    provider = CoolPropProvider()
    ci_status, ci_fail = _ci_first_failure()
    _, _, enum, _ = _enumerate_for_fixture()
    candidate_payloads: list[dict[str, Any]] = []
    by_id: dict[str, Any] = {}
    for cid in CANDIDATES:
        orig = _original_rating(cid, provider)
        shadow = _shadow_path(cid, provider)
        ghash = _geometry_hash(cid, enum)
        pack = {
            "candidate_id": cid,
            "geometry_projection_hash": ghash,
            "ORIGINAL_PRODUCTION_ACCEPTANCE": orig,
            **shadow,
        }
        by_id[cid] = pack
        candidate_payloads.append(pack)

    decision, l1_sufficient = decide_gate_impact(candidate_results=candidate_payloads)

    blockers_union: list[str] = []
    for p in candidate_payloads:
        blockers_union.extend(p.get("shadow_n1", {}).get("independent_remaining_blockers", []))

    agg_e1 = (
        candidate_payloads[0].get("shadow_n1", {}).get("aggregate", {})
        if candidate_payloads
        else {}
    )
    payload = {
        "TASK_ID": "V08_03_GATE_IMPACT_AND_SHADOW_AXIAL_FEASIBILITY",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": ci_status,
        "CI_FIRST_FAILURE": ci_fail,
        "CANDIDATE_1_GEOMETRY_HASH": by_id[CANDIDATES[0]].get("geometry_projection_hash"),
        "CANDIDATE_2_GEOMETRY_HASH": by_id[CANDIDATES[1]].get("geometry_projection_hash"),
        "CANDIDATE_1_ORIGINAL": by_id[CANDIDATES[0]]["ORIGINAL_PRODUCTION_ACCEPTANCE"],
        "CANDIDATE_1_SHADOW_N1": by_id[CANDIDATES[0]].get("shadow_n1"),
        "CANDIDATE_1_SHADOW_N2_N4": by_id[CANDIDATES[0]].get("shadow_n2_n4"),
        "CANDIDATE_2_ORIGINAL": by_id[CANDIDATES[1]]["ORIGINAL_PRODUCTION_ACCEPTANCE"],
        "CANDIDATE_2_SHADOW_N1": by_id[CANDIDATES[1]].get("shadow_n1"),
        "CANDIDATE_2_SHADOW_N2_N4": by_id[CANDIDATES[1]].get("shadow_n2_n4"),
        "SHADOW_ACTUAL_Q": agg_e1.get("Q_SUM_W", "not_available"),
        "SHADOW_OUTLET_TEMPERATURES": {
            "tube_k": agg_e1.get("TUBE_OUTLET_T_K"),
            "shell_k": agg_e1.get("SHELL_OUTLET_T_K"),
        },
        "SHADOW_ENERGY_BALANCE": agg_e1.get("ENERGY_RESIDUAL_W", "not_available"),
        "L1_ONLY_CHANGE_SUFFICIENT": l1_sufficient,
        "INDEPENDENT_REMAINING_BLOCKERS": sorted(set(blockers_union)),
        "DECISION": decision,
        "RFC_CONTRACT_APPROVAL_READY": decision == "B",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "DISTINCT_FULLY_CONVERGED": 0,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "candidates": by_id,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    slim = {k: v for k, v in payload.items() if k != "candidates"}
    print(json.dumps(slim, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
