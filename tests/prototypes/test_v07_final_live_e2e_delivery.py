"""V07 final live E2E delivery acceptance guards."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.v07_version_delivery import (
    ExecutionMode,
    acceptance_matrix_strict,
    build_full_design_report,
    load_user_case_json,
    validate_user_case,
    verify_independent_input_change,
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
                "mesh_rating_evidence": {"full_rating_converged": False},
                "rating_participation_status": "SCREENING_ONLY",
            }
        ],
    }
    dr = build_full_design_report(case, r27h)
    matrix = acceptance_matrix_strict(
        mode=ExecutionMode.LIVE_COMPUTE, case=case, r27h=r27h, design_report=dr
    )
    assert matrix["thermal_rating_n1_n2_n4"] == "FAIL"


def test_user_case_input_change_reflected() -> None:
    base = load_user_case_json(Path("tests/fixtures/v07_live_acceptance_user_case.json"))
    modified = base.model_copy(
        update={
            "tube_side": base.tube_side.model_copy(
                update={"inlet_temperature_k": Decimal("305.000000")}
            )
        }
    )
    out = verify_independent_input_change(base, modified)
    assert out["input_change_reflected_in_computation"] is True


def test_validate_user_case_accepts_baseline() -> None:
    case = load_user_case_json(Path("tests/fixtures/v07_live_acceptance_user_case.json"))
    v = validate_user_case(case)
    assert v["valid"] is True


def test_design_report_from_fixture_has_geometry() -> None:
    r27h = json.loads(
        Path("tests/fixtures/R27H_CANDIDATE_SPACE_EXTENSION.json").read_text(encoding="utf-8")
    )
    case = load_user_case_json(Path("tests/fixtures/v07_live_acceptance_user_case.json"))
    dr = build_full_design_report(case, r27h)
    assert dr["generated_structure"]["physical_tube_count"] == 337
    assert dr["generated_structure"]["shell_inside_diameter_m"] == "0.56"
