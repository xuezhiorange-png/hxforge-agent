"""Engineering shortlist (235/241 × 5.5/6.0 m canonical layouts) — baseline contract."""

from __future__ import annotations

from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    EngineeringShortlistRobustnessReport,
)

pytest_plugins = ["tests.prototypes.conftest_v08_engineering_shortlist"]


def test_engineering_shortlist_four_physical_layouts(
    engineering_shortlist_report_330: EngineeringShortlistRobustnessReport,
) -> None:
    report = engineering_shortlist_report_330
    assert report.frozen_candidate_c_unchanged is True
    assert report.canonical_shortlist_size == 4
    assert len(report.layouts) == 4
    keys = {row.shortlist_key for row in report.layouts}
    assert keys == {"T235_L5.5", "T235_L6.0", "T241_L5.5", "T241_L6.0"}
    assert report.task173_production_rating_status == "BLOCKED"
    assert report.clean_330kw_status == "MET_CLEAN_CONTRACT"
    assert report.engineering_acceptance_status == "EXPERIMENTAL_PRESCREEN_ONLY"
