"""High-K tube resistance budget and authorized 0.52 m variant scan."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.high_k_tube_side_structural_feasibility_v08 import (
    run_high_k_tube_side_structural_feasibility,
)


def test_design_c_high_k_budget_and_authorized_space_blocked() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_high_k_tube_side_structural_feasibility(normalized, handoff, provider=provider)
    assert report.frozen_candidate_c_unchanged is True
    assert report.design_c_reference["geometry_v2"] == FROZEN_FIRST_JOINT_GEOMETRY_V2
    assert Decimal(report.high_tube_dp_baseline_pa).quantize(Decimal("0.001")) == Decimal(
        "1198.676"
    )
    assert Decimal(report.high_tube_dp_nozzle_lower_bound_pa).quantize(Decimal("0.001")) == (
        Decimal("1197.218")
    )
    assert Decimal(report.high_tube_dp_excess_pa) == Decimal("48.676")
    assert report.tube_internal_friction_dp_pa == "567.893"
    assert Decimal(report.tube_local_dp_pa or "0") == Decimal("630.783")
    assert Decimal(report.tube_nozzle_pair_dp_pa or "0") == Decimal("549.627")
    assert report.existing_authorized_variant_feasible is False
    assert report.design_decision == "EXISTING_AUTHORIZED_SPACE_BLOCKED"
    assert report.new_tube_geometry_authority_required is False
    assert report.authorized_variants_evaluated >= 2
    design_c = next(v for v in report.variants if v.geometry_v2 == FROZEN_FIRST_JOINT_GEOMETRY_V2)
    assert Decimal(design_c.clean_q_w or "0") >= Decimal("330000")
    assert "HIGH_TUBE_DP" in design_c.failure_reasons[0]
