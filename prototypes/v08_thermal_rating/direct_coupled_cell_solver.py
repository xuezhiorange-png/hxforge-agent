"""Isolated direct coupled cell closure experiments (not production Task173 root search)."""

from __future__ import annotations

import math
from decimal import Decimal, localcontext
from typing import Any, Literal

import numpy as np
from scipy.optimize import least_squares

from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    Task172BlockedResult,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.service import validate_request
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _cell_evaluation,
    _CellEvaluation,
    _d,
    _LowSideDomainInfeasible,
    _Stage3Failure,
    _Task172NumericalHole,
)

ProbeClassification = Literal[
    "VALID_CONSTITUTIVE",
    "NUMERICAL_HOLE_PRODUCTION_RETRY_ACCEPTED",
    "NUMERICAL_HOLE_PRODUCTION_RETRY_BLOCKED",
    "LOW_SIDE_DOMAIN_INFEASIBLE",
    "HARD_BLOCKER",
]


def physical_q_upper_w(
    *,
    tube_upstream: Any,
    shell_physical_left: Any,
) -> float:
    from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173

    h_tube = _d(tube_upstream.native.enthalpy_j_kg)
    h_shell = _d(shell_physical_left.native.enthalpy_j_kg)
    h_min = t173._effective_h_min_j_kg()
    with localcontext() as ctx:
        ctx.prec = 70
        tube_cap = t173.effective_tube_mass_flow_kg_s() * (h_tube - h_min)
        shell_cap = t173.effective_shell_mass_flow_kg_s() * (h_shell - h_min)
    cap = min(tube_cap, shell_cap)
    if cap <= 0:
        return 0.0
    upper = float(cap)
    for _ in range(8):
        q_decimal = Decimal(str(upper))
        with localcontext() as ctx:
            ctx.prec = 70
            tube_h = h_tube - q_decimal / t173.effective_tube_mass_flow_kg_s()
            shell_h = h_shell - q_decimal / t173.effective_shell_mass_flow_kg_s()
        if tube_h >= h_min and shell_h >= h_min:
            break
        upper = math.nextafter(upper, 0.0)
    return upper


def _enthalpy_balance_check(
    evaluation: _CellEvaluation,
    q_w: float,
    *,
    tube_upstream: Any,
    shell_physical_left: Any,
) -> dict[str, str]:
    from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173

    q = _d(q_w)
    mdot_t = t173.effective_tube_mass_flow_kg_s()
    mdot_s = t173.effective_shell_mass_flow_kg_s()
    h_t_in = _d(tube_upstream.native.enthalpy_j_kg)
    h_s_in = _d(shell_physical_left.native.enthalpy_j_kg)
    h_t_out = h_t_in - q / mdot_t
    h_s_out = h_s_in - q / mdot_s
    return {
        "tube_enthalpy_drop_j_kg": str(h_t_in - h_t_out),
        "shell_enthalpy_drop_j_kg": str(h_s_in - h_s_out),
        "q_implied_w": str(q),
        "task172_q_w": str(evaluation.task172_result.signed_q_hot_to_cold_w),
    }


