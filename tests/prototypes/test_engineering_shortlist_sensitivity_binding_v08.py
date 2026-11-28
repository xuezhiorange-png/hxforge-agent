"""Regression tests for fixed-layout sensitivity replay (V08-03 shortlist)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    EngineeringShortlistRobustnessReport,
    artifact_dict,
)

pytest_plugins = ["tests.prototypes.conftest_v08_engineering_shortlist"]


def _scenario(layouts: tuple, key: str, scenario: str):
    row = next(r for r in layouts if r.shortlist_key == key)
    return next(s for s in row.sensitivity if s.scenario_key == scenario)


def test_fixed_layout_tube_flow_re_monotonicity(
    engineering_shortlist_report_330: EngineeringShortlistRobustnessReport,
) -> None:
    report = engineering_shortlist_report_330
    assert report.replay_binding_defect_confirmed is True
    assert report.canonical_shortlist_size == 4
    assert report.distinct_audited_layout_hash_count == 10
    base = _scenario(report.layouts, "T235_L5.5", "baseline")
    minus1 = _scenario(report.layouts, "T235_L5.5", "tube_mdot_minus_1pct")
    minus3 = _scenario(report.layouts, "T235_L5.5", "tube_mdot_minus_3pct")
    plus3 = _scenario(report.layouts, "T235_L5.5", "tube_mdot_plus_3pct")
    shellp = _scenario(report.layouts, "T235_L5.5", "shell_mdot_plus_3pct")
    assert base.task027_raw_blocker_code is None
    assert minus1.task168_wrapper_code is None
    assert Decimal(minus1.task026_reynolds or "0") < Decimal(base.task026_reynolds or "1")
    assert Decimal(plus3.task026_reynolds or "0") > Decimal(base.task026_reynolds or "0")
    assert minus3.task026_reynolds == "4004.1900"
    assert shellp.task026_reynolds == base.task026_reynolds
    audit = shellp.binding_audit
    assert audit.task021_layout_hash_expected == audit.task021_layout_hash_observed


def test_task027_physical_block_on_241_minus_flow(
    engineering_shortlist_report_330: EngineeringShortlistRobustnessReport,
) -> None:
    report = engineering_shortlist_report_330
    m3 = _scenario(report.layouts, "T241_L6.0", "tube_mdot_minus_3pct")
    assert m3.robustness_evidence_status == "PHYSICAL_MODEL_APPLICABILITY_BLOCKED"
    assert m3.task027_raw_blocker_code == "BL_T027_UNSUPPORTED_REYNOLDS_REGIME"
    assert m3.task168_wrapper_code is None
    assert m3.high_k_dp_computed is False


def test_r2_artifact_supersedes_r1_without_removing_r1(
    engineering_shortlist_report_330: EngineeringShortlistRobustnessReport,
) -> None:
    r1 = Path("docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r1.json")
    assert r1.is_file(), "historical r1 evidence must remain on disk"
    payload = artifact_dict(engineering_shortlist_report_330)
    assert payload["schema"] == "hxforge.engineering-shortlist-robustness.v3"
    r2 = "docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r2.json"
    assert payload["supersedes"] == r2


def test_nonbaseline_high_k_not_fabricated(
    engineering_shortlist_report_330: EngineeringShortlistRobustnessReport,
) -> None:
    report = engineering_shortlist_report_330
    nonbaseline = [
        s for row in report.layouts for s in row.sensitivity if s.scenario_key != "baseline"
    ]
    for s in nonbaseline:
        if not s.high_k_dp_computed:
            assert s.high_tube_dp_pa is None
            assert s.high_tube_margin_pa is None
