"""Frozen TASK-032 model and constant contracts."""

from dataclasses import fields

from hexagent.exchangers.shell_tube.shell_side_flow_state import models


def test_t032_mod_001_exact_field_tuples_and_counts() -> None:
    assert tuple(field.name for field in fields(models.ShellSideFlowStateRequest)) == (
        *models.REQUEST_FIELDS,
    )
    assert tuple(field.name for field in fields(models.ShellSideFlowState)) == (
        *models.SUCCESS_RESULT_FIELDS,
    )
    assert tuple(field.name for field in fields(models.ShellSideFlowStateBlockedResult)) == (
        *models.TYPED_BLOCKED_RESULT_FIELDS,
    )
    assert tuple(
        field.name for field in fields(models.ShellSideFlowStateRawBoundaryBlockedResult)
    ) == (*models.RAW_BOUNDARY_BLOCKED_RESULT_FIELDS,)
    assert len(models.REQUEST_FIELDS) == 7
    assert len(models.SUCCESS_RESULT_FIELDS) == 29
    assert len(models.TYPED_BLOCKED_RESULT_FIELDS) == 15
    assert len(models.RAW_BOUNDARY_BLOCKED_RESULT_FIELDS) == 8


def test_t032_mod_002_public_output_field_names_match_frozen_formula_authority() -> None:
    assert {
        "shell_side_mass_flow_rate_kg_s",
        "shell_side_mass_velocity_kg_m2_s",
        "shell_side_bulk_velocity_m_s",
        "shell_side_reynolds_number",
        "shell_side_prandtl_number",
    }.issubset(models.SUCCESS_RESULT_FIELDS)
    assert "flow_regime" not in models.SUCCESS_RESULT_FIELDS
    assert "nusselt_number" not in models.SUCCESS_RESULT_FIELDS
    assert "pressure_drop_pa" not in models.SUCCESS_RESULT_FIELDS


def test_t032_con_001_package_constants_and_profile_tokens() -> None:
    assert models.PROFILE_ID == "hxforge.shell_tube.shell_side_flow_state.v1"
    assert models.FLOW_MODEL == ("SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING")
    assert models.FIRST_SLICE_PROFILE_ID == (
        "SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1"
    )
    assert models.RHEOLOGY_MODEL == "NEWTONIAN"
    assert models.PROPERTY_STATE_ROLE == "BULK_SHELL_SIDE_STATE"
    assert len(models.BLOCKER_CODES) == 33
    assert len(models.WARNING_CODES) == 7
    assert len(models.DEFERRED_CAPABILITIES) == 17
