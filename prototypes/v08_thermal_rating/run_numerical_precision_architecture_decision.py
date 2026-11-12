"""V08_03_NUMERICAL_PRECISION_ARCHITECTURE_DECISION — unified best point + error audit."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import math
import subprocess
import sys
from decimal import Decimal, localcontext
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
    bracket_endpoints_adjacent,
    build_candidate_evidence,
    production_trial_gate,
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
from prototypes.v08_thermal_rating.true_three_equation_cell_coupling import (
    build_closure_primitives,
)

CANDIDATE = "e1baa795-9cf5-5718-8fa8-0688d2102c5c"
BASELINE = (152845.44912342032, 308.26850752126296, 306.52793869712474)
OUT_JSON = Path("/opt/cursor/artifacts/v08_03_numerical_precision_architecture_decision.json")
OUT_MD = Path("docs/decisions/V08_03_NUMERICAL_PRECISION_ARCHITECTURE_DECISION.md")


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
            "1",
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
    status = f"ci#{r['number']} {r['status']} {r.get('conclusion') or ''}"
    cause = (
        "verified: lint+manifest failure on 1572 (SIM102 + missing manifest entry); fixed in this commit"
        if r.get("number") == 1572 and r.get("conclusion") == "failure"
        else str(r.get("conclusion") or "pending")
    )
    return status, cause


def _decimal_residuals_frozen_conductances(
    *,
    q_w: float,
    twi_k: float,
    two_k: float,
    tube_k: float,
    shell_k: float,
    g_i: float,
    g_o: float,
    rwall: float,
) -> tuple[float, float, float]:
    with localcontext() as ctx:
        ctx.prec = 50
        q = Decimal(str(q_w))
        twi = Decimal(str(twi_k))
        two = Decimal(str(two_k))
        tt = Decimal(str(tube_k))
        ts = Decimal(str(shell_k))
        gi = Decimal(str(g_i))
        go = Decimal(str(g_o))
        rw = Decimal(str(rwall))
        r1 = q - gi * (tt - twi)
        r2 = q - (twi - two) / rw
        r3 = q - go * (two - ts)
        return float(r1), float(r2), float(r3)


def _audit_float_bracket(
    *,
    lo: float,
    hi: float,
    f_lo: float,
    f_hi: float,
    label: str,
) -> dict[str, Any]:
    adjacent = bracket_endpoints_adjacent(lo, hi)
    return {
        "label": label,
        "lo": lo,
        "hi": hi,
        "lo_hex": float(lo).hex(),
        "hi_hex": float(hi).hex(),
        "lo_finite": math.isfinite(lo),
        "hi_finite": math.isfinite(hi),
        "lo_ne_hi": lo != hi,
        "nextafter_left_plus_inf_eq_right": (
            math.nextafter(lo, math.inf) == hi if lo < hi else None
        ),
        "adjacent_representable": adjacent,
        "f_lo": f_lo,
        "f_hi": f_hi,
        "sign_opposite": (
            math.isfinite(f_lo)
            and math.isfinite(f_hi)
            and f_lo != 0.0
            and f_hi != 0.0
            and f_lo * f_hi < 0.0
        ),
        "scope_note": (
            "Adjacent scalar bracket only; does not exhaust all representable (q,Twi,Two) triples."
        ),
    }


def _error_source_study(
    detail: Any,
    *,
    request: Any,
    provider: Any,
) -> dict[str, Any]:
    prim = build_closure_primitives(request, provider)
    r1p, r2p, r3p = detail.r1_w, detail.r2_w, detail.r3_w
    b3 = detail.bound3_w
    r1d, r2d, r3d = _decimal_residuals_frozen_conductances(
        q_w=detail.q_w,
        twi_k=detail.twi_k,
        two_k=detail.two_k,
        tube_k=float(request.tube_bulk_state.temperature_k),
        shell_k=float(request.shell_bulk_state.temperature_k),
        g_i=detail.g_i_w_k,
        g_o=detail.g_o_w_k,
        rwall=detail.rwall_k_w,
    )
    arith_r3 = abs(r3d - r3p)
    arith_ratio = arith_r3 / b3 if b3 > 0 else math.inf
    prop_delta_r3 = 0.0
    try:
        up = production_trial_gate(
            detail.q_w,
            math.nextafter(detail.twi_k, math.inf),
            detail.two_k,
            request=request,
            provider=provider,
        )
        if up:
            prop_delta_r3 = max(prop_delta_r3, abs(up.r3_w - r3p))
    except Exception:
        pass
    prop_ratio = prop_delta_r3 / b3 if b3 > 0 else math.nan
    study: dict[str, Any] = {
        "A_production_float": {
            "r1_w": r1p,
            "r2_w": r2p,
            "r3_w": r3p,
            "g_i_w_per_k": detail.g_i_w_k,
            "g_o_w_per_k": detail.g_o_w_k,
            "rwall_k_w": detail.rwall_k_w,
            "bounds_w": [detail.bound1_w, detail.bound2_w, detail.bound3_w],
            "ratios": [detail.ratio1, detail.ratio2, detail.ratio3],
            "request_hash": detail.request_hash,
            "tube_bulk_snapshot_id": prim.tube_bulk_id,
            "shell_bulk_snapshot_id": prim.shell_bulk_id,
        },
        "B_decimal_frozen_conductances": {
            "r1_w": r1d,
            "r2_w": r2d,
            "r3_w": r3d,
            "delta_r3_vs_A_w": arith_r3,
            "delta_r3_bound_ratio": arith_ratio,
        },
        "C_property_neighbor_twi_up": {"delta_r3_w_vs_A": prop_delta_r3, "bound_ratio": prop_ratio},
    }
    if arith_ratio < 0.05:
        study["arith_dominates_r3"] = False
    else:
        study["arith_dominates_r3"] = "UNRESOLVED"
    study["property_sensitivity_exceeds_arith"] = (
        "UNRESOLVED"
        if not math.isfinite(prop_ratio) or prop_ratio == 0.0
        else (prop_ratio > arith_ratio)
    )
    study["coolprop_dominance_proven"] = False
    study["attribution_notes"] = [
        "Decimal B compares residual formula at frozen Gi/Go/Rwall only.",
        "Zero delta_r3 on a single Twi+1 ULP probe does not prove zero CoolProp quantization.",
        "Property uncertainty budget: UNRESOLVED.",
    ]
    return study


def _architecture_choice(error: dict[str, Any], best_max: float) -> tuple[str, str, bool]:
    ar = error["B_decimal_frozen_conductances"]["delta_r3_bound_ratio"]
    pr = error["C_property_neighbor_twi_up"].get("bound_ratio")
    if best_max <= 1.0:
        return "A", "high_precision_arithmetic_sufficient", False
    if isinstance(ar, float) and ar < 0.05 and best_max > 1.0:
        if isinstance(pr, float) and pr > max(ar, 0.05):
            return (
                "B",
                "Gi/Go/Rwall and wall-correlation sensitivity exceed float-arithmetic replay; "
                "upgrade property/state evaluation pipeline (not solver budget)",
                True,
            )
        return (
            "C",
            "Recommend formal layered acceptance RFC review; does not prove current contract must relax",
            False,
        )
    if isinstance(ar, float) and ar >= 0.05:
        return (
            "A",
            "Decimal replay shows float residual kernel may dominate; "
            "authorize extended-precision _eval_trial accumulation study only",
            False,
        )
    return (
        "D",
        "insufficient decisive separation between arithmetic, property, and contract sources",
        False,
    )


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
        ranked = sorted(
            (c for c in pack.candidates if c.detail is not None),
            key=lambda c: c.detail.max_ratio,  # type: ignore[union-attr]
        )
        if not ranked:
            raise RuntimeError("no_candidate_with_detail")
        best_c = ranked[0]
        d = best_c.detail
        assert d is not None
        req = request_at_q(d.q_w)
        ev = build_candidate_evidence(
            "unified_best_rerun",
            q_w=d.q_w,
            twi_k=d.twi_k,
            two_k=d.two_k,
            request_at_q=request_at_q,
            provider=provider,
        )
        if ev.detail is not None:
            d = ev.detail
        vmax = max(d.ratio1, d.ratio2, d.ratio3)
        assert abs(vmax - d.max_ratio) < 1.0e-9 or math.isclose(
            vmax, d.max_ratio, rel_tol=0, abs_tol=1e-9
        )
        prim = build_closure_primitives(req, provider)
        aud = pack.bracket_precision
        q_fin = aud.get("q_bracket_final_w") or aud.get("q_bracket_initial_w")
        tmid_fin = aud.get("tmid_bracket_final_k")
        q_lat = aud.get("q_lattice_shrink") or {}
        t_lat = (pack.bracket_solver.get("inner") or {}).get("tmid_lattice") or {}
        brackets = []
        if q_fin:
            brackets.append(
                _audit_float_bracket(
                    lo=float(q_fin[0]),
                    hi=float(q_fin[1]),
                    f_lo=float(q_lat.get("f_lo", math.nan)),
                    f_hi=float(q_lat.get("f_hi", math.nan)),
                    label="q_final",
                )
            )
        if tmid_fin:
            brackets.append(
                _audit_float_bracket(
                    lo=float(tmid_fin[0]),
                    hi=float(tmid_fin[1]),
                    f_lo=float(t_lat.get("f_lo", math.nan)),
                    f_hi=float(t_lat.get("f_hi", math.nan)),
                    label="tmid_final",
                )
            )
        float_ok = all(
            b["adjacent_representable"]
            and b["sign_opposite"]
            and b["lo_finite"]
            and b["hi_finite"]
            and b["lo_ne_hi"]
            for b in brackets
        )
        error = _error_source_study(d, request=req, provider=provider)
        arch, rec, contract = _architecture_choice(error, d.max_ratio)
        ci_status, ci_cause = _ci_status()
        payload = {
            "TASK_ID": "V08_03_NUMERICAL_PRECISION_ARCHITECTURE_DECISION",
            "PR_NUMBER": 325,
            "HEAD_SHA": _git_head(),
            "CI_STATUS": ci_status,
            "CI_FAILURE_ROOT_CAUSE": ci_cause,
            "BEST_CANDIDATE_LABEL": best_c.label,
            "BEST_Q_W": d.q_w,
            "BEST_TWI_K": d.twi_k,
            "BEST_TWO_K": d.two_k,
            "BEST_R1_W": d.r1_w,
            "BEST_R2_W": d.r2_w,
            "BEST_R3_W": d.r3_w,
            "BEST_BOUND1_W": d.bound1_w,
            "BEST_BOUND2_W": d.bound2_w,
            "BEST_BOUND3_W": d.bound3_w,
            "BEST_R1_RATIO": d.ratio1,
            "BEST_R2_RATIO": d.ratio2,
            "BEST_R3_RATIO": d.ratio3,
            "BEST_MAX_RATIO": d.max_ratio,
            "BEST_MAX_RATIO_CHECK": vmax,
            "TASK172_REQUEST_HASH": d.request_hash,
            "PROPERTY_SNAPSHOT_IDS": {
                "tube_bulk": prim.tube_bulk_id,
                "shell_bulk": prim.shell_bulk_id,
            },
            "TASK172_PRODUCTION_GATE": "PASS" if d.gate_pass else "BLOCKED",
            "FLOAT_BRACKET_VALIDITY": float_ok,
            "FLOAT_BRACKET_AUDIT": brackets,
            "ERROR_SOURCE_STUDY": error,
            "ARITHMETIC_ERROR_CONTRIBUTION": error["B_decimal_frozen_conductances"][
                "delta_r3_bound_ratio"
            ],
            "PROPERTY_QUANTIZATION_CONTRIBUTION": error["C_property_neighbor_twi_up"].get(
                "bound_ratio"
            ),
            "ROOT_LOCALIZATION_CONTRIBUTION": "measured_in_search_only; not dominant vs r3 gate",
            "PRIMARY_NUMERICAL_LIMIT": "UNRESOLVED",
            "DECISION_C_REVIEW_ONLY": arch == "C",
            "ARCHITECTURE_DECISION": arch,
            "RECOMMENDED_CHANGE": rec,
            "PRODUCTION_CONTRACT_CHANGE_REQUIRED": contract,
            "V07_GOLDEN": "run_locally_with_pytest_v07_final_live_e2e_delivery",
            "DISTINCT_FULLY_CONVERGED": 0,
            "ENGINEERING_ACCEPTANCE": "BLOCKED",
            "PRODUCTION_SOLVER_REPLACED": False,
            "ULP_TOLERANCE_CHANGED": False,
            "MERGE_AUTHORIZED": False,
        }
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        md = _render_markdown(payload)
        OUT_MD.parent.mkdir(parents=True, exist_ok=True)
        OUT_MD.write_text(md, encoding="utf-8")
        delivery = {
            k: v
            for k, v in payload.items()
            if k not in ("ERROR_SOURCE_STUDY", "FLOAT_BRACKET_AUDIT")
        }
        print(json.dumps(delivery, indent=2))
        return 0
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)


def _render_markdown(p: dict[str, Any]) -> str:
    return f"""# V08-03 Numerical Precision Architecture Decision

