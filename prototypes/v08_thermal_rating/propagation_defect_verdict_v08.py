"""Conservative propagation-defect causality (prototype; not production contract)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import (
    AuditContextSnapshot,
    TpPhReconstructionAudit,
    enthalpy_audit_precision_threshold_j_kg,
)
from prototypes.v08_thermal_rating.enthalpy_precision_trace_v08 import EnthalpyPrecisionTrace

ConsistencyStatus = Literal["CONSISTENT", "BLOCKED", "NOT_EVALUATED"]

CausalProof = Literal["true", "false", "unresolved"]
LocalRootStatus = Literal["PASS", "BLOCKED", "NOT_EVALUATED"]


@dataclass(frozen=True)
class PropagationDefectVerdict:
    cell_enthalpy_propagation_error_j_kg: float
    state_ph_reconstruction_error_j_kg: float | None
    outer_terminal_residual_j_kg: float
    local_constitutive_root_status: LocalRootStatus
    propagation_defect_causal_proof: CausalProof
    enthalpy_propagation_defect_confirmed: bool | Literal["unresolved"]


def assess_propagation_defect_verdict(
    *,
    context: AuditContextSnapshot,
    trace: EnthalpyPrecisionTrace,
    consistency_status: ConsistencyStatus,
    tp_ph: TpPhReconstructionAudit | None,
    task172_gate: str,
) -> PropagationDefectVerdict:
    if context.status != "VALID":
        return PropagationDefectVerdict(
            cell_enthalpy_propagation_error_j_kg=trace.cumulative_face_prediction_error_j_kg,
            state_ph_reconstruction_error_j_kg=None,
            outer_terminal_residual_j_kg=abs(float(trace.terminal_residual_j_kg or "0")),
            local_constitutive_root_status="NOT_EVALUATED",
            propagation_defect_causal_proof="unresolved",
            enthalpy_propagation_defect_confirmed="unresolved",
        )

    thresh = enthalpy_audit_precision_threshold_j_kg()
    prop = trace.cumulative_face_prediction_error_j_kg
    term = abs(float(trace.terminal_residual_j_kg or "0"))
    ph_err: float | None
    if tp_ph is not None and tp_ph.query_status == "PASS" and tp_ph.delta_h_j_kg is not None:
        ph_err = abs(float(tp_ph.delta_h_j_kg))
    else:
        ph_err = trace.max_ph_roundtrip_error_j_kg

    local_status: LocalRootStatus = (
        "BLOCKED"
        if task172_gate == "BLOCKED"
        else "PASS"
        if task172_gate == "PASS"
        else "NOT_EVALUATED"
    )

    reconstruction_dominates = ph_err is not None and ph_err > thresh and ph_err >= prop * 1000.0
    constitutive_explains = consistency_status == "BLOCKED" and local_status == "BLOCKED"
    propagation_explains_terminal = prop > thresh and term > 0 and prop >= term * 0.01

    if propagation_explains_terminal and not reconstruction_dominates and not constitutive_explains:
        causal: CausalProof = "true"
        confirmed: bool | Literal["unresolved"] = True
    elif term > max(prop, thresh) * 100.0:
        causal = "false"
        confirmed = False
    else:
        causal = "false"
        confirmed = False

    return PropagationDefectVerdict(
        cell_enthalpy_propagation_error_j_kg=prop,
        state_ph_reconstruction_error_j_kg=ph_err,
        outer_terminal_residual_j_kg=term,
        local_constitutive_root_status=local_status,
        propagation_defect_causal_proof=causal,
        enthalpy_propagation_defect_confirmed=confirmed,
    )


__all__ = ["PropagationDefectVerdict", "assess_propagation_defect_verdict"]
