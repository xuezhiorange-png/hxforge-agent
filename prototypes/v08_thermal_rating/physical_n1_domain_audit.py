"""Per-cell property-domain audit for joint N1 trials (prototype diagnostics only)."""
# ruff: noqa: E501

from __future__ import annotations

import math
from typing import Any

import numpy as np

from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _effective_h_min_j_kg,
    _LowSideDomainInfeasible,
    _Stage3Failure,
    _state_at_inlet,
    effective_admitted_h_max_j_kg,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_mass_flow_kg_s,
    effective_tube_inlet_temperature_k,
    effective_tube_mass_flow_kg_s,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    JointBVPCellRecord,
    _duty_uniform_q_per_cell,
    _enthalpy_step_feasible,
    _state_from_h,
    _supports_for_mesh,
    _wall_order_valid,
    audit_axial_feasibility,
    build_axial_enthalpies_from_q,
    build_task172_request_for_q,
)


def _face_enthalpy_audit_row(
    *,
    candidate_id: str,
    geometry_hash: str,
    cell_index: int,
    label: str,
    q_w: float,
    q_vector: np.ndarray,
    h_t_in: float,
    h_s_in: float,
    tube_mdot: float,
    shell_mdot: float,
    provider: Any,
    shell_authority: Any,
    support: Any,
) -> dict[str, Any]:
    h_min = float(_effective_h_min_j_kg())
    h_max = float(effective_admitted_h_max_j_kg(provider))
    h_t, h_s = build_axial_enthalpies_from_q(
        q_vector,
        h_t_inlet_j_kg=h_t_in,
        h_s_cold_inlet_j_kg=h_s_in,
        tube_mass_flow_kg_s=tube_mdot,
        shell_mass_flow_kg_s=shell_mdot,
    )
    i = cell_index
    tube_h_left = float(h_t[i])
    tube_h_right = float(h_t[i + 1])
    shell_h_left = float(h_s[i])
    shell_h_right = float(h_s[i + 1])
    ok_step, step_viol = _enthalpy_step_feasible(
        q_w=q_w,
        h_t_left=tube_h_left,
        h_s_left=shell_h_left,
        h_s_right=shell_h_right,
        tube_mdot=tube_mdot,
        shell_mdot=shell_mdot,
        h_min=h_min,
        h_max=h_max,
    )
    property_domain_status = "IN_DOMAIN"
    first_invalid_predicate = ""
    first_exception_code = ""
    tube_bulk_t = shell_bulk_t = twi = two = math.nan
    r1 = r2 = r3 = math.nan
    wall_order = "UNEVALUATED"
    rebuild_exc = ""
    if not ok_step:
        property_domain_status = "ENTHALPY_STEP_INFEASIBLE"
        if tube_h_right < h_min:
            first_invalid_predicate = f"tube_h_right<{h_min}"
        elif tube_h_right > h_max:
            first_invalid_predicate = f"tube_h_right>{h_max}"
        elif shell_h_left - q_w / shell_mdot < h_min:
            first_invalid_predicate = "shell_next_h<h_min"
        elif shell_h_left - q_w / shell_mdot > h_max:
            first_invalid_predicate = "shell_next_h>h_max"
        else:
            first_invalid_predicate = f"step_violation_j_kg={step_viol}"
    try:
        tube_up = _state_from_h(provider, tube_h_left, side="TUBE")
        shell_left = _state_from_h(provider, shell_h_left, side="SHELL")
        request, _, _ = build_task172_request_for_q(
            q_w,
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
        tube_bulk_t = float(request.tube_bulk_state.temperature_k)
        shell_bulk_t = float(request.shell_bulk_state.temperature_k)
        twi = float(getattr(request, "wall_temperature_inner_k", math.nan))
        two = float(getattr(request, "wall_temperature_outer_k", math.nan))
        if ok_step:
            wall_order = (
                "OK"
                if _wall_order_valid(twi, two, tube_bulk_t, shell_bulk_t)
                else "WALL_ORDER_FAIL"
            )
    except _LowSideDomainInfeasible:
        first_exception_code = "_LowSideDomainInfeasible"
        property_domain_status = "COOLPROP_LOW_SIDE_INFEASIBLE"
        if not first_invalid_predicate:
            first_invalid_predicate = "state_from_h_or_task172_request"
    except _Stage3Failure as exc:
        first_exception_code = exc.code if hasattr(exc, "code") else type(exc).__name__
        property_domain_status = "STAGE3_FAILURE"
        if not first_invalid_predicate:
            first_invalid_predicate = str(first_exception_code)
    except Exception as exc:  # noqa: BLE001
        first_exception_code = type(exc).__name__
        property_domain_status = "REQUEST_BUILD_FAILED"
        rebuild_exc = str(exc)[:200]
    temperature_approach = tube_bulk_t - shell_bulk_t if math.isfinite(tube_bulk_t) else math.nan
    return {
        "audit_label": label,
        "candidate_id": candidate_id,
        "geometry_projection_hash": geometry_hash,
        "cell_index": cell_index,
        "q_trial_w": q_w,
        "tube_h_left": tube_h_left,
        "tube_h_right": tube_h_right,
        "shell_h_left": shell_h_left,
        "shell_h_right": shell_h_right,
        "tube_bulk_T": tube_bulk_t,
        "shell_bulk_T": shell_bulk_t,
        "Twi": twi,
        "Two": two,
        "admitted_h_min": h_min,
        "admitted_h_max": h_max,
        "property_pressure_pa": 101325.0,
        "property_domain_status": property_domain_status,
        "temperature_approach": temperature_approach,
        "wall_order_status": wall_order,
        "r1_w": r1,
        "r2_w": r2,
        "r3_w": r3,
        "first_invalid_predicate": first_invalid_predicate,
        "first_exception_code": first_exception_code,
        "rebuild_error": rebuild_exc,
    }


def audit_n1_domain_timeline(
    *,
    candidate_id: str,
    geometry_hash: str,
    candidate_ctx: Any,
    provider: Any,
    shell_authority: Any,
    q_final: np.ndarray | None = None,
    cells: list[JointBVPCellRecord] | None = None,
) -> dict[str, Any]:
    subdivisions = 1
    supports = _supports_for_mesh(candidate_ctx, subdivisions)
    n = len(supports)
    tube_mdot = float(effective_tube_mass_flow_kg_s())
    shell_mdot = float(effective_shell_mass_flow_kg_s())
    h_t0 = float(
        _state_at_inlet(
            provider, effective_tube_inlet_temperature_k(), side="TUBE"
        ).native.enthalpy_j_kg
    )
    h_sN = float(effective_shell_cold_inlet_enthalpy_j_kg())
    q_uniform = _duty_uniform_q_per_cell(
        provider=provider, n_cells=n, h_t_in=h_t0, tube_mdot=tube_mdot
    )
    q_init = np.full(n, q_uniform, dtype=float)
    init_report = audit_axial_feasibility(
        q_init,
        provider=provider,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=tube_mdot,
        shell_mass_flow_kg_s=shell_mdot,
    )
    initial_rows = [
        _face_enthalpy_audit_row(
            candidate_id=candidate_id,
            geometry_hash=geometry_hash,
            cell_index=i,
            label="INITIAL_UNIFORM_Q",
            q_w=float(q_init[i]),
            q_vector=q_init,
            h_t_in=h_t0,
            h_s_in=h_sN,
            tube_mdot=tube_mdot,
            shell_mdot=shell_mdot,
            provider=provider,
            shell_authority=shell_authority,
            support=supports[i],
        )
        for i in range(n)
    ]
    first_init_bad = next(
        (r for r in initial_rows if r["property_domain_status"] != "IN_DOMAIN"), None
    )
    final_rows: list[dict[str, Any]] = []
    first_final_bad = None
    if q_final is not None:
        q_f = np.asarray(q_final, dtype=float)
        for i in range(n):
            row = _face_enthalpy_audit_row(
                candidate_id=candidate_id,
                geometry_hash=geometry_hash,
                cell_index=i,
                label="OPTIMIZER_FINAL_Q",
                q_w=float(q_f[i]),
                q_vector=q_f,
                h_t_in=h_t0,
                h_s_in=h_sN,
                tube_mdot=tube_mdot,
                shell_mdot=shell_mdot,
                provider=provider,
                shell_authority=shell_authority,
                support=supports[i],
            )
            if cells and i < len(cells):
                c = cells[i]
                row["r1_w"] = c.task172_r1_w
                row["r2_w"] = c.task172_r2_w
                row["r3_w"] = c.task172_r3_w
                row["domain_exit_from_solver"] = c.domain_exit
            final_rows.append(row)
        first_final_bad = next(
            (r for r in final_rows if r["property_domain_status"] != "IN_DOMAIN"),
            None,
        )
    return {
        "q_uniform_initial_w": q_uniform,
        "initial_axial_feasible": init_report.feasible,
        "initial_violation_j_kg": init_report.violation_j_kg,
        "initial_domain_blocked_before_iterate": first_init_bad is not None,
        "first_domain_exit_initial": first_init_bad,
        "first_domain_exit_final": first_final_bad,
        "initial_cells": initial_rows,
        "final_cells": final_rows,
    }
