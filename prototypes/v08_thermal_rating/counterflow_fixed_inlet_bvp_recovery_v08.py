"""Fixed dual-inlet counterflow BVP recovery for V08_03_COUNTERFLOW_FIXED_INLET_BVP_RECOVERY."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

import numpy as np

from hexagent.exchangers.shell_tube.task172_local_runtime.service import eval_trial_residual_gate
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    effective_admitted_h_max_j_kg,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    ENERGY_ACCEPTANCE_FLOOR_W,
    CandidateRatingBindings,
    PropertyProvider,
    _run_with_rating_context,
    solve_isolated_outer_boundary,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    JointBVPOutcome,
    build_axial_enthalpies_from_q,
    solve_joint_boundary_value_mesh,
)


@dataclass(frozen=True)
class BvpCellGateRow:
    cell_index: int
    q_w: float
    twi_k: float
    two_k: float
    r1_w: float
    r2_w: float
    r3_w: float
    r1_ratio: float
    r2_ratio: float
    r3_ratio: float
    task172_request_hash: str
    task172_gate_pass: bool


@dataclass(frozen=True)
class CounterflowBvpMeshResult:
    subdivisions: int
    outcome: JointBVPOutcome
    cell_gate_rows: tuple[BvpCellGateRow, ...]
    status: Literal["PASS", "BLOCKED"]
    original_task172_gate: Literal["PASS", "BLOCKED"]
    production_culp_all_validated: bool


@dataclass(frozen=True)
class ShootingBvpComparison:
    shooting_gate: str
    shooting_total_duty_w: str | None
    shooting_tube_outlet_k: str | None
    shooting_shell_outlet_k: str | None
    bvp_total_duty_w: float
    bvp_tube_outlet_k: float
    bvp_shell_outlet_k: float
    duty_delta_w: float | None
    tube_outlet_delta_k: float | None
    shell_outlet_delta_k: float | None


def build_n4_q_seed_from_n2_shooting_intervals(
    *,
    candidate_ctx: Any,
    n2_interval_duty_w: tuple[Decimal, ...],
    n4_subdivisions: int,
) -> np.ndarray:
    """Per-cell q uniform within each interval from N2 shooting interval duties."""
    n_intervals = int(candidate_ctx.interval_count)
    if len(n2_interval_duty_w) != n_intervals:
        raise ValueError(
            f"interval duty count {len(n2_interval_duty_w)} != ctx.interval_count {n_intervals}"
        )
    n_cells = n_intervals * n4_subdivisions
    q = np.zeros(n_cells, dtype=float)
    for interval_index, duty in enumerate(n2_interval_duty_w):
        per_cell = float(duty) / float(n4_subdivisions)
        base = interval_index * n4_subdivisions
        for sub in range(n4_subdivisions):
            q[base + sub] = per_cell
    return q


def _gate_ratios(gate: dict[str, Any] | None) -> tuple[float, float, float]:
    if not gate:
        return (math.inf, math.inf, math.inf)
    res = gate.get("residuals_w") or (math.nan, math.nan, math.nan)
    bounds = gate.get("acceptance_bounds_w") or (0.0, 0.0, 0.0)
    out: list[float] = []
    for r, b in zip(res, bounds, strict=True):
        out.append(abs(float(r)) / float(b) if float(b) > 0 else math.inf)
    while len(out) < 3:
        out.append(math.inf)
    return (out[0], out[1], out[2])


def cell_gate_rows_from_outcome(
    outcome: JointBVPOutcome,
    *,
    provider: Any,
    supports: list[Any],
    shell_authority: Any,
) -> tuple[BvpCellGateRow, ...]:
    """Re-snapshot production eval_trial_residual_gate per solved cell."""
    from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
        _state_at_inlet,
        _state_from_h,
        build_task172_request_for_q,
        effective_shell_cold_inlet_enthalpy_j_kg,
        effective_shell_mass_flow_kg_s,
        effective_tube_inlet_temperature_k,
        effective_tube_mass_flow_kg_s,
    )

    h_t0 = float(
        _state_at_inlet(
            provider, effective_tube_inlet_temperature_k(), side="TUBE"
        ).native.enthalpy_j_kg
    )
    h_sN = float(effective_shell_cold_inlet_enthalpy_j_kg())
    h_t, h_s = build_axial_enthalpies_from_q(
        [c.q_w for c in outcome.cells],
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=float(effective_tube_mass_flow_kg_s()),
        shell_mass_flow_kg_s=float(effective_shell_mass_flow_kg_s()),
    )
    from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
        _LowSideDomainInfeasible,
        _Stage3Failure,
    )

    rows: list[BvpCellGateRow] = []
    for cell, support in zip(outcome.cells, supports, strict=True):
        r1, r2, r3 = cell.task172_r1_w, cell.task172_r2_w, cell.task172_r3_w
        gate: dict[str, Any] | None = None
        try:
            tube_up = _state_from_h(provider, float(h_t[cell.index]), side="TUBE")
            shell_left = _state_from_h(provider, float(h_s[cell.index]), side="SHELL")
            request, _, _ = build_task172_request_for_q(
                cell.q_w,
                support=support,
                tube_upstream=tube_up,
                shell_physical_left=shell_left,
                provider=provider,
                shell_authority=shell_authority,
            )
            gate = eval_trial_residual_gate(request, provider, cell.q_w, cell.twi_k, cell.two_k)
            if gate:
                res = gate.get("residuals_w")
                if res and len(res) >= 3:
                    r1, r2, r3 = float(res[0]), float(res[1]), float(res[2])
        except (_LowSideDomainInfeasible, _Stage3Failure):
            gate = None
        r1r, r2r, r3r = _gate_ratios(gate)
        if gate is None and not math.isnan(cell.max_task172_residual_ratio):
            fill = float(cell.max_task172_residual_ratio)
            r1r = r1r if not math.isinf(r1r) else fill
            r2r = r2r if not math.isinf(r2r) else fill
            r3r = r3r if not math.isinf(r3r) else fill
        rows.append(
            BvpCellGateRow(
                cell_index=cell.index,
                q_w=float(cell.q_w),
                twi_k=float(cell.twi_k),
                two_k=float(cell.two_k),
                r1_w=float(r1),
                r2_w=float(r2),
                r3_w=float(r3),
                r1_ratio=float(r1r),
                r2_ratio=float(r2r),
                r3_ratio=float(r3r),
                task172_request_hash=str(
                    cell.task172_request_hash or (gate or {}).get("request_hash", "")
                ),
                task172_gate_pass=bool(cell.task172_gate_pass),
            )
        )
    return tuple(rows)


def _fixed_inlet_boundary_ok(outcome: JointBVPOutcome, *, provider: Any) -> bool:
    if not outcome.cells:
        return False
    h_max = float(effective_admitted_h_max_j_kg(provider))
    for cell in outcome.cells:
        if not (cell.h_t_left_j_kg <= h_max and cell.h_s_left_j_kg <= h_max):
            return False
        if cell.h_t_right_j_kg > cell.h_t_left_j_kg + 1.0e-6:
            return False
        if cell.h_s_left_j_kg < cell.h_s_right_j_kg - 1.0e-6:
            return False
    return True


def classify_numerical_decision(
    n4: CounterflowBvpMeshResult,
    *,
    provider: Any,
) -> tuple[Literal["A", "B", "C"], str]:
    """A=original Task172 gates + energy/boundaries; B=physical closure without C-ULP; C=blocked."""
    outcome = n4.outcome
    energy_ok = outcome.energy_balance_residual_w <= max(float(ENERGY_ACCEPTANCE_FLOOR_W), 1.0)
    gates_ok = n4.original_task172_gate == "PASS"
    boundary_ok = _fixed_inlet_boundary_ok(outcome, provider=provider)
    culp_ok = n4.production_culp_all_validated
    if gates_ok and energy_ok and boundary_ok:
        if culp_ok:
            return "A", "BVP_N4_ORIGINAL_GATES_PASS_WITH_CULP"
        return "A", "BVP_N4_ORIGINAL_GATES_PASS"
    physical = (
        energy_ok
        and boundary_ok
        and outcome.energy_conserving_formulation
        and all(c.q_w > 0.0 for c in outcome.cells)
    )
    if physical and not culp_ok:
        return "B", "BVP_PHYSICAL_CLOSURE_ONLY"
    first_fail = _first_failed_cell_summary(n4.cell_gate_rows)
    return "C", first_fail or "BVP_N4_BLOCKED"


def _first_failed_cell_summary(rows: tuple[BvpCellGateRow, ...]) -> str | None:
    for row in rows:
        if not row.task172_gate_pass:
            mx = max(row.r1_ratio, row.r2_ratio, row.r3_ratio)
            eq = (
                "r1"
                if row.r1_ratio >= row.r2_ratio and row.r1_ratio >= row.r3_ratio
                else ("r2" if row.r2_ratio >= row.r3_ratio else "r3")
            )
            return f"cell={row.cell_index};equation={eq};max_ratio={mx:.6g}"
    return None


def _run_bvp_mesh(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int,
    q_seed_per_cell: np.ndarray | None = None,
) -> CounterflowBvpMeshResult:
    from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import _supports_for_mesh

    def body(context: Any, _btoken: object) -> CounterflowBvpMeshResult:
        outcome = solve_joint_boundary_value_mesh(
            subdivisions=subdivisions,
            provider=provider,
            shell_authority=context.shell_authority,
            candidate_ctx=context,
            q_seed_per_cell=q_seed_per_cell,
        )
        supports = _supports_for_mesh(context, subdivisions)
        rows = cell_gate_rows_from_outcome(
            outcome,
            provider=provider,
            supports=supports,
            shell_authority=context.shell_authority,
        )
        original = "PASS" if all(r.task172_gate_pass for r in rows) else "BLOCKED"
        culp = all(c.production_validated for c in outcome.cells)
        status: Literal["PASS", "BLOCKED"] = (
            "PASS" if original == "PASS" and outcome.energy_balance_residual_w <= 1.0 else "BLOCKED"
        )
        return CounterflowBvpMeshResult(
            subdivisions=subdivisions,
            outcome=outcome,
            cell_gate_rows=rows,
            status=status,
            original_task172_gate=original,
            production_culp_all_validated=culp,
        )

    return _run_with_rating_context(bindings, provider, subdivisions=subdivisions, body=body)


def run_counterflow_fixed_inlet_bvp_recovery(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
) -> dict[str, Any]:
    """N4-first with N2-interval q seed; optional N1/N2 if N4 original gates pass."""
    n2_shoot = solve_isolated_outer_boundary(bindings, provider, subdivisions=2)
    n2_run = n2_shoot.accepted_run
    if n2_run is None:
        raise RuntimeError("N2 shooting ACCEPTED run required for N4 q seed")
    interval_duty = n2_run.observables.interval_duty_w

    def _q_seed_body(ctx: Any, _btoken: object) -> np.ndarray:
        return build_n4_q_seed_from_n2_shooting_intervals(
            candidate_ctx=ctx,
            n2_interval_duty_w=interval_duty,
            n4_subdivisions=4,
        )

    q_seed = _run_with_rating_context(bindings, provider, subdivisions=4, body=_q_seed_body)
    n4 = _run_bvp_mesh(bindings, provider, subdivisions=4, q_seed_per_cell=q_seed)

    decision, decision_note = classify_numerical_decision(n4, provider=provider)

    n1_bvp: CounterflowBvpMeshResult | None = None
    n2_bvp: CounterflowBvpMeshResult | None = None
    if n4.original_task172_gate == "PASS":
        n1_bvp = _run_bvp_mesh(bindings, provider, subdivisions=1)
        n2_bvp = _run_bvp_mesh(bindings, provider, subdivisions=2)

    from prototypes.v08_thermal_rating.axial_rating_engine_v1 import isolated_mesh_acceptance_gate

    shooting: dict[str, ShootingBvpComparison] = {}
    shooting_gates: dict[str, str] = {
        "2": isolated_mesh_acceptance_gate(bindings, provider, n2_shoot),
    }

    def _compare_shooting(
        subdiv: int, bvp: CounterflowBvpMeshResult, iso: Any
    ) -> ShootingBvpComparison:
        gate = isolated_mesh_acceptance_gate(bindings, provider, iso)
        shooting_gates[str(subdiv)] = str(gate)
        obs = iso.accepted_run.observables if iso.accepted_run is not None else None
        duty_delta = None
        tube_d = shell_d = None
        if obs is not None:
            duty_delta = float(bvp.outcome.total_q_w) - float(obs.total_duty_w)
            tube_d = float(bvp.outcome.tube_outlet_temperature_k) - float(
                obs.tube_outlet_temperature_k
            )
            shell_d = float(bvp.outcome.shell_outlet_temperature_k) - float(
                obs.shell_outlet_temperature_k
            )
        return ShootingBvpComparison(
            shooting_gate=str(gate),
            shooting_total_duty_w=str(obs.total_duty_w) if obs else None,
            shooting_tube_outlet_k=str(obs.tube_outlet_temperature_k) if obs else None,
            shooting_shell_outlet_k=str(obs.shell_outlet_temperature_k) if obs else None,
            bvp_total_duty_w=float(bvp.outcome.total_q_w),
            bvp_tube_outlet_k=float(bvp.outcome.tube_outlet_temperature_k),
            bvp_shell_outlet_k=float(bvp.outcome.shell_outlet_temperature_k),
            duty_delta_w=duty_delta,
            tube_outlet_delta_k=tube_d,
            shell_outlet_delta_k=shell_d,
        )

    shooting["2"] = _compare_shooting(2, n2_bvp or n4, n2_shoot)
    n4_iso = solve_isolated_outer_boundary(bindings, provider, subdivisions=4)
    shooting["4"] = _compare_shooting(4, n4, n4_iso)
    if n1_bvp is not None:
        n1_iso = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
        shooting["1"] = _compare_shooting(1, n1_bvp, n1_iso)
    else:
        n1_iso = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
        shooting_gates["1"] = isolated_mesh_acceptance_gate(bindings, provider, n1_iso)
        shooting["1"] = ShootingBvpComparison(
            shooting_gate="not_run",
            shooting_total_duty_w=None,
            shooting_tube_outlet_k=None,
            shooting_shell_outlet_k=None,
            bvp_total_duty_w=math.nan,
            bvp_tube_outlet_k=math.nan,
            bvp_shell_outlet_k=math.nan,
            duty_delta_w=None,
            tube_outlet_delta_k=None,
            shell_outlet_delta_k=None,
        )

    max_r1 = max((r.r1_ratio for r in n4.cell_gate_rows), default=math.nan)
    max_r2 = max((r.r2_ratio for r in n4.cell_gate_rows), default=math.nan)
    max_r3 = max((r.r3_ratio for r in n4.cell_gate_rows), default=math.nan)

    return {
        "n4": n4,
        "n2_bvp": n2_bvp,
        "n1_bvp": n1_bvp,
        "shooting_comparison": shooting,
        "numerical_decision": decision,
        "numerical_decision_note": decision_note,
        "n4_max_r1_ratio": max_r1,
        "n4_max_r2_ratio": max_r2,
        "n4_max_r3_ratio": max_r3,
        "q_seed_sum_w": float(np.sum(q_seed)),
        "isolated_shooting_gates": shooting_gates,
    }


__all__ = [
    "BvpCellGateRow",
    "CounterflowBvpMeshResult",
    "ShootingBvpComparison",
    "build_n4_q_seed_from_n2_shooting_intervals",
    "classify_numerical_decision",
    "run_counterflow_fixed_inlet_bvp_recovery",
]