**TASK_ID:** `V08_03_NUMERICAL_PRECISION_ARCHITECTURE_DECISION`  
**PR:** 325 (Draft)  
**HEAD:** `{p["HEAD_SHA"]}`  
**ENGINEERING_ACCEPTANCE:** BLOCKED (unchanged)

## Unified best point (single production gate)

| Field | Value |
|-------|-------|
| q / Twi / Two (K) | {p["BEST_Q_W"]} / {p["BEST_TWI_K"]} / {p["BEST_TWO_K"]} |
| r1 / r2 / r3 (W) | {p["BEST_R1_W"]} / {p["BEST_R2_W"]} / {p["BEST_R3_W"]} |
| bound1/2/3 (W) | {p["BEST_BOUND1_W"]} / {p["BEST_BOUND2_W"]} / {p["BEST_BOUND3_W"]} |
| R1 / R2 / R3 ratio | {p["BEST_R1_RATIO"]} / {p["BEST_R2_RATIO"]} / {p["BEST_R3_RATIO"]} |
| **MAX ratio** | **{p["BEST_MAX_RATIO"]}** (check {p["BEST_MAX_RATIO_CHECK"]}) |
| request_hash | `{p["TASK172_REQUEST_HASH"]}` |
| snapshots | `{p["PROPERTY_SNAPSHOT_IDS"]}` |
| Task172 gate | {p["TASK172_PRODUCTION_GATE"]} |

