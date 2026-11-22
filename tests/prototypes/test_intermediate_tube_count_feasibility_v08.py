"""Intermediate envelope / tube-count scan near frozen design C."""

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.intermediate_tube_count_feasibility_v08 import (
    FINITE_ENVELOPE_SCALES,
    run_intermediate_tube_count_feasibility,
)


def test_intermediate_scan_finds_high_k_joint_prescreen_pass() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_intermediate_tube_count_feasibility(normalized, handoff, provider=provider)
    assert report.task027_regime_unchanged is True
    assert report.frozen_candidate_c_unchanged is True
    assert report.frozen_baseline["candidate_id"] == FROZEN_FIRST_JOINT_CANDIDATE_ID
    assert report.frozen_baseline["geometry_v2"] == FROZEN_FIRST_JOINT_GEOMETRY_V2
    assert report.frozen_baseline["physical_tube_count"] == 223
    assert len(report.layouts_evaluated) == len(FINITE_ENVELOPE_SCALES) * 2
    assert report.high_k_joint_prescreen_pass_count >= 2
    assert report.design_decision == "EXPERIMENTAL_PRESCREEN_PASS"
    assert report.evidence_supersession.new_tube_geometry_authority_decision == "not_proven"
    assert report.frozen_baseline["high_k_joint_prescreen_pass"] is False
    assert report.best_variant is not None
    assert report.best_variant.physical_tube_count in (235, 241)
    assert Decimal(report.best_variant.high_tube_dp_pa or "2000") <= Decimal("1150")
    plateaus = {p["physical_tube_count"] for p in report.discrete_tube_count_plateaus}
    assert 223 in plateaus
    assert 235 in plateaus or 241 in plateaus
    blocked = [r for r in report.layouts_evaluated if r.envelope_scale in ("0.85", "0.84")]
    assert blocked
    assert all(
        r.isolation.task027_blocker_code == "BL_T027_UNSUPPORTED_REYNOLDS_REGIME"
        for r in blocked
        if r.isolation.task027_status == "BLOCKED"
    )
