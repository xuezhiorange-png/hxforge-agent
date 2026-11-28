"""R2 gate: separated engineering axes and no premature robust candidate."""

from __future__ import annotations

from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    EngineeringShortlistRobustnessReport,
)

pytest_plugins = ["tests.prototypes.conftest_v08_engineering_shortlist"]


def test_no_engineering_recommended_and_no_robust_proven(
    engineering_shortlist_report_330: EngineeringShortlistRobustnessReport,
) -> None:
    report = engineering_shortlist_report_330
    assert report.engineering_recommended is None
    assert report.robust_candidate_proven is False
    assert "NO_ROBUST_CANDIDATE_PROVEN" in report.final_engineering_decision


def test_regime_priority_excludes_241_blocked_layouts(
    engineering_shortlist_report_330: EngineeringShortlistRobustnessReport,
) -> None:
    report = engineering_shortlist_report_330
    assert report.regime_robustness_priority is not None
    assert report.regime_robustness_priority.shortlist_key.startswith("T235")


def test_layout_engineering_status_axes(
    engineering_shortlist_report_330: EngineeringShortlistRobustnessReport,
) -> None:
    report = engineering_shortlist_report_330
    eng = report.layout_engineering_status_by_key
    assert eng["T235_L5.5"] == "OPERATING_RANGE_THERMAL_FAIL"
    assert eng["T235_L6.0"] == "HYDRAULIC_SENSITIVITY_NOT_VERIFIED"
    assert eng["T241_L5.5"] == "PHYSICAL_MODEL_APPLICABILITY_BLOCKED"
    row_l55 = next(r for r in report.layouts if r.shortlist_key == "T235_L5.5")
    minus1 = next(s for s in row_l55.sensitivity if s.scenario_key == "tube_mdot_minus_1pct")
    assert minus1.robustness_evidence_status == "HYDRAULIC_SENSITIVITY_NOT_VERIFIED"
    assert minus1.high_k_dp_computed is False
