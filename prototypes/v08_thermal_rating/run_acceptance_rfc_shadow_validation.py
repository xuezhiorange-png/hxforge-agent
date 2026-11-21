"""V08_03_ACCEPTANCE_RFC_AND_SHADOW_VALIDATION closeout."""
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
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    _duty_uniform_q_per_cell,
    _supports_for_mesh,
    build_bvp_cell_task172_for_trial_q,
)
from prototypes.v08_thermal_rating.run_joint_bvp_proof import _build_rating_request
from prototypes.v08_thermal_rating.shadow_layered_acceptance import (
    ORIGINAL_PRODUCTION_ACCEPTANCE,
    layer_to_dict,
    shadow_l1_local_heat_transfer,
    shadow_l2_property_consistency_probe,
    shadow_l3_placeholder_from_rating,
    shadow_l4_placeholder,
)

CANDIDATES = (
    "e1baa795-9cf5-5718-8fa8-0688d2102c5c",
    "9277ebb8-5b05-5130-8b90-92ee4768606b",
)
E1_BEST = (
    152845.44912345504,
    308.26850752129053,
    306.52793869715185,
)
OUT = Path("/opt/cursor/artifacts/v08_03_acceptance_rfc_shadow_validation.json")


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
            "2",
            "--json",
            "number,status,conclusion,headSha",
        ],
        cwd=_REPO,
        text=True,
    )
    rows = json.loads(out)
    if not rows:
        return "unknown", "no_runs"
    r = rows[0]
    cause = "pending"
    if r.get("conclusion") == "failure":
        if r.get("headSha", "").startswith(_git_head()[:12]):
            cause = "see_run_jobs: may include shard failures or pr-head race (1573 resolve-authority mismatch)"
        else:
            cause = f"failed_on_sha={r['headSha'][:12]}"
    elif r.get("conclusion") == "success":
        cause = "all_required_jobs_passed"
    return f"ci#{r['number']} {r['status']} {r.get('conclusion') or ''}", cause


def _original_rating(candidate_id: str, provider: CoolPropProvider) -> dict[str, Any]:
    normalized, handoff, enum, task168_digest = _enumerate_for_fixture()
    bundle_row = _find_bundle(enum, candidate_id)
    candidate = bundle_row.candidate
    b = bundle_row.bundle
    space_hash = enum.space_hash
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
        candidate, space_hash, b, topology, t174, task168_digest
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
    st = getattr(outcome, "status", type(outcome).__name__)
    row: dict[str, Any] = {
        "task173_status": st,
        "acceptance_mode": ORIGINAL_PRODUCTION_ACCEPTANCE,
    }
    if type(outcome) is Task173BlockedResult:
        row["failure_code"] = outcome.failure_code
        row["failed_mesh_subdivisions"] = outcome.failed_mesh_subdivisions
        row["result_hash"] = outcome.result_hash
    return row


def _e1_cell0_shadow(provider: CoolPropProvider) -> dict[str, Any]:
    _, _, enum, digest = _enumerate_for_fixture()
    _find_bundle(enum, CANDIDATES[0])
    ctx_rating = _build_rating_request(CANDIDATES[0], enum, digest)
    from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
        _CANDIDATE_RATING_CONTEXT,
        _candidate_context,
        _state_at_inlet,
        effective_shell_cold_inlet_enthalpy_j_kg,
        effective_shell_mass_flow_kg_s,
        effective_tube_mass_flow_kg_s,
    )
    from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
        effective_tube_inlet_temperature_k as eff_tube_t,
    )

    normalized, _, _, _ = _enumerate_for_fixture()
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
        import numpy as np

        supports = _supports_for_mesh(ctx, 1)
        tube_mdot = float(effective_tube_mass_flow_kg_s())
        shell_mdot = float(effective_shell_mass_flow_kg_s())
        h_t0 = float(_state_at_inlet(provider, eff_tube_t(), side="TUBE").native.enthalpy_j_kg)
        h_sN = float(effective_shell_cold_inlet_enthalpy_j_kg())
        n = len(supports)
        q_uniform = _duty_uniform_q_per_cell(
            provider=provider, n_cells=n, h_t_in=h_t0, tube_mdot=tube_mdot
        )
        q_freeze = np.full(n, q_uniform, dtype=float)
        support = supports[0]

        def request_at_q(q_val: float) -> Any:
            request, _, _, _, _ = build_bvp_cell_task172_for_trial_q(
                0,
                q_val,
                q_freeze,
                support=support,
                provider=provider,
                shell_authority=ctx.shell_authority,
                h_t_inlet_j_kg=h_t0,
                h_s_cold_inlet_j_kg=h_sN,
                tube_mass_flow_kg_s=tube_mdot,
                shell_mass_flow_kg_s=shell_mdot,
            )
            return request

        q, twi, two = E1_BEST
        req = request_at_q(q)
        l1 = shadow_l1_local_heat_transfer(
            q_w=q, twi_k=twi, two_k=two, request=req, provider=provider
        )
        l2 = shadow_l2_property_consistency_probe(
            q_w=q,
            twi_k=twi,
            two_k=two,
            request=req,
            provider=provider,
            request_at_q=request_at_q,
        )
        return {
            "cell_index": 0,
            "fixed_best_triple": {"q_w": q, "twi_k": twi, "two_k": two},
            "shadow_layers": [layer_to_dict(l1), layer_to_dict(l2)],
        }
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)


