"""V08_03_FLOAT_LATTICE_ROOT_VERIFICATION closeout."""
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
OUT = Path("/opt/cursor/artifacts/v08_03_float_lattice_root_verification.json")
BRACKETED_ROOT_RATIO_BEFORE = 37.79067056744172
BASELINE = (
    152845.44912342032,
    308.26850752126296,
    306.52793869712474,
)


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
            "number,status,conclusion,headSha,url",
        ],
        cwd=_REPO,
        text=True,
    )
    rows = json.loads(out)
    if not rows:
        return "unknown", "no_runs"
    r = rows[0]
    status = f"ci#{r['number']} {r['status']} {r.get('conclusion') or ''} sha={r['headSha'][:12]}"
    root = "pending_analysis"
    if r.get("conclusion") == "failure":
        root = _ci_failure_snippet(r["number"])
    elif r.get("conclusion") == "success":
        root = "all_required_jobs_passed"
    elif r.get("status") in ("queued", "in_progress"):
        root = "ci_in_progress"
    return status, root


def _ci_failure_snippet(run_number: int) -> str:
    try:
        out = subprocess.check_output(
            [
                "gh",
                "run",
                "view",
                str(run_number),
                "--json",
                "jobs",
            ],
            cwd=_REPO,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        jobs = json.loads(out)["jobs"]
        failed = [j["name"] for j in jobs if j.get("conclusion") == "failure"]
        lint_ok = any(
            j.get("conclusion") == "success" and "lint" in j["name"].lower() for j in jobs
        )
        parts = [
            f"{len(failed)} failed jobs",
            "lint=pass" if lint_ok else "lint=unknown",
        ]
        if failed:
            parts.append(f"first_fail={failed[0][:80]}")
        return "; ".join(parts)
    except Exception:
        return "failure_details_unavailable"


def _evidence_row(ev: CandidateEvidence) -> dict[str, Any] | None:
    if ev.detail is None:
        return {"label": ev.label, "detail": None, "task172_validated": ev.task172_validated}
    d = ev.detail
    return {
        "label": ev.label,
        "q_w": d.q_w,
        "twi_k": d.twi_k,
        "two_k": d.two_k,
        "R1_RATIO": d.ratio1,
        "R2_RATIO": d.ratio2,
        "R3_RATIO": d.ratio3,
        "MAX_ULP_RATIO": d.max_ratio,
        "PRODUCTION_TASK172_GATE": "PASS" if d.gate_pass and ev.task172_validated else "BLOCKED",
        "INDEPENDENT_TASK173_ROOT_GATE": "PASS" if ev.task173_root_pass else "BLOCKED",
        "task173_reason": ev.task173_reason,
        "task173_f_q_w": ev.task173_f_q_w,
        "request_hash": d.request_hash,
    }


def _numerical_limit_evidence(
    pack: Any,
    lattice_ev: CandidateEvidence | None,
    refin: dict[str, Any],
) -> dict[str, Any]:
    aud = pack.bracket_precision
    det = lattice_ev.detail if lattice_ev and lattice_ev.detail else None
    return {
        "physical_residuals_w": {
            "r1": det.r1_w if det else None,
            "r2": det.r2_w if det else None,
            "r3": det.r3_w if det else None,
        },
        "ulp_bounds_w": {
            "bound1": det.bound1_w if det else None,
            "bound2": det.bound2_w if det else None,
            "bound3": det.bound3_w if det else None,
        },
        "achieved_ratios": {
            "r1": det.ratio1 if det else None,
            "r2": det.ratio2 if det else None,
            "r3": det.ratio3 if det else None,
        },
        "rounding_sources": [
            "binary64_q_and_enthalpy_rebuild_per_trial",
            "tmid_to_twi_two_wall_conduction",
            "coolprop_ph_quantization",
        ],
        "verified_float_lattice": {
            "q_adjacent": aud.get("q_bracket_adjacent_floats"),
            "tmid_adjacent": aud.get("tmid_bracket_adjacent_floats"),
            "q_shrink_evaluations": (aud.get("q_lattice_shrink") or {}).get("evaluations"),
            "discontinuities_q": (aud.get("q_lattice_shrink") or {}).get("discontinuities"),
        },
        "local_discrete_search": {
            "steps": refin.get("steps_evaluated"),
            "best_max_ratio": refin.get("best_max_ratio"),
            "sensitivity": refin.get("sensitivity_probe"),
        },
        "conclusion_class": "B_float_lattice_below_ulP_gate",
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
        lattice_ev = next(
            (c for c in pack.candidates if c.label == "4_float_lattice_scalar_root"), None
        )
        refin = pack.refinement_from_bracket
        det = lattice_ev.detail if lattice_ev and lattice_ev.detail else None
        best = refin.get("best_max_ratio", det.max_ratio if det else math.inf)
        sens = refin.get("sensitivity_probe") or {}
        ci_status, ci_root = _ci_status()
        aud = pack.bracket_precision
        payload = {
            "TASK_ID": "V08_03_FLOAT_LATTICE_ROOT_VERIFICATION",
            "PR_NUMBER": 325,
            "HEAD_SHA": _git_head(),
            "CI_STATUS": ci_status,
            "CI_FAILURE_ROOT_CAUSE": ci_root,
            "Q_BRACKET_ADJACENT_FLOATS": aud.get("q_bracket_adjacent_floats"),
            "TMID_BRACKET_ADJACENT_FLOATS": aud.get("tmid_bracket_adjacent_floats"),
            "Q_RESIDUAL_SENSITIVITY_CORRECTED": bool(sens.get("q_perturbation_uses_trial_request")),
            "BRACKETED_ROOT_RATIO_BEFORE": BRACKETED_ROOT_RATIO_BEFORE,
            "FLOAT_REFINED_MAX_ULP_RATIO": best,
            "R1_RATIO": det.ratio1 if det else None,
            "R2_RATIO": det.ratio2 if det else None,
            "R3_RATIO": det.ratio3 if det else None,
            "PRODUCTION_TASK172_GATE": "PASS"
            if lattice_ev
            and lattice_ev.detail
            and lattice_ev.detail.gate_pass
            and lattice_ev.task172_validated
            else "BLOCKED",
            "INDEPENDENT_TASK173_ROOT_GATE": "PASS"
            if lattice_ev and lattice_ev.task173_root_pass
            else "BLOCKED",
            "REAL_CELL0": "PASS" if pack.numerical_decision == "A" else "BLOCKED",
            "REAL_TWO_CELL": "not_run",
            "CANDIDATE_1_N1": "not_run",
            "CANDIDATE_2_N1": "not_run",
            "NUMERICAL_LIMIT_EVIDENCE": _numerical_limit_evidence(pack, lattice_ev, refin),
            "NUMERICAL_DECISION": pack.numerical_decision,
            "DISTINCT_FULLY_CONVERGED": 0,
            "ENGINEERING_ACCEPTANCE": "BLOCKED",
            "REMAINING_BLOCKER": pack.remaining_blocker,
            "PRODUCTION_SOLVER_REPLACED": False,
            "MERGE_AUTHORIZED": False,
            "candidate_gates": [_evidence_row(c) for c in pack.candidates],
            "bracket_precision_audit": aud,
            "refinement_from_lattice": {k: v for k, v in refin.items() if k != "evidence"},
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        delivery = {
            k: val
            for k, val in payload.items()
            if k not in ("candidate_gates", "bracket_precision_audit")
        }
        print(json.dumps(delivery, indent=2))
        return 0
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)


if __name__ == "__main__":
    raise SystemExit(main())
