"""SHADOW_LAYERED_ACCEPTANCE — isolated analysis only; never production VALIDATED."""
# ruff: noqa: E501

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from prototypes.v08_thermal_rating.cell0_bracketed_root_ulp import (
    production_trial_gate,
)
from prototypes.v08_thermal_rating.true_three_equation_cell_coupling import (
    build_closure_primitives,
)

EXPERIMENTAL_TAG = "EXPERIMENTAL_NOT_APPROVED"
ORIGINAL_PRODUCTION_ACCEPTANCE = "ORIGINAL_PRODUCTION_ACCEPTANCE"


@dataclass(frozen=True)
class ShadowLayerRecord:
    layer: str
    status: str
    metrics: dict[str, Any]
    approval_status: str = EXPERIMENTAL_TAG


def shadow_l1_local_heat_transfer(
    *,
    q_w: float,
    twi_k: float,
    two_k: float,
    request: Any,
    provider: Any,
) -> ShadowLayerRecord:
    """L1: production _eval_trial gate only (same as ORIGINAL Task172 C-ULP)."""
    det = production_trial_gate(q_w, twi_k, two_k, request=request, provider=provider)
    if det is None:
        return ShadowLayerRecord(
            layer="L1",
            status="UNAVAILABLE",
            metrics={"reason": "eval_trial_none"},
        )
    prim = build_closure_primitives(request, provider)
    metrics = {
        "q_w": det.q_w,
        "twi_k": det.twi_k,
        "two_k": det.two_k,
        "r1_w": det.r1_w,
        "r2_w": det.r2_w,
        "r3_w": det.r3_w,
        "bound1_w": det.bound1_w,
        "bound2_w": det.bound2_w,
        "bound3_w": det.bound3_w,
        "R1_RATIO": det.ratio1,
        "R2_RATIO": det.ratio2,
        "R3_RATIO": det.ratio3,
        "MAX_ULP_RATIO": det.max_ratio,
        "passes_original_c_ulp": det.gate_pass,
        "request_hash": det.request_hash,
        "tube_bulk_snapshot_id": prim.tube_bulk_id,
        "shell_bulk_snapshot_id": prim.shell_bulk_id,
        "g_i_w_per_k": det.g_i_w_k,
        "g_o_w_per_k": det.g_o_w_k,
        "rwall_k_w": det.rwall_k_w,
        "mode": ORIGINAL_PRODUCTION_ACCEPTANCE,
    }
    return ShadowLayerRecord(
        layer="L1",
        status="PASS" if det.gate_pass else "BLOCKED",
        metrics=metrics,
    )


def shadow_l2_property_consistency_probe(
    *,
    q_w: float,
    twi_k: float,
    two_k: float,
    request: Any,
    provider: Any,
    request_at_q: Any | None = None,
) -> ShadowLayerRecord:
    """L2: directional ULP probes; zero delta does NOT imply zero property quantization."""
    base = production_trial_gate(q_w, twi_k, two_k, request=request, provider=provider)
    if base is None:
        return ShadowLayerRecord(layer="L2", status="UNAVAILABLE", metrics={})
    probes: dict[str, Any] = {}

    def _probe(label: str, q: float, twi: float, two: float, req: Any) -> None:
        try:
            shell_k = float(req.shell_bulk_state.temperature_k)
            tube_k = float(req.tube_bulk_state.temperature_k)
            if not (shell_k <= two <= twi <= tube_k):
                probes[label] = {"valid": False, "reason": "wall_order"}
                return
            trial = production_trial_gate(q, twi, two, request=req, provider=provider)
            if trial is None:
                probes[label] = {"valid": False, "reason": "gate_none"}
                return
            probes[label] = {
                "valid": True,
                "dr1_w": trial.r1_w - base.r1_w,
                "dr2_w": trial.r2_w - base.r2_w,
                "dr3_w": trial.r3_w - base.r3_w,
                "d_gi": trial.g_i_w_k - base.g_i_w_k,
                "d_go": trial.g_o_w_k - base.g_o_w_k,
                "d_max_ratio": trial.max_ratio - base.max_ratio,
            }
        except Exception as exc:
            probes[label] = {"valid": False, "reason": type(exc).__name__}

    _probe("twi_up", q_w, math.nextafter(twi_k, math.inf), two_k, request)
    _probe("twi_dn", q_w, math.nextafter(twi_k, -math.inf), two_k, request)
    _probe("two_up", q_w, twi_k, math.nextafter(two_k, math.inf), request)
    _probe("two_dn", q_w, twi_k, math.nextafter(two_k, -math.inf), request)
    if request_at_q is not None:
        q_up = math.nextafter(q_w, math.inf)
        q_dn = math.nextafter(q_w, -math.inf)
        try:
            _probe("q_up", q_up, twi_k, two_k, request_at_q(q_up))
            _probe("q_dn", q_dn, twi_k, two_k, request_at_q(q_dn))
        except Exception as exc:
            probes["q_perturbation"] = {"valid": False, "reason": type(exc).__name__}

    property_budget = "UNRESOLVED"
    interpretation = (
        "Probe deltas measure local sensitivity at one frozen bulk request; "
        "a zero r3 delta at Twi+1 ULP does not prove CoolProp quantization is zero."
    )
    return ShadowLayerRecord(
        layer="L2",
        status="INFORMATIVE_ONLY",
        metrics={
            "probes": probes,
            "property_uncertainty_budget": property_budget,
            "interpretation": interpretation,
        },
    )


def shadow_l3_placeholder_from_rating(
    *, task173_status: str, detail: dict[str, Any] | None
) -> ShadowLayerRecord:
    """L3: whole-exchanger requires successful N1/N2/N4 — not inferred from cell L1."""
    return ShadowLayerRecord(
        layer="L3",
        status="UNRESOLVED" if task173_status != "VALIDATED" else "REQUIRES_FULL_MESH_AUDIT",
        metrics={
            "task173_overall_status": task173_status,
            "whole_energy_balance_verified": False,
            "axial_profile_verified": False,
            "mesh_convergence_verified": False,
            "detail_from_rating": detail or {},
            "note": "Local L1 PASS does not imply L3; shadow cannot auto-PASS L3.",
        },
    )


def shadow_l4_placeholder(*, task173_status: str, failure_code: str | None) -> ShadowLayerRecord:
    return ShadowLayerRecord(
        layer="L4",
        status="BLOCKED" if task173_status != "VALIDATED" else "UNRESOLVED",
        metrics={
            "engineering_design_acceptance": "BLOCKED",
            "task173_failure_code": failure_code,
            "outlet_temperature_verified": False,
            "pressure_drop_verified": False,
            "manufacturing_constraints_verified": False,
        },
    )


def layer_to_dict(rec: ShadowLayerRecord) -> dict[str, Any]:
    return {
        "layer": rec.layer,
        "status": rec.status,
        "approval_status": rec.approval_status,
        "metrics": rec.metrics,
    }
