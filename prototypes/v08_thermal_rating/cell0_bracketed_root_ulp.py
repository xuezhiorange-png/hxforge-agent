"""Cell 0 bracketed scalar roots and bounded ULP reachability (V08-03 PoC)."""
# ruff: noqa: E501

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import brentq

from hexagent.exchangers.shell_tube.task172_local_runtime.models import Task172LocalResult
from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    build_validated_local_result_from_verified_trial_triple,
    eval_trial_residual_gate,
)
from prototypes.v08_thermal_rating.true_three_equation_cell_coupling import (
    build_closure_primitives,
    evaluate_three_equation_residuals,
    solve_bvp_cell_u1_u2_trf,
    solve_bvp_cell_wall_eliminated_trf,
    wall_temperatures_from_tmid_k,
)


@dataclass
class TrialGateDetail:
    q_w: float
    twi_k: float
    two_k: float
    r1_w: float
    r2_w: float
    r3_w: float
    bound1_w: float
    bound2_w: float
    bound3_w: float
    ratio1: float
    ratio2: float
    ratio3: float
    max_ratio: float
    dominant_index: int
    gate_pass: bool
    domain_exit: str | None = None
    g_i_w_k: float = math.nan
    g_o_w_k: float = math.nan
    rwall_k_w: float = math.nan
    request_hash: str = ""


def production_trial_gate(
    q_w: float,
    twi_k: float,
    two_k: float,
    *,
    request: Any,
    provider: Any,
) -> TrialGateDetail | None:
    gate = eval_trial_residual_gate(request, provider, float(q_w), float(twi_k), float(two_k))
    if gate is None:
        return None
    r1, r2, r3 = (float(x) for x in gate["residuals_w"])
    b1, b2, b3 = (float(x) for x in gate["acceptance_bounds_w"])
    ratios = [
        abs(r1) / b1 if b1 > 0 else math.inf,
        abs(r2) / b2 if b2 > 0 else math.inf,
        abs(r3) / b3 if b3 > 0 else math.inf,
    ]
    dom = int(np.argmax(ratios))
    prim = build_closure_primitives(request, provider)
    ev = evaluate_three_equation_residuals(
        float(q_w),
        float(twi_k),
        float(two_k),
        request=request,
        provider=provider,
        primitives=prim,
    )
    return TrialGateDetail(
        q_w=float(q_w),
        twi_k=float(twi_k),
        two_k=float(two_k),
        r1_w=r1,
        r2_w=r2,
        r3_w=r3,
        bound1_w=b1,
        bound2_w=b2,
        bound3_w=b3,
        ratio1=ratios[0],
        ratio2=ratios[1],
        ratio3=ratios[2],
        max_ratio=max(ratios),
        dominant_index=dom,
        gate_pass=bool(gate.get("passes_original_residual_gate")),
        g_i_w_k=float(ev.get("g_i_w_per_k", math.nan)),
        g_o_w_k=float(ev.get("g_o_w_per_k", math.nan)),
        rwall_k_w=float(prim.wall_resistance_k_w),
    )


def _tmid_feasible_interval(
    q_w: float,
    *,
    tube_k: float,
    shell_k: float,
    rwall_k_w: float,
) -> tuple[float, float] | None:
    half = float(q_w) * float(rwall_k_w) / 2.0
    lo = shell_k + half
    hi = tube_k - half
    if not (math.isfinite(lo) and math.isfinite(hi) and lo < hi):
        return None
    margin = max(1.0e-9, 1.0e-6 * (hi - lo))
    return lo + margin, hi - margin