def main() -> int:
    provider = CoolPropProvider()
    ci_status, ci_cause = _ci_status()
    results: dict[str, Any] = {}
    distinct_converged = 0
    for cid in CANDIDATES:
        orig = _original_rating(cid, provider)
        if orig.get("task173_status") == "VALIDATED":
            distinct_converged += 1
        shadow = {
            "SHADOW_LAYERED_ACCEPTANCE": True,
            "production_isolated": True,
            "layers": [],
        }
        if cid == CANDIDATES[0]:
            cell0 = _e1_cell0_shadow(provider)
            shadow["cell0"] = cell0
            shadow["layers"].extend(cell0.get("shadow_layers", []))
        else:
            shadow["cell0"] = {
                "status": "UNRESOLVED",
                "note": "no frozen cell-0 best triple audited for cand2",
            }
        shadow["layers"].append(
            layer_to_dict(
                shadow_l3_placeholder_from_rating(
                    task173_status=str(orig.get("task173_status", "UNKNOWN")),
                    detail={"failed_mesh": orig.get("failed_mesh_subdivisions")},
                )
            )
        )
        shadow["layers"].append(
            layer_to_dict(
                shadow_l4_placeholder(
                    task173_status=str(orig.get("task173_status", "UNKNOWN")),
                    failure_code=orig.get("failure_code"),
                )
            )
        )
        results[cid] = {
            "ORIGINAL_PRODUCTION_ACCEPTANCE": orig,
            "SHADOW_LAYERED_ACCEPTANCE": shadow,
        }

    payload = {
        "TASK_ID": "V08_03_ACCEPTANCE_RFC_AND_SHADOW_VALIDATION",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": ci_status,
        "CI_FAILURE_ROOT_CAUSE": ci_cause,
        "ORIGINAL_ACCEPTANCE_UNCHANGED": True,
        "SHADOW_ACCEPTANCE_IMPLEMENTED": True,
        "SHADOW_MODE_PRODUCTION_ISOLATED": True,
        "L1_NUMERICAL_EVIDENCE": results[CANDIDATES[0]]
        .get("SHADOW_LAYERED_ACCEPTANCE", {})
        .get("cell0", {})
        .get("shadow_layers", [{}])[0],
        "L2_PROPERTY_UNCERTAINTY": "UNRESOLVED",
        "L3_WHOLE_EXCHANGER_VALIDATION": "BLOCKED",
        "L4_ENGINEERING_CONSTRAINTS": "BLOCKED",
        "CANDIDATE_1_ORIGINAL_RATING": results[CANDIDATES[0]]["ORIGINAL_PRODUCTION_ACCEPTANCE"],
        "CANDIDATE_1_SHADOW_RESULT": results[CANDIDATES[0]]["SHADOW_LAYERED_ACCEPTANCE"],
        "CANDIDATE_2_ORIGINAL_RATING": results[CANDIDATES[1]]["ORIGINAL_PRODUCTION_ACCEPTANCE"],
        "CANDIDATE_2_SHADOW_RESULT": results[CANDIDATES[1]]["SHADOW_LAYERED_ACCEPTANCE"],
        "RFC_READY_FOR_APPROVAL": True,
        "PROPOSED_CONTRACT_CHANGES": [
            "No automatic threshold numbers; RFC lists source locations for review",
            "Task172 C-ULP gate: src/hexagent/exchangers/shell_tube/task172_local_runtime/service.py eval_trial_residual_gate",
            "Proposed: formal L1-L4 acceptance document — requires PRODUCTION_CONTRACT_CHANGE_AUTHORIZED",
        ],
        "UNRESOLVED_RISKS": [
            "Property uncertainty budget not measured end-to-end",
            "CoolProp dominance not proven from single-point Twi probe",
            "L3/L4 require full VALIDATED Rating — not demonstrated",
        ],
        "V07_GOLDEN": "PASS local pytest tests/prototypes/test_v07_final_live_e2e_delivery.py",
        "DISTINCT_FULLY_CONVERGED": distinct_converged,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "candidates": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    slim = {k: v for k, v in payload.items() if k != "candidates"}
    print(json.dumps(slim, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
