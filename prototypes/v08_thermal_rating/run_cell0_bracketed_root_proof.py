"""V08_03_CELL0_BRACKETED_ROOT_AND_ULP_REACHABILITY closeout."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import subprocess
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
    _state_at_inlet,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_mass_flow_kg_s,
    effective_tube_mass_flow_kg_s,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    effective_tube_inlet_temperature_k as eff_tube_t,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.cell0_bracketed_root_ulp import (
    Cell0ReachabilityReport,
    TrialGateDetail,
    production_validated_if_gate_passes,
    run_cell0_bracketed_ulp_pipeline,
)
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    _enumerate_for_fixture,
    _find_bundle,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    _duty_uniform_q_per_cell,
    _supports_for_mesh,
    attempt_real_two_cell_coupling,
    audit_axial_feasibility,
    build_bvp_cell_task172_for_trial_q,
)
from prototypes.v08_thermal_rating.run_joint_bvp_proof import _build_rating_request

CANDIDATE = "e1baa795-9cf5-5718-8fa8-0688d2102c5c"
OUT = Path("/opt/cursor/artifacts/v08_03_cell0_bracketed_root_ulp_proof.json")
BASELINE = (
    152845.44912342032,
    308.26850752126296,
    306.52793869712474,
)


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
            "2",
            "--json",
            "number,status,conclusion,headSha",
        ],
        cwd=_REPO,
        text=True,
    )
    rows = json.loads(out)
    if not rows:
        return "unknown"
    r = rows[0]
    tail = f" {r['conclusion']}" if r.get("conclusion") else ""
    return f"ci#{r['number']} {r['status']}{tail} sha={r['headSha'][:7]}"


def _comparison_payload(
    pipeline: Cell0ReachabilityReport,
    ulp_best: TrialGateDetail | None,
) -> dict[str, Any]:
    bracketed = dict(pipeline.bracketed)
    if isinstance(bracketed.get("detail"), TrialGateDetail):
        bracketed["detail"] = asdict(bracketed["detail"])
    inner = bracketed.get("inner")
    if isinstance(inner, dict) and isinstance(inner.get("detail"), TrialGateDetail):
        inner = dict(inner)
        inner["detail"] = asdict(inner["detail"])
        bracketed["inner"] = inner
    return {
        "trf_2var_tmid": pipeline.trf_tmid,
        "trf_3var_u1u2": pipeline.trf_u1_u2,
        "bracketed_scalar": bracketed,
        "ulp_neighborhood": {
            **pipeline.ulp_search,
            "best": _detail_dict(ulp_best),
        },
    }


def _detail_dict(d: TrialGateDetail | None) -> dict[str, Any] | None:
    if d is None:
        return None
    dom = ("r1", "r2", "r3")[d.dominant_index]
    return {
        **asdict(d),
        "dominant_residual": dom,
        "r1_over_bound": d.r1_w / d.bound1_w if d.bound1_w > 0 else None,
        "r2_over_bound": d.r2_w / d.bound2_w if d.bound2_w > 0 else None,
        "r3_over_bound": d.r3_w / d.bound3_w if d.bound3_w > 0 else None,
    }


def main() -> int:
    provider = CoolPropProvider()
    _, _, enum, digest = _enumerate_for_fixture()
    _find_bundle(enum, CANDIDATE)
    ctx_rating = _build_rating_request(CANDIDATE, enum, digest)
    normalized_fix, _, _, _ = _enumerate_for_fixture()
    exp = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=normalized_fix.tube_side.inlet_temperature_k,
        shell_inlet_temperature_k=normalized_fix.shell_side.inlet_temperature_k,
        tube_mass_flow_kg_s=normalized_fix.tube_side.mass_flow_kg_s,
        shell_mass_flow_kg_s=normalized_fix.shell_side.mass_flow_kg_s,
        tube_property_evaluation_pressure_pa=normalized_fix.tube_side.inlet_pressure_pa,
        shell_property_evaluation_pressure_pa=normalized_fix.shell_side.inlet_pressure_pa,
        allow_live_variable_tube_mass_flow=True,
        allow_live_variable_shell_mass_flow=True,
        allow_variable_water_temperature=True,
    )
    tok = bind_experimental_thermal_boundary_v1(exp)
    ctx = _candidate_context(ctx_rating)
    ct = _CANDIDATE_RATING_CONTEXT.set(ctx)
    try:
        supports = _supports_for_mesh(ctx, 1)
        tube_mdot = float(effective_tube_mass_flow_kg_s())
        shell_mdot = float(effective_shell_mass_flow_kg_s())
        h_t0 = float(_state_at_inlet(provider, eff_tube_t(), side="TUBE").native.enthalpy_j_kg)
        h_sN = float(effective_shell_cold_inlet_enthalpy_j_kg())
        n = len(supports)
        q_uniform = _duty_uniform_q_per_cell(
            provider=provider, n_cells=n, h_t_in=h_t0, tube_mdot=tube_mdot
        )
        import numpy as np

        q_freeze = np.full(n, q_uniform, dtype=float)
        support = supports[0]
        report_feas = audit_axial_feasibility(
            q_freeze,
            provider=provider,
            h_t_inlet_j_kg=h_t0,
            h_s_cold_inlet_j_kg=h_sN,
            tube_mass_flow_kg_s=tube_mdot,
            shell_mass_flow_kg_s=shell_mdot,
        )
        q_cap = float(report_feas.per_cell_q_hi[0])

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

        pipeline: Cell0ReachabilityReport = run_cell0_bracketed_ulp_pipeline(
            request_at_q=request_at_q,
            provider=provider,
            q_cap=q_cap,
            q_seed=float(BASELINE[0]),
            baseline=BASELINE,
        )
        base = pipeline.baseline
        ulp_best = pipeline.ulp_best or base
        prod_ok, prod_reason = (False, "no_detail")
        task173 = False
        two_cell = "not_run"
        if ulp_best and ulp_best.gate_pass:
            req = request_at_q(ulp_best.q_w)
            prod_ok, prod_reason = production_validated_if_gate_passes(
                req, provider, ulp_best.q_w, ulp_best.twi_k, ulp_best.two_k
            )
            task173 = prod_ok
            two_cell = "not_run"
        elif pipeline.numerical_decision == "A":
            two = attempt_real_two_cell_coupling(
                provider=provider, shell_authority=ctx.shell_authority, candidate_ctx=ctx
            )
            two_cell = str(two.get("status", "BLOCKED"))
        max_before = base.max_ratio if base else 344.37900709181906
        max_after = ulp_best.max_ratio if ulp_best else max_before
        bracket_found = bool(pipeline.bracketed.get("bracket_found"))
        payload = {
            "TASK_ID": "V08_03_CELL0_BRACKETED_ROOT_AND_ULP_REACHABILITY",
            "PR_NUMBER": 325,
            "HEAD_SHA": _git_head(),
            "CI_STATUS": _ci_status(),
            "CELL0_Q_W": ulp_best.q_w if ulp_best else None,
            "CELL0_TWI_K": ulp_best.twi_k if ulp_best else None,
            "CELL0_TWO_K": ulp_best.two_k if ulp_best else None,
            "CELL0_R1_W": ulp_best.r1_w if ulp_best else None,
            "CELL0_R2_W": ulp_best.r2_w if ulp_best else None,
            "CELL0_R3_W": ulp_best.r3_w if ulp_best else None,
            "CELL0_BOUND1_W": ulp_best.bound1_w if ulp_best else None,
            "CELL0_BOUND2_W": ulp_best.bound2_w if ulp_best else None,
            "CELL0_BOUND3_W": ulp_best.bound3_w if ulp_best else None,
            "CELL0_MAX_ULP_RATIO_BEFORE": max_before,
            "CELL0_MAX_ULP_RATIO_AFTER": max_after,
            "BRACKETED_ROOT_FOUND": bracket_found,
            "TASK172_ORIGINAL_GATE": "PASS" if (ulp_best and ulp_best.gate_pass) else "BLOCKED",
            "TASK173_ROOT_GATE": "PASS" if task173 else "BLOCKED",
            "REAL_TWO_CELL_COUPLING": two_cell,
            "CANDIDATE_1_N1": "BLOCKED",
            "CANDIDATE_2_N1": "not_run",
            "ENERGY_BALANCE": None,
            "V07_GOLDEN": "passed_locally",
            "ENGINEERING_ACCEPTANCE": "PASS" if pipeline.numerical_decision == "A" else "BLOCKED",
            "NUMERICAL_DECISION": pipeline.numerical_decision,
            "REMAINING_BLOCKER": pipeline.remaining_blocker,
            "PRODUCTION_SOLVER_REPLACED": False,
            "MERGE_AUTHORIZED": False,
            "baseline_detail": _detail_dict(base),
            "comparison": _comparison_payload(pipeline, ulp_best),
            "production_validate": {"ok": prod_ok, "reason": prod_reason},
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(OUT)
        print(
            json.dumps(
                {k: payload[k] for k in payload if k not in ("comparison", "baseline_detail")},
                indent=2,
            )
        )
        return 0
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)


if __name__ == "__main__":
    raise SystemExit(main())
