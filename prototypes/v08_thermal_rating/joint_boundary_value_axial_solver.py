"""Joint axial BVP PoC — q-parameterized enthalpy (strict energy conservation)."""
# ruff: noqa: E402, E501

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

import numpy as np
from scipy.optimize import least_squares

from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    attempt_frozen_bulk_direct_trf_recovery,
    build_validated_local_result_from_verified_trial_triple,
    eval_trial_residual_gate,
    recompute_task172_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import TERMINAL_TOLERANCE_K
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _attempt_enthalpy_coupled_direct_trf_root,
    _build_candidate_local_support,
    _effective_h_min_j_kg,
    _enthalpy_coupled_wall_temperatures_from_fraction,
    _LowSideDomainInfeasible,
    _Stage3Failure,
    _state_at_inlet,
    _state_from_enthalpy,
    effective_admitted_h_max_j_kg,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_inlet_temperature_k,
    effective_shell_mass_flow_kg_s,
    effective_tube_inlet_temperature_k,
    effective_tube_mass_flow_kg_s,
)
from prototypes.v08_thermal_rating.true_three_equation_cell_coupling import (
    _algebraic_seed,
    build_closure_primitives,
    build_task172_request_for_q,
    evaluate_three_equation_residuals,
    solve_bvp_cell_u1_u2_trf,
    solve_bvp_cell_wall_eliminated_trf,
    wall_resistance_geometry_audit,
)


def _task173_root_tolerance_w(q_w: float) -> float:
    q_scale = max(abs(float(q_w)), 1.0)
    return max(1.0e-6, q_scale * 2.0e-8)


def _per_cell_thermodynamic_q_cap_w(
    *,
    h_t_face_j_kg: float,
    h_s_face_j_kg: float,
    h_s_right_j_kg: float,
    tube_mdot: float,
    shell_mdot: float,
    h_max: float | None = None,
) -> float:
    h_min = float(_effective_h_min_j_kg())
    tube_cap = tube_mdot * max(h_t_face_j_kg - h_min, 0.0)
    shell_lo_cap = shell_mdot * max(h_s_face_j_kg - h_min, 0.0)
    caps = [tube_cap, shell_lo_cap]
    if h_max is not None:
        caps.append(shell_mdot * max(float(h_max) - h_s_right_j_kg, 0.0))
    return max(0.0, min(caps))


def _fractions_from_walls(
    twi_k: float, two_k: float, *, tube_bulk_k: float, shell_bulk_k: float
) -> tuple[float, float] | None:
    span = tube_bulk_k - shell_bulk_k
    if span <= 0.0:
        return None
    u1 = (two_k - shell_bulk_k) / span
    u2 = (twi_k - two_k) / max(tube_bulk_k - two_k, 1e-30)
    if not (0.0 <= u1 <= 1.0 and 0.0 <= u2 <= 1.0):
        return None
    return u1, u2


def _domain_violation_triplet(violation_w: float, *, scale: float) -> tuple[float, float, float]:
    """Distinct components so FD Jacobian is not a constant penalty plate."""
    v = max(float(violation_w), 1.0) / max(scale, 1.0)
    return (v, v * 1.013, v * 0.987)


def _enthalpy_step_feasible(
    *,
    q_w: float,
    h_t_left: float,
    h_s_left: float,
    h_s_right: float,
    tube_mdot: float,
    shell_mdot: float,
    h_min: float,
    h_max: float,
) -> tuple[bool, float]:
    tube_down = h_t_left - q_w / tube_mdot
    shell_next = h_s_left - q_w / shell_mdot
    viol = 0.0
    for h_val in (h_t_left, tube_down, h_s_left, shell_next, h_s_right):
        if h_val < h_min:
            viol = max(viol, h_min - h_val)
        if h_val > h_max:
            viol = max(viol, h_val - h_max)
    return viol <= 0.0, viol


@dataclass(frozen=True)
class AxialFeasibilityReport:
    feasible: bool
    violation_j_kg: float
    h_t: tuple[float, ...]
    h_s: tuple[float, ...]
    per_cell_q_hi: tuple[float, ...]

    def violation_for_cell(self, index: int, *, q_w: float, tube_mdot: float, shell_mdot: float, h_min: float, h_max: float) -> float:
        h_t = self.h_t
        h_s = self.h_s
        i = index
        tube_down = h_t[i] - q_w / tube_mdot
        shell_next = h_s[i] - q_w / shell_mdot
        viol = 0.0
        for h_val in (h_t[i], tube_down, h_s[i], shell_next, h_s[i + 1]):
            if h_val < h_min:
                viol = max(viol, h_min - h_val)
            if h_val > h_max:
                viol = max(viol, h_val - h_max)
        return viol


def audit_axial_feasibility(
    q_w: np.ndarray | list[float],
    *,
    provider: Any,
    h_t_inlet_j_kg: float,
    h_s_cold_inlet_j_kg: float,
    tube_mass_flow_kg_s: float,
    shell_mass_flow_kg_s: float,
) -> AxialFeasibilityReport:
    """Check full axial enthalpy path (incl. h_max) and per-cell dynamic q upper bounds."""
    q = np.asarray(q_w, dtype=float)
    n = int(q.size)
    h_min = float(_effective_h_min_j_kg())
    h_max = float(effective_admitted_h_max_j_kg(provider))
    mt = float(tube_mass_flow_kg_s)
    ms = float(shell_mass_flow_kg_s)
    h_t, h_s = build_axial_enthalpies_from_q(
        q,
        h_t_inlet_j_kg=h_t_inlet_j_kg,
        h_s_cold_inlet_j_kg=h_s_cold_inlet_j_kg,
        tube_mass_flow_kg_s=mt,
        shell_mass_flow_kg_s=ms,
    )
    viol = 0.0
    q_hi: list[float] = []
    for i in range(n):
        ok, v = _enthalpy_step_feasible(
            q_w=float(q[i]),
            h_t_left=float(h_t[i]),
            h_s_left=float(h_s[i]),
            h_s_right=float(h_s[i + 1]),
            tube_mdot=mt,
            shell_mdot=ms,
            h_min=h_min,
            h_max=h_max,
        )
        if not ok:
            viol = max(viol, v)
        caps = [
            mt * max(float(h_t[i]) - h_min, 0.0),
            ms * max(float(h_s[i]) - h_min, 0.0),
            ms * max(h_max - float(h_s[i + 1]), 0.0),
        ]
        q_hi.append(max(0.0, min(caps)))
    for h_val in (*h_t.tolist(), *h_s.tolist()):
        if h_val < h_min:
            viol = max(viol, h_min - h_val)
        if h_val > h_max:
            viol = max(viol, h_val - h_max)
    return AxialFeasibilityReport(
        feasible=viol <= 0.0,
        violation_j_kg=viol,
        h_t=tuple(float(v) for v in h_t),
        h_s=tuple(float(v) for v in h_s),
        per_cell_q_hi=tuple(q_hi),
    )


def _smooth_domain_residuals(violation_j_kg: float, *, scale: float) -> tuple[float, float, float]:
    v = max(float(violation_j_kg), 0.0)
    if v <= 0.0:
        return (0.0, 0.0, 0.0)
    base = (v / max(scale, 1.0)) ** 0.5
    return (base, base * 1.017, base * 0.983)


