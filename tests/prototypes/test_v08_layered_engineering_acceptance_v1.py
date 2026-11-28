"""Layered contract negative controls (no mesh solve)."""

from __future__ import annotations

from prototypes.v08_thermal_rating.v08_layered_engineering_acceptance_v1 import (
    DualContractVerdict,
    IndependentErrorBudgetEvidence,
    LayerEvidence,
    run_layered_negative_controls,
)


def test_layered_negative_controls_reject_perturbations() -> None:
    template = DualContractVerdict(
        contract_id="V08_LAYERED_ENGINEERING_ACCEPTANCE_V1",
        original_production_acceptance="BLOCKED",
        original_detail={},
        experimental_engineering_acceptance="BLOCKED",
        experimental_detail={},
        layers=(
            LayerEvidence("L1", "BLOCKED", {"task172_numerical_holes": 1}),
            LayerEvidence("L2", "PASS", {"tp_ph_status": "PASS"}),
            LayerEvidence("L3", "BLOCKED", {"energy_balance_pass": True, "mesh_gates": {}}),
            LayerEvidence("L4", "BLOCKED", {"duty_at_or_above_target": False}),
        ),
        error_budget=IndependentErrorBudgetEvidence(
            independently_derived=True,
            task172_culp_ceiling=1.0,
            terminal_temperature_contract_k="1E-8",
            terminal_enthalpy_formula="cp*1e-8+ulp(h)",
            property_tp_ph_max_delta_h_j_kg=0.0,
            property_tp_ph_max_delta_t_k=0.0,
            float_ulp_water_300k_h_j_kg=1e-8,
            mesh_discretization_note="test",
            derivation_sources=("test",),
        ),
        geometry_projection_hash="g",
        candidate_id="c",
        rating_request_hash="r",
        normalized_input_hash="n",
    )
    neg = run_layered_negative_controls(template)
    assert neg.false_acceptance_count == 0
    assert neg.status == "PASS"
