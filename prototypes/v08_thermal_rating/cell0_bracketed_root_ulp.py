"""Cell 0 bracketed scalar roots and bounded ULP reachability (V08-03 PoC)."""
# ruff: noqa: E501

from __future__ import annotations

import contextlib
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


def _dominant_name(detail: TrialGateDetail | None) -> str:
    if detail is None:
        return "unknown"
    return ("r1", "r2", "r3")[detail.dominant_index]


def bracket_endpoints_adjacent(lo: float, hi: float) -> bool:
    if lo > hi:
        lo, hi = hi, lo
    if lo == hi:
        return True
    return math.nextafter(lo, math.inf) == hi


def count_representable_strictly_between(
    lo: float, hi: float, *, cap: int = 2_000_000
) -> int | str:
    if lo > hi:
        lo, hi = hi, lo
    if bracket_endpoints_adjacent(lo, hi):
        return 0
    n = 0
    x = math.nextafter(lo, math.inf)
    while x < hi:
        n += 1
        if n >= cap:
            return f">={cap}"
        x = math.nextafter(x, math.inf)
    return n


def float_binary_audit(value: float, *, partner: float | None = None) -> dict[str, Any]:
    na_up = math.nextafter(value, math.inf)
    na_dn = math.nextafter(value, -math.inf)
    out: dict[str, Any] = {
        "value": value,
        "hex": value.hex(),
        "ulp": math.ulp(value),
        "next_up": na_up,
        "next_down": na_dn,
    }
    if partner is not None:
        out["adjacent_to_partner"] = bracket_endpoints_adjacent(value, partner)
        out["representables_between"] = count_representable_strictly_between(value, partner)
    return out


def _float_lattice_midpoint(lo: float, hi: float) -> float:
    if lo > hi:
        lo, hi = hi, lo
    if bracket_endpoints_adjacent(lo, hi):
        return math.nan
    import struct

    def _bits(x: float) -> int:
        return struct.unpack(">Q", struct.pack(">d", x))[0]

    ia, ib = _bits(lo), _bits(hi)
    if ia > ib:
        ia, ib = ib, ia
    im = (ia + ib) // 2
    mid = struct.unpack(">d", struct.pack(">Q", im))[0]
    if lo < mid < hi:
        return mid
    na = math.nextafter(lo, math.inf)
    if na < hi:
        return na
    return math.nextafter(hi, -math.inf)


def _shrink_eval_budget(lo: float, hi: float, *, default: int = 96, ceiling: int = 256) -> int:
    mid = count_representable_strictly_between(lo, hi, cap=10_000)
    if isinstance(mid, int) and mid > 0:
        return min(ceiling, max(default, int(math.ceil(math.log2(mid + 2))) + default))
    return ceiling


def _float_neighbors(value: float) -> tuple[float, float, float]:
    return (math.nextafter(value, -math.inf), value, math.nextafter(value, math.inf))


def localize_sign_bracket_near_root(
    f: Callable[[float], float],
    center: float,
    *,
    lo_limit: float | None = None,
    hi_limit: float | None = None,
    max_steps: int = 64,
) -> tuple[float, float] | None:
    """Narrow异号括弧到根附近少量 ULP（用于可预算的 lattice shrink）。"""
    center = float(center)
    vc = f(center)
    if not math.isfinite(vc):
        return None
    if vc == 0.0:
        dn = math.nextafter(center, -math.inf)
        up = math.nextafter(center, math.inf)
        vd, vu = f(dn), f(up)
        if math.isfinite(vd) and vd != 0.0 and vd * vu < 0.0:
            return (dn, up)
        if math.isfinite(vd) and vd * vc < 0.0:
            return (dn, center) if dn < center else (center, dn)
        if math.isfinite(vu) and vu * vc < 0.0:
            return (center, up) if center < up else (up, center)
    found: tuple[float, float] | None = None
    x = center
    vx = vc
    for _ in range(max_steps):
        x = math.nextafter(x, -math.inf)
        if lo_limit is not None and x < lo_limit:
            break
        v = f(x)
        if not math.isfinite(v):
            break
        if vx * v < 0.0:
            found = (x, center) if x < center else (center, x)
            break
        x, vx = x, v
    if found is not None:
        return found
    x = center
    vx = vc
    for _ in range(max_steps):
        x = math.nextafter(x, math.inf)
        if hi_limit is not None and x > hi_limit:
            break
        v = f(x)
        if not math.isfinite(v):
            break
        if vx * v < 0.0:
            return (center, x) if center < x else (x, center)
        x, vx = x, v
    return None