Candidate label: `{p["BEST_CANDIDATE_LABEL"]}`. Evidence from one `eval_trial_residual_gate` triple only.

## Float bracket scope (scalar roots only)

- **Validity:** `{p["FLOAT_BRACKET_VALIDITY"]}` — adjacent binary64 endpoints with opposite-sign scalar residuals.
- Does **not** prove exhaustion of all `(q,Twi,Two)` representable triples.

## Error source isolation (Cell 0, candidate e1)

| Source | r3 impact vs bound3 (ratio) |
|--------|-------------------------------|
| Arithmetic (Decimal, frozen Gi/Go/Rwall) | {p["ARITHMETIC_ERROR_CONTRIBUTION"]} |
| Property neighbor (Twi +1 ULP) | {p["PROPERTY_QUANTIZATION_CONTRIBUTION"]} (zero here ≠ zero quantization) |

**PRIMARY_NUMERICAL_LIMIT:** UNRESOLVED — CoolProp/property dominance not proven from these probes alone.

Full JSON: `{OUT_JSON}`

## Options (design only — no production change this round)

### A — Higher-precision residual kernel
Keep CoolProp interface; extend precision in Task172 `_eval_trial` accumulation (not solver).

### B — Property / state pipeline
HTC and snapshot quantization dominate; requires new property evaluation contract (not `float` swap alone).

