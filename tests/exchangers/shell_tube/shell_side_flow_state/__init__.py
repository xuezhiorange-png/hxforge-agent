"""Shared TASK-032 contract fixtures for the allowlisted test modules."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
    mass_flow_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.models import (
    FIRST_SLICE_PROFILE_ID,
    FLOW_MODEL,
    FLOW_REGION_IDENTITY,
    IMPLEMENTATION_SOFTWARE_VERSION,
    MASS_FLOW_SIGN_CONVENTION,
    PROFILE_ID,
    PROPERTY_STATE_ROLE,
    REQUEST_SCHEMA_VERSION,
    RHEOLOGY_MODEL,
    ShellSideMassFlowAuthority,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    canonical as task031_canonical,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    models as task031_models,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    PhaseRegion,
    PropertySnapshot,
    recompute_property_snapshot_hash,
)


def _hash(fill: str) -> str:
    return fill * 64


def _geometry_provenance(
    *,
    request_hash: str,
    task020_id: str,
    task020_hash: str,
    task021_id: str,
    task021_hash: str,
    task022_id: str,
    task022_hash: str,
    task024_id: str,
    task024_hash: str,
    pattern_family: str,
    flow_region_identity: str,
) -> list[list[Any]]:
    return [
        ["task_id", "TASK-031"],
        ["design_contract_path", task031_models.DESIGN_CONTRACT_PATH],
        ["task020_configuration_id", task020_id],
        ["task020_configuration_hash", task020_hash],
        ["task021_layout_id", task021_id],
        ["task021_layout_hash", task021_hash],
        ["task022_geometry_id", task022_id],
        ["task022_geometry_hash", task022_hash],
        ["task024_geometry_id", task024_id],
        ["task024_geometry_hash", task024_hash],
        [
            "engineering_authority_profile_id",
            task031_models.AGGREGATE_AUTHORITY_PROFILE_ID,
        ],
        ["engineering_authority_hash", _hash("a")],
        ["formula_a_id", task031_models.FORMULA_A_ID],
        ["formula_b_id", task031_models.FORMULA_B_ID],
        ["freeze_comment_id", "5311936966"],
        [
            "source_ids",
            ["SRC-INTECHOPEN-100450-KHARAJI-2021", "SRC-TASK031-DESIGN-CONTRACT"],
        ],
        ["pattern_family", pattern_family],
        ["flow_region_identity", flow_region_identity],
        ["software_version", task031_canonical.IMPLEMENTATION_SOFTWARE_VERSION],
        ["git_commit", task031_canonical.GIT_COMMIT],
        ["request_hash", request_hash],
        ["warnings", []],
        ["deferred_capabilities", list(task031_models.DEFERRED_CAPABILITIES)],
    ]


def _geometry_raw() -> dict[str, Any]:
    task020_id = "TASK020-CASE-001"
    task020_hash = _hash("2")
    task021_id = "TASK021-LAYOUT-001"
    task021_hash = _hash("3")
    task022_id = "TASK022-GEOMETRY-001"
    task022_hash = _hash("4")
    task024_id = "TASK024-GEOMETRY-001"
    task024_hash = _hash("5")
    geometry_fields: dict[str, Any] = {
        "schema_version": task031_models.RESULT_SCHEMA_VERSION,
        "geometry_id": "",
        "geometry_hash": "",
        "request_hash": _hash("6"),
        "task020_configuration_id": task020_id,
        "task020_configuration_hash": task020_hash,
        "task021_layout_id": task021_id,
        "task021_layout_hash": task021_hash,
        "task022_geometry_id": task022_id,
        "task022_geometry_hash": task022_hash,
        "task024_geometry_id": task024_id,
        "task024_geometry_hash": task024_hash,
        "engineering_authority_id": "urn:hxforge:task031:engineering-authority:v1:fixture",
        "engineering_authority_hash": _hash("a"),
        "formula_a_id": task031_models.FORMULA_A_ID,
        "formula_b_id": task031_models.FORMULA_B_ID,
        "pattern_family": "SQUARE_45",
        "flow_region_identity": FLOW_REGION_IDENTITY,
        "central_inter_baffle_spacing_m": "0.0500000",
        "central_crossflow_flow_area_m2": "0.1000000",
        "shell_side_equivalent_hydraulic_diameter_m": "0.0200000",
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": list(task031_models.DEFERRED_CAPABILITIES),
        "provenance": [],
    }
    provenance = _geometry_provenance(
        request_hash=geometry_fields["request_hash"],
        task020_id=task020_id,
        task020_hash=task020_hash,
        task021_id=task021_id,
        task021_hash=task021_hash,
        task022_id=task022_id,
        task022_hash=task022_hash,
        task024_id=task024_id,
        task024_hash=task024_hash,
        pattern_family=geometry_fields["pattern_family"],
        flow_region_identity=geometry_fields["flow_region_identity"],
    )
    geometry_fields["provenance"] = provenance
    provisional = task031_models.ShellSideHydraulicGeometry(
        **geometry_fields,
    )
    geometry_hash = task031_canonical.sha256_hex(
        task031_canonical.success_geometry_canonical_projection(provisional)
    )
    geometry_fields["geometry_hash"] = geometry_hash
    geometry_fields["geometry_id"] = task031_canonical.geometry_id(geometry_hash)
    return geometry_fields


def _property_snapshot_raw() -> dict[str, Any]:
    values: dict[str, Any] = {
        "density_kg_m3": Decimal("998.2000"),
        "dynamic_viscosity_pa_s": Decimal("0.0010020"),
        "thermal_conductivity_w_m_k": Decimal("0.5980000"),
        "specific_heat_capacity_j_kg_k": Decimal("4182.0000"),
        "bulk_temperature_k": Decimal("298.1500"),
        "bulk_pressure_pa": Decimal("101325.0000"),
        "phase_region": PhaseRegion.SINGLE_PHASE_LIQUID,
        "property_source_id": "TASK026-FIXTURE-PROVIDER",
        "property_source_version": "v1",
        "property_snapshot_hash": _hash("0"),
    }
    snapshot = PropertySnapshot(**values)
    snapshot_hash = recompute_property_snapshot_hash(snapshot)
    values["property_snapshot_hash"] = snapshot_hash
    return {
        "density_kg_m3": str(values["density_kg_m3"]),
        "dynamic_viscosity_pa_s": str(values["dynamic_viscosity_pa_s"]),
        "thermal_conductivity_w_m_k": str(values["thermal_conductivity_w_m_k"]),
        "specific_heat_capacity_j_kg_k": str(values["specific_heat_capacity_j_kg_k"]),
        "bulk_temperature_k": str(values["bulk_temperature_k"]),
        "bulk_pressure_pa": str(values["bulk_pressure_pa"]),
        "phase_region": values["phase_region"].value,
        "property_source_id": values["property_source_id"],
        "property_source_version": values["property_source_version"],
        "property_snapshot_hash": snapshot_hash,
    }


def _mass_flow_authority_raw(
    *,
    geometry: dict[str, Any],
    property_snapshot_hash: str,
    mass_flow_rate: str = "2.0000000",
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "schema_version": "task032.shell-side-mass-flow-authority.v1",
        "authority_profile_id": FIRST_SLICE_PROFILE_ID,
        "shell_side_case_id": "CASE-001",
        "shell_side_stream_id": "SHELL-SIDE-001",
        "shell_side_fluid_id": "WATER",
        "rheology_model": RHEOLOGY_MODEL,
        "task020_configuration_id": geometry["task020_configuration_id"],
        "task020_configuration_hash": geometry["task020_configuration_hash"],
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "property_snapshot_hash": property_snapshot_hash,
        "property_state_role": PROPERTY_STATE_ROLE,
        "mass_flow_rate_kg_s": Decimal(mass_flow_rate),
        "mass_flow_sign_convention": MASS_FLOW_SIGN_CONVENTION,
        "authority_source_id": "TASK032-MASS-FLOW-FIXTURE",
        "authority_source_version": "v1",
        "evidence_refs": ("mass-z", "mass-a"),
        "authority_hash": _hash("0"),
    }
    authority = ShellSideMassFlowAuthority(**fields)
    authority_hash = mass_flow_authority_hash(authority)
    fields["authority_hash"] = authority_hash
    return {
        **fields,
        "mass_flow_rate_kg_s": str(fields["mass_flow_rate_kg_s"]),
        "evidence_refs": list(fields["evidence_refs"]),
    }


def make_valid_raw_request() -> dict[str, Any]:
    geometry = _geometry_raw()
    property_snapshot = _property_snapshot_raw()
    mass_flow = _mass_flow_authority_raw(
        geometry=geometry,
        property_snapshot_hash=property_snapshot["property_snapshot_hash"],
    )
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "task031_result": {
            "status": "VALID",
            "geometry": geometry,
            "warnings": [],
            "blockers": [],
            "deferred_capabilities": [],
            "blocked_result_hash": None,
        },
        "property_snapshot_hash": property_snapshot["property_snapshot_hash"],
        "property_snapshot": property_snapshot,
        "mass_flow_authority": mass_flow,
        "evidence_refs": ["request-z", "request-a"],
    }


def copy_request() -> dict[str, Any]:
    return deepcopy(make_valid_raw_request())


def authority_with_hash(raw_request: dict[str, Any]) -> ShellSideMassFlowAuthority:
    from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import parse_request

    return parse_request(raw_request).mass_flow_authority


def with_mass_flow(raw_request: dict[str, Any], value: str) -> dict[str, Any]:
    request = deepcopy(raw_request)
    authority = request["mass_flow_authority"]
    authority["mass_flow_rate_kg_s"] = value
    parsed = authority_with_hash(request)
    authority["authority_hash"] = mass_flow_authority_hash(
        replace(parsed, mass_flow_rate_kg_s=Decimal(value))
    )
    return request


__all__ = [
    "FLOW_MODEL",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "PhaseRegion",
    "authority_with_hash",
    "copy_request",
    "make_valid_raw_request",
    "with_mass_flow",
]
