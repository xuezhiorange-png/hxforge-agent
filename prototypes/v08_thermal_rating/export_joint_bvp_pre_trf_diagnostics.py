"""Dump pre-TRF initial state and Jacobian conditioning for joint BVP (e1 N1)."""
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
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    _enumerate_for_fixture,
    _find_bundle,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    _heat_residual_scale_w,
    _per_cell_thermodynamic_q_cap_w,
    _resistance_network_q_u_seed,
    _sequential_q_u_initial_guess,
    _supports_for_mesh,
    build_axial_enthalpies_from_q,
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
        h_t, h_s = build_axial_enthalpies_from_q(
            q_part,
            h_t_inlet_j_kg=h_t0,
            h_s_cold_inlet_j_kg=h_sN,
            tube_mass_flow_kg_s=tube_mdot,
            shell_mass_flow_kg_s=shell_mdot,
        )
        cells: list[dict[str, Any]] = []
        for i, support in enumerate(supports):
            tube_up = _state_from_enthalpy(provider, h_t[i], side="TUBE")
            shell_left = _state_from_enthalpy(
                provider, h_s[i], shell_search_state=True, side="SHELL"
            )
            q_i, u1, u2 = (float(x0[3 * i]), float(x0[3 * i + 1]), float(x0[3 * i + 2]))
            q_cap = _per_cell_thermodynamic_q_cap_w(
                h_t_face_j_kg=float(h_t[i]),
                h_s_face_j_kg=float(h_s[i]),
                tube_mdot=tube_mdot,
                shell_mdot=shell_mdot,
            )
            row: dict[str, Any] = {
                "index": i,
                "q_initial_w": q_i,
                "u1": u1,
                "u2": u2,
                "q_cap_w": q_cap,
            }
            try:
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
                g_wall = 1.0 / float(prim.wall_resistance_k_w)
                row.update(
                    {
                        "T_tube_bulk_k": float(request.tube_bulk_state.temperature_k),
                        "T_shell_bulk_k": float(request.shell_bulk_state.temperature_k),
                        "G_inner_w_k": g_i,
                        "G_outer_w_k": g_o,
                        "G_wall_w_k": g_wall,
                        "R_inner_w": 1.0 / g_i,
                        "R_wall_w": float(prim.wall_resistance_k_w),
                        "R_outer_w": 1.0 / g_o,
                        "property_domain_valid": True,
                        "enthalpy_domain_valid": True,
                    }
                )
                seed = _resistance_network_q_u_seed(
                    q_cap_w=q_cap,
                    support=support,
                    tube_up=tube_up,
                    shell_physical_left=shell_left,
                    provider=provider,
                    shell_authority=ctx.shell_authority,
                )
                row["resistance_seed"] = seed
            except Exception as exc:
                row["property_domain_valid"] = False
                row["domain_error"] = type(exc).__name__
            cells.append(row)

        scale = _heat_residual_scale_w(q_part, tube_mdot=tube_mdot, enthalpy_span_j_kg=h_t0 - h_sN)

        from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
            _enthalpy_coupled_wall_temperatures_from_fraction,
            _LowSideDomainInfeasible,
            _Stage3Failure,
        )
        from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
            _domain_violation_triplet,
        )

        def f(v: np.ndarray) -> np.ndarray:
            out: list[float] = []
            qtw = v.reshape(n, 3)
            try:
                h_t_l, h_s_l = build_axial_enthalpies_from_q(
                    qtw[:, 0],
                    h_t_inlet_j_kg=h_t0,
                    h_s_cold_inlet_j_kg=h_sN,
                    tube_mass_flow_kg_s=tube_mdot,
                    shell_mass_flow_kg_s=shell_mdot,
                )
            except ValueError:
                return np.full(3 * n, 1.0, dtype=float)
            for i, support in enumerate(supports):
                q, u1, u2 = map(float, qtw[i])
                try:
                    request, _, _ = build_task172_request_for_q(
                        q,
                        support=support,
                        tube_upstream=_state_from_enthalpy(provider, float(h_t_l[i]), side="TUBE"),
                        shell_physical_left=_state_from_enthalpy(
                            provider, float(h_s_l[i]), shell_search_state=True, side="SHELL"
                        ),
                        provider=provider,
                        shell_authority=ctx.shell_authority,
                    )
                except (_LowSideDomainInfeasible, _Stage3Failure):
                    out.extend(_domain_violation_triplet(1.0e3, scale=scale))
                    continue
                tube_k = float(request.tube_bulk_state.temperature_k)
                shell_k = float(request.shell_bulk_state.temperature_k)
                wall = _enthalpy_coupled_wall_temperatures_from_fraction(
                    u1, u2, tube_bulk_k=tube_k, shell_bulk_k=shell_k
                )
                if wall is None:
                    out.extend(_domain_violation_triplet(1.0, scale=scale))
                    continue
                twi, two = wall
                prim = build_closure_primitives(request, provider)
                gate = evaluate_three_equation_residuals(
                    q, twi, two, request=request, provider=provider, primitives=prim
                )
                out.extend(float(r) / scale for r in gate["residuals_w"])
            return np.asarray(out, dtype=float)

        f0 = f(x0)
        jac = approx_derivative(f, x0, method="2-point", rel_step=np.sqrt(np.finfo(float).eps))
        rank = int(np.linalg.matrix_rank(jac))
        cond = float(np.linalg.cond(jac)) if jac.size else math.inf

        payload = {
            "TASK_ID": "V08_03_JOINT_BVP_WALL_CLOSURE_RECOVERY",
            "candidate_id": CANDIDATE,
            "cells": cells,
            "initial_residual_f0": f0.tolist(),
            "initial_residual_norm": float(np.linalg.norm(f0)),
            "jacobian_shape": list(jac.shape),
            "jacobian_rank": rank,
            "jacobian_condition_number": cond,
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