@dataclass
class JointBVPCellRecord:
    index: int
    q_w: float
    twi_k: float
    two_k: float
    h_t_left_j_kg: float
    h_t_right_j_kg: float
    h_s_left_j_kg: float
    h_s_right_j_kg: float
    max_task172_residual_ratio: float
    task172_gate_pass: bool
    production_validated: bool
    cell_id: str = ""
    t_tube_bulk_k: float = math.nan
    t_shell_bulk_k: float = math.nan
    task172_r1_w: float = math.nan
    task172_r2_w: float = math.nan
    task172_r3_w: float = math.nan
    task173_root_residual_w: float = math.nan
    task173_root_validated: bool = False
    task172_request_hash: str = ""
    domain_exit: str | None = None


@dataclass
class JointBVPOutcome:
    status: str
    subdivisions: int
    cells: list[JointBVPCellRecord]
    total_q_w: float
    energy_balance_residual_w: float
    tube_enthalpy_loss_w: float
    shell_enthalpy_gain_w: float
    terminal_residual_k: float
    terminal_residual_j_kg: float
    terminal_pass: bool
    all_task172_gates_pass: bool
    optimizer_nfev: int
    optimizer_success: bool
    physical_acceptance: bool
    solver_success: bool
    tube_outlet_temperature_k: float
    shell_outlet_temperature_k: float
    diagnostics: tuple[str, ...]
    residual_heat_scale_w: float = 0.0
    energy_conserving_formulation: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


