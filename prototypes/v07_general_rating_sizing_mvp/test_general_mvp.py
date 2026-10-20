"""Tests for general rating + sizing MVP."""

# ruff: noqa: E501

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1
from prototypes.v07_general_rating_sizing_mvp.preflight import enumerate_task168_candidates
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task168_request,
    build_task173_sizing_request,
)
from prototypes.v07_general_rating_sizing_mvp.workflow import run_general_engineering_workflow

CASE_PATH = Path(__file__).resolve().parent / "cases" / "mvp_district_heating_water_water_r1.json"


def _load_case() -> GeneralEngineeringCaseV1:
    return GeneralEngineeringCaseV1.model_validate_json(CASE_PATH.read_text(encoding="utf-8"))


def test_case_json_parses_and_differs_from_validation_defaults() -> None:
    case = _load_case()
    assert case.engineering_case_id == "mvp-district-heating-water-water-r1"
    assert case.target_duty_w == Decimal("9500")
    assert case.candidate_constraints.shell_inside_diameter_m == Decimal("0.8")
    assert len(case.candidate_constraints.tube_lengths_m) == 3


def test_out_of_envelope_mass_flow_blocked() -> None:
    case = _load_case()
    bad = case.model_copy(
        update={"cold_side": case.cold_side.model_copy(update={"mass_flow_kg_s": Decimal("11.0")})}
    )
    status, detail = bad.applicability_status()
    assert status == "BLOCKED"
    assert detail is not None


def test_task168_generates_distinct_candidates() -> None:
    case = _load_case()
    task168 = build_task168_request(case)
    sizing = build_task173_sizing_request(case)
    assert task168.shell_geometry_catalog.records
    preflight = enumerate_task168_candidates(sizing)
    assert preflight["status"] == "VALID"
    assert preflight["candidate_count"] >= 3
    assert preflight["distinct_geometry_count"] >= 3
    assert preflight.get("structurally_admitted_count", 0) >= 1
    ids = {row["candidate_id"] for row in preflight["candidates"]}
    assert len(ids) == preflight["candidate_count"]
    assert "e152cca9" not in "".join(ids)  # not hard-coded Candidate B pin


def test_preflight_workflow_writes_reports(tmp_path: Path) -> None:
    case = _load_case()
    outcome = run_general_engineering_workflow(case, tmp_path, run_full_rating=False)
    assert outcome.status == "PARTIAL_RATING_BUDGET"
    assert outcome.report_json_path is not None
    assert outcome.report_md_path is not None
    assert outcome.report_json_path.is_file()
    report = json.loads(outcome.report_json_path.read_text(encoding="utf-8"))
    assert report["production_design_approved"] is False


@pytest.mark.slow
def test_full_sizing_end_to_end(tmp_path: Path) -> None:
    base = _load_case()
    case = base.model_copy(
        update={
            "candidate_constraints": base.candidate_constraints.model_copy(
                update={
                    "tube_lengths_m": (Decimal("5.20"),),
                    "baffle_spacings_m": (Decimal("0.88"),),
                }
            ),
            "solver_budget": base.solver_budget.model_copy(update={"max_candidates_to_rate": 1}),
        }
    )
    outcome = run_general_engineering_workflow(case, tmp_path, run_full_rating=True)
    assert outcome.status in {"EXPERIMENTAL_COMPLETE", "BLOCKED_SIZING"}
    assert (tmp_path / "TASK173_SIZING_OUTCOME.json").is_file()
