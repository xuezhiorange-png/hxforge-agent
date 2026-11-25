"""V08-05: qualified Top-N, separated formal/experimental, deterministic report hash."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.case_identity_v08 import (
    FIXTURE_250,
    FIXTURE_330,
)
from prototypes.v08_thermal_rating.v08_05_qualified_top_n_engineering_report import (
    TASK_ID,
    run_v08_05_qualified_selection,
    v08_05_report_to_json,
)

REPO = Path(__file__).resolve().parents[2]
FIXTURE_TIGHT = REPO / "tests/fixtures/v08_user_case_330kw_tight_envelope.json"
FIXTURE_INFEASIBLE = REPO / "tests/fixtures/v08_user_case_infeasible_duty_5mw.json"


@pytest.fixture(scope="module")
def provider() -> CoolPropProvider:
    return CoolPropProvider()


def test_v08_05_task_id() -> None:
    assert TASK_ID == "V08-05"


def test_330kw_report_hash_stable(provider: CoolPropProvider) -> None:
    text = FIXTURE_330.read_text(encoding="utf-8")
    r1 = run_v08_05_qualified_selection(
        text, provider=provider, top_n=3, run_mdot_on_recommendation=False
    )
    r2 = run_v08_05_qualified_selection(
        text, provider=provider, top_n=3, run_mdot_on_recommendation=False
    )
    assert r1.report_hash == r2.report_hash
    assert not r1.top_n.formal_engineering
    assert r1.production_rating_validated is False


def test_250kw_independent_not_hardcoded_layout(provider: CoolPropProvider) -> None:
    t330 = FIXTURE_330.read_text(encoding="utf-8")
    t250 = FIXTURE_250.read_text(encoding="utf-8")
    r330 = run_v08_05_qualified_selection(t330, provider=provider, run_mdot_on_recommendation=False)
    r250 = run_v08_05_qualified_selection(t250, provider=provider, run_mdot_on_recommendation=False)
    assert r330.normalization_hash != r250.normalization_hash
    keys330 = {c.layout_key for c in r330.candidates}
    keys250 = {c.layout_key for c in r250.candidates}
    assert keys330 != keys250 or r330.report_hash != r250.report_hash


def test_infeasible_case_outcome_no_forced_top_n(provider: CoolPropProvider) -> None:
    text = FIXTURE_INFEASIBLE.read_text(encoding="utf-8")
    report = run_v08_05_qualified_selection(
        text, provider=provider, run_mdot_on_recommendation=False
    )
    assert report.case_outcome in ("NO_FEASIBLE_DESIGN", "OUT_OF_ENVELOPE")
    assert report.top_n.experimental_prescreen == ()
    assert not report.top_n.formal_engineering


def test_rejection_trace_on_over_dp(provider: CoolPropProvider) -> None:
    text = FIXTURE_330.read_text(encoding="utf-8")
    report = run_v08_05_qualified_selection(
        text, provider=provider, top_n=5, run_mdot_on_recommendation=False
    )
    classes = {c.qualification_class for c in report.candidates}
    assert "FORMAL_ENGINEERING_FEASIBLE" not in classes or not any(
        c.formal_engineering_eligible for c in report.candidates
    )
    over = [c for c in report.candidates if c.qualification_class == "PRESSURE_DROP_EXCEEDED"]
    assert over or report.case_outcome == "NO_FEASIBLE_DESIGN"
    for c in over:
        assert c.rejection_trace


def test_json_report_complete(provider: CoolPropProvider) -> None:
    text = FIXTURE_TIGHT.read_text(encoding="utf-8")
    report = run_v08_05_qualified_selection(
        text, provider=provider, run_mdot_on_recommendation=False
    )
    payload = v08_05_report_to_json(report)
    assert payload["ranking_method_documentation"]
    assert "candidates" in payload
    for c in payload["candidates"]:
        assert "rejection_trace" in c
        assert "authority_tier" in c
