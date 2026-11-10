"""Joint (enthalpy + q + Twi + Two) axial BVP PoC — isolated from production Task173 outer shooting."""
# ruff: noqa: E402, E501

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

import numpy as np
from scipy.optimize import least_squares

from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    attempt_frozen_bulk_direct_trf_recovery,
    build_validated_local_result_from_verified_trial_triple,
    eval_trial_residual_gate,
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

_DOMAIN_PENALTY = 1e3


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


@dataclass
class JointBVPOutcome:
    status: str
    subdivisions: int
    cells: list[JointBVPCellRecord]
    total_q_w: float
    energy_balance_residual_w: float
    terminal_residual_k: float
    terminal_residual_j_kg: float
    terminal_pass: bool
    all_task172_gates_pass: bool
    optimizer_nfev: int
    optimizer_success: bool
    diagnostics: tuple[str, ...]


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


def _duty_scaled_q_per_cell(
    *,
    provider: Any,
    n_cells: int,
    h_t_in: float,
    tube_mdot: Decimal,
) -> float:
    t_tube = float(effective_tube_inlet_temperature_k())
    t_shell = float(effective_shell_inlet_temperature_k())
    t_tube_out = t_tube - 0.35 * (t_tube - t_shell)
    h_t_out = float(_state_at_inlet(provider, t_tube_out, side="TUBE").native.enthalpy_j_kg)
    total_q = max(float(tube_mdot) * (h_t_in - h_t_out), 1.0)
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


