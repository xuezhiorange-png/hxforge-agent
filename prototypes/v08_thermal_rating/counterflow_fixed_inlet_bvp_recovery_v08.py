"""Fixed dual-inlet counterflow BVP recovery for V08_03_COUNTERFLOW_FIXED_INLET_BVP_RECOVERY."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

import numpy as np

from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    PropertyProvider,
    _run_with_rating_context,
    solve_isolated_outer_boundary,
)
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import (
    BvpCellGateRow,
    audit_cell_production_gate,
    cell_gate_rows_from_outcome,
    physical_residual_closure,
    verified_max_ratios,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    JointBVPOutcome,
    solve_joint_boundary_value_mesh,
)


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
        original: Literal["PASS", "BLOCKED"] = (
            "PASS" if physical_residual_closure(rows) == "PASS" else "BLOCKED"
        )
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


def run_n4_bvp_only(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
) -> dict[str, Any]:
    """N4 BVP with N2-interval seed only (N1/N2 BVP not executed)."""
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
    cell0_row = next(r for r in n4.cell_gate_rows if r.cell_index == 0)
    cell0 = audit_cell_production_gate(0, cell0_row)
    mr1, mr2, mr3 = verified_max_ratios(n4.cell_gate_rows)
    return {
        "n4": n4,
        "cell0": cell0,
        "q_seed_sum_w": float(np.sum(q_seed)),
        "n4_max_r1_ratio": mr1,
        "n4_max_r2_ratio": mr2,
        "n4_max_r3_ratio": mr3,
    }


__all__ = [
    "BvpCellGateRow",
    "CounterflowBvpMeshResult",
    "ShootingBvpComparison",
    "build_n4_q_seed_from_n2_shooting_intervals",
    "run_n4_bvp_only",
    "_run_bvp_mesh",
]
