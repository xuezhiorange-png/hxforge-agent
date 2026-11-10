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
)


def _task173_root_tolerance_w(q_w: float) -> float:
    q_scale = max(abs(float(q_w)), 1.0)
    return max(1.0e-6, q_scale * 2.0e-8)


def _per_cell_thermodynamic_q_cap_w(
    *,
    h_t_face_j_kg: float,
    h_s_face_j_kg: float,
    tube_mdot: float,
    shell_mdot: float,
) -> float:
    h_min = float(_effective_h_min_j_kg())
    tube_cap = tube_mdot * (h_t_face_j_kg - h_min)
    shell_cap = shell_mdot * (h_s_face_j_kg - h_min)
    return max(0.0, min(tube_cap, shell_cap))


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
    tube_mdot: float,
    shell_mdot: float,
) -> tuple[bool, float]:
    h_min = float(_effective_h_min_j_kg())
    tube_down = h_t_left - q_w / tube_mdot
    shell_next = h_s_left - q_w / shell_mdot
    viol = 0.0
    if tube_down < h_min:
        viol = max(viol, h_min - tube_down)
    if shell_next < h_min:
        viol = max(viol, h_min - shell_next)
    return viol <= 0.0, viol


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
        q_cap = _per_cell_thermodynamic_q_cap_w(
            h_t_face_j_kg=float(h_t[i]),
            h_s_face_j_kg=float(h_s[i]),
            tube_mdot=tube_mdot,
            shell_mdot=shell_mdot,
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
            root_ok = abs(f_q) <= tol
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
    domain_plateau = False

    def residual(vec: np.ndarray) -> np.ndarray:
        nonlocal domain_plateau
        qtw = vec.reshape(n_cells, 3)
        q_vals = qtw[:, 0]
        try:
            h_t, h_s = build_axial_enthalpies_from_q(
                q_vals,
                h_t_inlet_j_kg=h_t0,
                h_s_cold_inlet_j_kg=h_sN,
                tube_mass_flow_kg_s=tube_mdot,
                shell_mass_flow_kg_s=shell_mdot,
            )
        except ValueError:
            domain_plateau = True
            v = _domain_violation_triplet(1.0e4, scale=heat_scale)
            return np.tile(np.asarray(v, dtype=float), n_cells)
        local_scale = _heat_residual_scale_w(
            q_vals, tube_mdot=tube_mdot, enthalpy_span_j_kg=h_t0 - h_sN
        )
        res: list[float] = []
        for i, support in enumerate(supports):
            q, u1, u2 = (float(v) for v in qtw[i])
            if q < 0.0 or q > float(hi[3 * i]) * 1.0001:
                v = _domain_violation_triplet(abs(q) + 1.0, scale=local_scale)
                res.extend(v)
                domain_plateau = True
                continue
            ok, viol = _enthalpy_step_feasible(
                q_w=q,
                h_t_left=float(h_t[i]),
                h_s_left=float(h_s[i]),
                tube_mdot=tube_mdot,
                shell_mdot=shell_mdot,
            )
            if not ok:
                v = _domain_violation_triplet(viol, scale=local_scale)
                res.extend(v)
                domain_plateau = True
                continue
            try:
                tube_up = _state_from_h(provider, float(h_t[i]), side="TUBE")
                shell_left = _state_from_h(provider, float(h_s[i]), side="SHELL")
            except (_Stage3Failure, _LowSideDomainInfeasible):
                v = _domain_violation_triplet(1.0e3, scale=local_scale)
                res.extend(v)
                domain_plateau = True
                continue
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
                v = _domain_violation_triplet(1.0e3, scale=local_scale)
                res.extend(v)
                domain_plateau = True
                continue
            tube_k = float(request.tube_bulk_state.temperature_k)
            shell_k = float(request.shell_bulk_state.temperature_k)
            wall = _enthalpy_coupled_wall_temperatures_from_fraction(
                u1, u2, tube_bulk_k=tube_k, shell_bulk_k=shell_k
            )
            if wall is None:
                v = _domain_violation_triplet(max(tube_k - shell_k, 1.0), scale=local_scale)
                res.extend(v)
                domain_plateau = True
                continue
            twi, two = wall
            prim = build_closure_primitives(request, provider)
            gate = evaluate_three_equation_residuals(
                q, twi, two, request=request, provider=provider, primitives=prim
            )
            for r in gate["residuals_w"]:
                res.append(float(r) / local_scale)
        return np.asarray(res, dtype=float)

    opt = least_squares(
        residual,
        x0,
        bounds=(lo, hi),
        method="trf",
        ftol=1e-15,
        xtol=1e-12,
        gtol=1e-15,
        max_nfev=max_nfev,
    )
    final_residual = residual(opt.x)
    h_t, h_s, q_final, cells, q_stable = _reconcile_q_after_validation(
        opt.x,
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
    residual_ok = float(np.linalg.norm(final_residual)) < 1.0
    physical = (
        post_ok
        and all_gates
        and all_validated
        and q_stable
        and energy_residual <= 1.0
        and residual_ok
    )
    status = "PASS" if physical and opt.success else "BLOCKED"
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
        optimizer_nfev=int(opt.nfev),
        optimizer_success=bool(opt.success),
        physical_acceptance=physical,
        solver_success=bool(opt.success),
        tube_outlet_temperature_k=tube_out_t,
        shell_outlet_temperature_k=shell_out_t,
        diagnostics=(
            f"residual_norm={float(np.linalg.norm(final_residual)):.6g}",
            f"optimizer_cost={float(opt.cost):.6g}",
            f"heat_scale_w={heat_scale:.6g}",
            f"q_reconcile_stable={q_stable}",
            f"trf_status={opt.status!s}",
            f"trf_message={str(opt.message)[:120]}",
            f"domain_penalty_plateau={domain_plateau}",
        ),
        residual_heat_scale_w=heat_scale,
        energy_conserving_formulation=True,
        extra={
            "energized_q_construction": True,
            "optimizer_unknown_count": 3 * n_cells,
            "parameterization": "q_u1_u2",
            "domain_penalty_plateau": domain_plateau,
        },
    )