def _algebraic_profile_seed(
    *,
    provider: Any,
    n_cells: int,
    h_t_in: float,
    h_s_in_terminal: float,
    tube_mdot: Decimal,
    shell_mdot: Decimal,
    supports: list[Any],
    shell_authority: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    q_guess = _duty_scaled_q_per_cell(
        provider=provider, n_cells=n_cells, h_t_in=h_t_in, tube_mdot=tube_mdot
    )
    h_t = np.linspace(h_t_in, h_t_in - q_guess * n_cells / float(tube_mdot), n_cells + 1)
    h_s = np.linspace(
        h_s_in_terminal + q_guess * n_cells / float(shell_mdot),
        h_s_in_terminal,
        n_cells + 1,
    )
    q_block = np.zeros(3 * n_cells, dtype=float)
    for i in range(n_cells):
        tube_up = _state_from_h(provider, h_t[i], side="TUBE")
        shell_left = _state_from_h(provider, h_s[i], side="SHELL")
        q_w, twi, two = _trf_cell_triple_warm_start(
            q_guess=q_guess,
            support=supports[i],
            tube_up=tube_up,
            shell_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
        q_block[3 * i : 3 * i + 3] = (q_w, twi, two)
        h_t[i + 1] = h_t[i] - q_w / float(tube_mdot)
        h_s[i + 1] = h_s[i] - q_w / float(shell_mdot)
    return h_t[1:], h_s[:-1], q_block


def solve_joint_boundary_value_mesh(
    *,
    subdivisions: int,
    provider: Any,
    shell_authority: Any,
    candidate_ctx: Any,
    max_nfev: int = 320,
) -> JointBVPOutcome:
    """Fix tube inlet (x=0) and shell cold inlet (x=L); solve enthalpy + (q,Twi,Two) jointly."""
    supports = _supports_for_mesh(candidate_ctx, subdivisions)
    n_cells = len(supports)
    if n_cells == 0:
        return JointBVPOutcome(
            status="BLOCKED",
            subdivisions=subdivisions,
            cells=[],
            total_q_w=0.0,
            energy_balance_residual_w=math.inf,
            terminal_residual_k=math.inf,
            terminal_residual_j_kg=math.inf,
            terminal_pass=False,
            all_task172_gates_pass=False,
            optimizer_nfev=0,
            optimizer_success=False,
            diagnostics=("no_cells",),
        )
    tube_mdot = effective_tube_mass_flow_kg_s()
    shell_mdot = effective_shell_mass_flow_kg_s()
    h_t0 = float(
        _state_at_inlet(
            provider, effective_tube_inlet_temperature_k(), side="TUBE"
        ).native.enthalpy_j_kg
    )
    h_sN = float(effective_shell_cold_inlet_enthalpy_j_kg())
    h_t_tail, h_s_head, q_block = _algebraic_profile_seed(
        provider=provider,
        n_cells=n_cells,
        h_t_in=h_t0,
        h_s_in_terminal=h_sN,
        tube_mdot=tube_mdot,
        shell_mdot=shell_mdot,
        supports=supports,
        shell_authority=shell_authority,
    )
    x0 = np.concatenate([h_t_tail, h_s_head, q_block])
    h_lo = min(h_t0, h_sN)
    h_hi = max(h_t0, h_sN)
    lo = np.concatenate(
        [
            np.full(n_cells, h_lo),
            np.full(n_cells, h_lo),
            np.tile(np.asarray([0.0, 280.0, 280.0], dtype=float), n_cells),
        ]
    )
    hi = np.concatenate(
        [
            np.full(n_cells, h_hi),
            np.full(n_cells, h_hi),
            np.tile(np.asarray([1e7, 400.0, 400.0], dtype=float), n_cells),
        ]
    )

    def residual(vec: np.ndarray) -> np.ndarray:
        h_t = [h_t0, *vec[0:n_cells]]
        h_s = [*vec[n_cells : 2 * n_cells], h_sN]
        qtw = vec[2 * n_cells :].reshape(n_cells, 3)
        res: list[float] = []
        for i, support in enumerate(supports):
            q, twi, two = (float(v) for v in qtw[i])
            if q < 0.0:
                res.extend([_DOMAIN_PENALTY] * 5)
                continue
            try:
                tube_up = _state_from_h(provider, h_t[i], side="TUBE")
                shell_left = _state_from_h(provider, h_s[i], side="SHELL")
            except (_Stage3Failure, _LowSideDomainInfeasible):
                res.extend([_DOMAIN_PENALTY] * 5)
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
                res.extend([_DOMAIN_PENALTY] * 5)
                continue
            prim = build_closure_primitives(request, provider)
            gate = evaluate_three_equation_residuals(
                q, twi, two, request=request, provider=provider, primitives=prim
            )
            scale = max(abs(q), 1.0)
            for r, b in zip(gate["residuals_w"], gate["acceptance_bounds_w"], strict=True):
                res.append(float(r) / max(float(b), 1e-12))
            res.append((q - float(tube_mdot) * (h_t[i] - h_t[i + 1])) / scale)
            res.append((q - float(shell_mdot) * (h_s[i] - h_s[i + 1])) / scale)
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
    h_t = [h_t0, *opt.x[0:n_cells]]
    h_s = [*opt.x[n_cells : 2 * n_cells], h_sN]
    qtw = opt.x[2 * n_cells :].reshape(n_cells, 3)

    cells: list[JointBVPCellRecord] = []
    total_q = 0.0
    all_gates = True
    post_ok = True
    for i, support in enumerate(supports):
        q, twi, two = (float(v) for v in qtw[i])
        try:
            tube_up = _state_from_h(provider, h_t[i], side="TUBE")
            shell_left = _state_from_h(provider, h_s[i], side="SHELL")
            request, _, _ = build_task172_request_for_q(
                q,
                support=support,
                tube_upstream=tube_up,
                shell_physical_left=shell_left,
                provider=provider,
                shell_authority=shell_authority,
            )
        except (_LowSideDomainInfeasible, _Stage3Failure):
            all_gates = False
            post_ok = False
            cells.append(
                JointBVPCellRecord(
                    index=i,
                    q_w=q,
                    twi_k=twi,
                    two_k=two,
                    h_t_left_j_kg=h_t[i],
                    h_t_right_j_kg=h_t[i + 1],
                    h_s_left_j_kg=h_s[i],
                    h_s_right_j_kg=h_s[i + 1],
                    max_task172_residual_ratio=math.inf,
                    task172_gate_pass=False,
                    production_validated=False,
                )
            )
            continue
        gate = eval_trial_residual_gate(request, provider, q, twi, two)
        gate_pass = bool(gate and gate.get("passes_original_residual_gate"))
        if not gate_pass:
            all_gates = False
        prod_ok = False
        try:
            validated = build_validated_local_result_from_verified_trial_triple(
                request, provider, q, twi, two, polish_nextafter=True
            )
            prod_ok = hasattr(validated, "signed_q_hot_to_cold_w")
            if prod_ok:
                q = float(validated.signed_q_hot_to_cold_w)  # type: ignore[union-attr]
                twi = float(validated.wall_temperature_inner_k)  # type: ignore[union-attr]
                two = float(validated.wall_temperature_outer_k)  # type: ignore[union-attr]
                gate = eval_trial_residual_gate(request, provider, q, twi, two)
                gate_pass = bool(gate and gate.get("passes_original_residual_gate"))
        except (RuntimeError, _Stage3Failure):
            prod_ok = False
        ratio = float(gate["max_residual_ratio"]) if gate else math.inf
        cells.append(
            JointBVPCellRecord(
                index=i,
                q_w=q,
                twi_k=twi,
                two_k=two,
                h_t_left_j_kg=h_t[i],
                h_t_right_j_kg=h_t[i + 1],
                h_s_left_j_kg=h_s[i],
                h_s_right_j_kg=h_s[i + 1],
                max_task172_residual_ratio=ratio,
                task172_gate_pass=gate_pass,
                production_validated=prod_ok,
            )
        )
        total_q += q

    hot_loss = float(tube_mdot) * (h_t0 - h_t[-1])
    cold_gain = float(shell_mdot) * (h_s[0] - h_sN)
    energy_residual = max(
        abs(hot_loss - total_q), abs(cold_gain - total_q), abs(hot_loss - cold_gain)
    )
    shell_out = _state_from_h(provider, h_sN, side="SHELL")
    terminal_t = float(shell_out.native.temperature_k) - float(
        effective_shell_inlet_temperature_k()
    )
    terminal_h = float(h_sN - float(effective_shell_cold_inlet_enthalpy_j_kg()))
    terminal_pass = abs(terminal_t) <= float(TERMINAL_TOLERANCE_K)
    residual_ok = float(np.linalg.norm(final_residual)) < 1.0
    status = (
        "PASS"
        if post_ok and all_gates and terminal_pass and residual_ok and opt.success
        else "BLOCKED"
    )
    return JointBVPOutcome(
        status=status,
        subdivisions=subdivisions,
        cells=cells,
        total_q_w=total_q,
        energy_balance_residual_w=energy_residual,
        terminal_residual_k=terminal_t,
        terminal_residual_j_kg=terminal_h,
        terminal_pass=terminal_pass,
        all_task172_gates_pass=all_gates,
        optimizer_nfev=int(opt.nfev),
        optimizer_success=bool(opt.success),
        diagnostics=(
            f"residual_norm={float(np.linalg.norm(final_residual)):.6g}",
            f"optimizer_cost={float(opt.cost):.6g}",
        ),
    )
