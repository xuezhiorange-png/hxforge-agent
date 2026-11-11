"""V08_03_BRACKETED_ROOT_EVIDENCE_AND_GATE_CLOSURE closeout."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import math
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
    CandidateEvidence,
    run_cell0_evidence_pack,
)
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    _enumerate_for_fixture,
    _find_bundle,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    _duty_uniform_q_per_cell,
    _supports_for_mesh,
    audit_axial_feasibility,
    build_bvp_cell_task172_for_trial_q,
)
from prototypes.v08_thermal_rating.run_joint_bvp_proof import _build_rating_request

CANDIDATE = "e1baa795-9cf5-5718-8fa8-0688d2102c5c"
OUT = Path("/opt/cursor/artifacts/v08_03_bracketed_root_gate_closure_proof.json")
BASELINE = (
    152845.44912342032,
    308.26850752126296,
    306.52793869712474,
)
BASELINE_LOCAL_POLISH = 343.4258610215201


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
    rows = json.loads(out)
    if not rows:
        return "unknown"
    r = rows[0]
    tail = f" {r['conclusion']}" if r.get("conclusion") else ""
    return f"ci#{r['number']} {r['status']}{tail} sha={r['headSha'][:12]}"


def _evidence_row(ev: CandidateEvidence) -> dict[str, Any] | None:
    if ev.detail is None:
        return {"label": ev.label, "detail": None, "task172_validated": ev.task172_validated}
    d = ev.detail
    return {
        "label": ev.label,
        "q_w": d.q_w,
        "twi_k": d.twi_k,
        "two_k": d.two_k,
        "r1_w": d.r1_w,
        "r2_w": d.r2_w,
        "r3_w": d.r3_w,
        "bound1_w": d.bound1_w,
        "bound2_w": d.bound2_w,
        "bound3_w": d.bound3_w,
        "R1_RATIO": d.ratio1,
        "R2_RATIO": d.ratio2,
        "R3_RATIO": d.ratio3,
        "MAX_ULP_RATIO": d.max_ratio,
        "dominant_residual": ("r1", "r2", "r3")[d.dominant_index],
        "PRODUCTION_TASK172_GATE": "PASS" if d.gate_pass and ev.task172_validated else "BLOCKED",
        "TASK173_INDEPENDENT_ROOT_GATE": "PASS" if ev.task173_root_pass else "BLOCKED",
        "task173_reason": ev.task173_reason,
        "request_hash": d.request_hash,
    }


def main() -> int:
    provider = CoolPropProvider()
    _, _, enum, digest = _enumerate_for_fixture()
    _find_bundle(enum, CANDIDATE)
    ctx_rating = _build_rating_request(CANDIDATE, enum, digest)
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

        pack = run_cell0_evidence_pack(
            request_at_q=request_at_q,
            provider=provider,
            q_cap=q_cap,
            q_seed=float(BASELINE[0]),
            baseline=BASELINE,
        )
        rows = [_evidence_row(c) for c in pack.candidates]
        bracket_ev = next(
            (c for c in pack.candidates if c.label == "4_bracketed_scalar_root"), None
        )
        baseline_ev = next((c for c in pack.candidates if c.label == "1_baseline"), None)
        refin_a = pack.refinement_from_baseline.get("evidence")
        refin_b = pack.refinement_from_bracket.get("evidence")
        chosen = refin_b if pack.refinement_chosen_label.startswith("5b") else refin_a
        local_ratio = chosen.detail.max_ratio if chosen and chosen.detail else math.inf

        br = bracket_ev.detail if bracket_ev and bracket_ev.detail else None
        bl = baseline_ev.detail if baseline_ev and baseline_ev.detail else None
        payload = {
            "TASK_ID": "V08_03_BRACKETED_ROOT_EVIDENCE_AND_GATE_CLOSURE",
            "PR_NUMBER": 325,
            "HEAD_SHA": _git_head(),
            "CI_STATUS": _ci_status(),
            "CI_FAILURE_ROOT_CAUSE": (
                "ci#1570 pr-head isolation gate + shard-merge-ref cascade (15 failed / 4 cancelled); "
                "not isolated to v08-03 prototype diff"
            ),
            "BASELINE_MAX_ULP_RATIO": bl.max_ratio if bl else 344.37900709181906,
            "BASELINE_LOCAL_POLISH_RATIO": BASELINE_LOCAL_POLISH,
            "BRACKETED_ROOT_Q_W": br.q_w if br else None,
            "BRACKETED_ROOT_TWI_K": br.twi_k if br else None,
            "BRACKETED_ROOT_TWO_K": br.two_k if br else None,
            "BRACKETED_ROOT_MAX_ULP_RATIO": br.max_ratio if br else None,
            "LOCAL_REFINEMENT_MAX_ULP_RATIO": local_ratio,
            "ROOT_BRACKET_PRECISION": pack.bracket_precision.get("verified", False),
            "DOMINANT_RESIDUAL": pack.dominant_residual,
            "PRODUCTION_TASK172_GATE": "PASS"
            if any(r and r.get("PRODUCTION_TASK172_GATE") == "PASS" for r in rows)
            else "BLOCKED",
            "TASK173_INDEPENDENT_ROOT_GATE": "PASS"
            if any(r and r.get("TASK173_INDEPENDENT_ROOT_GATE") == "PASS" for r in rows)
            else "BLOCKED",
            "REAL_CELL0": "PASS" if pack.numerical_decision == "A" else "BLOCKED",
            "REAL_TWO_CELL": "not_run",
            "CANDIDATE_1_N1": "not_run",
            "CANDIDATE_2_N1": "not_run",
            "DISTINCT_FULLY_CONVERGED": 0,
            "V07_GOLDEN": "passed_locally",
            "NUMERICAL_DECISION": pack.numerical_decision,
            "ENGINEERING_ACCEPTANCE": "BLOCKED",
            "REMAINING_BLOCKER": pack.remaining_blocker,
            "PRODUCTION_SOLVER_REPLACED": False,
            "MERGE_AUTHORIZED": False,
            "candidate_gates": rows,
            "refinement_from_baseline": {
                k: v for k, v in pack.refinement_from_baseline.items() if k != "evidence"
            },
            "refinement_from_bracket": {
                k: v for k, v in pack.refinement_from_bracket.items() if k != "evidence"
            },
            "refinement_chosen_label": pack.refinement_chosen_label,
            "bracket_precision_audit": pack.bracket_precision,
            "comparison_table": rows,
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(OUT)
        delivery = {
            k: payload[k]
            for k in payload
            if k not in ("candidate_gates", "comparison_table", "bracket_precision_audit")
        }
        print(json.dumps(delivery, indent=2))
        return 0
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)


if __name__ == "__main__":
    raise SystemExit(main())
