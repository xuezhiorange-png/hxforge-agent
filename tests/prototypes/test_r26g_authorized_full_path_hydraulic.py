"""R26G authorized full-path hydraulic calculation and input contract."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal

import pytest

from prototypes.v07_general_rating_sizing_mvp.authorized_full_path_hydraulic_calculation import (
    run_authorized_full_path_hydraulic_calculation,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import CandidateSelectionOutcome
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_dp_breakdown import (
    build_hydraulic_dp_breakdown,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_completeness import (
    assess_hydraulic_path_completeness,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    build_r26g_demonstration_hydraulic_path_input_v1,
    load_engineering_hydraulic_path_input_v1_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_authorized_full_path_study import (
    run_r26g_authorized_full_path_hydraulic_study,
)
from tests.prototypes.r26g_r26ga_shared_setup import (
    R26G_MIDDLE_CANDIDATE_ID,
    shared_r26e_engineering_case,
    shared_r26e_experimental_rating_selection,
)


@pytest.fixture(name="r26e_case")
def _r26e_case() -> EngineeringCase:
    return shared_r26e_engineering_case()


@pytest.fixture(name="r26e_experimental_rating_selection")
def _r26e_experimental_rating_selection() -> CandidateSelectionOutcome:
    return shared_r26e_experimental_rating_selection()


def test_r26g_breakdown_missing_nozzle_not_zero(r26e_case) -> None:
    postpass = {
        "recalculated_tube_dp_pa": "800",
        "recalculated_shell_dp_pa": "900",
        "experimental_transitional_tube_hydraulic": {
            "tube_friction_dp_pa": "700",
            "tube_local_loss_dp_pa": "100",
        },
        "shell_dp_components_pa": {"total": "900"},
    }
    breakdown = build_hydraulic_dp_breakdown(postpass, case=r26e_case)
    assert breakdown["SHELL_NOZZLE_AND_LOCAL_DP_PA"] is None
    assert breakdown["SHELL_MODELED_PARTIAL_DP_PA"] == "900"
    assert breakdown["SHELL_FULL_PATH_TOTAL_DP_PA"] is None
    assert breakdown["SHELL_FULL_PATH_STATUS"] == "ENGINEERING_GEOMETRY_INPUT_REQUIRED"


def test_r26g_demonstration_path_input_binds_and_parses(
    r26e_case, r26e_experimental_rating_selection
) -> None:
    record = next(
        r
        for r in r26e_experimental_rating_selection.records
        if r.candidate_id == R26G_MIDDLE_CANDIDATE_ID
    )
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    roundtrip = load_engineering_hydraulic_path_input_v1_json(path_input.model_dump_json())
    assert roundtrip.binding.candidate_id == record.candidate_id
    completeness = assess_hydraulic_path_completeness(roundtrip)
    assert completeness["path_completeness_status"] == "DEMONSTRATION_FULL_PATH_DECLARED"
    assert completeness["FULL_PATH_VERIFICATION_STATUS"] == "NOT_VERIFIED"


def test_r26g_authorized_calc_fail_closed_without_postpass(
    r26e_case, r26e_experimental_rating_selection
) -> None:
    record = r26e_experimental_rating_selection.records[0]
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    result = run_authorized_full_path_hydraulic_calculation(
        case=r26e_case,
        path_input=path_input,
        record=record,
        postpass=None,
    )
    assert result["status"] == "BLOCKED_UPSTREAM"
    assert result["TUBE_FULL_PATH_TOTAL_DP_PA"] is None
    assert result["SHELL_FULL_PATH_TOTAL_DP_PA"] is None


def test_r26g_authorized_calc_reconciles_with_postpass(
    r26e_case, r26e_experimental_rating_selection
) -> None:
    record = next(
        r
        for r in r26e_experimental_rating_selection.records
        if r.candidate_id == R26G_MIDDLE_CANDIDATE_ID
    )
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    postpass = {
        "recalculated_tube_dp_pa": "850",
        "recalculated_shell_dp_pa": "920",
        "tube_hydraulic_recompute_status": "EXPERIMENTAL_TRANSITIONAL_SUCCESS",
        "shell_hydraulic_recompute_status": "SUCCESS",
        "correlation_applicability_status": "APPLICABLE",
        "tube_inlet_pressure_pa": "101325",
        "shell_inlet_pressure_pa": "101325",
        "property_inputs": {
            "tube": {"bulk_pressure_pa": "101325", "bulk_temperature_k": "300"},
            "shell": {"bulk_pressure_pa": "101325", "bulk_temperature_k": "300"},
        },
        "coolprop_outlet_domain_checks": {
            "tube": {"ok": True},
            "shell": {"ok": True},
        },
        "experimental_transitional_tube_hydraulic": {
            "tube_friction_dp_pa": "750",
            "tube_local_loss_dp_pa": "100",
        },
        "shell_dp_components_pa": {"central_crossflow": "500", "window": "300", "total": "920"},
    }
    result = run_authorized_full_path_hydraulic_calculation(
        case=r26e_case,
        path_input=path_input,
        record=record,
        postpass=postpass,
    )
    assert result["status"] == "COMPUTED"
    assert result["TUBE_INTERNAL_FRICTION_DP_PA"] == "750"
    assert Decimal(result["TUBE_LOCAL_DP_PA"]) > 0
    assert Decimal(result["SHELL_EXTERNAL_LOCAL_DP_PA"]) > 0
    assert result["reconciliation"]["tube_full_equals_friction_plus_local"] is True
    assert result["reconciliation"]["shell_full_equals_bd_plus_external"] is True
    assert result["PRODUCTION_DESIGN_APPROVED"] is False
    assert (
        result["ENGINEERING_SIZING_ELIGIBILITY"]
        == "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
    )


@pytest.mark.slow
def test_r26g_representative_full_path_study_slow(r26e_case) -> None:
    study = run_r26g_authorized_full_path_hydraulic_study(
        r26e_case, use_demonstration_path_inputs=True
    )
    assert study["TASK_ID"] == "V07_R26G_A_FULL_PATH_PHYSICAL_CONSISTENCY_GATE"
    assert study["PRODUCTION_DESIGN_APPROVED"] is False
    middle = next(
        row
        for row in study["representative_candidates"]
        if row["candidate_geometry_authority"]["candidate_id"] == R26G_MIDDLE_CANDIDATE_ID
    )
    authorized = middle["authorized_full_path_model"]
    assert authorized["status"] == "COMPUTED", authorized.get("blockers")
    assert authorized["SHELL_BELL_DELAWARE_INTERNAL_DP_PA"] is not None
    assert authorized["SHELL_EXTERNAL_LOCAL_DP_PA"] is not None
    assert authorized["SHELL_FULL_PATH_TOTAL_DP_PA"] is not None
    assert middle["model_delta"]["status"] == "COMPUTED"
    baseline = next(
        row
        for row in study["representative_candidates"]
        if row["candidate_geometry_authority"]["shell_inside_diameter_m"] == "0.56"
        and row["candidate_geometry_authority"]["tube_length_m"] == "3.0"
    )
    assert baseline["authorized_full_path_model"]["status"] == "COMPUTED"
