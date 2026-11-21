"""Engineering acceptance layers and negative controls."""

from __future__ import annotations

from pathlib import Path

from prototypes.v08_thermal_rating.engineering_acceptance_decision_v08 import (
    build_engineering_acceptance_decision,
)
from prototypes.v08_thermal_rating.engineering_physical_evaluator_v08 import (
    assess_engineering_physical_layer,
    load_frozen_330_evidence,
    run_negative_controls_via_evaluator,
)

_REPO = Path(__file__).resolve().parents[2]
FIXTURE = _REPO / "tests/fixtures/v08_03_frozen_330kw_engineering_evidence.json"


def test_negative_controls_on_real_evaluator() -> None:
    ev = load_frozen_330_evidence(FIXTURE)
    neg = run_negative_controls_via_evaluator(ev, tp_ph_query_status="PASS")
    assert neg.status == "PASS"
    rules = {r.scenario: r.rejected_by_rule for r in neg.rows}
    assert rules["duty_below_330kw"].startswith("duty_screen:")
    assert rules["energy_balance_imbalance"] == "energy_balance:failed"
    assert rules["wall_temperature_order_inverted"] == "wall_temperature_order:BLOCKED"


def test_frozen_330_partial_physical_evidence_not_sufficient() -> None:
    ev = load_frozen_330_evidence(FIXTURE)
    physical = assess_engineering_physical_layer(ev, tp_ph_query_status="PASS")
    neg = run_negative_controls_via_evaluator(ev, tp_ph_query_status="PASS")
    pkg = build_engineering_acceptance_decision(
        ev=ev,
        physical=physical,
        negative=neg,
        task172_gate="BLOCKED",
        task173_gate="BLOCKED",
    )
    assert physical.grade == "PARTIAL"
    assert physical.screens.energy_balance == "not_evaluated"
    assert pkg.duty_screen == "INDICATIVE_PASS"
    assert pkg.hydraulic_screen == "PASS"
    assert pkg.local_heat_transfer == "BLOCKED"
    assert pkg.mesh_convergence == "BLOCKED"
    assert pkg.engineering_physical_evidence == "PARTIAL"
    assert pkg.production_numerical_status == "BLOCKED"
    assert pkg.contract_review_status == "ELIGIBLE_FOR_DISCUSSION"
    assert pkg.contract_change_evidence == "INSUFFICIENT"
    assert pkg.production_tolerance_change_approved is False
    assert pkg.engineering_acceptance == "BLOCKED"
    assert pkg.production_contract_change_authorized is False
