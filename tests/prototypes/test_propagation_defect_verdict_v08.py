"""Propagation defect must not blame face propagation for outer terminal residuals."""

from __future__ import annotations

from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import AuditContextSnapshot
from prototypes.v08_thermal_rating.enthalpy_precision_trace_v08 import EnthalpyPrecisionTrace
from prototypes.v08_thermal_rating.propagation_defect_verdict_v08 import (
    assess_propagation_defect_verdict,
)


def test_frozen_n4_scale_mismatch_not_causal_propagation() -> None:
    ctx = AuditContextSnapshot(
        status="VALID",
        audit_case_id="HXFORGE_330KW_STRICT_DP",
        audit_tube_inlet_k="310",
        audit_shell_inlet_k="295",
        audit_tube_mdot="12",
        audit_shell_mdot="20",
        authority_shell_inlet_h_j_kg="91746.66945958413",
        notes=(),
    )
    trace = EnthalpyPrecisionTrace(
        subdivisions=4,
        shooting_enthalpy_j_kg="",
        rows=(),
        cumulative_face_prediction_error_j_kg=2.2906666666666665e-10,
        max_ph_roundtrip_error_j_kg=0.0,
        first_precision_loss_cell=None,
        shell_cold_inlet_authority_j_kg="",
        shell_cold_inlet_face_j_kg="",
        shell_inlet_face_minus_authority_j_kg="",
        terminal_residual_k="1.13598E-8",
        terminal_residual_j_kg="0.00004757584",
        defect_attributed_to="local_q_root_or_other",
        max_tp_ph_delta_h_j_kg=0.0,
        max_tp_ph_delta_t_k=0.0,
    )
    from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import TpPhReconstructionAudit

    tp = TpPhReconstructionAudit(
        query_status="PASS",
        delta_t_k="0",
        delta_h_j_kg="0",
        h_tp_j_kg="1",
        t_ph_k="295",
        h_ph_j_kg="1",
        property_provider_identity="CoolPropProvider",
        user_fluid_identity="PURE_ORDINARY_WATER",
        coolprop_fluid_name="Water",
        mapping_basis="test",
        property_exception=None,
    )
    v = assess_propagation_defect_verdict(
        context=ctx,
        trace=trace,
        consistency_status="BLOCKED",
        tp_ph=tp,
        task172_gate="BLOCKED",
    )
    assert v.propagation_defect_causal_proof == "false"
    assert v.enthalpy_propagation_defect_confirmed is False
    assert v.outer_terminal_residual_j_kg > v.cell_enthalpy_propagation_error_j_kg * 1e4
