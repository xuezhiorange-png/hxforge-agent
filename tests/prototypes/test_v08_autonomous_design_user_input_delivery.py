"""V08_AUTONOMOUS_DESIGN_USER_INPUT_DELIVERY targeted tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250, FIXTURE_330
from prototypes.v08_thermal_rating.v08_autonomous_design_tool import (
    ENGINEERING_DESIGN_STATUS,
    ingest_user_design_input,
    run_autonomous_design_tool,
)

REPO = Path(__file__).resolve().parents[2]
FIXTURE_TIGHT = REPO / "tests/fixtures/v08_user_case_330kw_tight_envelope.json"
FIXTURE_INFEASIBLE = REPO / "tests/fixtures/v08_user_case_infeasible_duty_5mw.json"


@pytest.fixture(scope="module")
def provider() -> CoolPropProvider:
    return CoolPropProvider()


def test_unsupported_fluid_blocked_at_schema(provider: CoolPropProvider) -> None:
    base = json.loads(FIXTURE_330.read_text(encoding="utf-8"))
    base["tube_side"]["fluid"] = "NOT_A_SUPPORTED_FLUID"
    ingestion = ingest_user_design_input(json.dumps(base), provider=provider)
    assert ingestion.ok is False
    assert ingestion.blockers


def test_330kw_dynamic_generation_exceeds_fixed_shortlist(provider: CoolPropProvider) -> None:
    report = run_autonomous_design_tool(
        FIXTURE_330.read_text(encoding="utf-8"),
        provider=provider,
        max_candidates=32,
        run_mdot_on_recommendation=False,
    )
    assert report.ingestion.ok
    assert report.structural_candidates_generated >= 7
    assert report.engineering_design_status == ENGINEERING_DESIGN_STATUS
    assert report.recommended_layout_key is not None
    spec = report.design_specification
    assert spec is not None
    assert "geometry" in spec and "thermal_experimental_prescreen" in spec
    assert len(spec.get("nozzles_four_port", [])) == 4


def test_250kw_independent_generation_not_hardcoded_rank(provider: CoolPropProvider) -> None:
    r330 = run_autonomous_design_tool(
        FIXTURE_330.read_text(encoding="utf-8"),
        provider=provider,
        max_candidates=24,
        run_mdot_on_recommendation=False,
    )
    r250 = run_autonomous_design_tool(
        FIXTURE_250.read_text(encoding="utf-8"),
        provider=provider,
        max_candidates=24,
        run_mdot_on_recommendation=False,
    )
    assert r250.structural_candidates_generated > 0
    assert r250.ingestion.engineering_case_id != r330.ingestion.engineering_case_id
    by330 = {r.layout_key: r.thermal_q_w for r in r330.candidate_records if r.thermal_q_w}
    by250 = {r.layout_key: r.thermal_q_w for r in r250.candidate_records if r.thermal_q_w}
    shared = set(by330) & set(by250)
    assert shared, "expected overlapping manufacturable layouts across cases"
    assert any(by330[k] != by250[k] for k in shared), "thermal prescreen Q must track case duty/target"


def test_constraint_change_reduces_or_shifts_candidates(provider: CoolPropProvider) -> None:
    wide = run_autonomous_design_tool(
        FIXTURE_330.read_text(encoding="utf-8"),
        provider=provider,
        max_candidates=32,
        run_mdot_on_recommendation=False,
    )
    tight = run_autonomous_design_tool(
        FIXTURE_TIGHT.read_text(encoding="utf-8"),
        provider=provider,
        max_candidates=32,
        run_mdot_on_recommendation=False,
    )
    assert tight.structural_candidates_generated <= wide.structural_candidates_generated
    assert (
        tight.structural_candidates_generated < wide.structural_candidates_generated
        or tight.rankings != wide.rankings
        or tight.recommended_layout_key != wide.recommended_layout_key
    )


def test_infeasible_duty_no_forced_recommendation(provider: CoolPropProvider) -> None:
    report = run_autonomous_design_tool(
        FIXTURE_INFEASIBLE.read_text(encoding="utf-8"),
        provider=provider,
        max_candidates=24,
        run_mdot_on_recommendation=False,
    )
    assert report.ingestion.ok
    assert report.no_feasible_candidate is True
    assert report.recommended_layout_key is None
    assert report.design_specification is None
    assert report.structural_candidates_generated == 0 or not any(
        r.engineering_joint_pass for r in report.candidate_records
    )