"""R26G-A full-path physical consistency gates."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.authorized_full_path_hydraulic_calculation import (
    run_authorized_full_path_hydraulic_calculation,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    FluidDensitySourceV1,
    build_r26g_demonstration_hydraulic_path_input_v1,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_physical_consistency import (
    assess_full_path_hydraulic_constraints,
    assess_upstream_hydraulic_postpass_for_full_path,
    validate_path_input_physical_consistency,
)

_FIXTURE_R26E = (
    Path(__file__).resolve().parents[1]
    / "fixtures/r26e_multi_candidate_engineering_sizing_case.json"
)


@pytest.fixture(name="r26e_case")
def _r26e_case():
    return load_general_engineering_case_json(_FIXTURE_R26E.read_text(encoding="utf-8"))


def _good_postpass(**overrides: object) -> dict:
    base = {
        "recalculated_tube_dp_pa": "800",
        "recalculated_shell_dp_pa": "900",
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
            "tube_friction_dp_pa": "700",
            "tube_local_loss_dp_pa": "100",
        },
        "shell_dp_components_pa": {"total": "900"},
    }
    base.update(overrides)
    return base


def test_r26ga_blocks_tube_shell_mass_flow_mismatch(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    record = selection.records[0]
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    bad_tube = path_input.model_copy(
        update={
            "tube_side_components": tuple(
                c.model_copy(update={"mass_flow_kg_s": Decimal("99")})
                for c in path_input.tube_side_components
            )
        }
    )
    result = validate_path_input_physical_consistency(bad_tube, case=r26e_case)
    assert result["PHYSICAL_CONSISTENCY_STATUS"] == "BLOCKED"
    assert any("TUBE_MASS_FLOW_MISMATCH" in e for e in result["physical_consistency_errors"])


def test_r26ga_blocks_density_side_mismatch(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    record = selection.records[0]
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    shell_comp = path_input.shell_external_components[0]
    bad_shell = shell_comp.model_copy(
        update={
            "fluid_density_source": FluidDensitySourceV1(
                kind="CASE_SIDE_INLET",
                fluid_role="TUBE_SIDE",
            )
        }
    )
    bad_input = path_input.model_copy(
        update={"shell_external_components": (bad_shell, *path_input.shell_external_components[1:])}
    )
    result = validate_path_input_physical_consistency(bad_input, case=r26e_case)
    assert any("DENSITY_SIDE_MISMATCH" in e for e in result["physical_consistency_errors"])


def test_r26ga_blocks_upstream_tube_recompute_blocked(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    record = selection.records[0]
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    result = run_authorized_full_path_hydraulic_calculation(
        case=r26e_case,
        path_input=path_input,
        record=record,
        postpass=_good_postpass(tube_hydraulic_recompute_status="BLOCKED"),
    )
    assert result["TUBE_FULL_PATH_TOTAL_DP_PA"] is None
    assert result["TUBE_FULL_PATH_STATUS"] == "BLOCKED_UPSTREAM"


def test_r26ga_duplicate_local_loss_blocked(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    record = selection.records[0]
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    comp_id = path_input.tube_side_components[2].component_id
    postpass = _good_postpass(
        tube_local_loss_engineering={
            "computed_local_loss_components": [
                {
                    "component_id": comp_id,
                    "component_irreversible_pressure_loss_pa": "100",
                }
            ]
        }
    )
    result = run_authorized_full_path_hydraulic_calculation(
        case=r26e_case,
        path_input=path_input,
        record=record,
        postpass=postpass,
    )
    assert result["status"] == "BLOCKED_DUPLICATE_LOCAL_LOSS"
    assert result["TUBE_FULL_PATH_TOTAL_DP_PA"] is None


def test_r26ga_full_path_constraint_independent_of_partial_not_satisfied(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    record = selection.records[0]
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    postpass = _good_postpass(
        tube_dp_constraint="NOT_SATISFIED",
        recalculated_tube_dp_pa="50",
        experimental_transitional_tube_hydraulic={
            "tube_friction_dp_pa": "40",
            "tube_local_loss_dp_pa": "10",
        },
    )
    result = run_authorized_full_path_hydraulic_calculation(
        case=r26e_case,
        path_input=path_input,
        record=record,
        postpass=postpass,
    )
    assert result["TUBE_FULL_PATH_TOTAL_DP_PA"] is not None
    assert result["partial_model_tube_dp_constraint"] == "NOT_SATISFIED"
    assert result["FULL_PATH_TUBE_CONSTRAINT_STATUS"] in ("SATISFIED", "NOT_SATISFIED")


def test_r26ga_blocks_full_tube_path_when_coolprop_outlet_domain_fails(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    record = selection.records[0]
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    postpass = _good_postpass(
        coolprop_outlet_domain_checks={
            "tube": {"ok": False, "detail": "fixture domain fail"},
            "shell": {"ok": True},
        }
    )
    upstream = assess_upstream_hydraulic_postpass_for_full_path(postpass)
    assert upstream["tube_side_numeric_usable"] is False
    assert any("COOLPROP_OUTLET_DOMAIN_TUBE" in b for b in upstream["tube_upstream_blockers"])
    result = run_authorized_full_path_hydraulic_calculation(
        case=r26e_case,
        path_input=path_input,
        record=record,
        postpass=postpass,
    )
    assert result["TUBE_FULL_PATH_TOTAL_DP_PA"] is None
    assert result["TUBE_FULL_PATH_STATUS"] == "BLOCKED_UPSTREAM"


def test_r26ga_task029_total_without_friction_blocks_full_tube_path(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    record = selection.records[0]
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    postpass = _good_postpass(
        tube_hydraulic_recompute_status="SUCCESS",
        experimental_transitional_tube_hydraulic={},
    )
    result = run_authorized_full_path_hydraulic_calculation(
        case=r26e_case,
        path_input=path_input,
        record=record,
        postpass=postpass,
    )
    assert result["tube_friction_separation_authority"] == "TUBE_FRICTION_SEPARATION_UNRELIABLE"
    assert result["TUBE_FULL_PATH_TOTAL_DP_PA"] is None
    assert result["TUBE_INTERNAL_FRICTION_DP_PA"] is None


def test_r26ga_outlet_pressure_domain_blocks_satisfied_despite_dp_limit_ok(r26e_case) -> None:
    postpass = _good_postpass(tube_inlet_pressure_pa="100500")
    constraints = assess_full_path_hydraulic_constraints(
        case=r26e_case,
        postpass=postpass,
        tube_full_dp=Decimal("1000"),
        shell_full_dp=Decimal("500"),
    )
    assert constraints["FULL_PATH_TUBE_CONSTRAINT_STATUS"] == "SATISFIED"
    assert constraints["FULL_PATH_TUBE_OUTLET_DOMAIN_STATUS"] == "OUTLET_PRESSURE_OUT_OF_DOMAIN"
    assert constraints["FULL_PATH_HYDRAULIC_STATUS"] == "OUTLET_PRESSURE_DOMAIN_BLOCKED"


def test_r26ga_authorized_input_without_owner_evidence_not_verified(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    record = selection.records[0]
    path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=record)
    authorized_comp = path_input.tube_side_components[0].model_copy(
        update={"engineering_input_status": "AUTHORIZED_ENGINEERING_INPUT"}
    )
    bad = path_input.model_copy(
        update={"tube_side_components": (authorized_comp, *path_input.tube_side_components[1:])}
    )
    physical = validate_path_input_physical_consistency(bad, case=r26e_case)
    assert physical["INPUT_AUTHORITY_STATUS"] == "INPUT_AUTHORITY_NOT_VERIFIED"
