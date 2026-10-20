"""Tests for general rating + sizing MVP."""

# ruff: noqa: E501

from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1
from prototypes.v07_general_rating_sizing_mvp.preflight import enumerate_task168_candidates
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task168_request,
    build_task173_sizing_request,
    sizing_request_identity,
)
from prototypes.v07_general_rating_sizing_mvp.workflow import run_general_engineering_workflow

CASE_PATH = Path(__file__).resolve().parent / "cases" / "mvp_district_heating_water_water_r1.json"
PHYSICAL_CASE_PATH = Path(__file__).resolve().parent / "cases" / "mvp_water_water_physical_r2.json"


def _load_case(path: Path = CASE_PATH) -> GeneralEngineeringCaseV1:
    return GeneralEngineeringCaseV1.model_validate_json(path.read_text(encoding="utf-8"))


def test_case_json_parses_and_differs_from_validation_defaults() -> None:
    case = _load_case()
    assert case.engineering_case_id == "mvp-district-heating-water-water-r1"
    assert case.target_duty_w == Decimal("9500")
    assert case.candidate_constraints.shell_inside_diameter_m == Decimal("0.8")
    assert len(case.candidate_constraints.tube_lengths_m) == 3


def test_r1_case_physical_direction_conflict_blocked() -> None:
    case = _load_case()
    status, detail = case.applicability_status()
    assert status == "BLOCKED"
    assert detail is not None
    assert "hot_side.inlet_temperature_k" in detail


def test_physical_r2_case_in_scope() -> None:
    case = _load_case(PHYSICAL_CASE_PATH)
    status, detail = case.applicability_status()
    assert status == "IN_SCOPE"
    assert detail is None


def test_out_of_envelope_mass_flow_blocked() -> None:
    case = _load_case(PHYSICAL_CASE_PATH)
    bad = case.model_copy(
        update={"cold_side": case.cold_side.model_copy(update={"mass_flow_kg_s": Decimal("11.0")})}
    )
    status, detail = bad.applicability_status()
    assert status == "BLOCKED"
    assert detail is not None


def test_runtime_builder_does_not_import_tests_module() -> None:
    builder_path = Path(__file__).resolve().parent / "sizing_request_builder.py"
    tree = ast.parse(builder_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("tests"), alias.name
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("tests"), node.module


def test_engineering_temperature_changes_native_request_hash() -> None:
    base = _load_case(PHYSICAL_CASE_PATH)
    warm = base.model_copy(
        update={
            "hot_side": base.hot_side.model_copy(update={"inlet_temperature_k": Decimal("299.85")})
        }
    )
    h0 = sizing_request_identity(build_task173_sizing_request(base))
    h1 = sizing_request_identity(build_task173_sizing_request(warm))
    assert h0 != h1


def test_engineering_pressure_changes_native_request_hash() -> None:
    base = _load_case(PHYSICAL_CASE_PATH)
    press = base.model_copy(
        update={
            "cold_side": base.cold_side.model_copy(update={"inlet_pressure_pa": Decimal("101100")})
        }
    )
    h0 = sizing_request_identity(build_task173_sizing_request(base))
    h1 = sizing_request_identity(build_task173_sizing_request(press))
    assert h0 != h1


def test_geometry_changes_candidate_space() -> None:
    base = _load_case(PHYSICAL_CASE_PATH)
    wide = base.model_copy(
        update={
            "candidate_constraints": base.candidate_constraints.model_copy(
                update={"shell_inside_diameter_m": Decimal("0.81")}
            )
        }
    )
    pre0 = enumerate_task168_candidates(build_task173_sizing_request(base))
    pre1 = enumerate_task168_candidates(build_task173_sizing_request(wide))
    assert pre0["candidate_space_hash"] != pre1["candidate_space_hash"]


def test_task168_generates_distinct_candidates() -> None:
    case = _load_case(PHYSICAL_CASE_PATH)
    task168 = build_task168_request(case)
    sizing = build_task173_sizing_request(case)
    assert task168.shell_geometry_catalog.records
    preflight = enumerate_task168_candidates(sizing)
    assert preflight["status"] == "VALID"
    assert preflight["candidate_count"] >= 2
    assert preflight.get("structurally_admitted_count", 0) >= 2
    ids = {row["candidate_id"] for row in preflight["candidates"]}
    assert len(ids) == preflight["candidate_count"]


def test_preflight_workflow_writes_reports(tmp_path: Path) -> None:
    case = _load_case(PHYSICAL_CASE_PATH)
    outcome = run_general_engineering_workflow(case, tmp_path, run_full_rating=False)
    assert outcome.status == "PARTIAL_RATING_BUDGET"
    assert outcome.report_json_path is not None
    assert outcome.report_md_path is not None
    assert outcome.report_json_path.is_file()
    assert (tmp_path / "NATIVE_REQUEST_BINDING_DIAGNOSTICS.json").is_file()
    report = json.loads(outcome.report_json_path.read_text(encoding="utf-8"))
    assert report["production_design_approved"] is False


@pytest.mark.slow
def test_full_sizing_end_to_end(tmp_path: Path) -> None:
    case = _load_case(PHYSICAL_CASE_PATH)
    case = case.model_copy(
        update={
            "solver_budget": case.solver_budget.model_copy(update={"max_candidates_to_rate": 1}),
            "candidate_constraints": case.candidate_constraints.model_copy(
                update={
                    "tube_lengths_m": (Decimal("4.85"),),
                    "baffle_spacings_m": (Decimal("0.97"),),
                }
            ),
        }
    )
    outcome = run_general_engineering_workflow(case, tmp_path, run_full_rating=True)
    assert outcome.status in {"EXPERIMENTAL_COMPLETE", "BLOCKED_SIZING"}
    assert (tmp_path / "TASK173_SIZING_OUTCOME.json").is_file()
    if outcome.status == "EXPERIMENTAL_COMPLETE":
        assert outcome.rating_solver_calls >= 1
        outcome_json = json.loads((tmp_path / "TASK173_SIZING_OUTCOME.json").read_text())
        assert outcome_json["candidate_records"][0]["candidate_rating_result_hash"]
