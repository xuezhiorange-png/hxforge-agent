"""Regression tests for fixed-layout sensitivity replay (V08-03 shortlist)."""

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    artifact_dict,
    run_engineering_shortlist_robustness,
)


def _scenario(layouts: tuple, key: str, scenario: str):
    row = next(r for r in layouts if r.shortlist_key == key)
    return next(s for s in row.sensitivity if s.scenario_key == scenario)


def test_fixed_layout_tube_flow_re_monotonicity() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_engineering_shortlist_robustness(normalized, handoff, provider=provider)
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


def test_task027_physical_block_on_241_minus_flow() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_engineering_shortlist_robustness(normalized, handoff, provider=provider)
    m3 = _scenario(report.layouts, "T241_L6.0", "tube_mdot_minus_3pct")
    assert m3.robustness_evidence_status == "PHYSICAL_MODEL_APPLICABILITY_BLOCKED"
    assert m3.task027_raw_blocker_code == "BL_T027_UNSUPPORTED_REYNOLDS_REGIME"
    assert m3.task168_wrapper_code is None
    assert m3.high_k_dp_computed is False


def test_r2_artifact_supersedes_r1_without_removing_r1() -> None:
    from pathlib import Path

    r1 = Path("docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r1.json")
    assert r1.is_file(), "historical r1 evidence must remain on disk"
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_engineering_shortlist_robustness(normalized, handoff, provider=provider)
    payload = artifact_dict(report)
    assert payload["schema"] == "hxforge.engineering-shortlist-robustness.v2"
    assert payload["supersedes"] == "docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r1.json"


def test_nonbaseline_high_k_not_fabricated() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_engineering_shortlist_robustness(normalized, handoff, provider=provider)
    nonbaseline = [
        s for row in report.layouts for s in row.sensitivity if s.scenario_key != "baseline"
    ]
    for s in nonbaseline:
        if not s.high_k_dp_computed:
            assert s.high_tube_dp_pa is None
            assert s.high_tube_margin_pa is None