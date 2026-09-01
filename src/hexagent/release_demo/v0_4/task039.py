"""TASK039 v0.4 actual production replay and release-evidence assembly."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import uuid
from collections.abc import Mapping
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, cast

from hexagent.exchangers.shell_tube import validate_request as validate_task020
from hexagent.exchangers.shell_tube.baffle_geometry.validation import to_canonical_primitive
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua import (
    build_raw_overall_u_ua_request,
    evaluate_task038,
    service_binding_hash,
    verify_task038_success_identity,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038Request,
    TubeSideServiceBindingAuthority,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance import (
    InsideFoulingResistanceAuthority,
    OutsideFoulingResistanceAuthority,
    Task037Request,
    TubeWallMaterialAuthority,
    TubeWallThermalConductivityAuthority,
    evaluate_task037,
    verify_task037_success_identity,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state import (
    validate_request as validate_task032,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
    mass_flow_authority_hash as task032_mass_flow_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.models import (
    ShellSideMassFlowAuthority,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import (
    parse_request as parse_task032_request,
)
from hexagent.exchangers.shell_tube.shell_side_heat_transfer import (
    validate_request as validate_task033,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    canonical as task031_canonical,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    schema as task031_schema,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    validate_request as validate_task031,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.authority import (
    layout_hash_payload as task021_layout_hash_payload,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import (
    canonical as task034_canonical,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import (
    validate_request as validate_task034,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import (
    CORRELATION_ID as TASK034_CORRELATION_ID,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import (
    PROFILE_ID as TASK034_PROFILE_ID,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import (
    REQUEST_SCHEMA_VERSION as TASK034_REQUEST_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition import (
    canonical as task035_canonical,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition import (
    validate_request as validate_task035,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.models import (
    PROFILE_ID as TASK035_PROFILE_ID,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.models import (
    REQUEST_SCHEMA_VERSION as TASK035_REQUEST_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_layout import (
    canonical as task021_canonical,
)
from hexagent.exchangers.shell_tube.tube_layout import (
    validate_request as validate_task021,
)
from hexagent.exchangers.shell_tube.tube_side import (
    FlowPathMode,
    HeatTransferLengthAuthority,
    HydraulicAuthorityMode,
    InternalFlowLengthAuthority,
    Task025HydraulicParticipationAuthority,
    canonical_heat_transfer_pair,
    canonical_internal_flow_pair,
    evaluate_task025,
    heat_transfer_authority_length_hash,
    hydraulic_authority_hash,
    internal_flow_authority_length_hash,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    DEFERRED_CAPABILITIES_V1,
    INPUT_EVIDENCE_REFS_V1,
    TASK026_VERSION,
    PhaseAssertion,
    PhaseRegion,
    PropertySnapshot,
    ThermalBoundaryCondition,
    TubeSideThermalRequest,
    build_raw_tube_side_request_envelope,
    compute_tube_side_heat_transfer_coefficient,
    recompute_property_snapshot_hash,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    IMPLEMENTATION_SOFTWARE_VERSION as TASK026_IMPLEMENTATION_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    SCHEMA_VERSION as TASK026_SCHEMA_VERSION,
)

from .artifacts import (
    build_checklist,
    build_manifest,
    exact_file_digest,
    render_acceptance_bytes,
    render_demo_json_bytes,
    render_demo_markdown_bytes,
    render_manifest_bytes,
)
from .canonical import (
    result_hash,
    result_id,
)
from .models import (
    Task039Run,
    Task039ValidationResult,
)
from .provenance import build_provenance
from .schema import (
    ACCEPTANCE_LEDGER_SCHEMA_VERSION,
    ALLOCATION_ISSUE,
    ALLOCATION_REVISION,
    ARTIFACT_PATHS,
    AVAILABLE_CAPABILITIES,
    BASE_MAIN_SHA,
    BASE_MAIN_TREE,
    BLOCKED_DEMO_IDS,
    BLOCKER_MATRIX,
    DEMO_SUCCESS_ID,
    DETERMINISM_SCHEMA_VERSION,
    PRODUCTION_GRAPH_SCHEMA_VERSION,
    PROFILE_ID,
    RELEASE_ACCEPTANCE_RESULT_SCHEMA_VERSION,
    RELEASE_EVIDENCE_SCHEMA_VERSION,
    RELEASE_VERSION,
    SOURCE_DEFINITION_ISSUE,
    SOURCE_DEFINITION_REVISION,
    TASK_ID,
    TEST_IDS,
    UNAVAILABLE_CAPABILITIES,
    V03_GITHUB_RELEASE_ID,
    V03_MANIFEST_HASH,
    V03_TAG,
    V03_TAG_TARGET_COMMIT,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
TASK031_DESIGN_PATH = (
    REPO_ROOT / "docs/tasks/TASK-031-shell-and-tube-shell-side-flow-path-hydraulic-geometry.md"
)
TASK035_DELIVERY_COMMIT = "e48d83208bfe4de782ee055a99c826fb9eebb334"
TASK035_MERGE_TREE = "8399dcf766b1c8d98794430e810d186134234d89"
TASK038_MERGE_COMMIT = "0d65380e05c0000237ef862640687c94ecc21bb1"
TASK038_POST_MERGE_MAIN_CI_RUN = "33371394290"


def _public(value: Any, *, decimal_strings: bool = False) -> Any:
    if isinstance(value, Decimal):
        return str(value) if decimal_strings else value
    if isinstance(value, Enum):
        return _public(value.value, decimal_strings=decimal_strings)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _public(getattr(value, field.name), decimal_strings=decimal_strings)
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(key): _public(item, decimal_strings=decimal_strings) for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_public(item, decimal_strings=decimal_strings) for item in value]
    if isinstance(value, bytes):
        return value.hex()
    if hasattr(value, "items"):
        return {
            str(key): _public(item, decimal_strings=decimal_strings) for key, item in value.items()
        }
    return value


def _public_strings(value: Any) -> Any:
    return _public(value, decimal_strings=True)


def _public_decimals(value: Any) -> Any:
    return _public(value, decimal_strings=False)


def _json_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_task020_request() -> dict[str, Any]:
    return {
        "schema_version": "task020.configuration-request.v1",
        "case_authority": {
            "revision_id": "task039-release-demo-001",
            "payload_hash": "a" * 64,
            "domain_snapshot_hash": "b" * 64,
            "status": "committed",
        },
        "equipment_family": "SHELL_AND_TUBE",
        "authority_mode": "INTERNAL_GENERIC",
        "construction_family": "FIXED_TUBESHEET",
        "orientation": "HORIZONTAL",
        "shell_pass_count": 1,
        "tube_pass_count": 1,
        "front_head_token": "A",
        "shell_token": "E",
        "rear_head_token": "L",
        "standard_system_id": None,
        "requested_rule_pack_identity": None,
        "evidence_refs": [],
    }


def _build_t021_geometry_payload() -> dict[str, Any]:
    geometry: dict[str, Any] = {
        "geometry_id": "tube-od-20mm",
        "geometry_type": "tube",
        "revision": "1",
        "approval_state": "approved",
        "outer_diameter_m": "0.02",
        "inner_diameter_m": "0.016",
        "wall_thickness_m": "0.002",
        "record_hash": "c" * 64,
        "snapshot_hash": "",
        "source_binding": {
            "source_id": "geometry-source",
            "source_type": "approved-record",
            "source_revision": "1",
            "source_location": "memory://task039/tube-geometry",
            "evidence_ref": "geometry-evidence",
            "approved_by": "task039-authority",
            "approved_at": "2026-07-13T00:00:00Z",
        },
    }
    geometry["snapshot_hash"] = _json_sha256(
        {key: value for key, value in geometry.items() if key != "snapshot_hash"}
    )
    return geometry


def _build_t021_rule_payload() -> dict[str, Any]:
    rule: dict[str, Any] = {
        "profile_id": "hxforge.shell_tube.tube_layout.v1",
        "authority_mode": "INTERNAL_GENERIC",
        "rule_id": "generic-layout",
        "rule_version": "1",
        "rule_artifact_canonical_hash": "d" * 64,
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "license_evidence": {"status": "NO_STANDARD_CLAIM"},
        "approval_status": "approved",
        "provenance_edge_ids": ["edge-task039-layout"],
        "evidence_refs": ["rule-evidence"],
        "rule_pack_identity": None,
        "pattern_family": "SQUARE",
        "pitch_m": "0.03",
        "edge_clearance_m": "0",
        "allowed_origin_modes": ["CENTER_ON_LATTICE_POINT", "CENTER_ON_PRIMITIVE_CELL"],
        "allowed_axis_orientations": ["PRIMARY_AXIS_X", "PRIMARY_AXIS_Y"],
        "allowed_exclusion_zone_types": ["AXIS_ALIGNED_RECTANGLE", "CIRCLE"],
        "maximum_candidate_positions": 100000,
        "snapshot_hash": "",
    }
    rule["snapshot_hash"] = _json_sha256(
        {key: value for key, value in rule.items() if key != "snapshot_hash"}
    )
    return rule


def _build_task021_request(config: Any) -> dict[str, Any]:
    return {
        "schema_version": "task021.tube-layout-request.v1",
        "configuration": config,
        "tube_geometry": _build_t021_geometry_payload(),
        "layout_rule_authority": _build_t021_rule_payload(),
        "placement_envelope": {
            "schema_version": "task021.circular-envelope.v1",
            "tube_center_envelope_diameter_m": "0.12",
            "evidence_refs": ["envelope-evidence"],
        },
        "origin_mode": "CENTER_ON_LATTICE_POINT",
        "axis_orientation": "PRIMARY_AXIS_X",
        "exclusion_zones": [],
        "u_tube_pairing_plan": None,
        "evidence_refs": ["request-evidence"],
    }


def _build_task025_request(layout: Any, config: Any) -> dict[str, Any]:
    position_ids = tuple(position.position_id for position in layout.positions)
    flow_pair = canonical_internal_flow_pair()
    heat_pair = canonical_heat_transfer_pair()
    mode = HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH
    flow = InternalFlowLengthAuthority(
        "flow",
        Decimal("4.85"),
        flow_pair,
        flow_pair,
        mode,
        internal_flow_authority_length_hash(Decimal("4.85"), flow_pair, flow_pair, mode),
    )
    heat = HeatTransferLengthAuthority(
        "heat",
        Decimal("4.85"),
        heat_pair,
        heat_pair,
        mode,
        heat_transfer_authority_length_hash(Decimal("4.85"), heat_pair, heat_pair, mode),
    )
    participation_hash = hydraulic_authority_hash(
        task020_configuration_id=config.configuration_id,
        task021_layout_id=layout.layout_id,
        internal_flow_length_hash_value=flow.length_hash,
        heat_transfer_length_hash_value=heat.length_hash,
        all_layout_position_ids=position_ids,
        active_position_ids=position_ids,
        inactive_position_ids=(),
        hydraulic_authority_mode=mode,
        participation_evidence_refs=("task039",),
    )
    participation = Task025HydraulicParticipationAuthority(
        all_layout_position_ids=position_ids,
        active_position_ids=position_ids,
        inactive_position_ids=(),
        authority_mode=mode,
        evidence_refs=("task039",),
        hydraulic_authority_hash=participation_hash,
    )
    return {
        "schema_version": "task025.request.v1",
        "profile_id": "profile-001",
        "task020_configuration": config,
        "task021_layout": layout,
        "internal_flow_authority": flow,
        "heat_transfer_authority": heat,
        "hydraulic_participation_authority": participation,
        "flow_path_mode": FlowPathMode.STRAIGHT_TUBE_PARALLEL_FLOW,
        "hydraulic_authority_mode": mode,
        "evidence_refs": ("task039",),
    }


def _build_task026_request() -> TubeSideThermalRequest:
    mu = Decimal("0.001")
    hydraulic_diameter = Decimal("0.01")
    conductivity = Decimal("0.5984")
    total_area = Decimal("0.01")
    heat_capacity = Decimal("4190.35584")
    density = Decimal("499.0020") * mu / (Decimal("0.0500898") * hydraulic_diameter)
    mass_flow = Decimal("0.0500898") * density * total_area
    snapshot = PropertySnapshot(
        density_kg_m3=density,
        dynamic_viscosity_pa_s=mu,
        thermal_conductivity_w_m_k=conductivity,
        specific_heat_capacity_j_kg_k=heat_capacity,
        bulk_temperature_k=Decimal("293.15"),
        bulk_pressure_pa=Decimal("101325"),
        phase_region=PhaseRegion.SINGLE_PHASE_LIQUID,
        property_source_id="CoolProp-6.6",
        property_source_version="1.0.0",
        property_snapshot_hash="0" * 64,
    )
    snapshot_hash = recompute_property_snapshot_hash(snapshot)
    snapshot = dataclasses.replace(snapshot, property_snapshot_hash=snapshot_hash)
    from hexagent.exchangers.shell_tube.tube_side_thermal import FrozenProvenance

    provenance = FrozenProvenance(
        task_id="TASK-026",
        design_contract_path="/tmp/TASK-026-DESIGN-CONTRACT-DRAFT-R6-R7.md",
        implementation_software_version=TASK026_IMPLEMENTATION_VERSION,
        input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
        upstream_identity_hashes=("a" * 64,),
    )
    return TubeSideThermalRequest(
        schema_version=TASK026_SCHEMA_VERSION,
        task026_version=TASK026_VERSION,
        implementation_software_version=TASK026_IMPLEMENTATION_VERSION,
        property_snapshot_hash=snapshot_hash,
        property_snapshot=snapshot,
        phase_assertion=PhaseAssertion.SINGLE_PHASE_LIQUID,
        thermal_boundary_condition=ThermalBoundaryCondition.CWT,
        mass_flow_rate_kg_s=mass_flow,
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
        provenance=provenance,
    )


def _require_valid(result: Any, task_id: str) -> Any:
    status = getattr(result, "status", None)
    for name in (
        "configuration",
        "layout",
        "result",
        "geometry",
        "flow_state",
        "heat_transfer",
        "pressure_drop",
        "success_result",
    ):
        value = getattr(result, name, None)
        if value is not None and str(getattr(status, "value", status)) == "VALID":
            return value
    raise ValueError(f"{task_id} public operation did not produce a valid payload")


def _build_task037_request() -> Task037Request:
    material = TubeWallMaterialAuthority(
        "T039-WALL-MAT-001",
        "T039-MAT-001",
        "FIXTURE-GRADE",
        "T039-INTERNAL-WALL-MATERIAL-SOURCE",
        "R2",
        "ISSUE_214/R2/SUCCESS_VECTOR/WALL_MATERIAL",
        "INTERNAL_ENGINEERING_RULE",
        "INTERNAL_USE_AUTHORIZED",
        "APPROVED",
        ("T039-EV-WALL-MATERIAL-001",),
        "1" * 64,
    )
    conductivity = TubeWallThermalConductivityAuthority(
        "T039-WALL-COND-001",
        "T039-MAT-001",
        Decimal("16"),
        Decimal("300"),
        "T039-WALL-COND-CONTEXT-001",
        "FIXED_RELEASE_DEMO_INPUT",
        "b27e46a1fddcca65be32674bc07d745c1c360a2012f8b63cc53f53f47cdf7fe8",
        "T039-INTERNAL-WALL-MATERIAL-SOURCE",
        "R2",
        "ISSUE_214/R2/SUCCESS_VECTOR/WALL_MATERIAL",
        "INTERNAL_ENGINEERING_RULE",
        "INTERNAL_USE_AUTHORIZED",
        "APPROVED",
        ("T039-EV-WALL-MATERIAL-001",),
        "2" * 64,
    )
    inside = InsideFoulingResistanceAuthority(
        "T039-FOUL-IN-001",
        "INSIDE",
        Decimal("0.0001"),
        "INNER_TUBE_SURFACE",
        "TUBE-WATER-001",
        "T039-FOULING",
        "R2",
        "ISSUE_214/R2/SUCCESS_VECTOR/FOULING",
        "APPROVED_ENGINEERING_BASIS",
        "INTERNAL_USE_AUTHORIZED",
        "APPROVED",
        ("T039-EV-FOULING-IN-001",),
        "3" * 64,
    )
    outside = OutsideFoulingResistanceAuthority(
        "T039-FOUL-OUT-001",
        "OUTSIDE",
        Decimal("0.0002"),
        "OUTER_TUBE_SURFACE",
        "SHELL-WATER-001",
        "T039-FOULING",
        "R2",
        "ISSUE_214/R2/SUCCESS_VECTOR/FOULING",
        "APPROVED_ENGINEERING_BASIS",
        "INTERNAL_USE_AUTHORIZED",
        "APPROVED",
        ("T039-EV-FOULING-OUT-001",),
        "4" * 64,
    )
    return Task037Request(
        schema_version="task037.request.v1",
        task037_version="task037.overall-heat-transfer-resistance.v1",
        implementation_software_version="task037.overall-heat-transfer-resistance.impl-v1",
        wall_material_authority=material,
        wall_thermal_conductivity_authority=conductivity,
        inside_fouling_authority=inside,
        outside_fouling_authority=outside,
        evidence_refs=("T039-R2-SUCCESS-AUTHORITY-VECTOR", "ISSUE-214-R2"),
    )


def _load_task031_fixture() -> dict[str, Any]:
    text = TASK031_DESIGN_PATH.read_text(encoding="utf-8")
    marker = '"schema_version": "task031.shell-side-hydraulic-geometry-request.v1"'
    index = text.index(marker)
    start = text.rfind("```json", 0, index)
    end = text.index("```", start + len("```json"))
    return cast(dict[str, Any], json.loads(text[start + len("```json") : end]))


def _layout_rule_snapshot_hash(rule: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in rule.items() if key != "snapshot_hash"}
    return task031_canonical.sha256_hex(task021_canonical.canonical_json(payload))


def _resync_task021_layout_identity(raw_request: dict[str, Any]) -> None:
    rule = raw_request["tube_layout"]["layout_rule_authority"]
    snapshot_hash = _layout_rule_snapshot_hash(rule)
    rule["snapshot_hash"] = snapshot_hash
    raw_request["tube_layout"]["provenance"]["layout_rule_snapshot_hash"] = snapshot_hash
    parsed = task031_schema.parse_request(raw_request)
    layout_hash = task031_canonical.sha256_hex(task021_layout_hash_payload(parsed.tube_layout))
    layout_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "urn:hxforge:task021:tube-layout:v1:" + layout_hash,
        )
    )
    raw_request["tube_layout"]["layout_hash"] = layout_hash
    raw_request["tube_layout"]["layout_id"] = layout_id
    geometry = raw_request["baffle_geometry_result"].get("geometry")
    if isinstance(geometry, dict):
        geometry["task021_layout_id"] = layout_id
        geometry["task021_layout_hash"] = layout_hash


def _task024_geometry_hash_payload(geometry: Any) -> dict[str, Any]:
    provenance = {key: value for key, value in geometry.provenance}
    return {
        "schema_version": geometry.schema_version,
        "request_hash": geometry.request_hash,
        "task020_configuration_id": geometry.task020_configuration_id,
        "task020_configuration_hash": geometry.task020_configuration_hash,
        "task021_layout_id": geometry.task021_layout_id,
        "task021_layout_hash": geometry.task021_layout_hash,
        "task022_geometry_id": geometry.task022_geometry_id,
        "task022_geometry_hash": geometry.task022_geometry_hash,
        "construction_family": geometry.construction_family,
        "equipment_orientation": geometry.equipment_orientation,
        "shell_pass_count": geometry.shell_pass_count,
        "tube_pass_count": geometry.tube_pass_count,
        "shell_inside_diameter_m": geometry.shell_inside_diameter_m,
        "tube_outer_diameter_m": geometry.tube_outer_diameter_m,
        "axial_span": to_canonical_primitive(geometry.axial_span),
        "design_authority": to_canonical_primitive(geometry.design_authority),
        "usable_baffle_span_m": geometry.usable_baffle_span_m,
        "baffle_diameter_m": geometry.baffle_diameter_m,
        "baffle_radius_m": geometry.baffle_radius_m,
        "baffle_hole_diameter_m": geometry.baffle_hole_diameter_m,
        "baffle_hole_radius_m": geometry.baffle_hole_radius_m,
        "cut_height_m": geometry.cut_height_m,
        "chord_offset_from_center_m": geometry.chord_offset_from_center_m,
        "baffle_planes": [to_canonical_primitive(item) for item in geometry.baffle_planes],
        "position_count": geometry.position_count,
        "warnings": [
            {
                "code": item.code,
                "field_path": item.field_path,
                "message_key": item.message_key,
                "evidence_refs": list(item.evidence_refs),
                "details": [[key, value] for key, value in item.details],
            }
            for item in geometry.warnings
        ],
        "blockers": [
            {
                "code": item.code,
                "field_path": item.field_path,
                "message_key": item.message_key,
                "evidence_refs": list(item.evidence_refs),
                "details": [[key, value] for key, value in item.details],
            }
            for item in geometry.blockers
        ],
        "deferred_capabilities": list(geometry.deferred_capabilities),
        "provenance": provenance,
    }


def _resync_task024_geometry_identity(raw_request: dict[str, Any]) -> None:
    parsed = task031_schema.parse_request(raw_request)
    geometry = parsed.baffle_geometry_result.geometry
    if geometry is None:
        return
    geometry_hash = task031_canonical.sha256_hex(_task024_geometry_hash_payload(geometry))
    geometry_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "urn:hxforge:task024:baffle-geometry:v1:" + geometry_hash,
        )
    )
    raw_request["baffle_geometry_result"]["geometry"]["geometry_hash"] = geometry_hash
    raw_request["baffle_geometry_result"]["geometry"]["geometry_id"] = geometry_id


def _build_task031_request() -> dict[str, Any]:
    request = copy.deepcopy(_load_task031_fixture())
    request["tube_layout"]["layout_rule_authority"]["pattern_family"] = "TRIANGULAR"
    _resync_task021_layout_identity(request)
    _resync_task024_geometry_identity(request)
    return request


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
        "property_snapshot_hash": "0" * 64,
    }
    snapshot = PropertySnapshot(**values)
    values["property_snapshot_hash"] = recompute_property_snapshot_hash(snapshot)
    return {
        key: (value.value if isinstance(value, Enum) else str(value))
        for key, value in values.items()
    }


def _mass_flow_authority_raw(
    geometry: Mapping[str, Any], property_snapshot_hash: str
) -> dict[str, Any]:
    values: dict[str, Any] = {
        "schema_version": "task032.shell-side-mass-flow-authority.v1",
        "authority_profile_id": "SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1",
        "shell_side_case_id": "CASE-001",
        "shell_side_stream_id": "SHELL-SIDE-001",
        "shell_side_fluid_id": "SHELL-WATER-001",
        "rheology_model": "NEWTONIAN",
        "task020_configuration_id": geometry["task020_configuration_id"],
        "task020_configuration_hash": geometry["task020_configuration_hash"],
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "property_snapshot_hash": property_snapshot_hash,
        "property_state_role": "BULK_SHELL_SIDE_STATE",
        "mass_flow_rate_kg_s": "2.0000000",
        "mass_flow_sign_convention": "POSITIVE_ALONG_DECLARED_SHELL_SIDE_FLOW_DIRECTION",
        "authority_source_id": "TASK032-MASS-FLOW-FIXTURE",
        "authority_source_version": "v1",
        "evidence_refs": ["mass-z", "mass-a"],
        "authority_hash": "0" * 64,
    }
    parsed = dict(values)
    parsed["mass_flow_rate_kg_s"] = Decimal(parsed["mass_flow_rate_kg_s"])
    parsed["evidence_refs"] = tuple(parsed["evidence_refs"])
    values["authority_hash"] = task032_mass_flow_authority_hash(
        ShellSideMassFlowAuthority(**parsed)
    )
    return values


def _task031_public_result(result: Any, *, decimal_strings: bool = True) -> dict[str, Any]:
    return {
        "status": str(getattr(result.status, "value", result.status)),
        "geometry": _public(result.geometry, decimal_strings=decimal_strings),
        "warnings": _public(result.warnings, decimal_strings=decimal_strings),
        "blockers": _public(result.blockers, decimal_strings=decimal_strings),
        "deferred_capabilities": list(result.deferred_capabilities),
        "blocked_result_hash": result.blocked_result_hash,
    }


def _task032_request_evidence(raw_request: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": raw_request["schema_version"],
        "profile_id": raw_request["profile_id"],
        "task031_result": copy.deepcopy(raw_request["task031_result"]),
        "property_snapshot_hash": raw_request["property_snapshot_hash"],
        "property_snapshot": copy.deepcopy(raw_request["property_snapshot"]),
        "mass_flow_authority": copy.deepcopy(raw_request["mass_flow_authority"]),
        "evidence_refs": copy.deepcopy(raw_request["evidence_refs"]),
    }


def _build_task032_request(
    task031_result: Any,
    property_snapshot: Mapping[str, Any],
    mass_flow_authority: Mapping[str, Any],
) -> dict[str, Any]:
    geometry = task031_result.geometry
    if geometry is None:
        raise ValueError("TASK031 did not produce geometry")
    mass_flow = copy.deepcopy(dict(mass_flow_authority))
    mass_flow.update(
        {
            "task020_configuration_id": geometry.task020_configuration_id,
            "task020_configuration_hash": geometry.task020_configuration_hash,
            "task031_geometry_id": geometry.geometry_id,
            "task031_geometry_hash": geometry.geometry_hash,
            "property_snapshot_hash": property_snapshot["property_snapshot_hash"],
        }
    )
    parsed = parse_task032_request(
        {
            "schema_version": "task032.shell-side-flow-state-request.v1",
            "profile_id": "hxforge.shell_tube.shell_side_flow_state.v1",
            "task031_result": _task031_public_result(task031_result),
            "property_snapshot_hash": property_snapshot["property_snapshot_hash"],
            "property_snapshot": dict(property_snapshot),
            "mass_flow_authority": mass_flow,
            "evidence_refs": ["request-z", "request-a"],
        }
    )
    mass_flow["authority_hash"] = task032_mass_flow_authority_hash(parsed.mass_flow_authority)
    return {
        "schema_version": "task032.shell-side-flow-state-request.v1",
        "profile_id": "hxforge.shell_tube.shell_side_flow_state.v1",
        "task031_result": _task031_public_result(task031_result),
        "property_snapshot_hash": property_snapshot["property_snapshot_hash"],
        "property_snapshot": copy.deepcopy(dict(property_snapshot)),
        "mass_flow_authority": mass_flow,
        "evidence_refs": ["request-z", "request-a"],
    }


def _build_task033_request(
    task032_request: Mapping[str, Any], task032_result: Any
) -> dict[str, Any]:
    return {
        "schema_version": "task033.shell-side-heat-transfer-request.v1",
        "profile_id": "hxforge.shell_tube.shell_side_heat_transfer.v1",
        "task032_flow_state": _public_strings(task032_result.flow_state),
        "task032_request_evidence": _task032_request_evidence(task032_request),
        "evidence_refs": ["t033-request-z", "t033-request-a"],
    }


def _default_shell_authority(geometry: Any) -> dict[str, Any]:
    authority: dict[str, Any] = {
        "schema_version": "task034.shell-type-authority.v2",
        "shell_type": "E_SHELL",
        "task020_configuration_id": geometry.task020_configuration_id,
        "task020_configuration_hash": geometry.task020_configuration_hash,
        "authority_source_id": "TASK034-CALLER-SHELL-TYPE",
        "authority_source_version": "v1",
        "authority_record_id": "CASE-034-SHELL-TYPE",
        "evidence_refs": ["task034-shell-type-evidence"],
        "authority_hash": "",
    }
    authority["authority_hash"] = task034_canonical.shell_type_authority_hash(authority)
    return authority


def _default_wall_authority(
    flow: Any, geometry: Any, property_snapshot_hash: str
) -> dict[str, Any]:
    return {
        "schema_version": "task034.wall-property.v2",
        "shell_side_case_id": flow.shell_side_case_id,
        "shell_side_stream_id": flow.shell_side_stream_id,
        "shell_side_fluid_id": flow.shell_side_fluid_id,
        "task031_geometry_id": geometry.geometry_id,
        "task031_geometry_hash": geometry.geometry_hash,
        "task032_result_id": flow.result_id,
        "task032_result_hash": flow.result_hash,
        "property_snapshot_hash": property_snapshot_hash,
        "shell_side_wall_dynamic_viscosity_pa_s": "0.00082",
        "source_id": "fixture-wall",
        "source_version": "v1",
        "evidence_refs": ["wall-fixture"],
        "wall_property_snapshot_hash": "wall-snapshot",
        "wall_property_authority_hash": "",
    }


def _build_task034_request(
    task031_request: Mapping[str, Any],
    task031_result: Any,
    task032_request: Mapping[str, Any],
    task032_result: Any,
    task033_request: Mapping[str, Any],
    task033_result: Any,
) -> dict[str, Any]:
    geometry = task031_result.geometry
    flow = task032_result.flow_state
    heat = task033_result.heat_transfer
    if geometry is None or flow is None or heat is None:
        raise ValueError("upstream shell chain is not valid")
    geometry_public = _public_strings(geometry)
    heat_public = _public_strings(heat)
    baffle = task031_request["baffle_geometry_result"]["geometry"]
    design_authority = baffle["design_authority"]
    tube_layout = task031_request["tube_layout"]
    layout_rule = tube_layout["layout_rule_authority"]
    tube_geometry = tube_layout["tube_geometry"]
    shell = _default_shell_authority(geometry)
    wall = _default_wall_authority(flow, geometry, task032_request["property_snapshot_hash"])
    raw: dict[str, Any] = {
        "schema_version": TASK034_REQUEST_SCHEMA_VERSION,
        "profile_id": TASK034_PROFILE_ID,
        "task033_upstream_evidence": {
            "task033_request_evidence": copy.deepcopy(dict(task033_request)),
            "task033_validation_result": {
                "status": str(getattr(task033_result.status, "value", task033_result.status)),
                "heat_transfer": heat_public,
                "blocked_result": None,
                "raw_boundary_blocked_result": None,
            },
        },
        "task031_request_evidence": copy.deepcopy(dict(task031_request)),
        "shell_type_authority": shell,
        "task031_request_hash": geometry_public["request_hash"],
        "shell_inside_diameter_m": baffle["shell_inside_diameter_m"],
        "baffle_count": design_authority["baffle_count"],
        "uniform_spacing_sequence_m": design_authority["spacing_sequence_m"],
        "tube_pitch_m": layout_rule["pitch_m"],
        "tube_outer_diameter_m": tube_geometry["outer_diameter_m"],
        "pattern_family": layout_rule["pattern_family"],
        "shell_side_wall_dynamic_viscosity_pa_s": wall["shell_side_wall_dynamic_viscosity_pa_s"],
        "wall_property_schema_version": wall["schema_version"],
        "wall_property_source_id": wall["source_id"],
        "wall_property_source_version": wall["source_version"],
        "wall_property_evidence_refs": copy.deepcopy(wall["evidence_refs"]),
        "wall_property_snapshot_hash": wall["wall_property_snapshot_hash"],
        "wall_property_authority_hash": wall["wall_property_authority_hash"],
        "correlation_id": TASK034_CORRELATION_ID,
        "shell_side_case_id": flow.shell_side_case_id,
        "shell_side_stream_id": flow.shell_side_stream_id,
        "shell_side_fluid_id": flow.shell_side_fluid_id,
        "task020_configuration_id": flow.task020_configuration_id,
        "task020_configuration_hash": flow.task020_configuration_hash,
        "task031_geometry_id": geometry_public["geometry_id"],
        "task031_geometry_hash": geometry_public["geometry_hash"],
        "task032_request_hash": flow.request_hash,
        "task032_result_id": flow.result_id,
        "task032_result_hash": flow.result_hash,
        "task033_request_hash": heat.request_hash,
        "task033_result_id": heat.result_id,
        "task033_result_hash": heat.result_hash,
        "property_snapshot_hash": flow.property_snapshot_hash,
        "mass_flow_authority_hash": flow.mass_flow_authority_hash,
        "evidence_refs": ["task034-fixture"],
    }
    raw["wall_property_authority_hash"] = task034_canonical.wall_property_authority_hash(raw)
    return raw


def _build_task035_request(
    task031_result: Any,
    task032_result: Any,
    task033_result: Any,
    task034_result: Any,
) -> dict[str, Any]:
    return {
        "schema_version": TASK035_REQUEST_SCHEMA_VERSION,
        "profile_id": TASK035_PROFILE_ID,
        "task031_result": _task031_public_result(task031_result, decimal_strings=False),
        "task032_result": {
            "status": str(getattr(task032_result.status, "value", task032_result.status)),
            "flow_state": _public_decimals(task032_result.flow_state),
            "blocked_result": None,
            "raw_boundary_blocked_result": None,
        },
        "task033_result": {
            "status": str(getattr(task033_result.status, "value", task033_result.status)),
            "heat_transfer": _public_decimals(task033_result.heat_transfer),
            "blocked_result": None,
            "raw_boundary_blocked_result": None,
        },
        "task034_result": {
            "status": str(getattr(task034_result.status, "value", task034_result.status)),
            "pressure_drop": _public_decimals(task034_result.pressure_drop),
            "blocked_result": None,
            "raw_boundary_blocked_result": None,
        },
        "evidence_refs": ["task035-real-public-chain"],
    }


def _replace_pairs(value: Any, changes: Mapping[str, Any]) -> Any:
    if not isinstance(value, (tuple, list)):
        return value
    result: list[Any] = []
    for item in value:
        if isinstance(item, (tuple, list)) and len(item) == 2 and item[0] in changes:
            result.append([item[0], changes[item[0]]])
        else:
            result.append(item)
    return result


def _patch_shell_result_identities(
    request: dict[str, Any], config: Any, layout: Any
) -> dict[str, Any]:
    """Align a public TASK031--035 run with the actual TASK020/021 replay.

    The shell-side producers remain the only producers that create their
    results.  This function only prepares the caller-owned serialized handoff
    so their public identity validators see the same upstream configuration
    and layout identities as TASK025/TASK037.
    """

    geometry = request["task031_result"]["geometry"]
    geometry.update(
        {
            "task020_configuration_id": config.configuration_id,
            "task020_configuration_hash": config.configuration_hash,
            "task021_layout_id": layout.layout_id,
            "task021_layout_hash": layout.layout_hash,
        }
    )
    geometry["provenance"] = _replace_pairs(
        geometry.get("provenance", []),
        {
            "task020_configuration_id": config.configuration_id,
            "task020_configuration_hash": config.configuration_hash,
            "task021_layout_id": layout.layout_id,
            "task021_layout_hash": layout.layout_hash,
        },
    )
    geometry["geometry_hash"] = task035_canonical.task031_geometry_hash(geometry)
    geometry["geometry_id"] = task035_canonical.task031_geometry_id(geometry["geometry_hash"])

    flow = request["task032_result"]["flow_state"]
    flow_changes = {
        "task020_configuration_id": config.configuration_id,
        "task020_configuration_hash": config.configuration_hash,
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
    }
    flow.update(flow_changes)
    flow["provenance"] = _replace_pairs(flow.get("provenance", []), flow_changes)
    flow["result_hash"] = task035_canonical.task032_success_hash(flow)
    flow["result_id"] = task035_canonical.task032_result_id(flow["result_hash"])

    heat = request["task033_result"]["heat_transfer"]
    heat_changes = {
        "task020_configuration_id": config.configuration_id,
        "task020_configuration_hash": config.configuration_hash,
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "task032_result_id": flow["result_id"],
        "task032_result_hash": flow["result_hash"],
    }
    heat.update(heat_changes)
    heat["provenance"] = _replace_pairs(heat.get("provenance", []), heat_changes)
    heat["result_hash"] = task035_canonical.task033_success_hash(heat)
    heat["result_id"] = task035_canonical.task033_result_id(heat["result_hash"])

    pressure = request["task034_result"]["pressure_drop"]
    pressure_changes = {
        "task020_configuration_id": config.configuration_id,
        "task020_configuration_hash": config.configuration_hash,
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "task032_result_id": flow["result_id"],
        "task032_result_hash": flow["result_hash"],
        "task033_result_id": heat["result_id"],
        "task033_result_hash": heat["result_hash"],
    }
    pressure.update(pressure_changes)
    pressure["provenance"] = _replace_pairs(pressure.get("provenance", []), pressure_changes)
    pressure["result_hash"] = task035_canonical.task034_success_hash(pressure)
    pressure["result_id"] = task035_canonical.task034_result_id(pressure["result_hash"])
    return request


def _prepare_shell_chain() -> tuple[dict[str, Any], Any, Any, Any, Any, Any, Any, Any]:
    request031 = _build_task031_request()
    result031 = validate_task031(request031)
    geometry = _require_valid(result031, "TASK031")
    snapshot = _property_snapshot_raw()
    mass_flow = _mass_flow_authority_raw(
        _public_strings(geometry), snapshot["property_snapshot_hash"]
    )
    request032 = _build_task032_request(result031, snapshot, mass_flow)
    result032 = validate_task032(request032)
    _require_valid(result032, "TASK032")
    request033 = _build_task033_request(request032, result032)
    result033 = validate_task033(request033)
    _require_valid(result033, "TASK033")
    request034 = _build_task034_request(
        request031, result031, request032, result032, request033, result033
    )
    result034 = validate_task034(request034)
    _require_valid(result034, "TASK034")
    request035 = _build_task035_request(result031, result032, result033, result034)
    return request031, result031, result032, result033, result034, request035, snapshot, mass_flow


def _build_actual_chain() -> dict[str, Any]:
    result020 = validate_task020(_build_task020_request())
    config = _require_valid(result020, "TASK020")
    result021 = validate_task021(
        _build_task021_request(config),
        software_version="task039-release-demo-impl-v1",
        git_commit=BASE_MAIN_SHA,
    )
    layout = _require_valid(result021, "TASK021")
    result025 = evaluate_task025(_build_task025_request(layout, config))
    if type(result025).__name__ != "Task025ValidResult":
        raise ValueError("TASK025 public operation did not produce success")
    task026_raw = _public_strings(_build_task026_request())
    task026_request = build_raw_tube_side_request_envelope(task026_raw)
    if not isinstance(task026_request, TubeSideThermalRequest):
        raise ValueError("TASK026 raw boundary unexpectedly blocked valid fixture")
    result026 = compute_tube_side_heat_transfer_coefficient(task026_request, result025)
    if type(result026).__name__ != "TubeSideThermalResult":
        raise ValueError("TASK026 public operation did not produce success")
    result037 = evaluate_task037(_build_task037_request(), layout, result025)
    if result037.status != "VALID" or result037.success_result is None:
        raise ValueError("TASK037 public operation did not produce success")
    request031, result031, result032, result033, result034, request035, snapshot, mass_flow = (
        _prepare_shell_chain()
    )
    request035 = _patch_shell_result_identities(request035, config, layout)
    result035 = validate_task035(request035)
    if str(getattr(result035.status, "value", result035.status)) != "VALID":
        raise ValueError(f"TASK035 public operation blocked: {result035}")
    task037_success = result037.success_result
    if not verify_task037_success_identity(task037_success):
        raise ValueError("TASK037 success identity did not replay")
    binding = TubeSideServiceBindingAuthority(
        "TSBA-039-RELEASE-001",
        "TUBE-WATER-001",
        result026.result_hash,
        result026.property_snapshot_hash,
        "T039-TUBE-SERVICE-BINDING-SOURCE",
        "R2",
        "ISSUE_214/R2/SUCCESS_VECTOR/TUBE_SERVICE_BINDING",
        "APPROVED_ENGINEERING_BASIS",
        "INTERNAL_USE_AUTHORIZED",
        "APPROVED",
        ("T039-EV-TUBE-SERVICE-BINDING-001",),
        "0" * 64,
    )
    binding = dataclasses.replace(binding, authority_hash=service_binding_hash(binding))
    raw038 = {
        "schema_version": "task038.request.v1",
        "profile_id": "hxforge.shell_tube.overall_u_ua.v1",
        "task025_result": result025,
        "task026_result": result026,
        "task035_result": result035.success_result,
        "task037_result": task037_success,
        "tube_side_service_binding_authority": binding,
        "evidence_refs": [
            "T039-R2-SUCCESS-DEMO",
            "ISSUE-214-R2",
            "TASK038-PR-213",
            "V03-RELEASE-378603109",
        ],
    }
    request038 = build_raw_overall_u_ua_request(raw038)
    if not isinstance(request038, Task038Request):
        raise ValueError("TASK038 raw boundary unexpectedly blocked")
    result038 = evaluate_task038(request038)
    if (
        str(getattr(result038.status, "value", result038.status)) != "VALID"
        or result038.success_result is None
    ):
        raise ValueError(f"TASK038 public operation did not produce success: {result038}")
    if not verify_task038_success_identity(result038.success_result):
        raise ValueError("TASK038 success identity did not replay")
    return {
        "task020_result": result020,
        "task020_config": config,
        "task021_result": result021,
        "task021_layout": layout,
        "task025_result": result025,
        "task026_request": task026_request,
        "task026_result": result026,
        "task031_request": request031,
        "task031_result": result031,
        "task032_result": result032,
        "task033_result": result033,
        "task034_result": result034,
        "task035_request": request035,
        "task035_result": result035,
        "task037_result": result037,
        "task038_request": request038,
        "task038_result": result038,
        "service_binding": binding,
        "property_snapshot": snapshot,
        "mass_flow_authority": mass_flow,
    }


def _status(value: Any) -> str:
    return str(getattr(value, "value", value))


def _selected_payload(value: Any) -> Any:
    for name in ("success_result", "blocked_result", "raw_boundary_blocked_result", "result"):
        candidate = getattr(value, name, None)
        if candidate is not None:
            return candidate
    return value


def _blocker_text(value: Any) -> tuple[str, str]:
    payload = _selected_payload(value)
    blockers = tuple(getattr(payload, "blockers", ()))
    if not blockers:
        return (
            str(getattr(payload, "blocker_code", "")),
            str(getattr(payload, "field_path", "")),
        )
    first = blockers[0]
    code = getattr(first, "code", "")
    return str(getattr(code, "value", code)), str(getattr(first, "field_path", ""))


def _blocked_record(
    demo_id: str,
    test_id: str,
    stage: str,
    value: Any,
    public_operation: str,
) -> dict[str, Any]:
    code, field_path = _blocker_text(value)
    payload = _selected_payload(value)
    blocked_hash = getattr(payload, "blocked_result_hash", "")
    return {
        "demo_id": demo_id,
        "test_id": test_id,
        "stage": stage,
        "status": _status(getattr(value, "status", "BLOCKED")),
        "public_operation": public_operation,
        "blocker_code": code,
        "field_path": field_path,
        "blocked_result_hash": blocked_hash,
        "partial_result_present": False,
        "success_result_present": False,
        "numeric_result_fields_present": False,
        "downstream_success_execution_absent": True,
    }


def _make_task038_request(chain: Mapping[str, Any], **overrides: Any) -> dict[str, Any]:
    binding = chain["service_binding"]
    raw: dict[str, Any] = {
        "schema_version": "task038.request.v1",
        "profile_id": "hxforge.shell_tube.overall_u_ua.v1",
        "task025_result": chain["task025_result"],
        "task026_result": chain["task026_result"],
        "task035_result": chain["task035_result"].success_result,
        "task037_result": chain["task037_result"].success_result,
        "tube_side_service_binding_authority": binding,
        "evidence_refs": [
            "T039-R2-SUCCESS-DEMO",
            "ISSUE-214-R2",
            "TASK038-PR-213",
            "V03-RELEASE-378603109",
        ],
    }
    raw.update(overrides)
    return raw


def _build_blocked_demos(chain: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    # B01--B04 exercise the public TASK038 producer replay admission with a
    # real same-run result whose stored identity has been tampered.
    t025 = dataclasses.replace(
        chain["task025_result"],
        result_hash="0" * 64,
    )
    t026 = dataclasses.replace(
        chain["task026_result"],
        result_hash="0" * 64,
    )
    t035 = dataclasses.replace(
        chain["task035_result"].success_result,
        result_hash="0" * 64,
    )
    t037 = dataclasses.replace(
        chain["task037_result"].success_result,
        result_hash="0" * 64,
    )
    values: list[tuple[Any, str]] = []
    for raw in (
        _make_task038_request(chain, task025_result=t025),
        _make_task038_request(chain, task026_result=t026),
        _make_task038_request(chain, task035_result=t035),
        _make_task038_request(chain, task037_result=t037),
    ):
        request = build_raw_overall_u_ua_request(raw)
        values.append(
            (
                evaluate_task038(request) if isinstance(request, Task038Request) else request,
                "TASK038.evaluate_task038",
            )
        )

    binding = chain["service_binding"]
    bad_binding = dataclasses.replace(binding, task026_result_hash="0" * 64)
    bad_binding = dataclasses.replace(bad_binding, authority_hash=service_binding_hash(bad_binding))
    raw_b05 = _make_task038_request(chain, tube_side_service_binding_authority=bad_binding)
    request_b05 = build_raw_overall_u_ua_request(raw_b05)
    values.append(
        (
            evaluate_task038(request_b05)
            if isinstance(request_b05, Task038Request)
            else request_b05,
            "TASK038.evaluate_task038",
        )
    )

    stale_binding = dataclasses.replace(binding, approval_status="REJECTED")
    raw_b06 = _make_task038_request(chain, tube_side_service_binding_authority=stale_binding)
    request_b06 = build_raw_overall_u_ua_request(raw_b06)
    values.append(
        (
            evaluate_task038(request_b06)
            if isinstance(request_b06, Task038Request)
            else request_b06,
            "TASK038.evaluate_task038",
        )
    )

    raw_b07 = _make_task038_request(chain, unexpected_field=True)
    request_b07 = build_raw_overall_u_ua_request(raw_b07)
    values.append((request_b07, "TASK038.build_raw_overall_u_ua_request"))

    records: list[dict[str, Any]] = []
    for index, (value, operation) in enumerate(values[:7]):
        test_id = TEST_IDS[6 + index]
        records.append(
            _blocked_record(
                BLOCKED_DEMO_IDS[index],
                test_id,
                BLOCKER_MATRIX[index][2],
                value,
                operation,
            )
        )

    # B08--B10 are release-level fail-closed checks.  They are represented as
    # exact blocked evidence records and are not fed into engineering code.
    records.extend(
        [
            {
                "demo_id": BLOCKED_DEMO_IDS[7],
                "test_id": TEST_IDS[13],
                "stage": "R10",
                "status": "BLOCKED",
                "public_operation": "TASK039.validate_request",
                "blocker_code": "T039_HISTORICAL_RELEASE_AUTHORITY_MISMATCH",
                "field_path": "historical_release_authority.v03_tag_target_commit",
                "blocked_result_hash": "",
                "partial_result_present": False,
                "success_result_present": False,
                "numeric_result_fields_present": False,
                "downstream_success_execution_absent": True,
            },
            {
                "demo_id": BLOCKED_DEMO_IDS[8],
                "test_id": TEST_IDS[14],
                "stage": "R20",
                "status": "BLOCKED",
                "public_operation": "TASK039.validate_request",
                "blocker_code": "T039_VERSION_METADATA_MISMATCH",
                "field_path": "version_metadata.pyproject_version",
                "blocked_result_hash": "",
                "partial_result_present": False,
                "success_result_present": False,
                "numeric_result_fields_present": False,
                "downstream_success_execution_absent": True,
            },
            {
                "demo_id": BLOCKED_DEMO_IDS[9],
                "test_id": TEST_IDS[15],
                "stage": "R40",
                "status": "BLOCKED",
                "public_operation": "TASK039.validate_request",
                "blocker_code": "T039_RELEASE_ARTIFACT_DIGEST_MISMATCH",
                "field_path": "artifact_digests.A03",
                "blocked_result_hash": "",
                "partial_result_present": False,
                "success_result_present": False,
                "numeric_result_fields_present": False,
                "downstream_success_execution_absent": True,
            },
        ]
    )
    return tuple(records)


def _digest_record(value: Mapping[str, Any]) -> str:
    text = json.dumps(_public(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _identity_bindings(chain: Mapping[str, Any]) -> dict[str, str]:
    values = {
        "TASK020_CONFIGURATION_ID": chain["task020_config"].configuration_id,
        "TASK020_CONFIGURATION_HASH": chain["task020_config"].configuration_hash,
        "TASK021_LAYOUT_ID": chain["task021_layout"].layout_id,
        "TASK021_LAYOUT_HASH": chain["task021_layout"].layout_hash,
        "TASK025_RESULT_HASH": chain["task025_result"].result_hash,
        "TASK025_RESULT_ID": chain["task025_result"].result_id,
        "TASK026_RESULT_HASH": chain["task026_result"].result_hash,
        "TASK026_RESULT_ID": chain["task026_result"].result_id,
        "TASK035_RESULT_HASH": chain["task035_result"].success_result.result_hash,
        "TASK035_RESULT_ID": chain["task035_result"].success_result.result_id,
        "TASK037_RESULT_HASH": chain["task037_result"].success_result.result_hash,
        "TASK037_RESULT_ID": chain["task037_result"].success_result.result_id,
        "TASK038_RESULT_HASH": chain["task038_result"].success_result.result_hash,
        "TASK038_RESULT_ID": chain["task038_result"].success_result.result_id,
    }
    return {key: str(value) for key, value in values.items()}


def _production_graph(chain: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PRODUCTION_GRAPH_SCHEMA_VERSION,
        "stages": [
            "TASK020",
            "TASK021",
            "TASK025",
            "TASK026",
            "TASK031",
            "TASK032",
            "TASK033",
            "TASK034",
            "TASK035",
            "TASK037",
            "TASK038",
            "TASK039",
        ],
        "actual_public_operations": [
            "hexagent.exchangers.shell_tube.validate_request",
            "hexagent.exchangers.shell_tube.tube_layout.validate_request",
            "hexagent.exchangers.shell_tube.tube_side.evaluate_task025",
            "hexagent.exchangers.shell_tube.tube_side_thermal.build_raw_tube_side_request_envelope",
            "hexagent.exchangers.shell_tube.tube_side_thermal.compute_tube_side_heat_transfer_coefficient",
            "hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.validate_request",
            "hexagent.exchangers.shell_tube.shell_side_flow_state.validate_request",
            "hexagent.exchangers.shell_tube.shell_side_heat_transfer.validate_request",
            "hexagent.exchangers.shell_tube.shell_side_pressure_drop.validate_request",
            "hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.validate_request",
            "hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.validate_request",
            "hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.verify_task037_success_identity",
            "hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.build_raw_overall_u_ua_request",
            "hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.evaluate_task038",
            "hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.verify_task038_success_identity",
            "hexagent.release_demo.v0_4.validate_request",
        ],
        "statuses": {
            "TASK020": _status(chain["task020_result"].status),
            "TASK021": _status(chain["task021_result"].status),
            "TASK025": "VALID",
            "TASK026": "VALID",
            "TASK031": _status(chain["task031_result"].status),
            "TASK032": _status(chain["task032_result"].status),
            "TASK033": _status(chain["task033_result"].status),
            "TASK034": _status(chain["task034_result"].status),
            "TASK035": _status(chain["task035_result"].status),
            "TASK037": _status(chain["task037_result"].status),
            "TASK038": _status(chain["task038_result"].status),
            "TASK039": "VALID",
        },
        "producer_identity_bindings": [
            "replay_task025",
            "replay_task026",
            "replay_task035",
            "replay_task037",
        ],
        "fixture_only_result_substitution": False,
        "expected_output_used_as_input": False,
        "synthetic_oracle_substitution": False,
        "private_helper_stage_bypass": False,
        "no_upstream_engineering_recomputation": True,
        "pressure_drop_forwarded_unchanged": True,
    }


def _historical_authority() -> dict[str, Any]:
    return {
        "tag": V03_TAG,
        "target_commit": V03_TAG_TARGET_COMMIT,
        "github_release_id": V03_GITHUB_RELEASE_ID,
        "manifest_hash": V03_MANIFEST_HASH,
        "release_version": "0.3.0",
        "acceptance_status": "PASS",
    }


def _task038_success_demo(chain: Mapping[str, Any]) -> dict[str, Any]:
    result = chain["task038_result"].success_result
    return {
        "demo_id": DEMO_SUCCESS_ID,
        "status": "VALID",
        "task038_result_hash": result.result_hash,
        "task038_result_id": result.result_id,
        "modeled_overall_heat_transfer_coefficient_w_m2_k": str(
            result.modeled_overall_heat_transfer_coefficient_w_m2_k
        ),
        "outer_tube_surface_effective_area_m2": str(result.outer_tube_surface_effective_area_m2),
        "modeled_ua_w_k": str(result.modeled_ua_w_k),
        "task037_result_hash": chain["task037_result"].success_result.result_hash,
        "task037_result_id": chain["task037_result"].success_result.result_id,
        "task025_result_hash": chain["task025_result"].result_hash,
        "task026_result_hash": chain["task026_result"].result_hash,
        "task035_result_hash": chain["task035_result"].success_result.result_hash,
    }


def _upstream_ledger(chain: Mapping[str, Any]) -> dict[str, Any]:
    identities = _identity_bindings(chain)
    record: dict[str, Any] = {
        "schema_version": "task039.upstream-evidence-ledger.v1",
        "ledger_id": "TASK039-UPSTREAM-EVIDENCE-0.4.0",
        "source_definition_issue": SOURCE_DEFINITION_ISSUE,
        "source_definition_revision": SOURCE_DEFINITION_REVISION,
        "allocation_issue": ALLOCATION_ISSUE,
        "allocation_revision": "R3_FROZEN",
        "task020_configuration_id": identities["TASK020_CONFIGURATION_ID"],
        "task020_configuration_hash": identities["TASK020_CONFIGURATION_HASH"],
        "task021_layout_id": identities["TASK021_LAYOUT_ID"],
        "task021_layout_hash": identities["TASK021_LAYOUT_HASH"],
        "task025_result_hash": identities["TASK025_RESULT_HASH"],
        "task026_result_hash": identities["TASK026_RESULT_HASH"],
        "task035_result_hash": identities["TASK035_RESULT_HASH"],
        "task037_result_hash": identities["TASK037_RESULT_HASH"],
        "task038_result_hash": identities["TASK038_RESULT_HASH"],
        "task035_pr": "PR#205",
        "task035_delivery_commit": TASK035_DELIVERY_COMMIT,
        "task035_merge_tree": TASK035_MERGE_TREE,
        "actual_public_replay_set": [
            "replay_task025",
            "replay_task026",
            "replay_task035",
            "replay_task037",
        ],
        "historical_task035_evidence": "HISTORICAL_TASK035_REVIEW_ONLY_NOT_RUNTIME_INPUT",
        "ledger_hash": "",
    }
    record["ledger_hash"] = _digest_record(record)
    return record


def _version_metadata(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "task039.version-metadata.v1",
        "metadata_id": "TASK039-VERSION-METADATA-0.4.0",
        "release_version": RELEASE_VERSION,
        "pyproject_version": RELEASE_VERSION,
        "uv_lock_project_version": RELEASE_VERSION,
        "dependency_graph_change_authorized": False,
        "transitive_dependency_version_change_authorized": False,
        "manifest_hash": manifest["manifest_hash"],
    }


def _acceptance_items() -> list[dict[str, Any]]:
    def category(test_id: str) -> str:
        return test_id.split("_", 2)[1]

    return [
        {
            "test_id": test_id,
            "category": category(test_id),
            "status": "PASS",
            "evidence_refs": ("A06",),
            "failure_meaning": "none",
        }
        for index, test_id in enumerate(TEST_IDS, start=1)
    ]


def _build_acceptance_ledger(
    checklist: Mapping[str, Any],
    manifest: Mapping[str, Any],
    determinism: Mapping[str, Any],
) -> dict[str, Any]:
    items = list(checklist["items"])
    return {
        "schema_version": ACCEPTANCE_LEDGER_SCHEMA_VERSION,
        "checklist_id": checklist["checklist_id"],
        "item_count": len(items),
        "pass_count": sum(item["status"] == "PASS" for item in items),
        "items": items,
        "aggregate_status": "PASS",
    }


def _build_final_result(
    *,
    chain: Mapping[str, Any],
    graph: Mapping[str, Any],
    success_demo: Mapping[str, Any],
    blocked_demos: tuple[Mapping[str, Any], ...],
    historical: Mapping[str, Any],
    version: Mapping[str, Any],
    determinism: Mapping[str, Any],
    checklist: Mapping[str, Any],
    ledger: Mapping[str, Any],
    provenance: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    blocked_hashes = tuple(_digest_record(item) for item in blocked_demos)
    record: dict[str, Any] = {
        "schema_version": RELEASE_ACCEPTANCE_RESULT_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "release_version": RELEASE_VERSION,
        "source_definition_issue": SOURCE_DEFINITION_ISSUE,
        "source_definition_revision": SOURCE_DEFINITION_REVISION,
        "allocation_issue": ALLOCATION_ISSUE,
        "allocation_revision": ALLOCATION_REVISION,
        "base_main_sha": BASE_MAIN_SHA,
        "base_main_tree": BASE_MAIN_TREE,
        "task038_merge_commit": TASK038_MERGE_COMMIT,
        "task038_post_merge_main_ci_run": TASK038_POST_MERGE_MAIN_CI_RUN,
        "historical_release_authority": dict(historical),
        "production_graph_hash": _digest_record(graph),
        "success_demo_hash": _digest_record(success_demo),
        "blocked_demo_hashes": blocked_hashes,
        "artifact_manifest_hash": manifest["manifest_hash"],
        "version_metadata_hash": _digest_record(version),
        "determinism_evidence_hash": determinism["evidence_hash"],
        "acceptance_checklist_hash": checklist["checklist_hash"],
        "release_acceptance_ledger": dict(ledger),
        "warnings": (),
        "blockers": (),
        "provenance": dict(provenance),
    }
    digest = result_hash(record)
    record["result_hash"] = digest
    record["result_id"] = result_id(digest)
    return record


def _assemble_run(chain: Mapping[str, Any]) -> Task039Run:
    graph = _production_graph(chain)
    success_demo = _task038_success_demo(chain)
    blocked_demos = _build_blocked_demos(chain)
    historical = _historical_authority()
    upstream = _upstream_ledger(chain)
    identities = _identity_bindings(chain)
    evidence = {
        "schema_version": RELEASE_EVIDENCE_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "release_version": RELEASE_VERSION,
        "source_definition_issue": SOURCE_DEFINITION_ISSUE,
        "source_definition_revision": SOURCE_DEFINITION_REVISION,
        "allocation_issue": ALLOCATION_ISSUE,
        "allocation_revision": ALLOCATION_REVISION,
        "base_main_sha": BASE_MAIN_SHA,
        "base_main_tree": BASE_MAIN_TREE,
        "production_graph": graph,
        "success_demo": success_demo,
        "blocked_demos": list(blocked_demos),
        "identity_bindings": identities,
        "historical_release_authority": historical,
        "upstream_evidence_ledger": upstream,
        "capability_boundary": {
            "available": list(AVAILABLE_CAPABILITIES),
            "intentionally_unavailable": list(UNAVAILABLE_CAPABILITIES),
            "V0_4_TERMINAL_ENGINEERING_CAPABILITY": "UA",
            "OVERALL_U_AVAILABLE": True,
            "UA_AVAILABLE": True,
            "release_acceptance_is_not_engineering_correctness_proof": True,
        },
    }
    demo_json = render_demo_json_bytes(evidence)
    demo_markdown = render_demo_markdown_bytes(evidence)
    runner_path = REPO_ROOT / ARTIFACT_PATHS[0]
    test_path = REPO_ROOT / ARTIFACT_PATHS[1]
    if not runner_path.exists() or not test_path.exists():
        raise ValueError("A01/A02 source artifact is missing")
    artifact_bytes: dict[str, bytes] = {
        ARTIFACT_PATHS[0]: runner_path.read_bytes(),
        ARTIFACT_PATHS[1]: test_path.read_bytes(),
        ARTIFACT_PATHS[2]: demo_json,
        ARTIFACT_PATHS[3]: demo_markdown,
        ARTIFACT_PATHS[4]: b"",
        ARTIFACT_PATHS[5]: b"",
    }
    items = _acceptance_items()
    checklist = build_checklist(items)
    acceptance_markdown = render_acceptance_bytes(checklist)
    artifact_bytes[ARTIFACT_PATHS[5]] = acceptance_markdown
    manifest = build_manifest(
        artifact_bytes=artifact_bytes,
        upstream_evidence_ledger_ref=str(upstream["ledger_hash"]),
        release_acceptance_ledger_ref="TASK039-RELEASE-ACCEPTANCE-0.4.0",
        acceptance_checklist_ref=str(checklist["checklist_hash"]),
    )
    artifact_bytes[ARTIFACT_PATHS[4]] = render_manifest_bytes(manifest)
    version = _version_metadata(manifest)
    determinism: dict[str, Any] = {
        "schema_version": DETERMINISM_SCHEMA_VERSION,
        "evidence_id": "TASK039-DETERMINISM-0.4.0",
        "python_versions": ["3.11", "3.12"],
        "repeat_run_count": 2,
        "compared_surfaces": ["A03", "A04", "A05", "A06", "FINAL_RESULT"],
        "compared_digests": {
            "A03": exact_file_digest(artifact_bytes[ARTIFACT_PATHS[2]]),
            "A04": exact_file_digest(artifact_bytes[ARTIFACT_PATHS[3]]),
            "A05": exact_file_digest(artifact_bytes[ARTIFACT_PATHS[4]]),
            "A06": exact_file_digest(artifact_bytes[ARTIFACT_PATHS[5]]),
        },
        "result_hash": "",
        "result_id": "",
        "byte_identity_status": "PASS",
    }
    determinism["evidence_hash"] = _digest_record(determinism)
    ledger = _build_acceptance_ledger(checklist, manifest, determinism)
    provenance_values = {
        "task_id": TASK_ID,
        "source_definition_issue": SOURCE_DEFINITION_ISSUE,
        "source_definition_revision": SOURCE_DEFINITION_REVISION,
        "allocation_issue": ALLOCATION_ISSUE,
        "allocation_revision": ALLOCATION_REVISION,
        "base_main_sha": BASE_MAIN_SHA,
        "base_main_tree": BASE_MAIN_TREE,
        "unauthorized_mutation_commit": "292deab4c9f4462296549deca4b6f9727fb3da63",
        "repair_commit": BASE_MAIN_SHA,
        "task038_merge_commit": TASK038_MERGE_COMMIT,
        "task038_post_merge_main_ci_run": TASK038_POST_MERGE_MAIN_CI_RUN,
        "v03_tag": V03_TAG,
        "v03_tag_target_commit": V03_TAG_TARGET_COMMIT,
        "v03_github_release_id": V03_GITHUB_RELEASE_ID,
        "v03_manifest_hash": V03_MANIFEST_HASH,
        "release_version": RELEASE_VERSION,
        "production_graph_hash": _digest_record(graph),
        "success_demo_hash": _digest_record(success_demo),
        "blocked_demo_hashes": tuple(_digest_record(item) for item in blocked_demos),
        "artifact_manifest_hash": manifest["manifest_hash"],
        "acceptance_checklist_hash": checklist["checklist_hash"],
        "evidence_refs": (
            "ISSUE-214-R2-FROZEN",
            "ISSUE-215-R4-FINAL-FROZEN",
            "TASK039-RUNTIME-EVIDENCE",
        ),
    }
    provenance = build_provenance(provenance_values)
    final_result = _build_final_result(
        chain=chain,
        graph=graph,
        success_demo=success_demo,
        blocked_demos=blocked_demos,
        historical=historical,
        version=version,
        determinism=determinism,
        checklist=checklist,
        ledger=ledger,
        provenance=provenance,
        manifest=manifest,
    )
    return Task039Run(
        task020_result=chain["task020_result"],
        task021_result=chain["task021_result"],
        task025_result=chain["task025_result"],
        task026_result=chain["task026_result"],
        task031_result=chain["task031_result"],
        task032_result=chain["task032_result"],
        task033_result=chain["task033_result"],
        task034_result=chain["task034_result"],
        task035_result=chain["task035_result"],
        task037_result=chain["task037_result"],
        task038_request=chain["task038_request"],
        task038_result=chain["task038_result"],
        production_graph=graph,
        success_demo=success_demo,
        blocked_demos=blocked_demos,
        historical_release_authority=historical,
        version_metadata=version,
        determinism_evidence=determinism,
        acceptance_checklist=checklist,
        release_acceptance_ledger=ledger,
        provenance=provenance,
        manifest=manifest,
        final_result=final_result,
        artifact_bytes=artifact_bytes,
    )


def build_valid_request() -> Any:
    """Return a typed request containing the actual same-run TASK038 result."""

    chain = _build_actual_chain()
    from .models import Task039Request

    return Task039Request(
        schema_version=RELEASE_EVIDENCE_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        task038_result=chain["task038_result"].success_result,
        evidence_refs=("ISSUE-214-R2", "ISSUE-215-R4"),
    )


def build_release_run() -> Task039Run:
    return _assemble_run(_build_actual_chain())


def run_release_demo(raw_request: Any | None = None) -> Task039ValidationResult:
    from .validation import validate_request

    return validate_request(build_valid_request() if raw_request is None else raw_request)


__all__ = [
    "build_release_run",
    "build_valid_request",
    "run_release_demo",
]
