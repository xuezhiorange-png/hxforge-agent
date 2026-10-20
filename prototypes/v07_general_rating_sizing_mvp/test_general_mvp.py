"""Tests for general rating + sizing MVP."""

# ruff: noqa: E501

from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1
from prototypes.v07_general_rating_sizing_mvp.input_to_solver_binding import (
    build_input_to_solver_binding,
)
from prototypes.v07_general_rating_sizing_mvp.preflight import enumerate_task168_candidates
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task168_request,
    build_task173_sizing_request,
    sizing_request_identity,
)
from prototypes.v07_general_rating_sizing_mvp.workflow import run_general_engineering_workflow

CASE_PATH = Path(__file__).resolve().parent / "cases" / "mvp_district_heating_water_water_r1.json"
PHYSICAL_CASE_PATH = Path(__file__).resolve().parent / "cases" / "mvp_water_water_physical_r2.json"
R3_CASE_PATH = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r3.json"
R4_CASE_PATH = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r4.json"


def _load_case(path: Path = CASE_PATH) -> GeneralEngineeringCaseV1:
    return GeneralEngineeringCaseV1.model_validate_json(path.read_text(encoding="utf-8"))


def test_case_json_parses_and_differs_from_validation_defaults() -> None:
    case = _load_case()
    assert case.engineering_case_id == "mvp-district-heating-water-water-r1"
    assert case.target_duty_w == Decimal("9500")
    assert case.candidate_constraints.shell_inside_diameter_m == Decimal("0.8")
    assert len(case.candidate_constraints.tube_lengths_m) == 3


def test_r1_case_in_scope_under_tube_hot_convention() -> None:
    case = _load_case()
    status, detail = case.applicability_status()
    assert status == "IN_SCOPE"
    assert detail is None


def test_legacy_shell_hot_field_order_blocked() -> None:
    case = _load_case(PHYSICAL_CASE_PATH)
    status, detail = case.applicability_status()
    assert status == "BLOCKED"
    assert detail is not None
    assert "cold_side.inlet_temperature_k" in detail


def test_physical_r2_case_blocked_under_tube_hot_convention() -> None:
    case = _load_case(PHYSICAL_CASE_PATH)
    status, detail = case.applicability_status()
    assert status == "BLOCKED"
    assert detail is not None
    assert "cold_side.inlet_temperature_k" in detail


def test_r3_case_in_scope_tube_hot_shell_cold() -> None:
    case = _load_case(R3_CASE_PATH)
    status, detail = case.applicability_status()
    assert status == "IN_SCOPE"
    assert detail is None
    assert case.bind_task172_c3_reference_geometry is True


def test_r4_v2_case_in_scope_tube_side_hot_shell_side_cold() -> None:
    case = load_general_engineering_case_json(R4_CASE_PATH.read_text(encoding="utf-8"))
    status, detail = case.applicability_status()
    assert status == "IN_SCOPE"
    assert detail is None
    assert case.schema_version == "hxforge.general-engineering-case.v2"
    assert case.tube_side.inlet_temperature_k > case.shell_side.inlet_temperature_k


def test_r4_input_binding_maps_equipment_to_thermal_roles() -> None:
    case = load_general_engineering_case_json(R4_CASE_PATH.read_text(encoding="utf-8"))
    binding = build_input_to_solver_binding(case)
    assert binding["schema_version"] == "hxforge.input-to-solver-binding.v2"
    mapping = binding["equipment_thermal_mapping"]
    assert mapping["tube_thermal_role"] == "HOT"
    assert mapping["shell_thermal_role"] == "COLD"
    assert binding["physical_side_role_parity"] == "TUBE_HOT_SHELL_COLD"
    assert binding["rows"][0]["user_field"] == "tube_side.mass_flow_kg_s"
    assert binding["rows"][0]["participates_in_rating_kernel"] is True


def test_r3_and_r4_share_c3_candidate_space() -> None:
    r3 = _load_case(R3_CASE_PATH)
    r4 = load_general_engineering_case_json(R4_CASE_PATH.read_text(encoding="utf-8"))
    pre3 = enumerate_task168_candidates(build_task173_sizing_request(r3))
    pre4 = enumerate_task168_candidates(build_task173_sizing_request(r4))
    assert pre3["candidate_space_hash"] == pre4["candidate_space_hash"]
    r3_ids = {row["candidate_id"] for row in pre3["candidates"]}
    assert "82f370ff-73cd-5d71-aaf9-efc51645d22e" in r3_ids


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
    case = _load_case(R3_CASE_PATH)
    outcome = run_general_engineering_workflow(case, tmp_path, run_full_rating=False)
    assert outcome.status == "PREFLIGHT_COMPLETE"
    assert outcome.report_json_path is not None
    assert outcome.report_md_path is not None
    assert outcome.report_json_path.is_file()
    assert (tmp_path / "NATIVE_REQUEST_BINDING_DIAGNOSTICS.json").is_file()
    report = json.loads(outcome.report_json_path.read_text(encoding="utf-8"))
    assert report["production_design_approved"] is False


@pytest.mark.slow
def test_full_sizing_end_to_end(tmp_path: Path) -> None:
    case = _load_case(R3_CASE_PATH)
    outcome = run_general_engineering_workflow(case, tmp_path, run_full_rating=False)
    assert outcome.status == "PREFLIGHT_COMPLETE"
    assert (tmp_path / "INPUT_TO_SOLVER_BINDING.json").is_file()