def shrink_sign_bracket_float64(
    f: Callable[[float], float],
    lo: float,
    hi: float,
    *,
    max_evaluations: int = 128,
) -> dict[str, Any]:
    """Shrink异号括弧到相邻 binary64 端点（不用 brentq xtol 冒充精度）。"""
    initial = [float(lo), float(hi)]
    if lo > hi:
        lo, hi = hi, lo
    fa, fb = f(lo), f(hi)
    evaluations = 2
    discontinuities: list[dict[str, Any]] = []
    if not (math.isfinite(fa) and math.isfinite(fb)):
        return {
            "status": "BLOCKED",
            "reason": "endpoint_non_finite",
            "initial": initial,
            "final_lo": lo,
            "final_hi": hi,
            "adjacent": bracket_endpoints_adjacent(lo, hi),
            "f_lo": fa,
            "f_hi": fb,
            "evaluations": evaluations,
            "discontinuities": discontinuities,
        }
    if fa == 0.0 or fb == 0.0:
        return {
            "status": "ADJACENT" if bracket_endpoints_adjacent(lo, hi) else "ZERO_ENDPOINT",
            "initial": initial,
            "final_lo": lo,
            "final_hi": hi,
            "adjacent": bracket_endpoints_adjacent(lo, hi),
            "f_lo": fa,
            "f_hi": fb,
            "evaluations": evaluations,
            "discontinuities": discontinuities,
        }
    if fa * fb > 0.0:
        return {
            "status": "BLOCKED",
            "reason": "no_sign_change",
            "initial": initial,
            "final_lo": lo,
            "final_hi": hi,
            "adjacent": bracket_endpoints_adjacent(lo, hi),
            "f_lo": fa,
            "f_hi": fb,
            "evaluations": evaluations,
            "discontinuities": discontinuities,
        }
    a, b = lo, hi
    va, vb = fa, fb
    while not bracket_endpoints_adjacent(a, b) and evaluations < max_evaluations:
        mid = _float_lattice_midpoint(a, b)
        if not math.isfinite(mid) or not (a < mid < b):
            break
        vm = f(mid)
        evaluations += 1
        if not math.isfinite(vm):
            discontinuities.append({"position": mid, "kind": "non_finite_residual"})
            break
        if vm == 0.0:
            left = math.nextafter(mid, -math.inf)
            right = math.nextafter(mid, math.inf)
            fl, fr = f(left), f(right)
            if math.isfinite(fl) and math.isfinite(fr) and fl * fr < 0.0:
                a, b, va, vb = left, right, fl, fr
                if bracket_endpoints_adjacent(a, b):
                    break
                continue
            if math.isfinite(fl) and fl * vb < 0.0:
                a, va = left, fl
            elif math.isfinite(fr) and fr * va < 0.0:
                b, vb = right, fr
            else:
                break
            continue
        if va * vm < 0.0:
            b, vb = mid, vm
            continue
        if vm * vb < 0.0:
            a, va = mid, vm
            continue
        discontinuities.append(
            {
                "position": mid,
                "kind": "sign_plateau",
                "f_a": va,
                "f_mid": vm,
                "f_b": vb,
            }
        )
        if abs(va) > abs(vb):
            a, va = mid, vm
        else:
            b, vb = mid, vm
    if not bracket_endpoints_adjacent(a, b):
        mid_count = count_representable_strictly_between(a, b, cap=4)
        if mid_count == 1 and evaluations < max_evaluations + 1:
            lone = math.nextafter(a, math.inf)
            fm = f(lone)
            evaluations += 1
            if (
                math.isfinite(fm)
                and va * vb < 0.0
                and va * fm <= 0.0 <= fm * vb
                and (va * fm < 0.0 or fm * vb < 0.0)
            ):
                if va * fm < 0.0:
                    b, vb = lone, fm
                else:
                    a, va = lone, fm
    return {
        "status": "ADJACENT" if bracket_endpoints_adjacent(a, b) else "PARTIAL",
        "initial": initial,
        "final_lo": a,
        "final_hi": b,
        "adjacent": bracket_endpoints_adjacent(a, b),
        "f_lo": va,
        "f_hi": vb,
        "evaluations": evaluations,
        "discontinuities": discontinuities,
        "representables_between_final": count_representable_strictly_between(a, b),
    }


