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


def _dominant_name(detail: TrialGateDetail | None) -> str:
    if detail is None:
        return "unknown"
    return ("r1", "r2", "r3")[detail.dominant_index]


def float_binary_audit(value: float) -> dict[str, Any]:
    na_up = math.nextafter(value, math.inf)
    na_dn = math.nextafter(value, -math.inf)
    return {
        "value": value,
        "hex": value.hex(),
        "ulp": math.ulp(value),
        "next_up": na_up,
        "next_down": na_dn,
        "bracket_collapsed_up": na_up == value,
        "bracket_collapsed_down": na_dn == value,
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
) -> dict[str, float]:
    """Central nextafter bump for q,Twi,Two vs max ULP ratio (diagnostic only)."""
    q, twi, two = detail.q_w, detail.twi_k, detail.two_k
    sens: dict[str, float] = {}
    for name in ("q", "twi", "two"):
        try:
            req = request_at_q(q)
            up = production_trial_gate(
                math.nextafter(q, math.inf) if name == "q" else q,
                math.nextafter(twi, math.inf) if name == "twi" else twi,
                math.nextafter(two, math.inf) if name == "two" else two,
                request=req if name == "q" else request_at_q(q),
                provider=provider,
            )
            if name != "q":
                req = request_at_q(q)
            if up is None:
                sens[name] = math.inf
                continue
            sens[name] = abs(up.max_ratio - detail.max_ratio)
        except Exception:
            sens[name] = math.inf
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


def audit_bracket_scalar_precision(
    bracketed: dict[str, Any],
    *,
    request_at_q: Callable[[float], Any],
    provider: Any,
) -> dict[str, Any]:
    """Brentq bracket endpoints, binary64 representation, endpoint residual snapshot."""
    if not bracketed.get("bracket_found"):
        return {"verified": False, "reason": bracketed.get("reason", "no_bracket")}
    q_a, q_b = bracketed["q_bracket"]
    q_root = float(bracketed["q_w"])
    tmid = float(bracketed.get("tmid_k", math.nan))
    inner = bracketed.get("inner") or {}
    tmid_br = inner.get("bracket")
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

    for tag, q_val in (("q_lo", q_a), ("q_hi", q_b), ("q_root", q_root)):
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
    return {
        "verified": True,
        "q_bracket_w": [q_a, q_b],
        "q_bracket_width_w": abs(q_b - q_a),
        "q_bracket_binary": [
            float_binary_audit(q_a),
            float_binary_audit(q_b),
            float_binary_audit(q_root),
        ],
        "tmid_bracket_k": tmid_br,
        "tmid_root_k": tmid,
        "tmid_binary": float_binary_audit(tmid) if math.isfinite(tmid) else None,
        "brentq_q_xtol_w": 1.0e-9,
        "brentq_tmid_xtol_k": 1.0e-12,
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
                "4_bracketed_scalar_root",
                q_w=float(bracketed["q_w"]),
                twi_k=float(bracketed["twi_k"]),
                two_k=float(bracketed["two_k"]),
                request_at_q=request_at_q,
                provider=provider,
            )
        )
    pack.candidates = cands
    base_ev = _candidate_by_label(cands, "1_baseline")
    bracket_ev = _candidate_by_label(cands, "4_bracketed_scalar_root")
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
        pack.numerical_subclass = "B2_property_quantization_ulP"
        pack.remaining_blocker = (
            f"verified_local_search_only: min_max_ratio={min_r:.6g}, "
            f"dominant={pack.dominant_residual}; bracket_brentq_xtol not sufficient for nanowatt bounds"
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
    bracket_ev = _candidate_by_label(pack.candidates, "4_bracketed_scalar_root")
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
