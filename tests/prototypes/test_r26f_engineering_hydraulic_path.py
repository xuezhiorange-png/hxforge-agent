"""R26F hydraulic path geometry authority and report integrity fixes."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_dp_breakdown import (
    build_hydraulic_dp_breakdown,
    shell_dp_components_summary,
    tube_dp_components_summary,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_geometry import (
    assess_full_hydraulic_path_input_status,
    candidate_geometry_from_selection_record,
    historical_long_baseline_area,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_hydraulic_path_study import (
    run_experimental_engineering_hydraulic_path_study,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    run_experimental_multi_candidate_engineering_sizing,
)

_FIXTURE_R26E = (
    Path(__file__).resolve().parents[1]
    / "fixtures/r26e_multi_candidate_engineering_sizing_case.json"
)
_MIDDLE_CANDIDATE_ID = "3c129a7f-eba7-5b5a-9b86-5b2ce9629dae"


@pytest.fixture(name="r26e_case")
def _r26e_case():
    return load_general_engineering_case_json(_FIXTURE_R26E.read_text(encoding="utf-8"))


def test_r26f_middle_candidate_geometry_authority_matches_task168(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    record = next(r for r in selection.records if r.candidate_id == _MIDDLE_CANDIDATE_ID)
    facts = candidate_geometry_from_selection_record(record)
    assert facts["shell_inside_diameter_m"] == "0.54"
    assert record.physical_tube_count == 313
    assert facts["tube_length_m"] == "3.5"
    assert facts["baffle_spacing_m"] == "0.7"
    assert Decimal(facts["nominal_tube_outer_area_m2"]) == Decimal("65.562761025745127310075")


def test_r26f_full_path_input_status_requires_shell_nozzle_geometry(r26e_case) -> None:
    status = assess_full_hydraulic_path_input_status(r26e_case)
    assert status["FULL_PATH_INPUT_STATUS"] == "DEMONSTRATION_PARTIAL_PATH_ONLY"
    assert status["shell_side"]["shell_nozzle_path_status"] == "ENGINEERING_GEOMETRY_INPUT_REQUIRED"


def test_r26f_dp_breakdown_from_transitional_postpass_fields() -> None:
    postpass = {
        "recalculated_tube_dp_pa": "800",
        "recalculated_shell_dp_pa": "900",
        "experimental_transitional_tube_hydraulic": {
            "tube_friction_dp_pa": "700",
            "tube_local_loss_dp_pa": "100",
        },
        "shell_dp_components_pa": {
            "central_crossflow": "500",
            "window": "300",
            "end_zone": "100",
            "total": "900",
        },
        "tube_local_loss_engineering": {
            "computed_local_loss_components": [
                {
                    "component_id": "R21-DEMO-ENTRANCE-100MM",
                    "component_irreversible_pressure_loss_pa": "100",
                    "reference_flow_area_m2": "0.00785",
                    "loss_coefficient": "0.5",
                }
            ]
        },
    }
    from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
        load_general_engineering_case_json,
    )

    case = load_general_engineering_case_json(_FIXTURE_R26E.read_text(encoding="utf-8"))
    breakdown = build_hydraulic_dp_breakdown(postpass, case=case)
    assert breakdown["TUBE_FRICTION_DP_PA"] == "700"
    assert breakdown["TUBE_LOCAL_LOSS_DP_PA"] == "100"
    assert breakdown["TUBE_TOTAL_DP_PA"] == "800"
    assert breakdown["SHELL_INTERNAL_DP_PA"] == "900"
    assert breakdown["total_reconciliation_ok"] is True
    assert tube_dp_components_summary(breakdown)[0]["component_id"] == "TUBE_BUNDLE_FRICTION"
    shell_rows = shell_dp_components_summary(breakdown)
    assert any(r["component_id"] == "SHELL_INLET_OUTLET_NOZZLE" for r in shell_rows)


def test_r26f_intermediate_answer_uses_historical_long_reference(r26e_case) -> None:
    report = run_experimental_multi_candidate_engineering_sizing(
        r26e_case, run_full_mesh_hydraulic=False, max_candidates=1
    )
    tradeoff = report["experimental_tradeoff_comparison"]
    answer = tradeoff["intermediate_geometry_answer"]
    assert answer["historical_long_baseline_reference"]["authority"].startswith("HISTORICAL")
    assert Decimal(answer["historical_long_reference_area_m2"]) == historical_long_baseline_area()


def test_r26f_not_selected_candidates_not_marked_eliminated(r26e_case) -> None:
    report = run_experimental_multi_candidate_engineering_sizing(
        r26e_case, run_full_mesh_hydraulic=False, max_candidates=1
    )
    not_selected = [
        r
        for r in report["candidates"]
        if r["rating_participation_status"] == "NOT_SELECTED_FOR_RATING"
    ]
    assert not_selected
    assert not_selected[0]["elimination_reason"] is None


@pytest.mark.slow
def test_r26f_representative_hydraulic_path_study_slow(r26e_case) -> None:
    study = run_experimental_engineering_hydraulic_path_study(r26e_case)
    assert study["TASK_ID"] == "V07_R26F_ENGINEERING_HYDRAULIC_PATH_COMPLETION"
    assert study["representative_candidate_count"] >= 2
    middle = next(
        (
            row
            for row in study["representative_candidates"]
            if row["candidate_geometry_authority"]["candidate_id"] == _MIDDLE_CANDIDATE_ID
        ),
        None,
    )
    assert middle is not None
    assert middle["candidate_geometry_authority"]["shell_inside_diameter_m"] == "0.54"
    demo = middle["demonstration_entrance_only_model"]
    assert demo["ENGINEERING_SIZING_ELIGIBILITY"] == (
        "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
    )
    assert demo["TUBE_DP_COMPONENTS"]
    assert demo["SHELL_DP_COMPONENTS"]
    assert middle["authorized_full_path_model"]["status"] == "NOT_RUN"
