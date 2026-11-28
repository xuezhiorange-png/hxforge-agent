"""Dump pre-TRF initial state and physical vs penalty Jacobian (e1 N1)."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize._numdiff import approx_derivative

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
    _effective_h_min_j_kg,
    effective_admitted_h_max_j_kg,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    _enumerate_for_fixture,
    _find_bundle,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    _evaluate_cell_physics_residuals,
    _heat_residual_scale_w,
    _per_cell_thermodynamic_q_cap_w,
    _sequential_q_u_initial_guess,
    _supports_for_mesh,
    _wall_order_valid,
    audit_axial_feasibility,
    build_axial_enthalpies_from_q,
    joint_bvp_dof_audit_summary,
)
from prototypes.v08_thermal_rating.run_joint_bvp_proof import _build_rating_request
from prototypes.v08_thermal_rating.true_three_equation_cell_coupling import (
    build_closure_primitives,
    build_task172_request_for_q,
    evaluate_three_equation_residuals,
)

CANDIDATE = "e1baa795-9cf5-5718-8fa8-0688d2102c5c"
OUT = Path("/opt/cursor/artifacts/v08_03_joint_bvp_pre_trf_diagnostics.json")


def _setup() -> tuple[Any, Any, Any, Any, Any]:
    provider = CoolPropProvider()
    normalized, _, enum, task168_digest = _enumerate_for_fixture()
    _find_bundle(enum, CANDIDATE)
    ctx_rating = _build_rating_request(CANDIDATE, enum, task168_digest)
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
    return provider, ctx, tok, ct, ctx_rating


def main() -> int:
    from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
        _state_at_inlet,
        _state_from_enthalpy,
        effective_shell_cold_inlet_enthalpy_j_kg,
        effective_shell_mass_flow_kg_s,
        effective_tube_inlet_temperature_k,
        effective_tube_mass_flow_kg_s,
    )

    provider, ctx, tok, ct, _ = _setup()
    try:
        supports = _supports_for_mesh(ctx, 1)
        tube_mdot = float(effective_tube_mass_flow_kg_s())
        shell_mdot = float(effective_shell_mass_flow_kg_s())
        h_t0 = float(
            _state_at_inlet(
                provider, effective_tube_inlet_temperature_k(), side="TUBE"
            ).native.enthalpy_j_kg
        )
        h_sN = float(effective_shell_cold_inlet_enthalpy_j_kg())
        h_min = float(_effective_h_min_j_kg())
        h_max = float(effective_admitted_h_max_j_kg(provider))
        q_uniform = max(tube_mdot * 50.0, 5000.0) / len(supports)
        x0, lo, hi, q_part = _sequential_q_u_initial_guess(
            provider=provider,
            supports=supports,
            h_t0=h_t0,
            h_sN=h_sN,
            tube_mdot=tube_mdot,
            shell_mdot=shell_mdot,
            q_uniform=q_uniform,
            shell_authority=ctx.shell_authority,
        )
        n = len(supports)
        feas_report = audit_axial_feasibility(
            q_part,
            provider=provider,
            h_t_inlet_j_kg=h_t0,
            h_s_cold_inlet_j_kg=h_sN,
            tube_mass_flow_kg_s=tube_mdot,
            shell_mass_flow_kg_s=shell_mdot,
        )
        h_t, h_s = build_axial_enthalpies_from_q(
            q_part,
            h_t_inlet_j_kg=h_t0,
            h_s_cold_inlet_j_kg=h_sN,
            tube_mass_flow_kg_s=tube_mdot,
            shell_mass_flow_kg_s=shell_mdot,
        )
        scale = _heat_residual_scale_w(q_part, tube_mdot=tube_mdot, enthalpy_span_j_kg=h_t0 - h_sN)
        cells: list[dict[str, Any]] = []
        plateau_cells = 0
        for i, support in enumerate(supports):
            q_i, u1, u2 = (float(x0[3 * i]), float(x0[3 * i + 1]), float(x0[3 * i + 2]))
            q_cap = _per_cell_thermodynamic_q_cap_w(
                h_t_face_j_kg=float(h_t[i]),
                h_s_face_j_kg=float(h_s[i]),
                h_s_right_j_kg=float(h_s[i + 1]),
                tube_mdot=tube_mdot,
                shell_mdot=shell_mdot,
                h_max=h_max,
            )
            row: dict[str, Any] = {
                "index": i,
                "q_initial": q_i,
                "u1_initial": u1,
                "u2_initial": u2,
                "q_cap_static_w": q_cap,
                "q_cap_dynamic_w": float(feas_report.per_cell_q_hi[i]),
            }
            physical_evaluated = False
            penalty_used = False
            try:
                tube_up = _state_from_enthalpy(provider, h_t[i], side="TUBE")
                shell_left = _state_from_enthalpy(
                    provider, h_s[i], shell_search_state=True, side="SHELL"
                )
                request, _, _ = build_task172_request_for_q(
                    q_i,
                    support=support,
                    tube_upstream=tube_up,
                    shell_physical_left=shell_left,
                    provider=provider,
                    shell_authority=ctx.shell_authority,
                )
                prim = build_closure_primitives(request, provider)
                g_i = float(prim.tube_h_base * support.inside_area_m2)
                g_o = float(prim.shell_h_base * support.outside_area_m2)
                tube_h = float(tube_up.native.enthalpy_j_kg)
                shell_h = float(shell_left.native.enthalpy_j_kg)
                row.update(
                    {
                        "tube_bulk_temperature_k": float(request.tube_bulk_state.temperature_k),
                        "shell_bulk_temperature_k": float(request.shell_bulk_state.temperature_k),
                        "tube_face_enthalpies_j_kg": [float(h_t[i]), float(h_t[i + 1])],
                        "shell_face_enthalpies_j_kg": [float(h_s[i]), float(h_s[i + 1])],
                        "Gi_w_k": g_i,
                        "Go_w_k": g_o,
                        "Rwall_k_w": float(prim.wall_resistance_k_w),
                        "r1_1_over_Gi_k_w": 1.0 / g_i,
                        "r2_Rwall_k_w": float(prim.wall_resistance_k_w),
                        "r3_1_over_Go_k_w": 1.0 / g_o,
                        "property_domain_valid": True,
                        "enthalpy_domain_valid": h_min <= tube_h <= h_max
                        and h_min <= shell_h <= h_max,
                    }
                )
                from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
                    _enthalpy_coupled_wall_temperatures_from_fraction,
                )

                twi_guess, two_guess = _enthalpy_coupled_wall_temperatures_from_fraction(
                    u1,
                    u2,
                    tube_bulk_k=float(request.tube_bulk_state.temperature_k),
                    shell_bulk_k=float(request.shell_bulk_state.temperature_k),
                ) or (math.nan, math.nan)
                wall = _evaluate_cell_physics_residuals(
                    index=i,
                    q=q_i,
                    u1=u1,
                    u2=u2,
                    support=support,
                    h_t=h_t,
                    h_s=h_s,
                    provider=provider,
                    shell_authority=ctx.shell_authority,
                    heat_scale=scale,
                    h_min=h_min,
                    h_max=h_max,
                    tube_mdot=tube_mdot,
                    shell_mdot=shell_mdot,
                )
                res_vec, physical_evaluated, penalty_used, enth_ok, prop_ok = wall
                gate = evaluate_three_equation_residuals(
                    q_i,
                    float(twi_guess),
                    float(two_guess),
                    request=request,
                    provider=provider,
                    primitives=prim,
                )
                row.update(
                    {
                        "wall_order_valid": (
                            _wall_order_valid(
                                float(twi_guess),
                                float(two_guess),
                                float(request.tube_bulk_state.temperature_k),
                                float(request.shell_bulk_state.temperature_k),
                            )
                            if math.isfinite(twi_guess)
                            else False
                        ),
                        "physical_residual_evaluated": physical_evaluated,
                        "penalty_residual_used": penalty_used,
                        "enthalpy_domain_valid": enth_ok,
                        "property_domain_valid": prop_ok,
                        "task172_r1_w": gate["residuals_w"][0],
                        "task172_r2_w": gate["residuals_w"][1],
                        "task172_r3_w": gate["residuals_w"][2],
                        "initial_residual_triplet": res_vec.tolist(),
                    }
                )
                if penalty_used:
                    plateau_cells += 1
            except Exception as exc:
                row["property_domain_valid"] = False
                row["domain_error"] = type(exc).__name__
                row["penalty_residual_used"] = True
                plateau_cells += 1
            cells.append(row)

        def f_combined(v: np.ndarray, physical_only: bool) -> np.ndarray:
            out: list[float] = []
            qtw = v.reshape(n, 3)
            feas = audit_axial_feasibility(
                qtw[:, 0],
                provider=provider,
                h_t_inlet_j_kg=h_t0,
                h_s_cold_inlet_j_kg=h_sN,
                tube_mass_flow_kg_s=tube_mdot,
                shell_mass_flow_kg_s=shell_mdot,
            )
            if not feas.feasible:
                if physical_only:
                    return np.full(3 * n, math.nan, dtype=float)
                return np.full(3 * n, 1.0, dtype=float)
            h_t_l, h_s_l = build_axial_enthalpies_from_q(
                qtw[:, 0],
                h_t_inlet_j_kg=h_t0,
                h_s_cold_inlet_j_kg=h_sN,
                tube_mass_flow_kg_s=tube_mdot,
                shell_mass_flow_kg_s=shell_mdot,
            )
            for i, support in enumerate(supports):
                q, u1, u2 = map(float, qtw[i])
                res, phys, penal, _, _ = _evaluate_cell_physics_residuals(
                    index=i,
                    q=q,
                    u1=u1,
                    u2=u2,
                    support=support,
                    h_t=h_t_l,
                    h_s=h_s_l,
                    provider=provider,
                    shell_authority=ctx.shell_authority,
                    heat_scale=scale,
                    h_min=h_min,
                    h_max=h_max,
                    tube_mdot=tube_mdot,
                    shell_mdot=shell_mdot,
                )
                if physical_only and (penal or not phys):
                    out.extend([math.nan, math.nan, math.nan])
                else:
                    out.extend(res.tolist())
            return np.asarray(out, dtype=float)

        f_penalty = f_combined(x0, physical_only=False)
        f_phys = f_combined(x0, physical_only=True)
        jac_pen = approx_derivative(
            lambda v: f_combined(v, physical_only=False),
            x0,
            method="2-point",
            rel_step=np.sqrt(np.finfo(float).eps),
        )
        jac_phys = approx_derivative(
            lambda v: f_combined(v, physical_only=True),
            x0,
            method="2-point",
            rel_step=np.sqrt(np.finfo(float).eps),
        )
        jac_phys = np.nan_to_num(jac_phys, nan=0.0)

        perturb_audit: list[dict[str, Any]] = []
        step = np.sqrt(np.finfo(float).eps)
        for i in range(n):
            for j, name in enumerate(("q", "u1", "u2")):
                delta = np.zeros_like(x0)
                delta[3 * i + j] = step * max(abs(x0[3 * i + j]), 1.0)
                fp = f_combined(x0 + delta, physical_only=False)
                f0 = f_combined(x0, physical_only=False)
                fphy = f_combined(x0 + delta, physical_only=True)
                perturb_audit.append(
                    {
                        "cell": i,
                        "variable": name,
                        "penalty_delta_norm": float(np.linalg.norm(fp - f0)),
                        "physical_finite": bool(np.all(np.isfinite(fphy))),
                        "penalty_plateau": bool(np.linalg.norm(fp - f0) < 1.0e-9),
                    }
                )

        payload = {
            "TASK_ID": "V08_03_JOINT_BVP_FEASIBLE_DOMAIN_RECOVERY",
            "candidate_id": CANDIDATE,
            "bvp_dof_audit": joint_bvp_dof_audit_summary(),
            "initial_axial_feasible": feas_report.feasible,
            "initial_axial_violation_j_kg": feas_report.violation_j_kg,
            "cells": cells,
            "initial_residual_penalty_norm": float(np.linalg.norm(f_penalty)),
            "initial_residual_physical_norm": float(np.linalg.norm(f_phys[np.isfinite(f_phys)])),
            "jacobian_penalty_shape": list(jac_pen.shape),
            "penalty_jacobian_rank": int(np.linalg.matrix_rank(jac_pen)),
            "penalty_jacobian_condition_number": float(np.linalg.cond(jac_pen)),
            "physical_jacobian_shape": list(jac_phys.shape),
            "physical_jacobian_rank": int(np.linalg.matrix_rank(jac_phys)),
            "physical_jacobian_condition_number": float(np.linalg.cond(jac_phys))
            if jac_phys.size
            else math.inf,
            "domain_plateau_cells": plateau_cells,
            "perturbation_audit": perturb_audit,
            "x0": x0.tolist(),
            "heat_scale_w": scale,
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(OUT)
        return 0
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)


if __name__ == "__main__":
    raise SystemExit(main())