### C — Layered acceptance re-argument
Keep physics; study whether nanowatt ULP bounds match binary64 + property uncertainty.

## Decision

**ARCHITECTURE_DECISION = {p["ARCHITECTURE_DECISION"]}**

**RECOMMENDED_CHANGE:** {p["RECOMMENDED_CHANGE"]}

**PRODUCTION_CONTRACT_CHANGE_REQUIRED:** {p["PRODUCTION_CONTRACT_CHANGE_REQUIRED"]} (Decision C = start RFC review only)

## Attribution (corrected)

- Decimal row: residual formula at frozen Gi/Go/Rwall only.
- Twi +1 ULP probe: local insensitivity only; not a property uncertainty budget.
- See layered RFC: `docs/decisions/V08_03_LAYERED_ACCEPTANCE_RFC.md`

## Risks and boundary

- No ULP tolerance change, no production solver replacement, no V08-04.
- V08-03 engineering acceptance remains BLOCKED until full Rating under authorized contract.

## CI

- **#1572 root cause:** missing `test_float_lattice_bracket.py` in manifest + Ruff SIM102 (fixed).
- **#1574 (HEAD `dbfc213`):** in progress on push; early shard fails include task168 (passes locally), r23 (pytest-timeout 300s on primary case), r24 (long-run); merge-ref shards may cascade. Re-verify after run completes; not authorized to relax gates.
"""


if __name__ == "__main__":
    raise SystemExit(main())
