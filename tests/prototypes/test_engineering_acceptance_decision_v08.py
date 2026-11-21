"""Engineering acceptance layers and negative controls."""

from __future__ import annotations

from pathlib import Path

from prototypes.v08_thermal_rating.engineering_acceptance_decision_v08 import (
    build_engineering_acceptance_decision,
)
from prototypes.v08_thermal_rating.engineering_physical_evaluator_v08 import (
    assess_engineering_physical_layer,
    load_frozen_330_evidence,
    run_negative_controls,
)

_REPO = Path(__file__).resolve().parents[2]
FIXTURE = _REPO / "tests/fixtures/v08_03_frozen_330kw_engineering_evidence.json"


def test_negative_controls_pass() -> None:
    neg = run_negative_controls()
    assert neg.status == "PASS"
    assert neg.energy_inversion_blocked
    assert neg.wall_order_inversion_blocked


def test_frozen_330_contract_review_eligible_without_auto_tolerance_change() -> None:
    ev = load_frozen_330_evidence(FIXTURE)
    physical = assess_engineering_physical_layer(ev, tp_ph_query_status="PASS")
    neg = run_negative_controls()
    pkg = build_engineering_acceptance_decision(
        ev=ev,
        physical=physical,
        negative=neg,
        task172_gate="BLOCKED",
        task173_gate="BLOCKED",
    )
    assert pkg.production_numerical_status == "BLOCKED"
    assert pkg.contract_review_eligibility == "ELIGIBLE"
    assert pkg.engineering_acceptance == "BLOCKED"
    assert pkg.recommended_contract_change != "none"
    assert "330000" not in pkg.recommended_contract_change  # no back-solved tolerance