@dataclass
class CandidateEvidence:
    """Independent production eval_trial_residual_gate record for one PoC candidate."""

    label: str
    detail: TrialGateDetail | None
    task172_validated: bool
    task172_validate_reason: str | None
    task173_root_pass: bool
    task173_reason: str | None
    task173_f_q_w: float | None = None
    task173_q_confirmed_w: float | None = None


def task173_independent_root_gate(
    *,
    q_trial_w: float,
    twi_k: float,
    two_k: float,
    request: Any,
    provider: Any,
) -> dict[str, Any]:
    """Task173 F(q)=q_trial-q_confirmed using production confirm path; no circular F(q)=0."""
    from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
        _task173_root_tolerance_w,
    )

    pre = eval_trial_residual_gate(request, provider, q_trial_w, twi_k, two_k)
    if pre is None:
        return {"pass": False, "reason": "pre_eval_trial_none"}
    if not pre.get("passes_original_residual_gate"):
        return {
            "pass": False,
            "reason": "pre_ulp_gate_blocked",
            "max_residual_ratio": pre.get("max_residual_ratio"),
        }
    outcome = build_validated_local_result_from_verified_trial_triple(
        request, provider, q_trial_w, twi_k, two_k, polish_nextafter=True
    )
    if type(outcome) is not Task172LocalResult:
        return {"pass": False, "reason": type(outcome).__name__}
    q_confirmed = float(outcome.signed_q_hot_to_cold_w)
    twi_c = float(outcome.wall_temperature_inner_k)
    two_c = float(outcome.wall_temperature_outer_k)
    post = eval_trial_residual_gate(request, provider, q_confirmed, twi_c, two_c)
    if post is None or not post.get("passes_original_residual_gate"):
        return {"pass": False, "reason": "post_confirm_ulp_blocked"}
    tol = _task173_root_tolerance_w(q_confirmed)
    f_q = float(q_trial_w) - q_confirmed
    root_pass = abs(f_q) <= tol
    return {
        "pass": root_pass,
        "f_q_w": f_q,
        "tolerance_w": tol,
        "q_confirmed_w": q_confirmed,
        "reason": None if root_pass else "f_q_exceeds_tolerance",
    }