def probe_q_direct_coupled(
    q_w: float,
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: Any,
    shell_authority: Any,
) -> dict[str, Any]:
    """One q probe using production Task172 path; holes are not valid F(q)."""
    record: dict[str, Any] = {"q_trial_w": q_w}
    try:
        evaluation: _CellEvaluation = _cell_evaluation(
            q_w,
            support=support,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
            shell_authority=shell_authority,
        )
    except _LowSideDomainInfeasible:
        record["classification"] = "LOW_SIDE_DOMAIN_INFEASIBLE"
        return record
    except _Task172NumericalHole as hole:
        record["classification"] = "NUMERICAL_HOLE"
        record["task172_request_hash"] = hole.request_hash
        record["blocked_result_hash"] = hole.blocked_result_hash
        if hole.task172_request is not None:
            outcome = validate_request(hole.task172_request, provider)
            if type(outcome) is Task172LocalResult:
                record["production_retry_classification"] = (
                    "NUMERICAL_HOLE_PRODUCTION_RETRY_ACCEPTED"
                )
                record["signed_q_hot_to_cold_w"] = str(outcome.signed_q_hot_to_cold_w)
                record["task172_result_hash"] = outcome.result_hash
                record["f_q_w"] = str(Decimal(str(q_w)) - outcome.signed_q_hot_to_cold_w)
            elif type(outcome) is Task172BlockedResult:
                record["production_retry_classification"] = (
                    "NUMERICAL_HOLE_PRODUCTION_RETRY_BLOCKED"
                )
                record["production_retry_failure_code"] = outcome.failure_code
        return record
    except _Stage3Failure as exc:
        record["classification"] = "HARD_BLOCKER"
        record["failure_code"] = exc.code
        return record

    q172 = evaluation.task172_result.signed_q_hot_to_cold_w
    f_q = Decimal(str(q_w)) - q172
    record.update(
        {
            "classification": "VALID_CONSTITUTIVE",
            "task172_request_hash": evaluation.task172_result.request_hash,
            "task172_result_hash": evaluation.task172_result.result_hash,
            "signed_q_hot_to_cold_w": str(q172),
            "f_q_w": str(f_q),
            "enthalpy_balance": _enthalpy_balance_check(
                evaluation,
                q_w,
                tube_upstream=tube_upstream,
                shell_physical_left=shell_physical_left,
            ),
        }
    )
    return record


def scan_q_direct_coupled(
    q_points: list[float],
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: Any,
    shell_authority: Any,
) -> list[dict[str, Any]]:
    return [
        probe_q_direct_coupled(
            q,
            support=support,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
            shell_authority=shell_authority,
        )
        for q in sorted(set(q_points))
    ]


def attempt_joint_q_twi_two_closure(
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: Any,
    shell_authority: Any,
    q_upper: float,
    q_seed: float,
    max_nfev: int = 48,
) -> dict[str, Any]:
    """Search (q, u1, u2) for duty balance; independent acceptance must pass validate_request."""
    if q_upper <= 0:
        return {"status": "BLOCKED", "reason": "non_positive_q_upper"}

    def duty_residual(vec: np.ndarray) -> np.ndarray:
        q = float(vec[0])
        if q < 0.0 or q > q_upper:
            return np.asarray([10.0, 1.0, 1.0], dtype=float)
        probe = probe_q_direct_coupled(
            q,
            support=support,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
            shell_authority=shell_authority,
        )
        if probe.get("classification") == "VALID_CONSTITUTIVE" and probe.get("f_q_w") is not None:
            f_q = float(probe["f_q_w"])
            return np.asarray([f_q / max(abs(q), 1.0), 0.0, 0.0], dtype=float)
        return np.asarray([1.0, 1.0, 1.0], dtype=float)

    x0 = np.asarray([min(max(q_seed, 0.0), q_upper), 0.35, 0.35], dtype=float)
    result = least_squares(
        duty_residual,
        x0,
        bounds=([0.0, 0.0, 0.0], [q_upper, 1.0, 1.0]),
        method="trf",
        ftol=1e-10,
        xtol=1e-12,
        max_nfev=max_nfev,
    )
    q_final = float(result.x[0])
    final_probe = probe_q_direct_coupled(
        q_final,
        support=support,
        tube_upstream=tube_upstream,
        shell_physical_left=shell_physical_left,
        provider=provider,
        shell_authority=shell_authority,
    )
    accepted = False
    if final_probe.get("classification") == "VALID_CONSTITUTIVE":
        f_abs = abs(float(final_probe.get("f_q_w", "999")))
        accepted = f_abs <= max(1e-6, abs(q_final) * 2e-8)
    return {
        "optimizer_success": bool(result.success),
        "optimizer_nfev": int(result.nfev),
        "optimizer_cost": float(result.cost),
        "q_final_w": q_final,
        "final_probe": final_probe,
        "duty_closure_within_cell_tolerance": accepted,
        "task172_acceptance_at_solution": accepted
        and final_probe.get("classification") == "VALID_CONSTITUTIVE",
    }
