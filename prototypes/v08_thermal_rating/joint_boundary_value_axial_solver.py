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
    _build_candidate_local_support,
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
    build_closure_primitives,
    build_task172_request_for_q,
    evaluate_three_equation_residuals,
)

_DOMAIN_VIOLATION_SCALE = 1.0e3


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


def _trf_cell_triple_warm_start(
    *,
    q_guess: float,
    support: Any,
    tube_up: Any,
    shell_left: Any,
    provider: Any,
    shell_authority: Any,
) -> tuple[float, float, float]:
    try:
        request, _, _ = build_task172_request_for_q(
            q_guess,
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
    except _LowSideDomainInfeasible:
        return (
            q_guess,
            float(tube_up.native.temperature_k) - 1.0,
            float(shell_left.native.temperature_k) + 1.0,
        )
    outcome = attempt_frozen_bulk_direct_trf_recovery(request, provider)
    if getattr(outcome, "status", None) != "VALIDATED":
        twi = float(request.tube_bulk_state.temperature_k) - 1.0
        two = float(request.shell_bulk_state.temperature_k) + 1.0
        return q_guess, twi, two
    return (
        float(outcome.signed_q_hot_to_cold_w),  # type: ignore[union-attr]
        float(outcome.wall_temperature_inner_k),  # type: ignore[union-attr]
        float(outcome.wall_temperature_outer_k),  # type: ignore[union-attr]
    )


def _qtw_initial_guess(
    *,
    provider: Any,
    supports: list[Any],
    h_t: np.ndarray,
    h_s: np.ndarray,
    q_uniform: float,
    shell_authority: Any,
) -> np.ndarray:
    n = len(supports)
    out = np.zeros(3 * n, dtype=float)
    for i, support in enumerate(supports):
        tube_up = _state_from_h(provider, float(h_t[i]), side="TUBE")
        shell_left = _state_from_h(provider, float(h_s[i]), side="SHELL")
        q_w, twi, two = _trf_cell_triple_warm_start(
            q_guess=q_uniform,
            support=support,
            tube_up=tube_up,
            shell_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
        out[3 * i : 3 * i + 3] = (q_w, twi, two)
    return out


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
    q_out = q
    twi_out = twi
    two_out = two
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
    except (RuntimeError, _Stage3Failure):
        prod_ok = False
    ratio = float(three["max_residual_ratio"])
    root_residual = abs(r1) + abs(r2) + abs(r3)
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
        task173_root_residual_w=root_residual,
        task173_root_validated=gate_pass and prod_ok,
        task172_request_hash=req_hash,
        domain_exit=domain_exit,
    )


def _reconcile_q_after_validation(
    q_vec: np.ndarray,
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
    q_current = np.asarray(q_vec[:n], dtype=float)
    twi = q_vec[n : 2 * n].copy()
    two = q_vec[2 * n : 3 * n].copy()
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
            rec = _collect_cell_record(
                index=i,
                support=support,
                q=float(q_current[i]),
                twi=float(twi[i]),
                two=float(two[i]),
                h_t=h_t,
                h_s=h_s,
                provider=provider,
                shell_authority=shell_authority,
            )
            cells.append(rec)
            twi[i] = rec.twi_k
            two[i] = rec.two_k
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
    q_seed = np.full(n_cells, q_uniform, dtype=float)
    h_t_seed, h_s_seed = build_axial_enthalpies_from_q(
        q_seed,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=tube_mdot,
        shell_mass_flow_kg_s=shell_mdot,
    )
    q_block = _qtw_initial_guess(
        provider=provider,
        supports=supports,
        h_t=h_t_seed,
        h_s=h_s_seed,
        q_uniform=q_uniform,
        shell_authority=shell_authority,
    )
    q_part = q_block[: n_cells * 3 : 3]
    x0 = q_block.copy()
    heat_scale = _heat_residual_scale_w(q_part, tube_mdot=tube_mdot, enthalpy_span_j_kg=h_t0 - h_sN)

    lo = np.tile(np.asarray([0.0, 280.0, 280.0], dtype=float), n_cells)
    hi = np.tile(np.asarray([1.0e7, 400.0, 400.0], dtype=float), n_cells)

    def residual(vec: np.ndarray) -> np.ndarray:
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
            return np.full(3 * n_cells, _DOMAIN_VIOLATION_SCALE, dtype=float)
        local_scale = _heat_residual_scale_w(
            q_vals, tube_mdot=tube_mdot, enthalpy_span_j_kg=h_t0 - h_sN
        )
        res: list[float] = []
        for i, support in enumerate(supports):
            q, twi, two = (float(v) for v in qtw[i])
            if q < 0.0:
                res.extend((-_DOMAIN_VIOLATION_SCALE,) * 3)
                continue
            try:
                tube_up = _state_from_h(provider, float(h_t[i]), side="TUBE")
                shell_left = _state_from_h(provider, float(h_s[i]), side="SHELL")
            except (_Stage3Failure, _LowSideDomainInfeasible):
                res.extend((-_DOMAIN_VIOLATION_SCALE,) * 3)
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
                res.extend((-_DOMAIN_VIOLATION_SCALE,) * 3)
                continue
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
        ftol=1e-8,
        xtol=1e-10,
        max_nfev=max_nfev,
    )
    final_residual = residual(opt.x)
    qtw = opt.x.reshape(n_cells, 3)
    q_vec = np.concatenate([qtw[:, 0], qtw[:, 1], qtw[:, 2]])
    h_t, h_s, q_final, cells, q_stable = _reconcile_q_after_validation(
        q_vec,
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
        ),
        residual_heat_scale_w=heat_scale,
        energy_conserving_formulation=True,
        extra={
            "energized_q_construction": True,
            "optimizer_unknown_count": 3 * n_cells,
        },
    )
