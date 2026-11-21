"""Production Task172 gate evidence for isolated BVP (no synthetic inf ratios)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task172_local_runtime.service import eval_trial_residual_gate
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _LowSideDomainInfeasible,
    _Stage3Failure,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    JointBVPCellRecord,
    JointBVPOutcome,
    build_axial_enthalpies_from_q,
)

GateEvidenceKind = Literal[
    "VALID_PRODUCTION_GATE",
    "GATE_RETURNED_NONE",
    "PROPERTY_DOMAIN_EXIT",
    "REQUEST_REBUILD_FAILED",
    "NONFINITE_OR_INVALID_BOUND",
    "OPTIMIZER_NOT_CONVERGED",
]

GoDecision = Literal["A", "B", "C"]
BvpRoute = Literal["KEEP", "STOP"]

# Block Gauss–Seidel joint BVP is closed; do not extend this prototype path.
BVP_PROTOTYPE_ROUTE: BvpRoute = "STOP"
BVP_PHYSICAL_INFEASIBILITY_PROVEN: bool = False


@dataclass(frozen=True)
class BvpCellGateRow:
    cell_index: int
    q_w: float
    twi_k: float
    two_k: float
    r1_w: float | None
    r2_w: float | None
    r3_w: float | None
    bound1_w: float | None
    bound2_w: float | None
    bound3_w: float | None
    r1_ratio: float | None
    r2_ratio: float | None
    r3_ratio: float | None
    task172_request_hash: str
    gate_evidence: GateEvidenceKind
    task172_gate_pass: bool | None
    solver_recorded_gate_pass: bool
    identity_mismatch: bool
    request_hash_mismatch: bool
    gate_status_mismatch: bool
    property_domain_status: str


@dataclass(frozen=True)
class CellProductionGateAudit:
    cell_index: int
    q_w: float
    twi_k: float
    two_k: float
    r1_w: float | None
    r2_w: float | None
    r3_w: float | None
    bound1_w: float | None
    bound2_w: float | None
    bound3_w: float | None
    r1_ratio: float | None
    r2_ratio: float | None
    r3_ratio: float | None
    production_gate_available: bool
    production_gate_pass: bool | None
    task172_request_hash: str
    property_domain_status: str
    gate_evidence: GateEvidenceKind
    identity_mismatch: bool
    request_hash_mismatch: bool
    gate_status_mismatch: bool


def _ratio_triple(
    residuals: tuple[float, ...] | None, bounds: tuple[float, ...] | None
) -> tuple[float | None, float | None, float | None]:
    if residuals is None or bounds is None or len(residuals) < 3 or len(bounds) < 3:
        return (None, None, None)
    out: list[float | None] = []
    for r, b in zip(residuals, bounds, strict=True):
        bf = float(b)
        if bf <= 0.0 or not math.isfinite(bf):
            out.append(None)
            continue
        rf = float(r)
        if not math.isfinite(rf):
            out.append(None)
            continue
        out.append(abs(rf) / bf)
    while len(out) < 3:
        out.append(None)
    return (out[0], out[1], out[2])


def snapshot_production_task172_gate(
    *,
    cell: JointBVPCellRecord,
    support: Any,
    h_t: Any,
    h_s: Any,
    provider: Any,
    shell_authority: Any,
) -> BvpCellGateRow:
    from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
        _state_from_h,
        build_task172_request_for_q,
    )

    gate: dict[str, Any] | None = None
    evidence: GateEvidenceKind = "GATE_RETURNED_NONE"
    property_status = "OK"
    req_hash = str(cell.task172_request_hash or "")
    try:
        tube_up = _state_from_h(provider, float(h_t[cell.index]), side="TUBE")
        shell_left = _state_from_h(provider, float(h_s[cell.index]), side="SHELL")
        request, _, _ = build_task172_request_for_q(
            cell.q_w,
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=shell_authority,
        )
        req_hash = str(getattr(request, "request_hash", req_hash))
        gate = eval_trial_residual_gate(request, provider, cell.q_w, cell.twi_k, cell.two_k)
    except (_LowSideDomainInfeasible, _Stage3Failure) as exc:
        property_status = type(exc).__name__
        evidence = "PROPERTY_DOMAIN_EXIT"
    except Exception:
        property_status = "REQUEST_REBUILD_FAILED"
        evidence = "REQUEST_REBUILD_FAILED"

    if evidence == "GATE_RETURNED_NONE":
        if gate is None:
            evidence = "GATE_RETURNED_NONE"
        else:
            bounds = gate.get("acceptance_bounds_w")
            if bounds and any(float(b) <= 0.0 for b in bounds):
                evidence = "NONFINITE_OR_INVALID_BOUND"
            else:
                evidence = "VALID_PRODUCTION_GATE"

    r1w = r2w = r3w = None
    b1 = b2 = b3 = None
    r1r = r2r = r3r = None
    prod_pass: bool | None = None
    if gate is not None and evidence == "VALID_PRODUCTION_GATE":
        res = gate.get("residuals_w")
        if res and len(res) >= 3:
            r1w, r2w, r3w = float(res[0]), float(res[1]), float(res[2])
        bounds = gate.get("acceptance_bounds_w")
        if bounds and len(bounds) >= 3:
            b1, b2, b3 = float(bounds[0]), float(bounds[1]), float(bounds[2])
        r1r, r2r, r3r = _ratio_triple(
            tuple(float(x) for x in res) if res else None,
            tuple(float(x) for x in bounds) if bounds else None,
        )
        prod_pass = bool(gate.get("passes_original_residual_gate"))
        req_hash = str(gate.get("request_hash", req_hash))

    gate_hash = str(gate.get("request_hash", req_hash)) if gate else req_hash
    solver_hash = str(cell.task172_request_hash or "").strip()
    hash_mismatch = bool(
        gate is not None
        and evidence == "VALID_PRODUCTION_GATE"
        and solver_hash
        and gate_hash
        and solver_hash != gate_hash
    )
    status_mismatch = prod_pass is not None and bool(prod_pass) != bool(cell.task172_gate_pass)
    identity_mismatch = hash_mismatch or status_mismatch
    return BvpCellGateRow(
        cell_index=cell.index,
        q_w=float(cell.q_w),
        twi_k=float(cell.twi_k),
        two_k=float(cell.two_k),
        r1_w=r1w,
        r2_w=r2w,
        r3_w=r3w,
        bound1_w=b1,
        bound2_w=b2,
        bound3_w=b3,
        r1_ratio=r1r,
        r2_ratio=r2r,
        r3_ratio=r3r,
        task172_request_hash=req_hash,
        gate_evidence=evidence,
        task172_gate_pass=prod_pass,
        solver_recorded_gate_pass=bool(cell.task172_gate_pass),
        identity_mismatch=identity_mismatch,
        request_hash_mismatch=hash_mismatch,
        gate_status_mismatch=status_mismatch,
        property_domain_status=property_status,
    )


def cell_gate_rows_from_outcome(
    outcome: JointBVPOutcome,
    *,
    provider: Any,
    supports: list[Any],
    shell_authority: Any,
) -> tuple[BvpCellGateRow, ...]:
    from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
        _state_at_inlet,
        effective_shell_cold_inlet_enthalpy_j_kg,
        effective_shell_mass_flow_kg_s,
        effective_tube_inlet_temperature_k,
        effective_tube_mass_flow_kg_s,
    )

    h_t0 = float(
        _state_at_inlet(
            provider, effective_tube_inlet_temperature_k(), side="TUBE"
        ).native.enthalpy_j_kg
    )
    h_sN = float(effective_shell_cold_inlet_enthalpy_j_kg())
    h_t, h_s = build_axial_enthalpies_from_q(
        [c.q_w for c in outcome.cells],
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=float(effective_tube_mass_flow_kg_s()),
        shell_mass_flow_kg_s=float(effective_shell_mass_flow_kg_s()),
    )
    rows = [
        snapshot_production_task172_gate(
            cell=cell,
            support=support,
            h_t=h_t,
            h_s=h_s,
            provider=provider,
            shell_authority=shell_authority,
        )
        for cell, support in zip(outcome.cells, supports, strict=True)
    ]
    return tuple(rows)


def audit_cell_production_gate(
    cell_index: int,
    row: BvpCellGateRow,
) -> CellProductionGateAudit:
    return CellProductionGateAudit(
        cell_index=cell_index,
        q_w=row.q_w,
        twi_k=row.twi_k,
        two_k=row.two_k,
        r1_w=row.r1_w,
        r2_w=row.r2_w,
        r3_w=row.r3_w,
        bound1_w=row.bound1_w,
        bound2_w=row.bound2_w,
        bound3_w=row.bound3_w,
        r1_ratio=row.r1_ratio,
        r2_ratio=row.r2_ratio,
        r3_ratio=row.r3_ratio,
        production_gate_available=(row.gate_evidence == "VALID_PRODUCTION_GATE"),
        production_gate_pass=row.task172_gate_pass,
        task172_request_hash=row.task172_request_hash,
        property_domain_status=row.property_domain_status,
        gate_evidence=row.gate_evidence,
        identity_mismatch=row.identity_mismatch,
        request_hash_mismatch=row.request_hash_mismatch,
        gate_status_mismatch=row.gate_status_mismatch,
    )


def physical_residual_closure(rows: tuple[BvpCellGateRow, ...]) -> Literal["PASS", "BLOCKED"]:
    for row in rows:
        if row.gate_evidence != "VALID_PRODUCTION_GATE":
            return "BLOCKED"
        if row.task172_gate_pass is not True:
            return "BLOCKED"
    return "PASS" if rows else "BLOCKED"


def verified_max_ratios(
    rows: tuple[BvpCellGateRow, ...],
) -> tuple[float | None, float | None, float | None]:
    valid = [r for r in rows if r.gate_evidence == "VALID_PRODUCTION_GATE"]

    def _max(getter: Any) -> float | None:
        vals = [getter(r) for r in valid if getter(r) is not None]
        return max(vals) if vals else None

    return (_max(lambda r: r.r1_ratio), _max(lambda r: r.r2_ratio), _max(lambda r: r.r3_ratio))


def infinite_ratio_source(rows: tuple[BvpCellGateRow, ...]) -> str:
    if any(r.gate_evidence != "VALID_PRODUCTION_GATE" for r in rows):
        kinds = {r.gate_evidence for r in rows if r.gate_evidence != "VALID_PRODUCTION_GATE"}
        return ",".join(sorted(kinds))
    return "none"


def classify_bvp_go_no_go(
    *,
    rows: tuple[BvpCellGateRow, ...],
    cell0: CellProductionGateAudit,
    optimizer_actually_converged: bool,
) -> tuple[GoDecision, str, BvpRoute, str]:
    if cell0.identity_mismatch or any(r.identity_mismatch for r in rows):
        return (
            "A",
            "EVIDENCE_IDENTITY_DEFECT",
            "KEEP",
            "align solver_recorded_gate_pass with production eval_trial_residual_gate",
        )
    if cell0.gate_evidence != "VALID_PRODUCTION_GATE":
        return (
            "A",
            "EVIDENCE_IDENTITY_DEFECT",
            "KEEP",
            f"cell0_evidence={cell0.gate_evidence}",
        )
    r1 = cell0.r1_ratio
    if r1 is not None and r1 > 1.0:
        return (
            "B",
            "BVP_SOLVER_NONCONVERGENCE",
            "STOP",
            "block_gauss_seidel joint BVP fails original Task172 at N4 (cell0 production gate)",
        )
    if physical_residual_closure(rows) == "PASS":
        return (
            "A",
            "EVIDENCE_CONTRADICTS_FROZEN_STOP",
            "STOP",
            "all production gates pass in snapshot but route frozen STOP — re-audit only",
        )
    if not optimizer_actually_converged:
        return (
            "B",
            "BVP_SOLVER_NONCONVERGENCE",
            "STOP",
            "per-cell least_squares plateau/domain or q reconcile unstable",
        )
    return (
        "B",
        "BVP_SOLVER_NONCONVERGENCE",
        "STOP",
        "local Task172 residuals remain outside acceptance",
    )


def frozen_route_closeout_decision() -> tuple[GoDecision, str, BvpRoute, bool]:
    """Authoritative closeout after cell0 audit — no further BVP execution."""
    return (
        "B",
        "BVP_SOLVER_NONCONVERGENCE",
        BVP_PROTOTYPE_ROUTE,
        BVP_PHYSICAL_INFEASIBILITY_PROVEN,
    )


__all__ = [
    "BVP_PHYSICAL_INFEASIBILITY_PROVEN",
    "BVP_PROTOTYPE_ROUTE",
    "BvpCellGateRow",
    "BvpRoute",
    "CellProductionGateAudit",
    "GateEvidenceKind",
    "GoDecision",
    "audit_cell_production_gate",
    "cell_gate_rows_from_outcome",
    "classify_bvp_go_no_go",
    "frozen_route_closeout_decision",
    "infinite_ratio_source",
    "physical_residual_closure",
    "snapshot_production_task172_gate",
    "verified_max_ratios",
]