def _r1_at_tmid(
    tmid: float,
    *,
    q_w: float,
    request: Any,
    provider: Any,
) -> float:
    prim = build_closure_primitives(request, provider)
    rw = float(prim.wall_resistance_k_w)
    tube_k = float(request.tube_bulk_state.temperature_k)
    shell_k = float(request.shell_bulk_state.temperature_k)
    interval = _tmid_feasible_interval(q_w, tube_k=tube_k, shell_k=shell_k, rwall_k_w=rw)
    if interval is None:
        return math.nan
    lo, hi = interval
    if not (lo <= tmid <= hi):
        return math.nan
    twi, two = wall_temperatures_from_tmid_k(q_w, tmid, rwall_k_w=rw)
    if not (shell_k <= two <= twi <= tube_k):
        return math.nan
    gate = eval_trial_residual_gate(request, provider, float(q_w), twi, two)
    if gate is None:
        return math.nan
    return float(gate["residuals_w"][0])


def _scan_bracket(
    f: Callable[[float], float],
    lo: float,
    hi: float,
    *,
    n_samples: int = 72,
) -> tuple[float, float] | None:
    xs = np.linspace(lo, hi, n_samples)
    prev_x, prev_v = None, None
    for x in xs:
        v = f(float(x))
        if not math.isfinite(v):
            prev_x, prev_v = None, None
            continue
        if prev_v is not None and prev_v * v < 0.0:
            return float(prev_x), float(x)
        prev_x, prev_v = float(x), v
    return None


def solve_tmid_bracketed_r1_root(
    q_w: float,
    *,
    request: Any,
    provider: Any,
    tmid_seed: float | None = None,
) -> dict[str, Any]:
    """Scalar root for r1(Tmid) at fixed q with wall conduction identity."""
    prim = build_closure_primitives(request, provider)
    rw = float(prim.wall_resistance_k_w)
    tube_k = float(request.tube_bulk_state.temperature_k)
    shell_k = float(request.shell_bulk_state.temperature_k)
    interval = _tmid_feasible_interval(q_w, tube_k=tube_k, shell_k=shell_k, rwall_k_w=rw)
    if interval is None:
        return {"status": "BLOCKED", "reason": "tmid_interval_empty", "bracket_found": False}
    lo, hi = interval

    def f(tmid: float) -> float:
        return _r1_at_tmid(tmid, q_w=q_w, request=request, provider=provider)

    bracket = _scan_bracket(f, lo, hi)
    samples: list[dict[str, float]] = []
    if bracket is None:
        for x in np.linspace(lo, hi, 16):
            v = f(float(x))
            if math.isfinite(v):
                samples.append({"tmid": float(x), "r1_w": v})
        return {
            "status": "BLOCKED",
            "reason": "no_r1_sign_bracket",
            "bracket_found": False,
            "tmid_interval": [lo, hi],
            "samples": samples,
        }
    a, b = bracket
    try:
        tmid_root = float(brentq(f, a, b, maxiter=64, xtol=1.0e-12))
    except ValueError:
        return {
            "status": "BLOCKED",
            "reason": "brentq_r1_failed",
            "bracket_found": True,
            "bracket": [a, b],
        }
    twi, two = wall_temperatures_from_tmid_k(q_w, tmid_root, rwall_k_w=rw)
    detail = production_trial_gate(q_w, twi, two, request=request, provider=provider)
    return {
        "status": "SOLVED",
        "bracket_found": True,
        "bracket": [a, b],
        "tmid_k": tmid_root,
        "twi_k": twi,
        "two_k": two,
        "detail": detail,
    }


