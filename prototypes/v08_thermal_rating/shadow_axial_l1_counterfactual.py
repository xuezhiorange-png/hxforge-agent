"""L1 counterfactual N1 axial experiment — prototypes only; EXPERIMENTAL_NOT_APPROVED."""
# ruff: noqa: E501

from __future__ import annotations

import math
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task172_local_runtime.service import eval_trial_residual_gate
from prototypes.v08_thermal_rating.cell0_bracketed_root_ulp import production_trial_gate
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    JointBVPCellRecord,
    JointBVPOutcome,
    _state_from_h,
    _wall_order_valid,
    build_task172_request_for_q,
    solve_joint_boundary_value_mesh,
)

EXPERIMENTAL_TAG = "EXPERIMENTAL_NOT_APPROVED"
UNVERIFIED_CONTINUE = "UNVERIFIED_CONTINUE_FOR_DIAGNOSTIC"


def _cell_shadow_row(
    rec: JointBVPCellRecord,
    *,
    support: Any,
    provider: Any,
    shell_authority: Any,
) -> dict[str, Any]:
    tube_face_h = rec.h_t_left_j_kg
    shell_face_h = rec.h_s_left_j_kg
    property_domain = rec.domain_exit or "IN_DOMAIN"
    gate_detail: dict[str, Any] | None = None
    r1_ratio = r2_ratio = r3_ratio = math.nan
    physical_solution = rec.domain_exit is None and math.isfinite(rec.q_w)
    shadow_status: str = EXPERIMENTAL_TAG
    try:
        tube_up = _state_from_h(provider, float(rec.h_t_left_j_kg), side="TUBE")
        shell_left = _state_from_h(provider, float(rec.h_s_left_j_kg), side="SHELL")
        request, _, _ = build_task172_request_for_q(
            rec.q_w,
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
    except Exception as exc:  # noqa: BLE001 — diagnostic export only
        property_domain = type(exc).__name__
        physical_solution = False
        shadow_status = "BLOCKED_REQUEST_BUILD"
        return {
            "cell_id": rec.cell_id,
            "index": rec.index,
            "q_w": rec.q_w,
            "Twi_k": rec.twi_k,
            "Two_k": rec.two_k,
            "r1_w": rec.task172_r1_w,
            "r2_w": rec.task172_r2_w,
            "r3_w": rec.task172_r3_w,
            "r1_ratio": r1_ratio,
            "r2_ratio": r2_ratio,
            "r3_ratio": r3_ratio,
            "tube_face_h": tube_face_h,
            "shell_face_h": shell_face_h,
            "tube_bulk_T": rec.t_tube_bulk_k,
            "shell_bulk_T": rec.t_shell_bulk_k,
            "property_domain": property_domain,
            "physical_solution_available": physical_solution,
            "shadow_status": shadow_status,
            "task172_gate_pass": rec.task172_gate_pass,
        }

    gate = eval_trial_residual_gate(request, provider, rec.q_w, rec.twi_k, rec.two_k)
    det = production_trial_gate(rec.q_w, rec.twi_k, rec.two_k, request=request, provider=provider)
    if det:
        r1_ratio, r2_ratio, r3_ratio = det.ratio1, det.ratio2, det.ratio3
    if rec.task172_gate_pass:
        shadow_status = "ORIGINAL_L1_PASS"
    elif rec.domain_exit:
        shadow_status = f"BLOCKED_{rec.domain_exit}"
    elif physical_solution and not rec.task172_gate_pass:
        shadow_status = UNVERIFIED_CONTINUE
    return {
        "cell_id": rec.cell_id,
        "index": rec.index,
        "q_w": rec.q_w,
        "Twi_k": rec.twi_k,
        "Two_k": rec.two_k,
        "r1_w": rec.task172_r1_w,
        "r2_w": rec.task172_r2_w,
        "r3_w": rec.task172_r3_w,
        "r1_ratio": r1_ratio,
        "r2_ratio": r2_ratio,
        "r3_ratio": r3_ratio,
        "tube_face_h": tube_face_h,
        "shell_face_h": shell_face_h,
        "tube_bulk_T": rec.t_tube_bulk_k,
        "shell_bulk_T": rec.t_shell_bulk_k,
        "property_domain": property_domain,
        "physical_solution_available": physical_solution,
        "shadow_status": shadow_status,
        "task172_gate_pass": rec.task172_gate_pass,
        "passes_production_c_ulp": bool(gate and gate.get("passes_original_residual_gate")),
        "request_hash": rec.task172_request_hash,
        "gate_residuals_w": (gate or {}).get("residuals_w"),
    }


def assess_shadow_n1_counterfactual(
    outcome: JointBVPOutcome,
    *,
    supports: list[Any],
    provider: Any,
    shell_authority: Any,
    l1_stop_would_block: bool,
) -> dict[str, Any]:
    """Path B: L1 gate not used as trial stop; report independent blockers."""
    cells = outcome.cells
    blockers: list[str] = []
    domain_exit_cells = any(c.domain_exit for c in cells)
    if domain_exit_cells:
        blockers.append("PROPERTY_DOMAIN_EXIT")
    if not outcome.optimizer_success:
        blockers.append("OPTIMIZER_UNDERCONVERGED")
    if outcome.energy_balance_residual_w > 1.0:
        blockers.append(f"ENERGY_RESIDUAL_W={outcome.energy_balance_residual_w}")
    if not outcome.terminal_pass:
        blockers.append(
            f"TERMINAL_BOUNDARY_RESIDUAL_K={outcome.terminal_residual_k}"
        )
    if l1_stop_would_block and not outcome.all_task172_gates_pass:
        blockers.append("L1_C_ULP_WOULD_STOP_IN_PRODUCTION")
    if not all(c.q_w > 0.0 for c in cells):
        blockers.append("NON_POSITIVE_Q")
    wall_bad = [
        c.index
        for c in cells
        if not math.isnan(c.t_tube_bulk_k)
        and not _wall_order_valid(c.twi_k, c.two_k, c.t_tube_bulk_k, c.t_shell_bulk_k)
    ]
    if wall_bad:
        blockers.append(f"WALL_ORDER_VIOLATION_CELLS={wall_bad}")
    if not all(c.task173_root_validated for c in cells):
        blockers.append("TASK173_F_Q_ROOT_NOT_VALIDATED")
    shadow_physical = (
        not domain_exit_cells
        and outcome.energy_balance_residual_w <= 1.0
        and all(c.q_w > 0.0 for c in cells)
        and not wall_bad
        and outcome.optimizer_success
    )
    rows = [
        _cell_shadow_row(
            c,
            support=supports[c.index],
            provider=provider,
            shell_authority=shell_authority,
        )
        for c in cells
    ]
    return {
        "approval_status": EXPERIMENTAL_TAG,
        "l1_gate_used_as_stop": False,
        "l1_would_block_production": l1_stop_would_block,
        "shadow_physical_profile_without_l1_stop": shadow_physical,
        "independent_remaining_blockers": blockers,
        "aggregate": {
            "Q_SUM_W": outcome.total_q_w,
            "TUBE_ENTHALPY_LOSS_W": outcome.tube_enthalpy_loss_w,
            "SHELL_ENTHALPY_GAIN_W": outcome.shell_enthalpy_gain_w,
            "ENERGY_RESIDUAL_W": outcome.energy_balance_residual_w,
            "TUBE_OUTLET_T_K": outcome.tube_outlet_temperature_k,
            "SHELL_OUTLET_T_K": outcome.shell_outlet_temperature_k,
            "TERMINAL_BOUNDARY_RESIDUAL_K": outcome.terminal_residual_k,
            "TERMINAL_BOUNDARY_RESIDUAL_J_KG": outcome.terminal_residual_j_kg,
        },
        "cells": rows,
        "production_joint_bvp_status": outcome.status,
        "production_physical_acceptance": outcome.physical_acceptance,
        "all_task172_gates_pass": outcome.all_task172_gates_pass,
    }


def run_shadow_n1_mesh(
    *,
    subdivisions: int,
    provider: Any,
    shell_authority: Any,
    candidate_ctx: Any,
) -> tuple[JointBVPOutcome, dict[str, Any]]:
    from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import _supports_for_mesh

    supports = _supports_for_mesh(candidate_ctx, subdivisions)
    outcome = solve_joint_boundary_value_mesh(
        subdivisions=subdivisions,
        provider=provider,
        shell_authority=shell_authority,
        candidate_ctx=candidate_ctx,
    )
    l1_would_block = not outcome.all_task172_gates_pass
    shadow = assess_shadow_n1_counterfactual(
        outcome,
        supports=supports,
        provider=provider,
        shell_authority=shell_authority,
        l1_stop_would_block=l1_would_block,
    )
    return outcome, shadow


def decide_gate_impact(
    *,
    candidate_results: list[dict[str, Any]],
) -> tuple[Literal["A", "B", "C"], bool | str]:
    """Return DECISION and L1_ONLY_CHANGE_SUFFICIENT."""
    n1_ok: list[bool] = []
    l1_only: list[bool] = []
    for cr in candidate_results:
        sh = cr.get("shadow_n1", {})
        ok = bool(sh.get("shadow_physical_profile_without_l1_stop"))
        n1_ok.append(ok)
        blockers = set(sh.get("independent_remaining_blockers", []))
        l1_related = {
            "L1_C_ULP_WOULD_STOP_IN_PRODUCTION",
            "TASK173_F_Q_ROOT_NOT_VALIDATED",
        }
        non_l1 = blockers - l1_related
        l1_only.append(ok and len(non_l1) == 0 and bool(blockers & l1_related))
    energy_ok = [
        float(cr.get("shadow_n1", {}).get("aggregate", {}).get("ENERGY_RESIDUAL_W", math.inf))
        <= 1.0
        for cr in candidate_results
    ]
    any_unverified = any(
        any(
            cell.get("shadow_status") == UNVERIFIED_CONTINUE
            for cell in cr.get("shadow_n1", {}).get("cells", [])
        )
        for cr in candidate_results
    )
    if not any(n1_ok):
        if any(energy_ok) and any_unverified:
            return "A", False
        return "C", False
    if all(n1_ok):
        suff: bool | str = all(l1_only)
        return "B", suff
    return "A", False
