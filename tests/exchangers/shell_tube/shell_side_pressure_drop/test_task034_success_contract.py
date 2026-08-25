"""TASK-034 success contract and shared deterministic fixture."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.authority import task031_request_hash
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.canonical import (
    mass_flow_authority_hash,
    property_snapshot_hash,
    task031_geometry_hash,
    task031_geometry_id,
    task032_request_hash,
    task032_result_id,
    task032_success_hash,
    task033_request_hash,
    task033_result_hash,
    task033_result_id,
    wall_property_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import (
    CORRELATION_ID,
    PROFILE_ID,
    REQUEST_SCHEMA_VERSION,
)


def _geometry() -> dict[str, Any]:
    geometry: dict[str, Any] = {
        "schema_version": "task031.shell-side-hydraulic-geometry.v1",
        "request_hash": "31" * 32,
        "task020_configuration_id": "TASK020-034-CASE",
        "task020_configuration_hash": "20" * 32,
        "task021_layout_id": "TASK021-034-LAYOUT",
        "task021_layout_hash": "21" * 32,
        "task022_geometry_id": "TASK022-034-GEOMETRY",
        "task022_geometry_hash": "22" * 32,
        "task024_geometry_id": "TASK024-034-GEOMETRY",
        "task024_geometry_hash": "24" * 32,
        "pattern_family": "TRIANGULAR_PITCH",
        "central_inter_baffle_spacing_m": "0.120",
        "central_crossflow_flow_area_m2": "0.085",
        "shell_side_equivalent_hydraulic_diameter_m": "0.041",
        "shell_inside_diameter_m": "1.200",
        "engineering_authority_id": "TASK031-ENGINEERING-AUTHORITY",
        "engineering_authority_hash": "aa" * 32,
        "formula_a_id": "TASK031-FORMULA-A",
        "formula_b_id": "TASK031-FORMULA-B",
        "flow_region_identity": "CENTRAL_CROSSFLOW_SCREENING",
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
        "provenance": [
            ["task_id", "TASK031"],
            ["design_contract_path", "docs/tasks/TASK-031.md"],
            ["task020_configuration_id", "TASK020-034-CASE"],
            ["task020_configuration_hash", "20" * 32],
            ["task021_layout_id", "TASK021-034-LAYOUT"],
            ["task021_layout_hash", "21" * 32],
            ["task022_geometry_id", "TASK022-034-GEOMETRY"],
            ["task022_geometry_hash", "22" * 32],
            ["task024_geometry_id", "TASK024-034-GEOMETRY"],
            ["task024_geometry_hash", "24" * 32],
            ["engineering_authority_profile_id", "TASK031-ENGINEERING"],
            ["engineering_authority_hash", "aa" * 32],
            ["formula_a_id", "TASK031-FORMULA-A"],
            ["formula_b_id", "TASK031-FORMULA-B"],
            ["freeze_comment_id", "TASK031-FREEZE"],
            ["source_ids", ["TASK031-SOURCE"]],
            ["pattern_family", "TRIANGULAR_PITCH"],
            ["flow_region_identity", "CENTRAL_CROSSFLOW_SCREENING"],
            ["software_version", "task031.test-fixture-v1"],
            ["git_commit", "fixture"],
            ["request_hash", "31" * 32],
            ["warnings", []],
            ["deferred_capabilities", []],
        ],
    }
    geometry_hash = task031_geometry_hash(geometry)
    geometry["geometry_hash"] = geometry_hash
    geometry["geometry_id"] = task031_geometry_id(geometry_hash)
    return geometry


def make_valid_raw_request() -> dict[str, Any]:
    geometry = _geometry()
    task031_result = {
        "status": "VALID",
        "geometry": geometry,
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
        "blocked_result_hash": None,
    }
    task031_request = {
        "schema_version": "task031.shell-side-hydraulic-geometry-request.v1",
        "tube_layout": {
            "schema_version": "task021.tube-layout.v1",
            "request_hash": "21-request",
            "positions": [],
            "tube_hole_count": 0,
            "physical_tube_count": 0,
            "boundary_rejection_count": 0,
            "exclusion_rejection_count": 0,
            "exclusion_audit": [],
            "warnings": [],
            "blockers": [],
            "deferred_capabilities": [],
            "provenance_pre_hash": {},
            "layout_rule_authority": {"pitch_m": "0.025", "pattern_family": "TRIANGULAR_PITCH"},
            "tube_geometry": {"outer_diameter_m": "0.020"},
        },
        "baffle_geometry_result": {
            "status": "VALID",
            "geometry": {
                "schema_version": "task024.baffle-geometry.v1",
                "geometry_id": "TASK024-034-GEOMETRY",
                "geometry_hash": "24" * 32,
                "request_hash": "24-request",
                "task020_configuration_id": "TASK020-034-CASE",
                "task020_configuration_hash": "20" * 32,
                "task021_layout_id": "TASK021-034-LAYOUT",
                "task021_layout_hash": "21" * 32,
                "task022_geometry_id": "TASK022-034-GEOMETRY",
                "task022_geometry_hash": "22" * 32,
                "construction_family": "E_SHELL",
                "shell_pass_count": 1,
                "shell_inside_diameter_m": "1.200",
                "tube_outer_diameter_m": "0.020",
                "design_authority": {
                    "schema_version": "task024.baffle-design-authority.v1",
                    "baffle_type": "SINGLE_SEGMENTAL",
                    "baffle_count": 12,
                    "spacing_sequence_m": ["0.120", "0.120"],
                    "authority_hash": "24-authority",
                },
            },
        },
        "engineering_authority": {
            "schema_version": "task031.engineering-authority-request.v1",
            "authority_profile_id": "TASK031-ENGINEERING",
            "authority_hash": "aa" * 32,
            "evidence_refs": ["task031-authority-fixture"],
        },
        "evidence_refs": ["task031-fixture"],
    }
    task031_hash = task031_request_hash(task031_request)
    snapshot: dict[str, Any] = {
        "density_kg_m3": "998",
        "dynamic_viscosity_pa_s": "0.001",
        "thermal_conductivity_w_m_k": "0.60",
        "specific_heat_capacity_j_kg_k": "4180",
        "bulk_temperature_k": "300",
        "bulk_pressure_pa": "101325",
        "phase_region": "SINGLE_PHASE_LIQUID",
        "property_source_id": "fixture-property",
        "property_source_version": "v1",
    }
    snapshot["property_snapshot_hash"] = property_snapshot_hash(snapshot)
    mass_flow: dict[str, Any] = {
        "schema_version": "task032.shell-side-mass-flow-authority.v1",
        "authority_profile_id": "TASK032-MASS-FLOW",
        "shell_side_case_id": "CASE-034",
        "shell_side_stream_id": "STREAM-034",
        "shell_side_fluid_id": "FLUID-034",
        "rheology_model": "NEWTONIAN",
        "task020_configuration_id": "TASK020-034-CASE",
        "task020_configuration_hash": "20" * 32,
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "property_snapshot_hash": snapshot["property_snapshot_hash"],
        "property_state_role": "BULK_SHELL_SIDE_STATE",
        "mass_flow_rate_kg_s": "102.0",
        "mass_flow_sign_convention": "POSITIVE_INTO_SHELL",
        "authority_source_id": "fixture-mass-flow",
        "authority_source_version": "v1",
        "evidence_refs": ["mass-fixture"],
    }
    mass_flow["authority_hash"] = mass_flow_authority_hash(mass_flow)
    task032_evidence = {
        "schema_version": "task032.shell-side-flow-state-request.v1",
        "profile_id": "hxforge.shell_tube.shell_side_flow_state.v1",
        "task031_result": task031_result,
        "property_snapshot_hash": snapshot["property_snapshot_hash"],
        "property_snapshot": snapshot,
        "mass_flow_authority": mass_flow,
        "evidence_refs": ["task032-fixture"],
    }
    flow: dict[str, Any] = {
        "schema_version": "task032.shell-side-flow-state-success.v1",
        "profile_id": "hxforge.shell_tube.shell_side_flow_state.v1",
        "implementation_software_version": "task032.fixture-v1",
        "shell_side_case_id": "CASE-034",
        "shell_side_stream_id": "STREAM-034",
        "shell_side_fluid_id": "FLUID-034",
        "task020_configuration_id": "TASK020-034-CASE",
        "task020_configuration_hash": "20" * 32,
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "property_snapshot_hash": snapshot["property_snapshot_hash"],
        "mass_flow_authority_hash": mass_flow["authority_hash"],
        "engineering_authority_id": "TASK032-ENGINEERING",
        "engineering_authority_hash": "32" * 32,
        "flow_model": "SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING",
        "phase_region": "SINGLE_PHASE_LIQUID",
        "rheology_model": "NEWTONIAN",
        "shell_side_mass_flow_rate_kg_s": "102.0",
        "shell_side_mass_velocity_kg_m2_s": "1200",
        "shell_side_bulk_velocity_m_s": "1.2",
        "shell_side_reynolds_number": "12000",
        "shell_side_prandtl_number": "6.96",
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
        "provenance": [
            ["task_id", "TASK032"],
            ["design_contract_path", "docs/tasks/TASK-032.md"],
            ["implementation_software_version", "task032.fixture-v1"],
            ["request_hash", ""],
            ["task020_configuration_id", "TASK020-034-CASE"],
            ["task020_configuration_hash", "20" * 32],
            ["task031_geometry_id", geometry["geometry_id"]],
            ["task031_geometry_hash", geometry["geometry_hash"]],
            ["property_snapshot_hash", snapshot["property_snapshot_hash"]],
            ["mass_flow_authority_hash", mass_flow["authority_hash"]],
            ["engineering_authority_id", "TASK032-ENGINEERING"],
            ["engineering_authority_hash", "32" * 32],
            ["formula_ids", ["F1"]],
            ["source_ids", ["TASK032-SOURCE"]],
            ["flow_model", "SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING"],
            ["phase_region", "SINGLE_PHASE_LIQUID"],
            ["rheology_model", "NEWTONIAN"],
            ["shell_side_case_id", "CASE-034"],
            ["shell_side_stream_id", "STREAM-034"],
            ["shell_side_fluid_id", "FLUID-034"],
            ["warnings", []],
            ["deferred_capabilities", []],
            ["evidence_refs", ["task032-fixture"]],
            ["engineering_source_formula_freeze_comment_id", "TASK032-FREEZE"],
            ["source_definition_issue", "185"],
        ],
    }
    flow["request_hash"] = task032_request_hash(task032_evidence)
    flow["provenance"][3][1] = flow["request_hash"]
    flow["result_hash"] = task032_success_hash(flow)
    flow["result_id"] = task032_result_id(flow["result_hash"])
    upstream: dict[str, Any] = {
        "status": "SUCCESS",
        "engineering_source_authority_record_id": "5387111841",
        "construction_family": "E_SHELL",
        "shell_pass_count": 1,
        "baffle_type": "SINGLE_SEGMENTAL",
        "pattern_family": "TRIANGULAR_PITCH",
        "baffle_cut": "CONSTANT_25_PERCENT_SOURCE_PROFILE",
        "task032_flow_state": flow,
        "task032_request_evidence": task032_evidence,
        "evidence_refs": ["task033-fixture"],
    }
    upstream["request_hash"] = task033_request_hash(upstream)
    result = {
        "schema_version": "task033.shell-side-heat-transfer.v1",
        "profile_id": "hxforge.shell_tube.shell_side_heat_transfer.v1",
        "first_slice_profile_id": (
            "SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_KERN_KHARAJI_2021_EQ58_"
            "OUTER_TUBE_SURFACE_HTC_SCREENING_V1"
        ),
        "implementation_software_version": "task033.fixture-v1",
        "shell_side_case_id": "CASE-034",
        "shell_side_stream_id": "STREAM-034",
        "shell_side_fluid_id": "FLUID-034",
        "task020_configuration_id": "TASK020-034-CASE",
        "task020_configuration_hash": "20" * 32,
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "property_snapshot_hash": snapshot["property_snapshot_hash"],
        "mass_flow_authority_hash": mass_flow["authority_hash"],
        "task032_request_hash": flow["request_hash"],
        "task032_result_hash": flow["result_hash"],
        "task032_result_id": flow["result_id"],
        "correlation_id": "TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1",
        "engineering_source_authority_record_id": "5387111841",
        "heat_transfer_surface": "OUTER_TUBE_SURFACE",
        "modeled_shell_side_heat_transfer_coefficient_w_m2_k": "100.000",
        "request_hash": upstream["request_hash"],
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
        "applicability_context": [],
        "provenance": [],
    }
    upstream["result"] = result
    upstream["result_hash"] = task033_result_hash(upstream)
    upstream["result_id"] = task033_result_id(upstream["result_hash"])
    raw: dict[str, Any] = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "task033_upstream_evidence": upstream,
        "task031_request_evidence": task031_request,
        "task031_request_hash": task031_hash,
        "shell_inside_diameter_m": "1.200",
        "baffle_count": 12,
        "uniform_spacing_sequence_m": ["0.120", "0.120"],
        "tube_pitch_m": "0.025",
        "tube_outer_diameter_m": "0.020",
        "pattern_family": "TRIANGULAR_PITCH",
        "shell_side_wall_dynamic_viscosity_pa_s": "0.00082",
        "wall_property_schema_version": "task034.wall-property.v1",
        "wall_property_source_id": "fixture-wall",
        "wall_property_source_version": "v1",
        "wall_property_evidence_refs": ["wall-fixture"],
        "wall_property_snapshot_hash": "wall-snapshot",
        "wall_property_authority_hash": "",
        "correlation_id": CORRELATION_ID,
        "shell_side_case_id": "CASE-034",
        "shell_side_stream_id": "STREAM-034",
        "shell_side_fluid_id": "FLUID-034",
        "task020_configuration_id": "TASK020-034-CASE",
        "task020_configuration_hash": "20" * 32,
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "task032_request_hash": flow["request_hash"],
        "task032_result_id": flow["result_id"],
        "task032_result_hash": flow["result_hash"],
        "task033_request_hash": upstream["request_hash"],
        "task033_result_id": upstream["result_id"],
        "task033_result_hash": upstream["result_hash"],
        "property_snapshot_hash": snapshot["property_snapshot_hash"],
        "mass_flow_authority_hash": mass_flow["authority_hash"],
        "evidence_refs": ["task034-fixture"],
    }
    raw["wall_property_authority_hash"] = wall_property_authority_hash(raw)
    return raw


def copy_request() -> dict[str, Any]:
    return deepcopy(make_valid_raw_request())


def test_x001_success_nominal_liquid() -> None:
    result = validate_request(make_valid_raw_request())
    assert result.status.value == "VALID"
    assert result.pressure_drop is not None
    assert result.pressure_drop.modeled_shell_side_pressure_drop_pa > 0


def test_x006_physical_boundary_no_double_count() -> None:
    result = validate_request(make_valid_raw_request()).pressure_drop
    assert result is not None
    assert dict(result.physical_boundary_context)["total_shell_side_pressure_drop"] is False


def test_x007_success_hash_self_exclusion() -> None:
    result = validate_request(make_valid_raw_request()).pressure_drop
    assert result is not None and result.result_hash and result.result_id


def test_x010_c5_schema_contract() -> None:
    assert len(validate_request(make_valid_raw_request()).pressure_drop.__dataclass_fields__) == 40
