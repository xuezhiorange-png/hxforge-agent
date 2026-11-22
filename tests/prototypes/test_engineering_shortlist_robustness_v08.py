"""Engineering shortlist (235/241 × 5.5/6.0 m canonical layouts)."""

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    run_engineering_shortlist_robustness,
)


def test_engineering_shortlist_four_physical_layouts() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_engineering_shortlist_robustness(normalized, handoff, provider=provider)
    assert report.frozen_candidate_c_unchanged is True
    assert report.unique_physical_layout_count == 4
    assert len(report.layouts) == 4
    keys = {row.shortlist_key for row in report.layouts}
    assert keys == {"T235_L5.5", "T235_L6.0", "T241_L5.5", "T241_L6.0"}
    assert "layout_hash" in report.identity_binding_status
    assert report.task173_production_rating_status == "BLOCKED"
    assert report.placement_envelope_approval_required is True
    assert report.new_tube_catalog_record_required == "not_proven"
    assert report.clean_330kw_status == "MET_CLEAN_CONTRACT"
    assert report.fouled_330kw_status == "FOULED_BELOW_330KW_T039_DEMO"
    for row in report.layouts:
        base = next(s for s in row.sensitivity if s.scenario_key == "baseline")
        assert base.task027_status == "PASS"
        assert Decimal(base.task026_reynolds or "0") >= Decimal("4000")
    minus_three = [
        s
        for row in report.layouts
        for s in row.sensitivity
        if s.scenario_key == "tube_mdot_minus_3pct"
    ]
    assert len(minus_three) == 4
    assert all(s.task027_status == "BLOCKED" for s in minus_three)
    assert report.thermal_priority is not None
    assert report.engineering_recommended is not None