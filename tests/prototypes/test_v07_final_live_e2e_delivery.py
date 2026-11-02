"""V07 final live E2E delivery acceptance guards."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
)
from prototypes.v07_general_rating_sizing_mvp.thermal_hydraulic_geometry_cooptimization_sizing import (  # noqa: E501
    _mesh_rating_evidence_from_multi_row,
)
from prototypes.v07_general_rating_sizing_mvp.v07_version_delivery import (
    ExecutionMode,
    acceptance_matrix_strict,
    build_full_design_report,
    load_user_case_json,
    mesh_rating_evidence_consistent,
    validate_user_case,
    verify_independent_input_effects,
)


def test_replay_matrix_never_passes_live_items() -> None:
    r27h = json.loads(
        Path("tests/fixtures/R27H_CANDIDATE_SPACE_EXTENSION.json").read_text(encoding="utf-8")
    )
    case = load_user_case_json(Path("tests/fixtures/v07_live_acceptance_user_case.json"))
    dr = build_full_design_report(case, r27h)
    matrix = acceptance_matrix_strict(
        mode=ExecutionMode.FIXTURE_REPLAY, case=case, r27h=r27h, design_report=dr
    )
    assert all(v == "REPLAY" for v in matrix.values())
    assert "PASS" not in matrix.values()


def test_mesh_evidence_converged_requires_ladder_and_valid_n1() -> None:
    row = {
        "FULL_RATING_CONVERGED": True,
        "rating_participation_status": "FULLY_RATED",
        "screening_n1_status": ENGINEERING_NUMERIC_VALID,
        "n1_thermal_numeric_status": ENGINEERING_NUMERIC_VALID,
        "mesh_ladder_levels_completed": [1, 2, 4],
        "entered_n2_n4_mesh_ladder": True,
    }
    ev = _mesh_rating_evidence_from_multi_row(row)
    assert ev["full_rating_converged"] is True
    assert ev["entered_n2_n4_mesh_ladder"] is True
    assert mesh_rating_evidence_consistent(ev)


def test_mesh_evidence_wrong_n1_literal_no_false_converged_ladder() -> None:
    row = {
        "FULL_RATING_CONVERGED": True,
        "rating_participation_status": "FULLY_RATED",
        "screening_n1_status": ENGINEERING_NUMERIC_VALID,
        "n1_thermal_numeric_status": ENGINEERING_NUMERIC_VALID,
    }
    ev = _mesh_rating_evidence_from_multi_row(row)
    assert ev["entered_n2_n4_mesh_ladder"] is True


def test_incomplete_rating_not_pass_on_synthetic_row() -> None:
    case = load_user_case_json(Path("tests/fixtures/v07_live_acceptance_user_case.json"))
    r27h = {
        "engineering_answers": {
            "best_candidate_id_prefix": "aaaa",
            "new_structurally_legal_distinct_geometries": 1,
        },
        "candidates": [
            {
                "candidate_id_prefix": "aaaa",
                "phase_a": {"phase_a_status": "ELIGIBLE_FOR_N1_SCREEN", "physical_tube_count": 100},
                "mesh_rating_evidence": {
                    "full_rating_converged": False,
                    "entered_n2_n4_mesh_ladder": False,
                    "n1_thermal_numeric_status": ENGINEERING_NUMERIC_VALID,
                },
                "rating_participation_status": "SCREENING_ONLY",
            }
        ],
    }
    dr = build_full_design_report(case, r27h)
    matrix = acceptance_matrix_strict(
        mode=ExecutionMode.LIVE_COMPUTE, case=case, r27h=r27h, design_report=dr
    )
    assert matrix["thermal_rating_n1_n2_n4"] == "FAIL"


def test_independent_input_effects_duty_and_thermal() -> None:
    base = load_user_case_json(Path("tests/fixtures/v07_live_acceptance_user_case.json"))
    out = verify_independent_input_effects(base)
    assert out["target_duty_constraint_judgment_changed"] is True
    assert out["thermal_n1_changed_with_inlet_temperature"] is True
    assert out["independent_input_change_pass"] is True


def test_validate_user_case_accepts_baseline() -> None:
    case = load_user_case_json(Path("tests/fixtures/v07_live_acceptance_user_case.json"))
    v = validate_user_case(case)
    assert v["valid"] is True


def test_design_report_from_fixture_has_geometry_and_components() -> None:
    r27h = json.loads(
        Path("tests/fixtures/R27H_CANDIDATE_SPACE_EXTENSION.json").read_text(encoding="utf-8")
    )
    case = load_user_case_json(Path("tests/fixtures/v07_live_acceptance_user_case.json"))
    dr = build_full_design_report(case, r27h)
    assert dr["generated_structure"]["physical_tube_count"] == 337
    mid = (
        ((next(c for c in r27h["candidates"] if c["candidate_id_prefix"] == "5e78f6a8"))
        .get("loss_scenario_results") or {})
        .get("mid_band") or {}
    )
    fp = mid.get("full_path_hydraulic_verification") or {}
    comp = dr["hydraulic_results"]["authorized_mid_band_optimized_nozzles"]["component_rows"]
    assert comp["TUBE_DP_COMPONENTS"] == fp.get("TUBE_DP_COMPONENTS")
    assert float(fp["TUBE_FULL_PATH_DP_MARGIN_PA"]) == pytest.approx(0.0, abs=1e-6)