def build_candidate_evidence(
    label: str,
    *,
    q_w: float,
    twi_k: float,
    two_k: float,
    request_at_q: Callable[[float], Any],
    provider: Any,
) -> CandidateEvidence:
    try:
        request = request_at_q(float(q_w))
    except Exception as exc:
        return CandidateEvidence(
            label=label,
            detail=None,
            task172_validated=False,
            task172_validate_reason=type(exc).__name__,
            task173_root_pass=False,
            task173_reason="request_build_failed",
        )
    detail = production_trial_gate(
        float(q_w), float(twi_k), float(two_k), request=request, provider=provider
    )
    if detail is None:
        return CandidateEvidence(
            label=label,
            detail=None,
            task172_validated=False,
            task172_validate_reason="eval_trial_none",
            task173_root_pass=False,
            task173_reason="eval_trial_none",
        )
    t173 = task173_independent_root_gate(
        q_trial_w=float(q_w),
        twi_k=float(twi_k),
        two_k=float(two_k),
        request=request,
        provider=provider,
    )
    if detail.gate_pass:
        ok, reason = production_validated_if_gate_passes(
            request, provider, float(q_w), float(twi_k), float(two_k)
        )
    else:
        ok, reason = (False, "ulp_gate_blocked")
    return CandidateEvidence(
        label=label,
        detail=detail,
        task172_validated=ok,
        task172_validate_reason=reason,
        task173_root_pass=bool(t173.get("pass")),
        task173_reason=str(t173.get("reason")) if not t173.get("pass") else None,
        task173_f_q_w=t173.get("f_q_w"),
        task173_q_confirmed_w=t173.get("q_confirmed_w"),
    )


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
        request_hash=str(gate.get("request_hash", "")),
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
    brentq_ref = math.nan
    with contextlib.suppress(ValueError):
        brentq_ref = float(brentq(f, a, b, maxiter=32, xtol=1.0e-12))
    narrow = (
        localize_sign_bracket_near_root(f, brentq_ref, lo_limit=lo, hi_limit=hi)
        if math.isfinite(brentq_ref)
        else None
    )
    shrink_lo, shrink_hi = narrow if narrow else (a, b)
    tmid_budget = _shrink_eval_budget(shrink_lo, shrink_hi)
    tmid_shrink = shrink_sign_bracket_float64(f, shrink_lo, shrink_hi, max_evaluations=tmid_budget)
    if narrow:
        tmid_shrink["initial_wide"] = [a, b]
        tmid_shrink["localized_seed"] = [shrink_lo, shrink_hi]
    ta, tb = float(tmid_shrink["final_lo"]), float(tmid_shrink["final_hi"])
    tmid_candidates: set[float] = set()
    if tmid_shrink.get("adjacent"):
        tmid_candidates.update((ta, tb))
    if math.isfinite(brentq_ref):
        tmid_candidates.update(_float_neighbors(brentq_ref))
    pick: list[tuple[float, TrialGateDetail | None]] = []
    for tmid_c in tmid_candidates:
        twi_c, two_c = wall_temperatures_from_tmid_k(q_w, tmid_c, rwall_k_w=rw)
        if not (shell_k <= two_c <= twi_c <= tube_k):
            continue
        pick.append(
            (
                tmid_c,
                production_trial_gate(q_w, twi_c, two_c, request=request, provider=provider),
            )
        )
    valid = [p for p in pick if p[1] is not None and math.isfinite(p[1].max_ratio)]
    if not valid:
        return {
            "status": "BLOCKED",
            "reason": "lattice_tmid_gate_none",
            "bracket_found": True,
            "bracket_initial": [a, b],
            "tmid_lattice": tmid_shrink,
        }
    tmid_root, detail = min(valid, key=lambda p: p[1].max_ratio)  # type: ignore[union-attr]
    twi, two = wall_temperatures_from_tmid_k(q_w, tmid_root, rwall_k_w=rw)
    return {
        "status": "SOLVED",
        "bracket_found": True,
        "bracket_initial": [a, b],
        "bracket_final": [ta, tb],
        "tmid_lattice": tmid_shrink,
        "brentq_reference_k": brentq_ref,
        "bracket": [ta, tb],
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

    def r3_for_shrink(qv: float) -> float:
        return r3_scalar(qv)

    brentq_ref = math.nan
    with contextlib.suppress(ValueError):
        brentq_ref = float(brentq(lambda v: r3_for_shrink(v), a, b, maxiter=32, xtol=1.0e-9))
    narrow_q = (
        localize_sign_bracket_near_root(r3_for_shrink, brentq_ref, lo_limit=q_lo, hi_limit=q_hi)
        if math.isfinite(brentq_ref)
        else None
    )
    shrink_lo, shrink_hi = narrow_q if narrow_q else (a, b)
    q_budget = _shrink_eval_budget(shrink_lo, shrink_hi, default=72)
    q_shrink = shrink_sign_bracket_float64(
        r3_for_shrink, shrink_lo, shrink_hi, max_evaluations=q_budget
    )
    if narrow_q:
        q_shrink["initial_wide"] = [a, b]
        q_shrink["localized_seed"] = [shrink_lo, shrink_hi]
    qa, qb = float(q_shrink["final_lo"]), float(q_shrink["final_hi"])
    q_trials: set[float] = set()
    if q_shrink.get("adjacent"):
        q_trials.update((qa, qb))
    if math.isfinite(brentq_ref):
        q_trials.update(_float_neighbors(brentq_ref))
    candidates: list[dict[str, Any]] = []
    for q_cand in q_trials:
        try:
            request_c = request_at_q(q_cand)
        except Exception:
            continue
        inner_c = solve_tmid_bracketed_r1_root(q_cand, request=request_c, provider=provider)
        if inner_c.get("status") != "SOLVED":
            continue
        det = production_trial_gate(
            q_cand,
            float(inner_c["twi_k"]),
            float(inner_c["two_k"]),
            request=request_c,
            provider=provider,
        )
        if det is None or not math.isfinite(det.max_ratio):
            continue
        candidates.append(
            {
                "q_w": q_cand,
                "inner": inner_c,
                "detail": det,
                "request": request_c,
            }
        )
    if not candidates:
        return {
            "status": "BLOCKED",
            "reason": "lattice_q_no_valid_endpoint",
            "bracket_found": True,
            "q_bracket_initial": [a, b],
            "q_lattice": q_shrink,
        }
    best = min(candidates, key=lambda c: c["detail"].max_ratio)
    q_root = float(best["q_w"])
    inner = best["inner"]
    twi, two = float(inner["twi_k"]), float(inner["two_k"])
    detail = best["detail"]
    return {
        "status": "SOLVED",
        "bracket_found": True,
        "q_bracket_initial": [a, b],
        "q_bracket_final": [qa, qb],
        "q_lattice": q_shrink,
        "q_bracket": [qa, qb],
        "brentq_reference_w": brentq_ref,
        "q_w": q_root,
        "tmid_k": inner["tmid_k"],
        "twi_k": twi,
        "two_k": two,
        "detail": detail,
        "inner": inner,
        "lattice_endpoints_evaluated": len(candidates),
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


def _residual_sensitivity(
    detail: TrialGateDetail,
    *,
    request_at_q: Callable[[float], Any],
    provider: Any,
) -> dict[str, Any]:
    """Nextafter bumps: each perturbation uses matching request_at_q(q_trial) for q."""
    q, twi, two = detail.q_w, detail.twi_k, detail.two_k
    base_req = request_at_q(q)
    sens: dict[str, Any] = {}
    for name, (var, direction) in (
        ("q_up", ("q", math.inf)),
        ("q_down", ("q", -math.inf)),
        ("twi_up", ("twi", math.inf)),
        ("twi_down", ("twi", -math.inf)),
        ("two_up", ("two", math.inf)),
        ("two_down", ("two", -math.inf)),
    ):
        try:
            if var == "q":
                q_trial = math.nextafter(q, direction)
                req = request_at_q(q_trial)
                trial = production_trial_gate(q_trial, twi, two, request=req, provider=provider)
            else:
                req = base_req
                shell_k = float(req.shell_bulk_state.temperature_k)
                tube_k = float(req.tube_bulk_state.temperature_k)
                twi_t = twi
                two_t = two
                if var == "twi":
                    twi_t = math.nextafter(twi, direction)
                else:
                    two_t = math.nextafter(two, direction)
                if not (shell_k <= two_t <= twi_t <= tube_k):
                    sens[name] = {"valid": False, "reason": "wall_order"}
                    continue
                trial = production_trial_gate(q, twi_t, two_t, request=req, provider=provider)
            if trial is None:
                sens[name] = {"valid": False, "reason": "eval_none"}
                continue
            sens[name] = {
                "valid": True,
                "dr1_w": trial.r1_w - detail.r1_w,
                "dr2_w": trial.r2_w - detail.r2_w,
                "dr3_w": trial.r3_w - detail.r3_w,
                "d_ratio1": trial.ratio1 - detail.ratio1,
                "d_ratio2": trial.ratio2 - detail.ratio2,
                "d_ratio3": trial.ratio3 - detail.ratio3,
                "d_max_ratio": trial.max_ratio - detail.max_ratio,
            }
        except Exception as exc:
            sens[name] = {"valid": False, "reason": type(exc).__name__}
    sens["q_perturbation_uses_trial_request"] = True
    return sens


def bounded_ulp_neighborhood_search(
    detail: TrialGateDetail,
    *,
    request_at_q: Callable[[float], Any],
    provider: Any,
    max_steps: int = 54,
    label: str = "local_refinement",
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
    ev = build_candidate_evidence(
        label,
        q_w=best.q_w,
        twi_k=best.twi_k,
        two_k=best.two_k,
        request_at_q=request_at_q,
        provider=provider,
    )
    return {
        "label": label,
        "start_max_ratio": detail.max_ratio,
        "steps_evaluated": steps,
        "best_max_ratio": best.max_ratio,
        "improved": best.max_ratio < detail.max_ratio,
        "sensitivity_probe": _residual_sensitivity(
            detail, request_at_q=request_at_q, provider=provider
        ),
        "evidence": ev,
    }


def _snapshot_residual_at_tmid(
    tmid: float,
    *,
    q_w: float,
    request: Any,
    provider: Any,
) -> dict[str, Any]:
    prim = build_closure_primitives(request, provider)
    rw = float(prim.wall_resistance_k_w)
    twi, two = wall_temperatures_from_tmid_k(q_w, tmid, rwall_k_w=rw)
    det = production_trial_gate(q_w, twi, two, request=request, provider=provider)
    gate = asdict(det) if det else None
    return {
        "tmid_k": tmid,
        "production_gate": gate,
        "domain_exit": det.domain_exit if det else None,
    }


def audit_bracket_scalar_precision(
    bracketed: dict[str, Any],
    *,
    request_at_q: Callable[[float], Any],
    provider: Any,
) -> dict[str, Any]:
    """Initial vs final float-lattice brackets, endpoint production residuals."""
    if not bracketed.get("bracket_found"):
        return {"verified": False, "reason": bracketed.get("reason", "no_bracket")}
    q_init = bracketed.get("q_bracket_initial") or bracketed.get("q_bracket")
    q_final = bracketed.get("q_bracket_final") or bracketed["q_bracket"]
    q_lo_i, q_hi_i = float(q_init[0]), float(q_init[1])
    q_lo_f, q_hi_f = float(q_final[0]), float(q_final[1])
    q_root = float(bracketed["q_w"])
    inner = bracketed.get("inner") or {}
    tmid_init = inner.get("bracket_initial") or inner.get("bracket")
    tmid_final = inner.get("bracket_final") or inner.get("bracket")
    tmid = float(bracketed.get("tmid_k", math.nan))
    q_lat = bracketed.get("q_lattice") or {}
    tmid_lat = inner.get("tmid_lattice") or {}
    endpoint_gates: dict[str, Any] = {}

    def _gate_at_q(q_val: float) -> TrialGateDetail | None:
        try:
            request = request_at_q(q_val)
        except Exception:
            return None
        inner_r1 = solve_tmid_bracketed_r1_root(q_val, request=request, provider=provider)
        if inner_r1.get("status") != "SOLVED":
            return None
        return production_trial_gate(
            q_val,
            float(inner_r1["twi_k"]),
            float(inner_r1["two_k"]),
            request=request,
            provider=provider,
        )

    for tag, q_val in (
        ("q_initial_lo", q_lo_i),
        ("q_initial_hi", q_hi_i),
        ("q_final_lo", q_lo_f),
        ("q_final_hi", q_hi_f),
        ("q_root", q_root),
    ):
        det = (
            _gate_at_q(q_val)
            if tag != "q_root"
            else production_trial_gate(
                q_root,
                float(bracketed["twi_k"]),
                float(bracketed["two_k"]),
                request=request_at_q(q_root),
                provider=provider,
            )
        )
        endpoint_gates[tag] = asdict(det) if det else None
    tmid_endpoint: dict[str, Any] = {}
    if tmid_final and q_root:
        try:
            request = request_at_q(q_root)
            for tag, tv in (("tmid_final_lo", tmid_final[0]), ("tmid_final_hi", tmid_final[1])):
                tmid_endpoint[tag] = _snapshot_residual_at_tmid(
                    float(tv), q_w=q_root, request=request, provider=provider
                )
        except Exception:
            pass
    return {
        "verified": bool(
            q_lat.get("adjacent") and (tmid_lat.get("adjacent") if tmid_lat else True)
        ),
        "q_bracket_initial_w": [q_lo_i, q_hi_i],
        "q_bracket_final_w": [q_lo_f, q_hi_f],
        "q_bracket_adjacent_floats": bracket_endpoints_adjacent(q_lo_f, q_hi_f),
        "q_bracket_initial_adjacent": bracket_endpoints_adjacent(q_lo_i, q_hi_i),
        "q_lattice_shrink": q_lat,
        "q_endpoint_binary": {
            "initial_lo": float_binary_audit(q_lo_i, partner=q_hi_i),
            "initial_hi": float_binary_audit(q_hi_i, partner=q_lo_i),
            "final_lo": float_binary_audit(q_lo_f, partner=q_hi_f),
            "final_hi": float_binary_audit(q_hi_f, partner=q_lo_f),
            "root": float_binary_audit(q_root),
        },
        "tmid_bracket_initial_k": tmid_init,
        "tmid_bracket_final_k": tmid_final,
        "tmid_bracket_adjacent_floats": (
            bracket_endpoints_adjacent(float(tmid_final[0]), float(tmid_final[1]))
            if tmid_final
            else None
        ),
        "tmid_lattice_shrink": tmid_lat,
        "tmid_root_k": tmid,
        "tmid_endpoint_residuals": tmid_endpoint,
        "brentq_q_reference_w": bracketed.get("brentq_reference_w"),
        "brentq_tmid_reference_k": inner.get("brentq_reference_k"),
        "endpoint_gates": endpoint_gates,
    }


@dataclass
class Cell0EvidencePack:
    candidates: list[CandidateEvidence] = field(default_factory=list)
    refinement_from_baseline: dict[str, Any] = field(default_factory=dict)
    refinement_from_bracket: dict[str, Any] = field(default_factory=dict)
    refinement_chosen_label: str = ""
    trf_tmid_solver: dict[str, Any] = field(default_factory=dict)
    trf_u1_u2_solver: dict[str, Any] = field(default_factory=dict)
    bracket_solver: dict[str, Any] = field(default_factory=dict)
    bracket_precision: dict[str, Any] = field(default_factory=dict)
    numerical_decision: str = "C"
    numerical_subclass: str = ""
    remaining_blocker: str = ""
    dominant_residual: str = "unknown"
    engineering_acceptance: str = "BLOCKED"


@dataclass
class Cell0ReachabilityReport:
    """Backward-compatible view; populated from Cell0EvidencePack."""

    baseline: TrialGateDetail | None
    trf_u1_u2: dict[str, Any] = field(default_factory=dict)
    trf_tmid: dict[str, Any] = field(default_factory=dict)
    bracketed: dict[str, Any] = field(default_factory=dict)
    ulp_search: dict[str, Any] = field(default_factory=dict)
    ulp_best: TrialGateDetail | None = None
    numerical_decision: str = "C"
    remaining_blocker: str = ""
    evidence: Cell0EvidencePack | None = None


def _candidate_by_label(cands: list[CandidateEvidence], label: str) -> CandidateEvidence | None:
    for c in cands:
        if c.label == label:
            return c
    return None


def run_cell0_evidence_pack(
    *,
    request_at_q: Callable[[float], Any],
    provider: Any,
    q_cap: float,
    q_seed: float,
    baseline: tuple[float, float, float] | None = None,
) -> Cell0EvidencePack:
    """Five independent production gates + separate local refinements (no mixed ancestry)."""
    pack = Cell0EvidencePack()
    trf_tmid = solve_bvp_cell_wall_eliminated_trf(
        request_at_q=request_at_q, provider=provider, q_upper=q_cap, q_seed=q_seed
    )
    trf_u1_u2 = solve_bvp_cell_u1_u2_trf(
        request_at_q=request_at_q, provider=provider, q_upper=q_cap, q_seed=q_seed
    )
    q_lo = max(0.0, float(q_seed) * 0.85)
    q_hi = min(float(q_cap), float(q_seed) * 1.15)
    if q_hi <= q_lo:
        q_lo, q_hi = 0.0, float(q_cap)
    bracketed = solve_q_bracketed_r3_with_inner_r1(
        request_at_q=request_at_q,
        provider=provider,
        q_lo=q_lo,
        q_hi=q_hi,
        q_seed=q_seed,
    )
    pack.bracket_solver = bracketed
    pack.trf_tmid_solver = trf_tmid
    pack.trf_u1_u2_solver = trf_u1_u2
    pack.bracket_precision = audit_bracket_scalar_precision(
        bracketed, request_at_q=request_at_q, provider=provider
    )
    cands: list[CandidateEvidence] = []
    if baseline is not None:
        q0, twi0, two0 = baseline
        cands.append(
            build_candidate_evidence(
                "1_baseline",
                q_w=q0,
                twi_k=twi0,
                two_k=two0,
                request_at_q=request_at_q,
                provider=provider,
            )
        )
    if trf_tmid.get("q_w"):
        cands.append(
            build_candidate_evidence(
                "2_trf_tmid_2var",
                q_w=float(trf_tmid["q_w"]),
                twi_k=float(trf_tmid["twi_k"]),
                two_k=float(trf_tmid["two_k"]),
                request_at_q=request_at_q,
                provider=provider,
            )
        )
    if trf_u1_u2.get("q_w"):
        cands.append(
            build_candidate_evidence(
                "3_trf_u1u2_3var",
                q_w=float(trf_u1_u2["q_w"]),
                twi_k=float(trf_u1_u2["twi_k"]),
                two_k=float(trf_u1_u2["two_k"]),
                request_at_q=request_at_q,
                provider=provider,
            )
        )
    if bracketed.get("status") == "SOLVED" and bracketed.get("q_w") is not None:
        cands.append(
            build_candidate_evidence(
                "4_float_lattice_scalar_root",
                q_w=float(bracketed["q_w"]),
                twi_k=float(bracketed["twi_k"]),
                two_k=float(bracketed["two_k"]),
                request_at_q=request_at_q,
                provider=provider,
            )
        )
    pack.candidates = cands
    base_ev = _candidate_by_label(cands, "1_baseline")
    bracket_ev = _candidate_by_label(cands, "4_float_lattice_scalar_root")
    if base_ev and base_ev.detail:
        pack.refinement_from_baseline = bounded_ulp_neighborhood_search(
            base_ev.detail,
            request_at_q=request_at_q,
            provider=provider,
            label="5a_refinement_from_baseline",
        )
        pack.refinement_from_baseline["label"] = "5a_refinement_from_baseline"
        if base_ev.detail:
            cands.append(pack.refinement_from_baseline["evidence"])
    if bracket_ev and bracket_ev.detail:
        pack.refinement_from_bracket = bounded_ulp_neighborhood_search(
            bracket_ev.detail,
            request_at_q=request_at_q,
            provider=provider,
            label="5b_refinement_from_bracket_root",
        )
        pack.refinement_from_bracket["label"] = "5b_refinement_from_bracket_root"
        cands.append(pack.refinement_from_bracket["evidence"])
    pack.candidates = cands
    rb = pack.refinement_from_bracket.get("best_max_ratio", math.inf)
    bb = pack.refinement_from_baseline.get("best_max_ratio", math.inf)
    if rb <= bb and pack.refinement_from_bracket:
        pack.refinement_chosen_label = "5b_refinement_from_bracket_root"
    elif pack.refinement_from_baseline:
        pack.refinement_chosen_label = "5a_refinement_from_baseline"
    finite = [c for c in cands if c.detail is not None]
    best_detail = min(finite, key=lambda c: c.detail.max_ratio).detail if finite else None  # type: ignore[union-attr]
    pack.dominant_residual = _dominant_name(best_detail)
    any_pass = any(c.detail and c.detail.gate_pass and c.task172_validated for c in cands)
    if any_pass:
        pack.numerical_decision = "A"
        pack.numerical_subclass = "cell0_ulp_gate_pass"
        pack.remaining_blocker = "none"
    elif bracketed.get("bracket_found"):
        pack.numerical_decision = "B"
        min_r = best_detail.max_ratio if best_detail else math.inf
        pack.numerical_subclass = "B2_float_lattice_ulP_limit"
        pack.remaining_blocker = (
            f"verified_float_lattice_only: min_max_ratio={min_r:.6g}, "
            f"dominant={pack.dominant_residual}; adjacent binary64 root still exceeds Task172 W bounds"
        )
    else:
        pack.numerical_decision = "C"
        pack.numerical_subclass = "C_frozen_neighbour_no_bracket"
        pack.remaining_blocker = str(bracketed.get("reason", "no_bracket"))
    pack.engineering_acceptance = "BLOCKED"
    return pack


def run_cell0_bracketed_ulp_pipeline(
    *,
    request_at_q: Callable[[float], Any],
    provider: Any,
    q_cap: float,
    q_seed: float,
    baseline: tuple[float, float, float] | None = None,
) -> Cell0ReachabilityReport:
    pack = run_cell0_evidence_pack(
        request_at_q=request_at_q,
        provider=provider,
        q_cap=q_cap,
        q_seed=q_seed,
        baseline=baseline,
    )
    baseline_ev = _candidate_by_label(pack.candidates, "1_baseline")
    bracket_ev = _candidate_by_label(pack.candidates, "4_float_lattice_scalar_root")
    refin_b = pack.refinement_from_baseline.get("evidence")
    refin_r = pack.refinement_from_bracket.get("evidence")
    ulp_best = None
    for c in (refin_r, refin_b, bracket_ev, baseline_ev):
        if c and c.detail and (ulp_best is None or c.detail.max_ratio < ulp_best.max_ratio):
            ulp_best = c.detail
    return Cell0ReachabilityReport(
        baseline=baseline_ev.detail if baseline_ev else None,
        trf_u1_u2=pack.trf_u1_u2_solver,
        trf_tmid=pack.trf_tmid_solver,
        bracketed=pack.bracket_solver,
        ulp_search={
            "from_baseline": {
                k: v for k, v in pack.refinement_from_baseline.items() if k != "evidence"
            },
            "from_bracket": {
                k: v for k, v in pack.refinement_from_bracket.items() if k != "evidence"
            },
            "chosen": pack.refinement_chosen_label,
        },
        ulp_best=ulp_best,
        numerical_decision=pack.numerical_decision,
        remaining_blocker=pack.remaining_blocker,
        evidence=pack,
    )