def solve_q_bracketed_r3_with_inner_r1(
    *,
    request_at_q: Callable[[float], Any],
    provider: Any,
    q_lo: float,
    q_hi: float,
    q_seed: float,
) -> dict[str, Any]:
    """Outer q root on r3; inner Tmid root on r1 per q trial."""

    def r3_scalar(q: float) -> float:
        if q < q_lo or q > q_hi:
            return math.nan
        try:
            request = request_at_q(q)
        except Exception:
            return math.nan
        inner = solve_tmid_bracketed_r1_root(q, request=request, provider=provider)
        if inner.get("status") != "SOLVED":
            return math.nan
        twi = float(inner["twi_k"])
        two = float(inner["two_k"])
        gate = eval_trial_residual_gate(request, provider, q, twi, two)
        if gate is None:
            return math.nan
        return float(gate["residuals_w"][2])

    bracket = _scan_bracket(r3_scalar, q_lo, q_hi)
    q_samples: list[dict[str, Any]] = []
    if bracket is None:
        for q in np.linspace(q_lo, q_hi, 20):
            v = r3_scalar(float(q))
            if math.isfinite(v):
                q_samples.append({"q_w": float(q), "r3_w": v})
        return {
            "status": "BLOCKED",
            "reason": "no_r3_sign_bracket",
            "bracket_found": False,
            "q_interval": [q_lo, q_hi],
            "samples": q_samples,
        }
    a, b = bracket
    try:
        q_root = float(brentq(lambda v: r3_scalar(v), a, b, maxiter=48, xtol=1.0e-9))
    except ValueError:
        return {
            "status": "BLOCKED",
            "reason": "brentq_r3_failed",
            "bracket_found": True,
            "bracket": [a, b],
        }
    request = request_at_q(q_root)
    inner = solve_tmid_bracketed_r1_root(q_root, request=request, provider=provider)
    if inner.get("status") != "SOLVED":
        return {"status": "BLOCKED", "reason": "inner_r1_after_q", "q_w": q_root, "inner": inner}
    twi, two = float(inner["twi_k"]), float(inner["two_k"])
    detail = production_trial_gate(q_root, twi, two, request=request, provider=provider)
    return {
        "status": "SOLVED",
        "bracket_found": True,
        "q_bracket": [a, b],
        "q_w": q_root,
        "tmid_k": inner["tmid_k"],
        "twi_k": twi,
        "two_k": two,
        "detail": detail,
        "inner": inner,
    }


def bounded_ulp_neighborhood_search(
    detail: TrialGateDetail,
    *,
    request_at_q: Callable[[float], Any],
    provider: Any,
    max_steps: int = 54,
) -> dict[str, Any]:
    """1-ULP neighbors on q,Twi,Two; minimize max ULP ratio (no bound relaxation)."""

    def trial(q: float, twi: float, two: float) -> TrialGateDetail | None:
        try:
            request = request_at_q(q)
        except Exception:
            return None
        return production_trial_gate(q, twi, two, request=request, provider=provider)

    def neighbors(v: float) -> tuple[float, ...]:
        return (
            v,
            math.nextafter(v, math.inf),
            math.nextafter(v, -math.inf),
        )

    start = detail
    best = start
    frontier: list[tuple[float, float, float, int]] = [(start.q_w, start.twi_k, start.two_k, 0)]
    visited: set[tuple[int, int, int]] = set()

    steps = 0
    while frontier and steps < max_steps:
        q, twi, two, depth = frontier.pop(0)
        k = (q, twi, two)
        if k in visited:
            continue
        visited.add(k)
        cur = trial(q, twi, two)
        steps += 1
        if cur is None:
            continue
        if cur.max_ratio < best.max_ratio:
            best = cur
        if cur.gate_pass or depth >= 2:
            continue
        for nq in neighbors(q):
            for nwi in neighbors(twi):
                for nwo in neighbors(two):
                    try:
                        req = request_at_q(nq)
                    except Exception:
                        continue
                    shell_k = float(req.shell_bulk_state.temperature_k)
                    tube_k = float(req.tube_bulk_state.temperature_k)
                    if not (shell_k <= nwo <= nwi <= tube_k):
                        continue
                    frontier.append((nq, nwi, nwo, depth + 1))
    return {
        "steps_evaluated": steps,
        "best": best,
        "improved": best.max_ratio < detail.max_ratio,
        "gate_pass": best.gate_pass,
    }


def production_validated_if_gate_passes(
    request: Any,
    provider: Any,
    q: float,
    twi: float,
    two: float,
) -> tuple[bool, str | None]:
    """Independent _eval_trial gate before accepting build_validated_local_result."""
    gate = eval_trial_residual_gate(request, provider, q, twi, two)
    if gate is None:
        return False, "eval_trial_none"
    if not gate.get("passes_original_residual_gate"):
        return False, "ulp_gate_blocked"
    outcome = build_validated_local_result_from_verified_trial_triple(
        request, provider, q, twi, two, polish_nextafter=True
    )
    if type(outcome) is not Task172LocalResult:
        return False, type(outcome).__name__
    if outcome.status != "VALIDATED":
        return False, str(outcome.status)
    return True, None