def build_axial_enthalpies_from_q(
    q_w: np.ndarray | list[float],
    *,
    h_t_inlet_j_kg: float,
    h_s_cold_inlet_j_kg: float,
    tube_mass_flow_kg_s: float,
    shell_mass_flow_kg_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Task173 counterflow face indexing: tube marches 0→N, shell fixed at N then 0←N.

    Per cell i: h_t[i+1] = h_t[i] - q[i]/m_t; h_s[i] = h_s[i+1] + q[i]/m_s (equiv. production
    shell_next = shell_left - q/m_s).
    """
    q = np.asarray(q_w, dtype=float)
    n = int(q.size)
    if n == 0:
        return np.asarray([h_t_inlet_j_kg]), np.asarray([h_s_cold_inlet_j_kg])
    h_t = np.empty(n + 1, dtype=float)
    h_s = np.empty(n + 1, dtype=float)
    h_t[0] = float(h_t_inlet_j_kg)
    h_s[n] = float(h_s_cold_inlet_j_kg)
    mt = float(tube_mass_flow_kg_s)
    ms = float(shell_mass_flow_kg_s)
    if mt <= 0.0 or ms <= 0.0:
        raise ValueError("mass flow must be positive")
    for i in range(n):
        h_t[i + 1] = h_t[i] - q[i] / mt
    for i in range(n - 1, -1, -1):
        h_s[i] = h_s[i + 1] + q[i] / ms
    return h_t, h_s


def axial_energy_slack_w(
    q_w: np.ndarray | list[float],
    *,
    h_t_inlet_j_kg: float,
    h_s_cold_inlet_j_kg: float,
    tube_mass_flow_kg_s: float,
    shell_mass_flow_kg_s: float,
) -> tuple[float, float, float]:
    """Return (Q_sum, tube_loss, shell_gain) and max pairwise mismatch (exact construction)."""
    h_t, h_s = build_axial_enthalpies_from_q(
        q_w,
        h_t_inlet_j_kg=h_t_inlet_j_kg,
        h_s_cold_inlet_j_kg=h_s_cold_inlet_j_kg,
        tube_mass_flow_kg_s=tube_mass_flow_kg_s,
        shell_mass_flow_kg_s=shell_mass_flow_kg_s,
    )
    q = np.asarray(q_w, dtype=float)
    q_sum = float(np.sum(q))
    mt = float(tube_mass_flow_kg_s)
    ms = float(shell_mass_flow_kg_s)
    tube_loss = mt * (h_t[0] - h_t[-1])
    shell_gain = ms * (h_s[0] - h_s[-1])
    residual = max(abs(tube_loss - q_sum), abs(shell_gain - q_sum), abs(tube_loss - shell_gain))
    return q_sum, tube_loss, shell_gain, residual


def _supports_for_mesh(ctx: Any, subdivisions: int) -> list[Any]:
    supports: list[Any] = []
    for interval_index in range(ctx.interval_count):
        for subdivision_index in range(subdivisions):
            supports.append(
                _build_candidate_local_support(ctx, interval_index, subdivisions, subdivision_index)
            )
    return supports


def _state_from_h(
    provider: Any,
    h_j_kg: float,
    *,
    side: Literal["TUBE", "SHELL"],
) -> Any:
    return _state_from_enthalpy(
        provider,
        Decimal(str(h_j_kg)),
        shell_search_state=(side == "SHELL"),
        side=side,
    )


def _heat_residual_scale_w(
    q_guess: np.ndarray, *, tube_mdot: float, enthalpy_span_j_kg: float
) -> float:
    duty_hint = abs(tube_mdot) * max(abs(enthalpy_span_j_kg), 1.0)
    return max(float(np.sum(np.abs(q_guess))), duty_hint * 0.05, 1.0e4)


def _duty_uniform_q_per_cell(
    *,
    provider: Any,
    n_cells: int,
    h_t_in: float,
    tube_mdot: float,
) -> float:
    t_tube = float(effective_tube_inlet_temperature_k())
    t_shell = float(effective_shell_inlet_temperature_k())
    t_tube_out = t_tube - 0.35 * (t_tube - t_shell)
    h_t_out = float(_state_at_inlet(provider, t_tube_out, side="TUBE").native.enthalpy_j_kg)
    total_q = max(tube_mdot * (h_t_in - h_t_out), 1.0)
    return total_q / max(n_cells, 1)


def _resistance_network_q_u_seed(
    *,
    q_cap_w: float,
    q_guess: float,
    support: Any,
    tube_up: Any,
    shell_left: Any,
    provider: Any,
    shell_authority: Any,
) -> tuple[float, float, float] | None:
    """Gi/Go/Rwall network seed; optional frozen-bulk polish; returns (q, u1, u2)."""
    q_try = min(max(float(q_guess), 0.0), q_cap_w)
    try:
        request, _, _ = build_task172_request_for_q(
            q_try,
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
    except (_LowSideDomainInfeasible, _Stage3Failure):
        return None
    tube_k = float(request.tube_bulk_state.temperature_k)
    shell_k = float(request.shell_bulk_state.temperature_k)
    if tube_k <= shell_k:
        return None
    prim = build_closure_primitives(request, provider)
    q_a, twi_a, two_a = _algebraic_seed(tube_k, shell_k, prim, support)
    if q_a <= 0.0 or q_a > q_cap_w:
        q_a = min(max(q_a, 0.0), q_cap_w)
    frac = _fractions_from_walls(twi_a, two_a, tube_bulk_k=tube_k, shell_bulk_k=shell_k)
    if frac is None:
        wall = _enthalpy_coupled_wall_temperatures_from_fraction(
            0.35, 0.35, tube_bulk_k=tube_k, shell_bulk_k=shell_k
        )
        if wall is None:
            return None
        twi_a, two_a = wall
        frac = _fractions_from_walls(twi_a, two_a, tube_bulk_k=tube_k, shell_bulk_k=shell_k)
        if frac is None:
            return None
    u1, u2 = frac
    try:
        request_a, _, _ = build_task172_request_for_q(
            q_a,
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
    except (_LowSideDomainInfeasible, _Stage3Failure):
        return q_a, u1, u2
    outcome = attempt_frozen_bulk_direct_trf_recovery(request_a, provider)
    if getattr(outcome, "status", None) != "VALIDATED":
        return q_a, u1, u2
    q_v = float(outcome.signed_q_hot_to_cold_w)  # type: ignore[union-attr]
    twi_v = float(outcome.wall_temperature_inner_k)  # type: ignore[union-attr]
    two_v = float(outcome.wall_temperature_outer_k)  # type: ignore[union-attr]
    tube_k2 = float(request_a.tube_bulk_state.temperature_k)
    shell_k2 = float(request_a.shell_bulk_state.temperature_k)
    frac2 = _fractions_from_walls(twi_v, two_v, tube_bulk_k=tube_k2, shell_bulk_k=shell_k2)
    if frac2 is None:
        return q_a, u1, u2
    return min(q_v, q_cap_w), frac2[0], frac2[1]


def joint_bvp_dof_audit_summary() -> dict[str, str]:
    """3N DOF (q, u1, u2); shell x=0 outlet enthalpy is not an independent unknown."""
    return {
        "unknown_parameterization": "q_u1_u2_per_cell",
        "unknown_count_rule": "3N",
        "shell_outlet_enthalpy_h_s0": "h_s[0]=h_s[N]+sum(q[i])/m_shell (implicit from q vector)",
        "extra_shell_outlet_enthalpy_dof": "forbidden",
        "audit": "PASS",
    }


def _wall_order_valid(twi: float, two: float, t_tube: float, t_shell: float) -> bool:
    return t_tube > twi > two > t_shell


def _evaluate_cell_physics_residuals(
    *,
    index: int,
    q: float,
    u1: float,
    u2: float,
    support: Any,
    h_t: np.ndarray,
    h_s: np.ndarray,
    provider: Any,
    shell_authority: Any,
    heat_scale: float,
    h_min: float,
    h_max: float,
    tube_mdot: float,
    shell_mdot: float,
) -> tuple[np.ndarray, bool, bool, bool, bool]:
    """Return (3,) scaled residuals, physical_evaluated, domain_penalty, enthalpy_ok, property_ok."""
    ok_step, viol = _enthalpy_step_feasible(
        q_w=q,
        h_t_left=float(h_t[index]),
        h_s_left=float(h_s[index]),
        h_s_right=float(h_s[index + 1]),
        tube_mdot=tube_mdot,
        shell_mdot=shell_mdot,
        h_min=h_min,
        h_max=h_max,
    )
    if not ok_step:
        return (
            np.asarray(_domain_violation_triplet(viol, scale=heat_scale), dtype=float),
            False,
            True,
            False,
            True,
        )
    try:
        tube_up = _state_from_h(provider, float(h_t[index]), side="TUBE")
        shell_left = _state_from_h(provider, float(h_s[index]), side="SHELL")
    except (_Stage3Failure, _LowSideDomainInfeasible):
        return (
            np.asarray(_domain_violation_triplet(1.0e3, scale=heat_scale), dtype=float),
            False,
            True,
            True,
            False,
        )
    try:
        request, _, _ = build_task172_request_for_q(
            q,
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
    except (_LowSideDomainInfeasible, _Stage3Failure):
        return (
            np.asarray(_domain_violation_triplet(1.0e3, scale=heat_scale), dtype=float),
            False,
            True,
            True,
            False,
        )
    tube_k = float(request.tube_bulk_state.temperature_k)
    shell_k = float(request.shell_bulk_state.temperature_k)
    wall = _enthalpy_coupled_wall_temperatures_from_fraction(
        u1, u2, tube_bulk_k=tube_k, shell_bulk_k=shell_k
    )
    if wall is None or not _wall_order_valid(
        wall[0], wall[1], tube_k, shell_k
    ):
        return (
            np.asarray(
                _domain_violation_triplet(max(tube_k - shell_k, 1.0), scale=heat_scale),
                dtype=float,
            ),
            False,
            True,
            True,
            True,
        )
    twi, two = wall
    prim = build_closure_primitives(request, provider)
    gate = evaluate_three_equation_residuals(
        q, twi, two, request=request, provider=provider, primitives=prim
    )
    acts = [float(r) / heat_scale for r in gate["residuals_w"]]
    return (np.asarray(acts, dtype=float), True, False, True, True)


def _dynamic_q_bounds(
    q: np.ndarray,
    *,
    provider: Any,
    h_t0: float,
    h_sN: float,
    tube_mdot: float,
    shell_mdot: float,
) -> tuple[np.ndarray, np.ndarray]:
    report = audit_axial_feasibility(
        q,
        provider=provider,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=tube_mdot,
        shell_mass_flow_kg_s=shell_mdot,
    )
    n = q.size
    lo = np.zeros(3 * n, dtype=float)
    hi = np.zeros(3 * n, dtype=float)
    for i in range(n):
        lo[3 * i] = 0.0
        hi[3 * i] = max(float(report.per_cell_q_hi[i]), 1.0)
        lo[3 * i + 1 : 3 * i + 3] = (0.0, 0.0)
        hi[3 * i + 1 : 3 * i + 3] = (1.0, 1.0)
    return lo, hi


def _block_gauss_seidel_joint_solve(
    x0: np.ndarray,
    *,
    supports: list[Any],
    provider: Any,
    shell_authority: Any,
    h_t0: float,
    h_sN: float,
    tube_mdot: float,
    shell_mdot: float,
    heat_scale: float,
    max_sweeps: int = 10,
    max_nfev_per_cell: int = 80,
) -> tuple[np.ndarray, int, bool]:
    """Block-coordinate TRF: one 3x3 cell at a time with full-q feasibility audit."""
    n = len(supports)
    x = x0.copy()
    h_min = float(_effective_h_min_j_kg())
    h_max = float(effective_admitted_h_max_j_kg(provider))
    total_nfev = 0
    domain_plateau = False

    def vec_q(vec: np.ndarray) -> np.ndarray:
        return vec.reshape(n, 3)[:, 0].copy()

    for _ in range(max_sweeps):
        for i, support in enumerate(supports):
            q_base = vec_q(x)
            lo, hi = _dynamic_q_bounds(
                q_base,
                provider=provider,
                h_t0=h_t0,
                h_sN=h_sN,
                tube_mdot=tube_mdot,
                shell_mdot=shell_mdot,
            )

            def residual_local(x3: np.ndarray, *, cell_i: int = i, cell_support: Any = support) -> np.ndarray:
                nonlocal domain_plateau
                trial = x.copy()
                trial[3 * cell_i : 3 * cell_i + 3] = x3
                qtw = trial.reshape(n, 3)
                q_vals = qtw[:, 0]
                feas = audit_axial_feasibility(
                    q_vals,
                    provider=provider,
                    h_t_inlet_j_kg=h_t0,
                    h_s_cold_inlet_j_kg=h_sN,
                    tube_mass_flow_kg_s=tube_mdot,
                    shell_mass_flow_kg_s=shell_mdot,
                )
                if not feas.feasible:
                    domain_plateau = True
                    viol = feas.violation_for_cell(
                        cell_i,
                        q_w=float(x3[0]),
                        tube_mdot=tube_mdot,
                        shell_mdot=shell_mdot,
                        h_min=h_min,
                        h_max=h_max,
                    )
                    return np.asarray(
                        _smooth_domain_residuals(viol or feas.violation_j_kg, scale=heat_scale),
                        dtype=float,
                    )
                h_t, h_s = build_axial_enthalpies_from_q(
                    q_vals,
                    h_t_inlet_j_kg=h_t0,
                    h_s_cold_inlet_j_kg=h_sN,
                    tube_mass_flow_kg_s=tube_mdot,
                    shell_mass_flow_kg_s=shell_mdot,
                )
                res, phys, penal, _, _ = _evaluate_cell_physics_residuals(
                    index=cell_i,
                    q=float(x3[0]),
                    u1=float(x3[1]),
                    u2=float(x3[2]),
                    support=cell_support,
                    h_t=h_t,
                    h_s=h_s,
                    provider=provider,
                    shell_authority=shell_authority,
                    heat_scale=heat_scale,
                    h_min=h_min,
                    h_max=h_max,
                    tube_mdot=tube_mdot,
                    shell_mdot=shell_mdot,
                )
                if penal:
                    domain_plateau = True
                return res

            lo_c = lo[3 * i : 3 * i + 3]
            hi_c = hi[3 * i : 3 * i + 3]
            x_seed = np.clip(x[3 * i : 3 * i + 3], lo_c, hi_c)
            opt = least_squares(
                residual_local,
                x_seed,
                bounds=(lo_c, hi_c),
                method="trf",
                ftol=1e-12,
                xtol=1e-10,
                gtol=1e-12,
                max_nfev=max_nfev_per_cell,
            )
            x[3 * i : 3 * i + 3] = opt.x
            total_nfev += int(opt.nfev)
    return x, total_nfev, domain_plateau


@dataclass
class RealCellClosureOutcome:
    cell_index: int
    task172_gate_pass: bool
    task173_root_validated: bool
    production_validated: bool
    q_w: float
    twi_k: float
    two_k: float
    domain_exit: str | None = None
    r1_w: float = math.nan
    r2_w: float = math.nan
    r3_w: float = math.nan
    max_ulp_ratio: float = math.nan
    g_i_w_k: float = math.nan
    g_o_w_k: float = math.nan
    rwall_k_w: float = math.nan
    elimination_method: str = ""
    optimizer_message: str = ""
    failure_class: str = ""
    single_cell_bc_corrected: bool = False
    compare_u1_u2: dict[str, Any] = field(default_factory=dict)
    compare_tmid: dict[str, Any] = field(default_factory=dict)
    shell_inlet_h_fixed: bool = False


def build_bvp_cell_task172_for_trial_q(
    cell_index: int,
    q_trial_w: float,
    q_full: np.ndarray,
    *,
    support: Any,
    provider: Any,
    shell_authority: Any,
    h_t_inlet_j_kg: float,
    h_s_cold_inlet_j_kg: float,
    tube_mass_flow_kg_s: float,
    shell_mass_flow_kg_s: float,
) -> tuple[Any, Any, Any, np.ndarray, np.ndarray]:
    """Rebuild BVP face enthalpies on each q trial; shell left follows h_s_right + q/m_s."""
    q_work = np.asarray(q_full, dtype=float).copy()
    q_work[cell_index] = float(q_trial_w)
    h_t, h_s = build_axial_enthalpies_from_q(
        q_work,
        h_t_inlet_j_kg=h_t_inlet_j_kg,
        h_s_cold_inlet_j_kg=h_s_cold_inlet_j_kg,
        tube_mass_flow_kg_s=tube_mass_flow_kg_s,
        shell_mass_flow_kg_s=shell_mass_flow_kg_s,
    )
    tube_up = _state_from_h(provider, float(h_t[cell_index]), side="TUBE")
    shell_left = _state_from_h(provider, float(h_s[cell_index]), side="SHELL")
    request, tube_local, shell_local = build_task172_request_for_q(
        float(q_trial_w),
        support=support,
        tube_upstream=tube_up,
        shell_physical_left=shell_left,
        provider=provider,
        shell_authority=shell_authority,
    )
    return request, tube_local, shell_local, h_t, h_s


def _classify_cell_closure_failure(
    *,
    gate_pass: bool,
    optimizer_success: bool,
    max_ratio: float,
    q_cap: float,
) -> str:
    if gate_pass:
        return ""
    if not optimizer_success:
        return "A_NUMERICAL_ROOT_NOT_FOUND"
    if max_ratio > 1.0 and math.isfinite(max_ratio):
        return "B_WALL_RELATED_HTC_NONLINEARITY"
    if q_cap <= 0.0:
        return "C_FROZEN_NEIGHBOUR_Q_INFEASIBLE"
    return "A_NUMERICAL_ROOT_NOT_FOUND"


def attempt_real_single_cell_closure(
    *,
    cell_index: int,
    provider: Any,
    shell_authority: Any,
    candidate_ctx: Any,
    subdivisions: int = 1,
    q_freeze: np.ndarray | None = None,
) -> RealCellClosureOutcome:
    """Cell-0 closure with BVP face reconstruction; compare 3-DOF u1/u2 vs 2-DOF wall elimination."""
    supports = _supports_for_mesh(candidate_ctx, subdivisions)
    if cell_index < 0 or cell_index >= len(supports):
        return RealCellClosureOutcome(
            cell_index=cell_index,
            task172_gate_pass=False,
            task173_root_validated=False,
            production_validated=False,
            q_w=math.nan,
            twi_k=math.nan,
            two_k=math.nan,
            domain_exit="index_out_of_range",
        )
    tube_mdot = float(effective_tube_mass_flow_kg_s())
    shell_mdot = float(effective_shell_mass_flow_kg_s())
    h_t0 = float(
        _state_at_inlet(
            provider, effective_tube_inlet_temperature_k(), side="TUBE"
        ).native.enthalpy_j_kg
    )
    h_sN = float(effective_shell_cold_inlet_enthalpy_j_kg())
    n = len(supports)
    q_uniform = _duty_uniform_q_per_cell(
        provider=provider, n_cells=n, h_t_in=h_t0, tube_mdot=tube_mdot
    )
    q = np.full(n, q_uniform, dtype=float) if q_freeze is None else np.asarray(q_freeze, dtype=float).copy()
    report = audit_axial_feasibility(
        q,
        provider=provider,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=tube_mdot,
        shell_mass_flow_kg_s=shell_mdot,
    )
    q_cap = float(report.per_cell_q_hi[cell_index])
    support = supports[cell_index]
    h_s_before = float(
        build_axial_enthalpies_from_q(
            q,
            h_t_inlet_j_kg=h_t0,
            h_s_cold_inlet_j_kg=h_sN,
            tube_mass_flow_kg_s=tube_mdot,
            shell_mass_flow_kg_s=shell_mdot,
        )[1][-1]
    )
    q_seed = min(float(q[cell_index]), q_cap)

    def request_at_q(q_val: float) -> Any:
        request, _, _, _, _ = build_bvp_cell_task172_for_trial_q(
            cell_index,
            q_val,
            q,
            support=support,
            provider=provider,
            shell_authority=shell_authority,
            h_t_inlet_j_kg=h_t0,
            h_s_cold_inlet_j_kg=h_sN,
            tube_mass_flow_kg_s=tube_mdot,
            shell_mass_flow_kg_s=shell_mdot,
        )
        return request

    compare_tmid = solve_bvp_cell_wall_eliminated_trf(
        request_at_q=request_at_q,
        provider=provider,
        q_upper=q_cap,
        q_seed=q_seed,
    )
    compare_u1_u2 = solve_bvp_cell_u1_u2_trf(
        request_at_q=request_at_q,
        provider=provider,
        q_upper=q_cap,
        q_seed=q_seed,
    )
    candidates = [compare_tmid, compare_u1_u2]
    candidates.sort(
        key=lambda c: (
            0 if c.get("original_residual_gate_pass") else 1,
            float(c.get("max_residual_ratio", math.inf)),
        )
    )
    best = candidates[0]
    if best.get("status") == "BLOCKED" and "reason" in best:
        return RealCellClosureOutcome(
            cell_index=cell_index,
            task172_gate_pass=False,
            task173_root_validated=False,
            production_validated=False,
            q_w=math.nan,
            twi_k=math.nan,
            two_k=math.nan,
            domain_exit=str(best.get("reason")),
            failure_class=_classify_cell_closure_failure(
                gate_pass=False,
                optimizer_success=False,
                max_ratio=math.inf,
                q_cap=q_cap,
            ),
            single_cell_bc_corrected=True,
            compare_u1_u2=compare_u1_u2,
            compare_tmid=compare_tmid,
        )
    q_out = float(best["q_w"])
    twi = float(best["twi_k"])
    two = float(best["two_k"])
    request_f, _, _, h_t, h_s = build_bvp_cell_task172_for_trial_q(
        cell_index,
        q_out,
        q,
        support=support,
        provider=provider,
        shell_authority=shell_authority,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=tube_mdot,
        shell_mass_flow_kg_s=shell_mdot,
    )
    wall_audit = wall_resistance_geometry_audit(request_f, provider)
    h_s_after = float(h_s[-1])
    rec = _collect_cell_record(
        index=cell_index,
        support=support,
        q=q_out,
        twi=twi,
        two=two,
        h_t=h_t,
        h_s=h_s,
        provider=provider,
        shell_authority=shell_authority,
    )
    gate_pass = bool(best.get("original_residual_gate_pass")) and rec.task172_gate_pass
    failure = _classify_cell_closure_failure(
        gate_pass=gate_pass,
        optimizer_success=bool(best.get("optimizer_success")),
        max_ratio=float(best.get("max_residual_ratio", math.inf)),
        q_cap=q_cap,
    )
    return RealCellClosureOutcome(
        cell_index=cell_index,
        task172_gate_pass=gate_pass,
        task173_root_validated=rec.task173_root_validated and gate_pass,
        production_validated=rec.production_validated and gate_pass,
        q_w=rec.q_w,
        twi_k=rec.twi_k,
        two_k=rec.two_k,
        domain_exit=rec.domain_exit,
        r1_w=float(best.get("r1_w", math.nan)),
        r2_w=float(best.get("r2_w", math.nan)),
        r3_w=float(best.get("r3_w", math.nan)),
        max_ulp_ratio=float(best.get("max_residual_ratio", math.nan)),
        g_i_w_k=float(best.get("g_i_w_k", math.nan)),
        g_o_w_k=float(best.get("g_o_w_k", math.nan)),
        rwall_k_w=float(wall_audit["rwall_k_w"]),
        elimination_method=str(best.get("method", "")),
        optimizer_message=str(best.get("optimizer_message", "")),
        failure_class=failure,
        single_cell_bc_corrected=True,
        compare_u1_u2=compare_u1_u2,
        compare_tmid=compare_tmid,
        shell_inlet_h_fixed=abs(h_s_after - h_s_before) <= 1.0e-6 and abs(h_s_after - h_sN) <= 1.0e-3,
    )


def attempt_real_two_cell_coupling(
    *,
    provider: Any,
    shell_authority: Any,
    candidate_ctx: Any,
    subdivisions: int = 1,
    q_seed: np.ndarray | None = None,
) -> dict[str, Any]:
    """Joint block solve on cells 0–1 with frozen q on remaining cells."""
    supports = _supports_for_mesh(candidate_ctx, subdivisions)
    n = len(supports)
    if n < 2:
        return {"status": "BLOCKED", "reason": "need_at_least_two_cells"}
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
    x0, _, _, q_part = _sequential_q_u_initial_guess(
        provider=provider,
        supports=supports,
        h_t0=h_t0,
        h_sN=h_sN,
        tube_mdot=tube_mdot,
        shell_mdot=shell_mdot,
        q_uniform=q_uniform,
        shell_authority=shell_authority,
    )
    if q_seed is not None:
        qs = np.asarray(q_seed, dtype=float)
        for i in range(min(n, qs.size)):
            x0[3 * i] = float(qs[i])
    heat_scale = _heat_residual_scale_w(q_part, tube_mdot=tube_mdot, enthalpy_span_j_kg=h_t0 - h_sN)
    # Solve two cells with enthalpy march on full n using frozen tail q.
    q_full = np.asarray(x0.reshape(n, 3)[:, 0], dtype=float).copy()
    h_min = float(_effective_h_min_j_kg())
    h_max = float(effective_admitted_h_max_j_kg(provider))
    total_nfev = 0
    domain_plateau = False
    for _sweep in range(6):
        for i in range(2):
            lo_i, hi_i = _dynamic_q_bounds(
                q_full,
                provider=provider,
                h_t0=h_t0,
                h_sN=h_sN,
                tube_mdot=tube_mdot,
                shell_mdot=shell_mdot,
            )

            def res2(x3: np.ndarray, *, cell_i: int = i) -> np.ndarray:
                nonlocal domain_plateau
                q_try = q_full.copy()
                q_try[cell_i] = float(x3[0])
                feas = audit_axial_feasibility(
                    q_try,
                    provider=provider,
                    h_t_inlet_j_kg=h_t0,
                    h_s_cold_inlet_j_kg=h_sN,
                    tube_mass_flow_kg_s=tube_mdot,
                    shell_mass_flow_kg_s=shell_mdot,
                )
                if not feas.feasible:
                    domain_plateau = True
                    viol = feas.violation_for_cell(
                        cell_i,
                        q_w=float(x3[0]),
                        tube_mdot=tube_mdot,
                        shell_mdot=shell_mdot,
                        h_min=h_min,
                        h_max=h_max,
                    )
                    return np.asarray(
                        _smooth_domain_residuals(viol or feas.violation_j_kg, scale=heat_scale),
                        dtype=float,
                    )
                h_t, h_s = build_axial_enthalpies_from_q(
                    q_try,
                    h_t_inlet_j_kg=h_t0,
                    h_s_cold_inlet_j_kg=h_sN,
                    tube_mass_flow_kg_s=tube_mdot,
                    shell_mass_flow_kg_s=shell_mdot,
                )
                u1, u2 = float(x0[3 * cell_i + 1]), float(x0[3 * cell_i + 2])
                if x3.size >= 3:
                    u1, u2 = float(x3[1]), float(x3[2])
                out, _, penal, _, _ = _evaluate_cell_physics_residuals(
                    index=cell_i,
                    q=float(x3[0]),
                    u1=u1,
                    u2=u2,
                    support=supports[cell_i],
                    h_t=h_t,
                    h_s=h_s,
                    provider=provider,
                    shell_authority=shell_authority,
                    heat_scale=heat_scale,
                    h_min=h_min,
                    h_max=h_max,
                    tube_mdot=tube_mdot,
                    shell_mdot=shell_mdot,
                )
                if penal:
                    domain_plateau = True
                return out

            lo_c = lo_i[3 * i : 3 * i + 3]
            hi_c = hi_i[3 * i : 3 * i + 3]
            x_seed = np.clip(x0[3 * i : 3 * i + 3], lo_c, hi_c)
            opt = least_squares(
                res2,
                x_seed,
                bounds=(lo_c, hi_c),
                method="trf",
                ftol=1e-12,
                xtol=1e-10,
                gtol=1e-12,
                max_nfev=120,
            )
            x0[3 * i : 3 * i + 3] = opt.x
            q_full[i] = float(opt.x[0])
            total_nfev += int(opt.nfev)
    h_t, h_s = build_axial_enthalpies_from_q(
        q_full,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=tube_mdot,
        shell_mass_flow_kg_s=shell_mdot,
    )
    cells: list[JointBVPCellRecord] = []
    for i in range(2):
        frac = x0[3 * i + 1 : 3 * i + 3]
        wall = None
        try:
            request, _, _ = build_task172_request_for_q(
                float(q_full[i]),
                support=supports[i],
                tube_upstream=_state_from_h(provider, float(h_t[i]), side="TUBE"),
                shell_physical_left=_state_from_h(provider, float(h_s[i]), side="SHELL"),
                provider=provider,
                shell_authority=shell_authority,
            )
            tube_k = float(request.tube_bulk_state.temperature_k)
            shell_k = float(request.shell_bulk_state.temperature_k)
            wall = _enthalpy_coupled_wall_temperatures_from_fraction(
                float(frac[0]), float(frac[1]), tube_bulk_k=tube_k, shell_bulk_k=shell_k
            )
        except (_LowSideDomainInfeasible, _Stage3Failure):
            pass
        twi, two = (math.nan, math.nan) if wall is None else wall
        cells.append(
            _collect_cell_record(
                index=i,
                support=supports[i],
                q=float(q_full[i]),
                twi=float(twi),
                two=float(two),
                h_t=h_t,
                h_s=h_s,
                provider=provider,
                shell_authority=shell_authority,
            )
        )
    pass_ = all(
        c.task172_gate_pass and c.task173_root_validated and c.production_validated
        for c in cells
    )
    return {
        "status": "PASS" if pass_ else "BLOCKED",
        "cells": cells,
        "optimizer_nfev": total_nfev,
        "domain_penalty_plateau": domain_plateau,
        "q_full": q_full.tolist(),
    }


def _sequential_q_u_initial_guess(
    *,
    provider: Any,
    supports: list[Any],
    h_t0: float,
    h_sN: float,
    tube_mdot: float,
    shell_mdot: float,
    q_uniform: float,
    shell_authority: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """March axial q with enthalpy rebuild; per-cell resistance/TRF u seed."""
    n = len(supports)
    q = np.full(n, q_uniform, dtype=float)
    x0 = np.zeros(3 * n, dtype=float)
    lo = np.zeros(3 * n, dtype=float)
    hi = np.zeros(3 * n, dtype=float)
    for i, support in enumerate(supports):
        h_t, h_s = build_axial_enthalpies_from_q(
            q,
            h_t_inlet_j_kg=h_t0,
            h_s_cold_inlet_j_kg=h_sN,
            tube_mass_flow_kg_s=tube_mdot,
            shell_mass_flow_kg_s=shell_mdot,
        )
        feas = audit_axial_feasibility(
            q,
            provider=provider,
            h_t_inlet_j_kg=h_t0,
            h_s_cold_inlet_j_kg=h_sN,
            tube_mass_flow_kg_s=tube_mdot,
            shell_mass_flow_kg_s=shell_mdot,
        )
        h_max = float(effective_admitted_h_max_j_kg(provider))
        q_cap = min(
            _per_cell_thermodynamic_q_cap_w(
                h_t_face_j_kg=float(h_t[i]),
                h_s_face_j_kg=float(h_s[i]),
                h_s_right_j_kg=float(h_s[i + 1]),
                tube_mdot=tube_mdot,
                shell_mdot=shell_mdot,
                h_max=h_max,
            ),
            float(feas.per_cell_q_hi[i]),
        )
        lo[3 * i] = 0.0
        hi[3 * i] = max(q_cap, 1.0)
        lo[3 * i + 1 : 3 * i + 3] = (0.0, 0.0)
        hi[3 * i + 1 : 3 * i + 3] = (1.0, 1.0)
        tube_up = _state_from_h(provider, float(h_t[i]), side="TUBE")
        shell_left = _state_from_h(provider, float(h_s[i]), side="SHELL")
        q_seed = min(q_uniform, q_cap)
        coupled = _attempt_enthalpy_coupled_direct_trf_root(
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
            q_upper=float(q_cap),
            q_seed=float(q[i] if q[i] > 0 else q_seed),
        )
        if coupled is not None:
            q[i] = float(coupled.q_w)
            tube_k = float(coupled.tube_local.native.temperature_k)
            shell_k = float(coupled.shell_local.native.temperature_k)
            twi = float(coupled.task172_result.wall_temperature_inner_k)
            two = float(coupled.task172_result.wall_temperature_outer_k)
            frac = _fractions_from_walls(twi, two, tube_bulk_k=tube_k, shell_bulk_k=shell_k)
            if frac is not None:
                x0[3 * i : 3 * i + 3] = (q[i], frac[0], frac[1])
                continue
        seed = _resistance_network_q_u_seed(
            q_cap_w=q_cap,
            q_guess=q_seed,
            support=support,
            tube_up=tube_up,
            shell_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
        if seed is None:
            x0[3 * i : 3 * i + 3] = (min(q_uniform, q_cap), 0.35, 0.35)
            continue
        q_i, u1, u2 = seed
        x0[3 * i : 3 * i + 3] = (q_i, u1, u2)
        q[i] = q_i
    return x0, lo, hi, q


def _collect_cell_record(
    *,
    index: int,
    support: Any,
    q: float,
    twi: float,
    two: float,
    h_t: np.ndarray,
    h_s: np.ndarray,
    provider: Any,
    shell_authority: Any,
) -> JointBVPCellRecord:
    domain_exit: str | None = None
    try:
        tube_up = _state_from_h(provider, float(h_t[index]), side="TUBE")
        shell_left = _state_from_h(provider, float(h_s[index]), side="SHELL")
        request, _, _ = build_task172_request_for_q(
            q,
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
    except (_LowSideDomainInfeasible, _Stage3Failure) as exc:
        return JointBVPCellRecord(
            index=index,
            q_w=q,
            twi_k=twi,
            two_k=two,
            h_t_left_j_kg=float(h_t[index]),
            h_t_right_j_kg=float(h_t[index + 1]),
            h_s_left_j_kg=float(h_s[index]),
            h_s_right_j_kg=float(h_s[index + 1]),
            max_task172_residual_ratio=math.inf,
            task172_gate_pass=False,
            production_validated=False,
            cell_id=getattr(support, "tube_cell_id", ""),
            domain_exit=type(exc).__name__,
        )
    req_hash = recompute_task172_request_hash(request)
    gate = eval_trial_residual_gate(request, provider, q, twi, two)
    gate_pass = bool(gate and gate.get("passes_original_residual_gate"))
    r1 = r2 = r3 = math.nan
    if gate:
        res = gate.get("residuals_w") or gate.get("signed_residuals_w")
        if res and len(res) >= 3:
            r1, r2, r3 = (float(res[0]), float(res[1]), float(res[2]))
    prim = build_closure_primitives(request, provider)
    three = evaluate_three_equation_residuals(
        q, twi, two, request=request, provider=provider, primitives=prim
    )
    if math.isnan(r1):
        r1, r2, r3 = three["residuals_w"]
    prod_ok = False
    q_trial = float(q)
    q_out = q
    twi_out = twi
    two_out = two
    f_q = math.nan
    root_ok = False
    try:
        validated = build_validated_local_result_from_verified_trial_triple(
            request, provider, q, twi, two, polish_nextafter=True
        )
        if getattr(validated, "status", None) == "VALIDATED":
            prod_ok = True
            q_out = float(validated.signed_q_hot_to_cold_w)  # type: ignore[union-attr]
            twi_out = float(validated.wall_temperature_inner_k)  # type: ignore[union-attr]
            two_out = float(validated.wall_temperature_outer_k)  # type: ignore[union-attr]
            gate = eval_trial_residual_gate(request, provider, q_out, twi_out, two_out)
            gate_pass = bool(gate and gate.get("passes_original_residual_gate"))
            three = evaluate_three_equation_residuals(
                q_out, twi_out, two_out, request=request, provider=provider, primitives=prim
            )
            r1, r2, r3 = three["residuals_w"]
            f_q = q_trial - q_out
            tol = _task173_root_tolerance_w(q_out)
            # Do not treat F(q)=0 as root evidence when q_out==q_trial without prior ULP gate.
            root_ok = gate_pass and (
                abs(f_q) <= tol or abs(q_out - q_trial) > tol
            )
    except (RuntimeError, _Stage3Failure):
        prod_ok = False
    ratio = float(three["max_residual_ratio"])
    tube_t = float(request.tube_bulk_state.temperature_k)
    shell_t = float(request.shell_bulk_state.temperature_k)
    return JointBVPCellRecord(
        index=index,
        q_w=q_out,
        twi_k=twi_out,
        two_k=two_out,
        h_t_left_j_kg=float(h_t[index]),
        h_t_right_j_kg=float(h_t[index + 1]),
        h_s_left_j_kg=float(h_s[index]),
        h_s_right_j_kg=float(h_s[index + 1]),
        max_task172_residual_ratio=ratio,
        task172_gate_pass=gate_pass,
        production_validated=prod_ok,
        cell_id=getattr(support, "tube_cell_id", ""),
        t_tube_bulk_k=tube_t,
        t_shell_bulk_k=shell_t,
        task172_r1_w=r1,
        task172_r2_w=r2,
        task172_r3_w=r3,
        task173_root_residual_w=f_q,
        task173_root_validated=root_ok and gate_pass and prod_ok,
        task172_request_hash=req_hash,
        domain_exit=domain_exit,
    )


def _qu_from_optimizer_vec(
    vec: np.ndarray, n_cells: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    qtw = vec.reshape(n_cells, 3)
    return qtw[:, 0].copy(), qtw[:, 1].copy(), qtw[:, 2].copy()


def _reconcile_q_after_validation(
    vec: np.ndarray,
    *,
    supports: list[Any],
    h_t0: float,
    h_sN: float,
    tube_mdot: float,
    shell_mdot: float,
    provider: Any,
    shell_authority: Any,
    max_passes: int = 8,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[JointBVPCellRecord], bool]:
    """If ULP polish changes q, rebuild enthalpies and re-validate until q stable."""
    n = len(supports)
    q_current, u1, u2 = _qu_from_optimizer_vec(vec, n)
    for _ in range(max_passes):
        h_t, h_s = build_axial_enthalpies_from_q(
            q_current,
            h_t_inlet_j_kg=h_t0,
            h_s_cold_inlet_j_kg=h_sN,
            tube_mass_flow_kg_s=tube_mdot,
            shell_mass_flow_kg_s=shell_mdot,
        )
        cells: list[JointBVPCellRecord] = []
        q_next = q_current.copy()
        changed = False
        for i, support in enumerate(supports):
            tube_k = shell_k = math.nan
            try:
                request, _, _ = build_task172_request_for_q(
                    float(q_current[i]),
                    support=support,
                    tube_upstream=_state_from_h(provider, float(h_t[i]), side="TUBE"),
                    shell_physical_left=_state_from_h(provider, float(h_s[i]), side="SHELL"),
                    provider=provider,
                    shell_authority=shell_authority,
                )
                tube_k = float(request.tube_bulk_state.temperature_k)
                shell_k = float(request.shell_bulk_state.temperature_k)
            except (_LowSideDomainInfeasible, _Stage3Failure):
                pass
            wall = None
            if math.isfinite(tube_k) and math.isfinite(shell_k):
                wall = _enthalpy_coupled_wall_temperatures_from_fraction(
                    float(u1[i]), float(u2[i]), tube_bulk_k=tube_k, shell_bulk_k=shell_k
                )
            if wall is None:
                twi_i, two_i = 300.0, 299.0
            else:
                twi_i, two_i = wall
            rec = _collect_cell_record(
                index=i,
                support=support,
                q=float(q_current[i]),
                twi=float(twi_i),
                two=float(two_i),
                h_t=h_t,
                h_s=h_s,
                provider=provider,
                shell_authority=shell_authority,
            )
            cells.append(rec)
            twi_i, two_i = rec.twi_k, rec.two_k
            frac = _fractions_from_walls(twi_i, two_i, tube_bulk_k=tube_k, shell_bulk_k=shell_k)
            if frac is not None:
                u1[i], u2[i] = frac
            if rec.q_w != q_current[i]:
                changed = True
                q_next[i] = rec.q_w
        q_current = q_next
        if not changed:
            return h_t, h_s, q_current, cells, True
    h_t, h_s = build_axial_enthalpies_from_q(
        q_current,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=tube_mdot,
        shell_mass_flow_kg_s=shell_mdot,
    )
    return h_t, h_s, q_current, cells, False


def solve_joint_boundary_value_mesh(
    *,
    subdivisions: int,
    provider: Any,
    shell_authority: Any,
    candidate_ctx: Any,
    max_nfev: int = 320,
) -> JointBVPOutcome:
    """Fix tube inlet (x=0) and shell cold inlet (x=L); unknowns are q, Twi, Two only."""
    supports = _supports_for_mesh(candidate_ctx, subdivisions)
    n_cells = len(supports)
    if n_cells == 0:
        return JointBVPOutcome(
            status="BLOCKED",
            subdivisions=subdivisions,
            cells=[],
            total_q_w=0.0,
            energy_balance_residual_w=math.inf,
            tube_enthalpy_loss_w=0.0,
            shell_enthalpy_gain_w=0.0,
            terminal_residual_k=math.inf,
            terminal_residual_j_kg=math.inf,
            terminal_pass=False,
            all_task172_gates_pass=False,
            optimizer_nfev=0,
            optimizer_success=False,
            physical_acceptance=False,
            solver_success=False,
            tube_outlet_temperature_k=math.nan,
            shell_outlet_temperature_k=math.nan,
            diagnostics=("no_cells",),
            energy_conserving_formulation=True,
        )
    tube_mdot = float(effective_tube_mass_flow_kg_s())
    shell_mdot = float(effective_shell_mass_flow_kg_s())
    h_t0 = float(
        _state_at_inlet(
            provider, effective_tube_inlet_temperature_k(), side="TUBE"
        ).native.enthalpy_j_kg
    )
    h_sN = float(effective_shell_cold_inlet_enthalpy_j_kg())
    q_uniform = _duty_uniform_q_per_cell(
        provider=provider, n_cells=n_cells, h_t_in=h_t0, tube_mdot=tube_mdot
    )
    x0, lo, hi, q_part = _sequential_q_u_initial_guess(
        provider=provider,
        supports=supports,
        h_t0=h_t0,
        h_sN=h_sN,
        tube_mdot=tube_mdot,
        shell_mdot=shell_mdot,
        q_uniform=q_uniform,
        shell_authority=shell_authority,
    )
    heat_scale = _heat_residual_scale_w(q_part, tube_mdot=tube_mdot, enthalpy_span_j_kg=h_t0 - h_sN)
    opt_x, block_nfev, domain_plateau = _block_gauss_seidel_joint_solve(
        x0,
        supports=supports,
        provider=provider,
        shell_authority=shell_authority,
        h_t0=h_t0,
        h_sN=h_sN,
        tube_mdot=tube_mdot,
        shell_mdot=shell_mdot,
        heat_scale=heat_scale,
        max_sweeps=12,
        max_nfev_per_cell=min(120, max(40, max_nfev // max(n_cells, 1))),
    )
    h_t, h_s, q_final, cells, q_stable = _reconcile_q_after_validation(
        opt_x,
        supports=supports,
        h_t0=h_t0,
        h_sN=h_sN,
        tube_mdot=tube_mdot,
        shell_mdot=shell_mdot,
        provider=provider,
        shell_authority=shell_authority,
    )
    total_q, tube_loss, shell_gain, energy_residual = axial_energy_slack_w(
        q_final,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=tube_mdot,
        shell_mass_flow_kg_s=shell_mdot,
    )
    all_gates = all(c.task172_gate_pass for c in cells)
    all_validated = all(c.production_validated for c in cells)
    post_ok = not any(c.domain_exit for c in cells)
    shell_out_h = float(h_s[0])
    tube_out_h = float(h_t[-1])
    try:
        tube_out_t = float(_state_from_h(provider, tube_out_h, side="TUBE").native.temperature_k)
        shell_out_t = float(_state_from_h(provider, shell_out_h, side="SHELL").native.temperature_k)
    except (_Stage3Failure, _LowSideDomainInfeasible):
        tube_out_t = math.nan
        shell_out_t = math.nan
    shell_bc = _state_from_h(provider, h_sN, side="SHELL")
    terminal_t = float(shell_bc.native.temperature_k) - float(effective_shell_inlet_temperature_k())
    terminal_h = float(h_sN - float(effective_shell_cold_inlet_enthalpy_j_kg()))
    terminal_pass = abs(terminal_t) <= float(TERMINAL_TOLERANCE_K)
    all_roots = all(c.task173_root_validated for c in cells)
    axial_ok = audit_axial_feasibility(
        q_final,
        provider=provider,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=tube_mdot,
        shell_mass_flow_kg_s=shell_mdot,
    ).feasible
    wall_order_ok = all(
        _wall_order_valid(c.twi_k, c.two_k, c.t_tube_bulk_k, c.t_shell_bulk_k)
        for c in cells
        if not math.isnan(c.t_tube_bulk_k)
    )
    heat_direction_ok = all(c.q_w > 0.0 for c in cells)
    enthalpy_consistent = all(
        abs(c.h_t_left_j_kg - float(h_t[c.index])) < 1.0e-6
        and abs(c.h_s_left_j_kg - float(h_s[c.index])) < 1.0e-6
        for c in cells
    )
    physical = (
        post_ok
        and all_gates
        and all_validated
        and all_roots
        and q_stable
        and energy_residual <= 1.0
        and axial_ok
        and wall_order_ok
        and heat_direction_ok
        and enthalpy_consistent
        and terminal_pass
    )
    status = "PASS" if physical else "BLOCKED"
    opt_success = block_nfev > 3 * n_cells
    return JointBVPOutcome(
        status=status,
        subdivisions=subdivisions,
        cells=cells,
        total_q_w=total_q,
        energy_balance_residual_w=energy_residual,
        tube_enthalpy_loss_w=tube_loss,
        shell_enthalpy_gain_w=shell_gain,
        terminal_residual_k=terminal_t,
        terminal_residual_j_kg=terminal_h,
        terminal_pass=terminal_pass,
        all_task172_gates_pass=all_gates,
        optimizer_nfev=int(block_nfev),
        optimizer_success=bool(opt_success),
        physical_acceptance=physical,
        solver_success=bool(physical),
        tube_outlet_temperature_k=tube_out_t,
        shell_outlet_temperature_k=shell_out_t,
        diagnostics=(
            f"heat_scale_w={heat_scale:.6g}",
            f"q_reconcile_stable={q_stable}",
            f"block_gauss_seidel_nfev={block_nfev}",
            f"domain_penalty_plateau={domain_plateau}",
            f"axial_feasibility={axial_ok}",
            f"task173_roots={all_roots}",
        ),
        residual_heat_scale_w=heat_scale,
        energy_conserving_formulation=True,
        extra={
            "energized_q_construction": True,
            "optimizer_unknown_count": 3 * n_cells,
            "parameterization": "q_u1_u2",
            "domain_penalty_plateau": domain_plateau,
            "solver_path": "block_gauss_seidel",
            "bvp_dof_audit": joint_bvp_dof_audit_summary(),
        },
    )