@dataclass
class Cell0ReachabilityReport:
    baseline: TrialGateDetail | None
    trf_u1_u2: dict[str, Any] = field(default_factory=dict)
    trf_tmid: dict[str, Any] = field(default_factory=dict)
    bracketed: dict[str, Any] = field(default_factory=dict)
    ulp_search: dict[str, Any] = field(default_factory=dict)
    ulp_best: TrialGateDetail | None = None
    numerical_decision: str = "C"
    remaining_blocker: str = ""


def run_cell0_bracketed_ulp_pipeline(
    *,
    request_at_q: Callable[[float], Any],
    provider: Any,
    q_cap: float,
    q_seed: float,
    baseline: tuple[float, float, float] | None = None,
) -> Cell0ReachabilityReport:
    report = Cell0ReachabilityReport(
        baseline=None, trf_u1_u2={}, trf_tmid={}, bracketed={}, ulp_search={}
    )
    if baseline is not None:
        q0, twi0, two0 = baseline
        try:
            req0 = request_at_q(q0)
            report.baseline = production_trial_gate(q0, twi0, two0, request=req0, provider=provider)
        except Exception:
            report.baseline = None
    report.trf_tmid = solve_bvp_cell_wall_eliminated_trf(
        request_at_q=request_at_q, provider=provider, q_upper=q_cap, q_seed=q_seed
    )
    report.trf_u1_u2 = solve_bvp_cell_u1_u2_trf(
        request_at_q=request_at_q, provider=provider, q_upper=q_cap, q_seed=q_seed
    )
    q_lo = max(0.0, float(q_seed) * 0.85)
    q_hi = min(float(q_cap), float(q_seed) * 1.15)
    if q_hi <= q_lo:
        q_lo, q_hi = 0.0, float(q_cap)
    report.bracketed = solve_q_bracketed_r3_with_inner_r1(
        request_at_q=request_at_q,
        provider=provider,
        q_lo=q_lo,
        q_hi=q_hi,
        q_seed=q_seed,
    )
    ref = report.baseline
    if ref is None and report.bracketed.get("detail"):
        ref = report.bracketed["detail"]
    elif ref is None and report.trf_tmid.get("q_w"):
        qf = float(report.trf_tmid["q_w"])
        req = request_at_q(qf)
        report.trf_tmid = {**report.trf_tmid}
        ref = production_trial_gate(
            qf,
            float(report.trf_tmid["twi_k"]),
            float(report.trf_tmid["two_k"]),
            request=req,
            provider=provider,
        )
    if ref is not None:
        raw_ulp = bounded_ulp_neighborhood_search(ref, request_at_q=request_at_q, provider=provider)
        report.ulp_search = {k: v for k, v in raw_ulp.items() if k != "best"}
        if isinstance(raw_ulp.get("best"), TrialGateDetail):
            report.ulp_best = raw_ulp["best"]
            report.ulp_search["best_detail"] = asdict(raw_ulp["best"])
    best = report.ulp_best if report.ulp_best is not None else ref
    if isinstance(best, TrialGateDetail) and best.gate_pass:
        report.numerical_decision = "A"
        report.remaining_blocker = "none"
    elif report.bracketed.get("bracket_found"):
        report.numerical_decision = "B"
        dom = ref.dominant_index if ref else -1
        names = ("r1", "r2", "r3")
        dom_name = names[dom] if 0 <= dom < 3 else "unknown"
        min_ratio = best.max_ratio if isinstance(best, TrialGateDetail) else math.inf
        report.remaining_blocker = f"ULP_unreachable_at_frozen_boundary: dominant={dom_name}, min_observed_max_ratio={min_ratio}"
    else:
        report.numerical_decision = "C"
        report.remaining_blocker = str(report.bracketed.get("reason", "no_bracket"))
    return report
