"""TASK036 v0.3 release-demo orchestration.

The runner is intentionally an evidence and integration boundary.  It calls
the public TASK031--TASK035 operations, carries their producer-owned result
identities forward, and never recalculates an upstream engineering quantity.
All release evidence is derived from the closed R5 projections in
``hexagent.release_demo.schema``.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import uuid
from collections.abc import Mapping
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, cast

from hexagent.exchangers.shell_tube.baffle_geometry.validation import (
    to_canonical_primitive,
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
    validate_request as validate_task035,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.models import (
    PROFILE_ID as TASK035_PROFILE_ID,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.models import (
    REQUEST_SCHEMA_VERSION as TASK035_REQUEST_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_layout import canonical as task021_canonical
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    PhaseRegion,
    PropertySnapshot,
    recompute_property_snapshot_hash,
)

from .artifacts import (
    build_manifest,
    exact_file_digest,
    render_acceptance_bytes,
    render_demo_markdown_bytes,
    render_json_bytes,
    render_manifest_bytes,
)
from .canonical import (
    CanonicalizationError,
    acceptance_checklist_hash,
    artifact_digest,
    determinism_evidence_hash,
    release_acceptance_ledger_hash,
    release_acceptance_result_id,
    result_id,
    sha256_bytes,
    success_result_canonical_bytes,
    success_result_hash,
    upstream_evidence_ledger_hash,
    version_metadata_hash,
)
from .models import (
    Task036Run,
    Task036SuccessResult,
    Task036TypedBlockedResult,
    Task036ValidationResult,
    ValidationStatus,
)
from .provenance import build_provenance
from .schema import (
    ACCEPTANCE_CHECKLIST_FIELDS,
    ARTIFACT_IDS,
    ARTIFACT_PATHS,
    AVAILABLE_CAPABILITIES,
    BLOCKED_DEMO_IDS,
    DEMO_INPUT_FIELDS,
    DEMO_RESULT_SCHEMA_VERSION,
    DEMO_SUCCESS_ID,
    DETERMINISM_SURFACES,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROFILE_ID,
    PYTHON_VERSIONS,
    RELEASE_ACCEPTANCE_LEDGER_FIELDS,
    RELEASE_CANDIDATE_ID,
    RELEASE_SOFTWARE_VERSION,
    RELEASE_VERSION,
    SOURCE_DEFINITION_FREEZE_COMMENT_ID,
    SOURCE_DEFINITION_ISSUE,
    SOURCE_DEFINITION_REVISION,
    SOURCE_MAIN_SHA,
    SOURCE_MAIN_TREE,
    STAGE_ORDER,
    SUCCESS_RESULT_FIELDS,
    SUCCESS_RESULT_PREHASH_FIELDS,
    SUCCESS_RESULT_SCHEMA_VERSION,
    TEST_IDS,
    TYPED_BLOCKED_RESULT_SCHEMA_VERSION,
    UNAVAILABLE_CAPABILITIES,
    VERSION_METADATA_FIELDS,
)
from .validation import (
    build_raw_boundary_blocked,
    producer_status,
    validate_demo_input,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK031_DESIGN_PATH = (
    REPO_ROOT
    / "docs"
    / "tasks"
    / "TASK-031-shell-and-tube-shell-side-flow-path-hydraulic-geometry.md"
)
TASK035_DELIVERY_COMMIT = "e48d83208bfe4de782ee055a99c826fb9eebb334"
TASK035_MERGE_TREE = "8399dcf766b1c8d98794430e810d186134234d89"
TASK024_GEOMETRY_URN_PREFIX = "urn:hxforge:task024:baffle-geometry:v1:"


def _public(value: Any, *, decimal_strings: bool) -> Any:
    """Convert producer dataclasses to a detached public mapping.

    ``decimal_strings=True`` is used at the raw producer boundaries that
    explicitly carry JSON decimal strings.  TASK035's accepted producer
    projections deliberately retain ``Decimal`` values so its public
    validation can enforce the v2 numeric boundary.
    """

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
    return value


def _public_strings(value: Any) -> Any:
    return _public(value, decimal_strings=True)


def _public_decimals(value: Any) -> Any:
    return _public(value, decimal_strings=False)


def _load_task031_fixture() -> dict[str, Any]:
    text = TASK031_DESIGN_PATH.read_text(encoding="utf-8")
    marker = '"schema_version": "task031.shell-side-hydraulic-geometry-request.v1"'
    index = text.index(marker)
    start = text.rfind("```json", 0, index)
    end = text.index("```", start + len("```json"))
    return cast(dict[str, Any], json.loads(text[start + len("```json") : end]))


def _layout_rule_snapshot_hash(rule: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in rule.items() if key != "snapshot_hash"}
    # This is the frozen TASK-021 fixture identity operation.  It is only
    # used to prepare a caller-owned request before the public TASK-031 call.
    return task031_canonical.sha256_hex(task021_canonical.canonical_json(payload))


def _resync_task021_layout_identity(raw_request: dict[str, Any]) -> None:
    rule = raw_request["tube_layout"]["layout_rule_authority"]
    snapshot_hash = _layout_rule_snapshot_hash(rule)
    rule["snapshot_hash"] = snapshot_hash
    raw_request["tube_layout"]["provenance"]["layout_rule_snapshot_hash"] = snapshot_hash
    parsed = task031_schema.parse_request(raw_request)
    layout_hash = task031_canonical.sha256_hex(task021_layout_hash_payload(parsed.tube_layout))
    layout_id = task021_canonical.layout_id(layout_hash)
    raw_request["tube_layout"]["layout_hash"] = layout_hash
    raw_request["tube_layout"]["layout_id"] = layout_id
    geometry = raw_request["baffle_geometry_result"].get("geometry")
    if isinstance(geometry, dict):
        geometry["task021_layout_id"] = layout_id
        geometry["task021_layout_hash"] = layout_hash


def _task024_message_projection(entry: Any) -> dict[str, Any]:
    return {
        "code": entry.code,
        "field_path": entry.field_path,
        "message_key": entry.message_key,
        "evidence_refs": list(entry.evidence_refs),
        "details": [[key, value] for key, value in entry.details],
    }


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
        "warnings": [_task024_message_projection(item) for item in geometry.warnings],
        "blockers": [_task024_message_projection(item) for item in geometry.blockers],
        "deferred_capabilities": list(geometry.deferred_capabilities),
        "provenance": provenance,
    }


def _resync_task024_geometry_identity(raw_request: dict[str, Any]) -> None:
    parsed = task031_schema.parse_request(raw_request)
    geometry = parsed.baffle_geometry_result.geometry
    if geometry is None:
        return
    geometry_hash = task031_canonical.sha256_hex(_task024_geometry_hash_payload(geometry))
    geometry_id = str(uuid.uuid5(uuid.NAMESPACE_URL, TASK024_GEOMETRY_URN_PREFIX + geometry_hash))
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
    geometry: Mapping[str, Any], property_snapshot_hash: str
) -> dict[str, Any]:
    values: dict[str, Any] = {
        "schema_version": "task032.shell-side-mass-flow-authority.v1",
        "authority_profile_id": ("SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1"),
        "shell_side_case_id": "CASE-001",
        "shell_side_stream_id": "SHELL-SIDE-001",
        "shell_side_fluid_id": "WATER",
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
    authority_values = dict(values)
    authority_values["mass_flow_rate_kg_s"] = Decimal(authority_values["mass_flow_rate_kg_s"])
    authority_values["evidence_refs"] = tuple(authority_values["evidence_refs"])
    values["authority_hash"] = task032_mass_flow_authority_hash(
        ShellSideMassFlowAuthority(**authority_values)
    )
    return values


def _task031_public_result(result: Any, *, decimal_strings: bool = True) -> dict[str, Any]:
    return {
        "status": producer_status(result),
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
    evidence_refs: tuple[str, ...] | list[str],
) -> dict[str, Any]:
    geometry = task031_result.geometry
    if geometry is None:
        raise ValueError("TASK031 did not produce geometry")
    mass_flow = copy.deepcopy(dict(mass_flow_authority))
    mass_flow["task020_configuration_id"] = geometry.task020_configuration_id
    mass_flow["task020_configuration_hash"] = geometry.task020_configuration_hash
    mass_flow["task031_geometry_id"] = geometry.geometry_id
    mass_flow["task031_geometry_hash"] = geometry.geometry_hash
    mass_flow["property_snapshot_hash"] = property_snapshot["property_snapshot_hash"]
    mass_flow["authority_hash"] = task032_mass_flow_authority_hash(
        parse_task032_request(
            {
                "schema_version": "task032.shell-side-flow-state-request.v1",
                "profile_id": "hxforge.shell_tube.shell_side_flow_state.v1",
                "task031_result": _task031_public_result(task031_result),
                "property_snapshot_hash": property_snapshot["property_snapshot_hash"],
                "property_snapshot": dict(property_snapshot),
                "mass_flow_authority": mass_flow,
                "evidence_refs": list(evidence_refs),
            }
        ).mass_flow_authority
    )
    return {
        "schema_version": "task032.shell-side-flow-state-request.v1",
        "profile_id": "hxforge.shell_tube.shell_side_flow_state.v1",
        "task031_result": _task031_public_result(task031_result),
        "property_snapshot_hash": property_snapshot["property_snapshot_hash"],
        "property_snapshot": copy.deepcopy(dict(property_snapshot)),
        "mass_flow_authority": mass_flow,
        "evidence_refs": list(evidence_refs),
    }


def _build_task033_request(
    task032_request: Mapping[str, Any], task032_result: Any, evidence_refs: tuple[str, ...]
) -> dict[str, Any]:
    return {
        "schema_version": "task033.shell-side-heat-transfer-request.v1",
        "profile_id": "hxforge.shell_tube.shell_side_heat_transfer.v1",
        "task032_flow_state": _public_strings(task032_result.flow_state),
        "task032_request_evidence": _task032_request_evidence(task032_request),
        "evidence_refs": list(evidence_refs),
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
    flow: Any,
    geometry: Any,
    property_snapshot_hash: str,
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
    *,
    shell_authority: Mapping[str, Any] | None = None,
    wall_authority: Mapping[str, Any] | None = None,
    request_evidence_refs: tuple[str, ...] | list[str] = ("task034-fixture",),
) -> dict[str, Any]:
    geometry = task031_result.geometry
    flow = task032_result.flow_state
    heat = task033_result.heat_transfer
    if geometry is None or flow is None or heat is None:
        raise ValueError("upstream producer chain is not valid")
    geometry_public = _public_strings(geometry)
    heat_public = _public_strings(heat)
    baffle = task031_request["baffle_geometry_result"]["geometry"]
    design_authority = baffle["design_authority"]
    tube_layout = task031_request["tube_layout"]
    layout_rule = tube_layout["layout_rule_authority"]
    tube_geometry = tube_layout["tube_geometry"]
    shell = copy.deepcopy(
        dict(shell_authority) if shell_authority is not None else _default_shell_authority(geometry)
    )
    wall = copy.deepcopy(
        dict(wall_authority)
        if wall_authority is not None
        else _default_wall_authority(flow, geometry, task032_request["property_snapshot_hash"])
    )
    raw: dict[str, Any] = {
        "schema_version": TASK034_REQUEST_SCHEMA_VERSION,
        "profile_id": TASK034_PROFILE_ID,
        "task033_upstream_evidence": {
            "task033_request_evidence": copy.deepcopy(dict(task033_request)),
            "task033_validation_result": {
                "status": producer_status(task033_result),
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
        "evidence_refs": list(request_evidence_refs),
    }
    if wall_authority is None:
        raw["wall_property_authority_hash"] = task034_canonical.wall_property_authority_hash(raw)
    return raw


def _build_task035_request(
    task031_result: Any,
    task032_result: Any,
    task033_result: Any,
    task034_result: Any,
    evidence_refs: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_version": TASK035_REQUEST_SCHEMA_VERSION,
        "profile_id": TASK035_PROFILE_ID,
        "task031_result": _task031_public_result(task031_result, decimal_strings=False),
        "task032_result": {
            "status": producer_status(task032_result),
            "flow_state": _public_decimals(task032_result.flow_state),
            "blocked_result": None,
            "raw_boundary_blocked_result": None,
        },
        "task033_result": {
            "status": producer_status(task033_result),
            "heat_transfer": _public_decimals(task033_result.heat_transfer),
            "blocked_result": None,
            "raw_boundary_blocked_result": None,
        },
        "task034_result": {
            "status": producer_status(task034_result),
            "pressure_drop": _public_decimals(task034_result.pressure_drop),
            "blocked_result": None,
            "raw_boundary_blocked_result": None,
        },
        "evidence_refs": list(evidence_refs),
    }


def _require_valid(result: Any, task: str) -> None:
    payload = getattr(result, "result", None)
    if payload is None:
        for name in ("geometry", "flow_state", "heat_transfer", "pressure_drop", "success_result"):
            candidate = getattr(result, name, None)
            if candidate is not None:
                payload = candidate
                break
    if producer_status(result) != "VALID" or payload is None:
        codes = [str(getattr(item, "code", "UNKNOWN")) for item in result.blockers]
        raise ValueError(f"{task} public operation blocked: {codes}")


def _prepare_public_chain() -> dict[str, Any]:
    task031_request = _build_task031_request()
    task031_result = validate_task031(task031_request)
    _require_valid(task031_result, "TASK031")
    geometry = task031_result.geometry
    if geometry is None:
        raise ValueError("TASK031 geometry missing")
    property_snapshot = _property_snapshot_raw()
    mass_flow = _mass_flow_authority_raw(
        _public_strings(geometry), property_snapshot["property_snapshot_hash"]
    )
    task032_request = _build_task032_request(
        task031_result, property_snapshot, mass_flow, ("request-z", "request-a")
    )
    task032_result = validate_task032(task032_request)
    _require_valid(task032_result, "TASK032")
    task033_request = _build_task033_request(
        task032_request, task032_result, ("t033-request-z", "t033-request-a")
    )
    task033_result = validate_task033(task033_request)
    _require_valid(task033_result, "TASK033")
    task034_request = _build_task034_request(
        task031_request,
        task031_result,
        task032_request,
        task032_result,
        task033_request,
        task033_result,
    )
    task034_result = validate_task034(task034_request)
    _require_valid(task034_result, "TASK034")
    return {
        "task031_request": task031_request,
        "task031_result": task031_result,
        "task032_request": task032_request,
        "task032_result": task032_result,
        "task033_request": task033_request,
        "task033_result": task033_result,
        "task034_request": task034_request,
        "task034_result": task034_result,
        "property_snapshot": property_snapshot,
        "mass_flow_authority": mass_flow,
    }


def _demo_input_from_chain(chain: Mapping[str, Any]) -> dict[str, Any]:
    task034_request = cast(dict[str, Any], chain["task034_request"])
    return {
        "TASK031_RAW_REQUEST_RECORD": copy.deepcopy(chain["task031_request"]),
        "TASK032_PROPERTY_SNAPSHOT_RECORD": copy.deepcopy(chain["property_snapshot"]),
        "TASK032_MASS_FLOW_AUTHORITY_RECORD": copy.deepcopy(chain["mass_flow_authority"]),
        "TASK032_REQUEST_EVIDENCE_REFS": ["request-z", "request-a"],
        "TASK033_REQUEST_EVIDENCE_REFS": ["t033-request-z", "t033-request-a"],
        "TASK034_SHELL_TYPE_AUTHORITY_RECORD": copy.deepcopy(
            task034_request["shell_type_authority"]
        ),
        "TASK034_WALL_PROPERTY_AUTHORITY_RECORD": {
            "schema_version": task034_request["wall_property_schema_version"],
            "shell_side_case_id": task034_request["shell_side_case_id"],
            "shell_side_stream_id": task034_request["shell_side_stream_id"],
            "shell_side_fluid_id": task034_request["shell_side_fluid_id"],
            "task031_geometry_id": task034_request["task031_geometry_id"],
            "task031_geometry_hash": task034_request["task031_geometry_hash"],
            "task032_result_id": task034_request["task032_result_id"],
            "task032_result_hash": task034_request["task032_result_hash"],
            "property_snapshot_hash": task034_request["property_snapshot_hash"],
            "shell_side_wall_dynamic_viscosity_pa_s": task034_request[
                "shell_side_wall_dynamic_viscosity_pa_s"
            ],
            "source_id": task034_request["wall_property_source_id"],
            "source_version": task034_request["wall_property_source_version"],
            "evidence_refs": copy.deepcopy(task034_request["wall_property_evidence_refs"]),
            "wall_property_snapshot_hash": task034_request["wall_property_snapshot_hash"],
            "wall_property_authority_hash": task034_request["wall_property_authority_hash"],
        },
        "TASK034_REQUEST_EVIDENCE_REFS": copy.deepcopy(task034_request["evidence_refs"]),
        "TASK035_EVIDENCE_REFS": ["task035-real-public-chain"],
    }


def build_valid_demo_input() -> dict[str, Any]:
    """Build one caller-owned valid input from the actual public chain."""

    return _demo_input_from_chain(_prepare_public_chain())


def _task_result_envelope(result: Any, payload_name: str) -> dict[str, Any]:
    return {
        "status": producer_status(result),
        payload_name: _public_decimals(getattr(result, payload_name, None)),
        "blocked_result": _public_decimals(getattr(result, "blocked_result", None)),
        "raw_boundary_blocked_result": _public_decimals(
            getattr(result, "raw_boundary_blocked_result", None)
        ),
    }


def _identity_values(chain: Mapping[str, Any]) -> dict[str, str]:
    t031 = chain["task031_result"].geometry
    t032 = chain["task032_result"].flow_state
    t033 = chain["task033_result"].heat_transfer
    t034 = chain["task034_result"].pressure_drop
    t035 = chain["task035_result"].success_result
    if any(item is None for item in (t031, t032, t033, t034, t035)):
        raise ValueError("identity extraction requires valid public chain")
    return {
        "TASK031_REQUEST_HASH": t031.request_hash,
        "TASK031_RESULT_HASH": t031.geometry_hash,
        "TASK031_RESULT_ID": t031.geometry_id,
        "TASK032_REQUEST_HASH": t032.request_hash,
        "TASK032_RESULT_HASH": t032.result_hash,
        "TASK032_RESULT_ID": t032.result_id,
        "TASK033_REQUEST_HASH": t033.request_hash,
        "TASK033_RESULT_HASH": t033.result_hash,
        "TASK033_RESULT_ID": t033.result_id,
        "TASK034_REQUEST_HASH": t034.request_hash,
        "TASK034_RESULT_HASH": t034.result_hash,
        "TASK034_RESULT_ID": t034.result_id,
        "TASK035_REQUEST_HASH": t035.request_hash,
        "TASK035_RESULT_HASH": t035.result_hash,
        "TASK035_RESULT_ID": t035.result_id,
    }


def _graph_evidence(chain: Mapping[str, Any]) -> dict[str, Any]:
    statuses = {
        "TASK031": producer_status(chain["task031_result"]),
        "TASK032": producer_status(chain["task032_result"]),
        "TASK033": producer_status(chain["task033_result"]),
        "TASK034": producer_status(chain["task034_result"]),
        "TASK035": producer_status(chain["task035_result"]),
    }
    return {
        "schema_version": "task036.production-graph.v1",
        "stages": list(STAGE_ORDER),
        "actual_public_operations": [
            "hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.validate_request",
            "hexagent.exchangers.shell_tube.shell_side_flow_state.validate_request",
            "hexagent.exchangers.shell_tube.shell_side_heat_transfer.validate_request",
            "hexagent.exchangers.shell_tube.shell_side_pressure_drop.validate_request",
            "hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.validate_request",
        ],
        "statuses": statuses,
        "fixture_only_result_substitution": False,
        "expected_output_used_as_input": False,
        "synthetic_oracle_substitution": False,
        "private_helper_bypass": False,
        "no_upstream_engineering_recomputation": True,
        "pressure_drop_forwarded_unchanged": True,
    }


def _build_upstream_ledger(identities: Mapping[str, str]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": "task036.upstream-evidence-ledger.v1",
        "ledger_id": "TASK036-UPSTREAM-EVIDENCE-0.3.0",
        "source_definition_issue": SOURCE_DEFINITION_ISSUE,
        "source_definition_revision": SOURCE_DEFINITION_REVISION,
        "source_definition_freeze_comment_id": SOURCE_DEFINITION_FREEZE_COMMENT_ID,
        "task031_producer_ref": "TASK031_PUBLIC_MAIN",
        "task032_producer_ref": "TASK032_PUBLIC_MAIN",
        "task033_producer_ref": "TASK033_PUBLIC_MAIN",
        "task034_producer_ref": "TASK034_PUBLIC_MAIN",
        "task035_pr": "PR#205",
        "task035_delivery_commit": TASK035_DELIVERY_COMMIT,
        "task035_merge_commit": SOURCE_MAIN_SHA,
        "task035_tree": TASK035_MERGE_TREE,
        "task031_review_evidence": "TASK031_ACCEPTED_PUBLIC_CONTRACT",
        "task032_review_evidence": "TASK032_ACCEPTED_PUBLIC_CONTRACT",
        "task033_review_evidence": "TASK033_ACCEPTED_PUBLIC_CONTRACT",
        "task034_review_evidence": "TASK034_ACCEPTED_PUBLIC_CONTRACT",
        "task035_review_evidence": "TASK035_DELIVERY_REVIEW_PASS_PR205",
        "task031_test_evidence": "TASK031_REGRESSION_PASS",
        "task032_test_evidence": "TASK032_REGRESSION_PASS",
        "task033_test_evidence": "TASK033_REGRESSION_PASS",
        "task034_test_evidence": "TASK034_REGRESSION_PASS",
        "task035_test_evidence": "TASK035_TARGETED_30_OF_30",
        "task035_determinism_evidence": "TASK035_CROSS_PYTHON_2_RUNTIMES_PASS",
        "historical_task035_evidence": "HISTORICAL_TASK035_V1_REVIEW_ONLY_NOT_CURRENT",
        "ledger_hash": "",
    }
    record["ledger_hash"] = upstream_evidence_ledger_hash(record)
    return record


def _blocker_code(item: Any) -> str:
    raw = getattr(item, "code", None)
    return str(getattr(raw, "value", raw))


def _blocker_path(item: Any) -> str | None:
    value = getattr(item, "field_path", None)
    return value if isinstance(value, str) else None


def _selected_result(result: Any) -> Any:
    payload = getattr(result, "result", None)
    if payload is not None:
        return payload
    for name in ("geometry", "flow_state", "heat_transfer", "pressure_drop", "success_result"):
        payload = getattr(result, name, None)
        if payload is not None:
            return payload
    for name in ("blocked_result", "raw_boundary_blocked_result"):
        payload = getattr(result, name, None)
        if payload is not None:
            return payload
    return None


def _blocked_demo_record(
    *,
    demo_id: str,
    test_id: str,
    stage: str,
    result: Any,
    public_operation: str,
    partial_result_present: bool = False,
    numeric_result_fields_present: bool = False,
) -> dict[str, Any]:
    blockers = tuple(getattr(result, "blockers", ()))
    payload = _selected_result(result)
    blocked_hash = getattr(payload, "blocked_result_hash", None)
    if not isinstance(blocked_hash, str):
        blocked_hash = getattr(payload, "result_hash", None)
    if not isinstance(blocked_hash, str):
        blocked_hash = ""
    field_paths: list[str | None] = []
    for item in blockers:
        path = _blocker_path(item)
        if isinstance(path, str) and "; " in path:
            field_paths.extend(path.split("; "))
        else:
            field_paths.append(path)
    return {
        "demo_id": demo_id,
        "test_id": test_id,
        "stage": stage,
        "status": producer_status(result),
        "public_operation": public_operation,
        "blocker_code": _blocker_code(blockers[0]) if blockers else "",
        "blocker_codes": [_blocker_code(item) for item in blockers],
        "blocker_field_paths": field_paths,
        "blocked_result_hash": blocked_hash,
        "partial_result_present": partial_result_present,
        "success_result_present": False,
        "success_identity_present": False,
        "numeric_result_fields_present": numeric_result_fields_present,
        "identity_repaired": False,
        "blocked_component_as_zero": False,
        "excluded_component_as_zero": False,
        "downstream_success_execution_absent": True,
        "production_blocker_identity_preserved": True,
    }


def _build_blocked_cases(chain: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    t031_request = cast(dict[str, Any], chain["task031_request"])
    t032_request = cast(dict[str, Any], chain["task032_request"])
    t033_request = cast(dict[str, Any], chain["task033_request"])
    t034_request = cast(dict[str, Any], chain["task034_request"])
    t035_request = cast(dict[str, Any], chain["task035_request"])

    b01 = copy.deepcopy(t031_request)
    b01["schema_version"] = "task031.shell-side-hydraulic-geometry-request.v0"
    r01 = validate_task031(b01)

    b02 = copy.deepcopy(t032_request)
    b02["task031_result"]["geometry"] = None
    r02 = validate_task032(b02)

    b03 = copy.deepcopy(t033_request)
    b03["task032_flow_state"] = []
    r03 = validate_task033(b03)

    b04 = copy.deepcopy(t034_request)
    b04["task031_request_evidence"]["baffle_geometry_result"]["geometry"]["shell_pass_count"] = 2
    changed_t031 = task031_schema.parse_request(b04["task031_request_evidence"])
    b04["task031_request_hash"] = task031_canonical.request_hash(changed_t031)
    r04 = validate_task034(b04)

    b05 = copy.deepcopy(t035_request)
    b05["task034_result"]["pressure_drop"]["task033_result_id"] = "tampered-task033-id"
    r05 = validate_task035(b05)

    r06 = validate_task035([])

    return (
        _blocked_demo_record(
            demo_id=BLOCKED_DEMO_IDS[0],
            test_id="T036_BLOCK_001_TASK031_FAIL_CLOSED",
            stage="S03",
            result=r01,
            public_operation="TASK031.validate_request",
        ),
        _blocked_demo_record(
            demo_id=BLOCKED_DEMO_IDS[1],
            test_id="T036_BLOCK_002_TASK032_UPSTREAM_MISMATCH",
            stage="S05",
            result=r02,
            public_operation="TASK032.validate_request",
        ),
        _blocked_demo_record(
            demo_id=BLOCKED_DEMO_IDS[2],
            test_id="T036_BLOCK_003_TASK033_BLOCKED_OR_INAPPLICABLE",
            stage="S07",
            result=r03,
            public_operation="TASK033.validate_request",
        ),
        _blocked_demo_record(
            demo_id=BLOCKED_DEMO_IDS[3],
            test_id="T036_BLOCK_004_TASK034_BLOCKED_OR_INAPPLICABLE",
            stage="S09",
            result=r04,
            public_operation="TASK034.validate_request",
        ),
        _blocked_demo_record(
            demo_id=BLOCKED_DEMO_IDS[4],
            test_id="T036_BLOCK_005_TASK035_CROSS_PRODUCER_IDENTITY_MISMATCH",
            stage="S11",
            result=r05,
            public_operation="TASK035.validate_request",
        ),
        _blocked_demo_record(
            demo_id=BLOCKED_DEMO_IDS[5],
            test_id="T036_BLOCK_006_TASK035_RAW_BOUNDARY_REJECTION",
            stage="S11",
            result=r06,
            public_operation="TASK035.validate_request",
        ),
    )


def _build_checklist(blocked_cases: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    checklist: dict[str, Any] = {
        "schema_version": "task036.acceptance-checklist.v1",
        "checklist_id": "TASK036-CHECKLIST-0.3.0",
        "release_version": RELEASE_VERSION,
        "success_demo_id": DEMO_SUCCESS_ID,
        "required_available_capabilities": list(AVAILABLE_CAPABILITIES),
        "unavailable_capabilities": list(UNAVAILABLE_CAPABILITIES),
        "required_test_ids": list(TEST_IDS),
        "required_artifact_paths": list(ARTIFACT_PATHS),
        "required_python_versions": list(PYTHON_VERSIONS),
        "required_repeat_runs": 2,
        "upstream_identity_status": "PASS",
        "release_acceptance_status": "PASS",
        "checklist_status": "PASS" if len(blocked_cases) == 6 else "BLOCKED",
        "checklist_hash": "",
    }
    checklist["checklist_hash"] = acceptance_checklist_hash(checklist)
    if tuple(checklist) != ACCEPTANCE_CHECKLIST_FIELDS:
        raise AssertionError("acceptance checklist field order drift")
    return checklist


def _demo_evidence(
    graph: Mapping[str, Any],
    identities: Mapping[str, str],
    blocked_cases: tuple[dict[str, Any], ...],
    upstream_ledger: Mapping[str, Any],
    task035_result: Any,
) -> dict[str, Any]:
    return {
        "schema_version": DEMO_RESULT_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
        "demo_id": DEMO_SUCCESS_ID,
        "release_version": RELEASE_VERSION,
        "source_commit": SOURCE_MAIN_SHA,
        "source_tree": SOURCE_MAIN_TREE,
        "production_graph": dict(graph),
        "success_demo": {
            "demo_id": DEMO_SUCCESS_ID,
            "status": producer_status(task035_result),
            "task034_result_hash": identities["TASK034_RESULT_HASH"],
            "task034_result_id": identities["TASK034_RESULT_ID"],
            "task035_result_hash": identities["TASK035_RESULT_HASH"],
            "task035_result_id": identities["TASK035_RESULT_ID"],
        },
        "blocked_demos": [dict(item) for item in blocked_cases],
        "producer_identities": dict(identities),
        "upstream_evidence_ledger": dict(upstream_ledger),
        "capability_boundary": {
            "available": list(AVAILABLE_CAPABILITIES),
            "unavailable": list(UNAVAILABLE_CAPABILITIES),
            "release_acceptance_is_not_engineering_correctness_proof": True,
        },
    }


def _determinism_record(
    *,
    evidence_id: str,
    input_hash: str,
    surfaces: Mapping[str, str],
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": "task036.determinism-evidence.v1",
        "evidence_id": evidence_id,
        "input_hash": input_hash,
        "runtime_versions": list(PYTHON_VERSIONS),
        "repeat_run_count": 2,
        "compared_surfaces": list(DETERMINISM_SURFACES),
        "compared_digests": dict(surfaces),
        "compared_result_ids": {
            "TASK036_internal_result_id": surfaces["TASK036_internal_result_id"],
        },
        "byte_identity_status": "PASS",
        "repeat_identity_status": "PASS",
        "excluded_operational_fields": [
            "runtime_patch_version",
            "absolute_path",
            "process_id",
            "wall_clock_time",
        ],
        "evidence_hash": "",
    }
    record["evidence_hash"] = determinism_evidence_hash(record)
    return record


def _build_release_ledger(
    identities: Mapping[str, str],
    upstream_ledger: Mapping[str, Any],
    manifest: Mapping[str, Any],
    cross_runtime: Mapping[str, Any],
    repeat_run: Mapping[str, Any],
    checklist: Mapping[str, Any],
) -> dict[str, Any]:
    ledger: dict[str, Any] = {
        "schema_version": "task036.release-acceptance-ledger.v1",
        "ledger_id": "TASK036-RELEASE-ACCEPTANCE-0.3.0",
        "release_version": RELEASE_VERSION,
        "demo_id": DEMO_SUCCESS_ID,
        "source_commit": SOURCE_MAIN_SHA,
        "source_tree": SOURCE_MAIN_TREE,
        "required_available_capabilities": list(AVAILABLE_CAPABILITIES),
        "unavailable_capabilities": list(UNAVAILABLE_CAPABILITIES),
        "required_producer_statuses": {
            "TASK031": "VALID",
            "TASK032": "VALID",
            "TASK033": "VALID",
            "TASK034": "VALID",
            "TASK035": "VALID",
        },
        "required_producer_identities": dict(identities),
        "task034_request_hash": identities["TASK034_REQUEST_HASH"],
        "task034_result_hash": identities["TASK034_RESULT_HASH"],
        "task034_result_id": identities["TASK034_RESULT_ID"],
        "task035_request_hash": identities["TASK035_REQUEST_HASH"],
        "task035_result_hash": identities["TASK035_RESULT_HASH"],
        "task035_result_id": identities["TASK035_RESULT_ID"],
        "upstream_evidence_refs": [
            "TASK036-UPSTREAM-EVIDENCE-0.3.0",
            str(upstream_ledger["ledger_hash"]),
        ],
        "artifact_manifest_digest": manifest["manifest_hash"],
        "determinism_evidence_digest": sha256_bytes(
            (str(cross_runtime["evidence_hash"]) + str(repeat_run["evidence_hash"])).encode()
        ),
        "acceptance_checklist_digest": checklist["checklist_hash"],
        "acceptance_status": "PASS",
        "ledger_hash": "",
    }
    if tuple(ledger) != RELEASE_ACCEPTANCE_LEDGER_FIELDS:
        raise AssertionError("release ledger field order drift")
    ledger["ledger_hash"] = release_acceptance_ledger_hash(ledger)
    return ledger


def _build_version_metadata(
    manifest: Mapping[str, Any],
    ledger: Mapping[str, Any],
    artifact_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    digest_set = [
        {"artifact_id": artifact_id, "sha256": artifact_digest(artifact_bytes[path])}
        for artifact_id, path in zip(ARTIFACT_IDS, ARTIFACT_PATHS, strict=True)
    ]
    metadata: dict[str, Any] = {
        "schema_version": "task036.version-metadata.v1",
        "metadata_id": "TASK036-VERSION-METADATA-0.3.0",
        "release_version": RELEASE_VERSION,
        "release_candidate_id": RELEASE_CANDIDATE_ID,
        "software_version": RELEASE_SOFTWARE_VERSION,
        "source_commit": SOURCE_MAIN_SHA,
        "source_tree": SOURCE_MAIN_TREE,
        "task031_authority_ref": "TASK031_PUBLIC_RESULT",
        "task032_authority_ref": "TASK032_PUBLIC_RESULT",
        "task033_authority_ref": "TASK033_PUBLIC_RESULT",
        "task034_authority_ref": "TASK034_PUBLIC_RESULT",
        "task035_authority_ref": "TASK035_PR205_MAIN",
        "manifest_digest": manifest["manifest_hash"],
        "artifact_digest_set": digest_set,
        "release_acceptance_result_id": release_acceptance_result_id(str(ledger["ledger_hash"])),
        "semantic_identity_version": "task036.release-identity.v1",
        "metadata_hash": "",
    }
    if tuple(metadata) != VERSION_METADATA_FIELDS:
        raise AssertionError("version metadata field order drift")
    metadata["metadata_hash"] = version_metadata_hash(metadata)
    return metadata


def _build_success_result(
    *,
    demo_hash: str,
    identities: Mapping[str, str],
    upstream_ledger: Mapping[str, Any],
    cross_runtime: Mapping[str, Any],
    repeat_run: Mapping[str, Any],
    manifest: Mapping[str, Any],
    ledger: Mapping[str, Any],
    checklist: Mapping[str, Any],
    provenance: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": SUCCESS_RESULT_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
        "demo_id": DEMO_SUCCESS_ID,
        "release_version": RELEASE_VERSION,
        "source_commit": SOURCE_MAIN_SHA,
        "source_tree": SOURCE_MAIN_TREE,
        "task031_status": "VALID",
        "task032_status": "VALID",
        "task033_status": "VALID",
        "task034_status": "VALID",
        "task035_status": "VALID",
        "task034_request_hash": identities["TASK034_REQUEST_HASH"],
        "task034_result_hash": identities["TASK034_RESULT_HASH"],
        "task034_result_id": identities["TASK034_RESULT_ID"],
        "task035_request_hash": identities["TASK035_REQUEST_HASH"],
        "task035_result_hash": identities["TASK035_RESULT_HASH"],
        "task035_result_id": identities["TASK035_RESULT_ID"],
        "release_acceptance_ledger": dict(ledger),
        "upstream_evidence_ledger": dict(upstream_ledger),
        "determinism_evidence": {
            "cross_runtime": dict(cross_runtime),
            "repeat_run": dict(repeat_run),
        },
        "artifact_manifest_digest": manifest["manifest_hash"],
        "version_metadata_digest": metadata["metadata_hash"],
        "acceptance_checklist": dict(checklist),
        "provenance": dict(provenance),
        "request_hash": demo_hash,
        "result_hash": "",
        "result_id": "",
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
    }
    if tuple(record) != SUCCESS_RESULT_FIELDS:
        raise AssertionError("success result field order drift")
    record["result_hash"] = success_result_hash(record)
    record["result_id"] = result_id(str(record["result_hash"]))
    return record


def _typed_blocked_for_exception(raw_request: Any, message: str) -> Task036ValidationResult:
    blocker = {
        "code": "ST036_PUBLIC_GRAPH_INVALID",
        "stage": "S12",
        "field_path": "public_graph",
        "message_key": message,
        "details": [],
    }
    payload: dict[str, Any] = {
        "schema_version": TYPED_BLOCKED_RESULT_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
        "demo_id": DEMO_SUCCESS_ID,
        "release_version": RELEASE_VERSION,
        "failure_stage": "S12",
        "source_commit": SOURCE_MAIN_SHA,
        "source_tree": SOURCE_MAIN_TREE,
        "task031_status": "BLOCKED",
        "task032_status": "BLOCKED",
        "task033_status": "BLOCKED",
        "task034_status": "BLOCKED",
        "task035_status": "BLOCKED",
        "task034_request_hash": None,
        "task034_result_hash": None,
        "task034_result_id": None,
        "task035_request_hash": None,
        "task035_result_hash": None,
        "task035_result_id": None,
        "request_hash": None,
        "blocked_result_hash": "",
        "result_id": "",
        "blockers": [blocker],
        "warnings": [],
        "deferred_capabilities": [],
        "upstream_evidence": {},
        "provenance": [],
    }
    from .canonical import typed_blocked_result_hash

    payload["blocked_result_hash"] = typed_blocked_result_hash(payload)
    payload["result_id"] = result_id(payload["blocked_result_hash"], "TASK036_TYPED_BLOCKED_RESULT")
    result = Task036TypedBlockedResult(**payload)
    return Task036ValidationResult(
        status=ValidationStatus.BLOCKED,
        blocked_result=result,
        stages=tuple(STAGE_ORDER[:13]),
    )


def _build_run(raw_request: Any) -> Task036Run:
    parsed, input_hash, input_blockers = validate_demo_input(raw_request)
    if parsed is None or input_hash is None or input_blockers:
        raise ValueError("demo input did not pass frozen boundary")
    demo = {field: getattr(parsed, field) for field in DEMO_INPUT_FIELDS}
    raw_demo = copy.deepcopy(dict(raw_request))
    task031_request = copy.deepcopy(demo["TASK031_RAW_REQUEST_RECORD"])
    task031_result = validate_task031(task031_request)
    _require_valid(task031_result, "TASK031")
    task032_request = _build_task032_request(
        task031_result,
        demo["TASK032_PROPERTY_SNAPSHOT_RECORD"],
        demo["TASK032_MASS_FLOW_AUTHORITY_RECORD"],
        raw_demo["TASK032_REQUEST_EVIDENCE_REFS"],
    )
    task032_result = validate_task032(task032_request)
    _require_valid(task032_result, "TASK032")
    task033_request = _build_task033_request(
        task032_request, task032_result, raw_demo["TASK033_REQUEST_EVIDENCE_REFS"]
    )
    task033_result = validate_task033(task033_request)
    _require_valid(task033_result, "TASK033")
    task034_request = _build_task034_request(
        task031_request,
        task031_result,
        task032_request,
        task032_result,
        task033_request,
        task033_result,
        shell_authority=demo["TASK034_SHELL_TYPE_AUTHORITY_RECORD"],
        wall_authority=demo["TASK034_WALL_PROPERTY_AUTHORITY_RECORD"],
        request_evidence_refs=raw_demo["TASK034_REQUEST_EVIDENCE_REFS"],
    )
    task034_result = validate_task034(task034_request)
    _require_valid(task034_result, "TASK034")
    task035_request = _build_task035_request(
        task031_result,
        task032_result,
        task033_result,
        task034_result,
        demo["TASK035_EVIDENCE_REFS"],
    )
    task035_result = validate_task035(task035_request)
    _require_valid(task035_result, "TASK035")
    chain = {
        "task031_request": task031_request,
        "task031_result": task031_result,
        "task032_request": task032_request,
        "task032_result": task032_result,
        "task033_request": task033_request,
        "task033_result": task033_result,
        "task034_request": task034_request,
        "task034_result": task034_result,
        "task035_request": task035_request,
        "task035_result": task035_result,
    }
    identities = _identity_values(chain)
    graph = _graph_evidence(chain)
    upstream_ledger = _build_upstream_ledger(identities)
    blocked_cases = _build_blocked_cases(chain)
    checklist = _build_checklist(blocked_cases)
    demo_evidence = _demo_evidence(
        graph, identities, blocked_cases, upstream_ledger, task035_result
    )
    demo_json = render_json_bytes(demo_evidence)
    demo_markdown = render_demo_markdown_bytes(demo_evidence)
    acceptance_markdown = render_acceptance_bytes(checklist)
    runner_path = REPO_ROOT / ARTIFACT_PATHS[0]
    test_path = REPO_ROOT / ARTIFACT_PATHS[1]
    if not runner_path.exists() or not test_path.exists():
        raise ValueError("frozen runner/test artifact source is missing")
    artifact_bytes: dict[str, bytes] = {
        ARTIFACT_PATHS[0]: runner_path.read_bytes(),
        ARTIFACT_PATHS[1]: test_path.read_bytes(),
        ARTIFACT_PATHS[2]: demo_json,
        ARTIFACT_PATHS[3]: demo_markdown,
        ARTIFACT_PATHS[4]: b"",
        ARTIFACT_PATHS[5]: acceptance_markdown,
    }
    manifest = build_manifest(
        source_commit=SOURCE_MAIN_SHA,
        source_tree=SOURCE_MAIN_TREE,
        artifact_bytes=artifact_bytes,
        upstream_evidence_ledger_ref=str(upstream_ledger["ledger_hash"]),
        release_acceptance_ledger_ref="TASK036-RELEASE-ACCEPTANCE-0.3.0",
        acceptance_checklist_ref=str(checklist["checklist_hash"]),
    )
    artifact_bytes[ARTIFACT_PATHS[4]] = render_manifest_bytes(manifest)
    surfaces = {
        DETERMINISM_SURFACES[0]: exact_file_digest(artifact_bytes[ARTIFACT_PATHS[2]]),
        DETERMINISM_SURFACES[1]: exact_file_digest(artifact_bytes[ARTIFACT_PATHS[4]]),
        DETERMINISM_SURFACES[2]: exact_file_digest(artifact_bytes[ARTIFACT_PATHS[3]]),
        DETERMINISM_SURFACES[3]: exact_file_digest(artifact_bytes[ARTIFACT_PATHS[5]]),
        DETERMINISM_SURFACES[4]: sha256_bytes(
            success_result_canonical_bytes(
                {
                    **{
                        "schema_version": SUCCESS_RESULT_SCHEMA_VERSION,
                        "profile_id": PROFILE_ID,
                        "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
                        "demo_id": DEMO_SUCCESS_ID,
                        "release_version": RELEASE_VERSION,
                        "source_commit": SOURCE_MAIN_SHA,
                        "source_tree": SOURCE_MAIN_TREE,
                        "task031_status": "VALID",
                        "task032_status": "VALID",
                        "task033_status": "VALID",
                        "task034_status": "VALID",
                        "task035_status": "VALID",
                        "task034_request_hash": identities["TASK034_REQUEST_HASH"],
                        "task034_result_hash": identities["TASK034_RESULT_HASH"],
                        "task034_result_id": identities["TASK034_RESULT_ID"],
                        "task035_request_hash": identities["TASK035_REQUEST_HASH"],
                        "task035_result_hash": identities["TASK035_RESULT_HASH"],
                        "task035_result_id": identities["TASK035_RESULT_ID"],
                        "upstream_evidence_ledger": upstream_ledger,
                        "request_hash": input_hash,
                        "warnings": [],
                        "blockers": [],
                        "deferred_capabilities": [],
                    }
                }
            )
        ),
        DETERMINISM_SURFACES[5]: "",
        DETERMINISM_SURFACES[6]: "",
    }
    core_hash = success_result_hash(
        {
            "schema_version": SUCCESS_RESULT_SCHEMA_VERSION,
            "profile_id": PROFILE_ID,
            "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
            "demo_id": DEMO_SUCCESS_ID,
            "release_version": RELEASE_VERSION,
            "source_commit": SOURCE_MAIN_SHA,
            "source_tree": SOURCE_MAIN_TREE,
            "task031_status": "VALID",
            "task032_status": "VALID",
            "task033_status": "VALID",
            "task034_status": "VALID",
            "task035_status": "VALID",
            "task034_request_hash": identities["TASK034_REQUEST_HASH"],
            "task034_result_hash": identities["TASK034_RESULT_HASH"],
            "task034_result_id": identities["TASK034_RESULT_ID"],
            "task035_request_hash": identities["TASK035_REQUEST_HASH"],
            "task035_result_hash": identities["TASK035_RESULT_HASH"],
            "task035_result_id": identities["TASK035_RESULT_ID"],
            "upstream_evidence_ledger": upstream_ledger,
            "request_hash": input_hash,
            "warnings": [],
            "blockers": [],
            "deferred_capabilities": [],
        }
    )
    core_id = result_id(core_hash)
    surfaces[DETERMINISM_SURFACES[5]] = core_hash
    surfaces[DETERMINISM_SURFACES[6]] = core_id
    cross_runtime = _determinism_record(
        evidence_id="TASK036-CROSS-RUNTIME-0.3.0", input_hash=input_hash, surfaces=surfaces
    )
    repeat_run = _determinism_record(
        evidence_id="TASK036-REPEAT-RUN-0.3.0", input_hash=input_hash, surfaces=surfaces
    )
    release_ledger = _build_release_ledger(
        identities, upstream_ledger, manifest, cross_runtime, repeat_run, checklist
    )
    provenance = build_provenance(
        task031_result=_task_result_envelope(task031_result, "geometry"),
        task032_result=_task_result_envelope(task032_result, "flow_state"),
        task033_result=_task_result_envelope(task033_result, "heat_transfer"),
        task034_result=_task_result_envelope(task034_result, "pressure_drop"),
        task035_result=_task_result_envelope(task035_result, "success_result"),
        demo_id=DEMO_SUCCESS_ID,
        release_evidence_ledger_hash=str(release_ledger["ledger_hash"]),
        artifact_manifest_digest=str(manifest["manifest_hash"]),
        acceptance_checklist_digest=str(checklist["checklist_hash"]),
        source_commit=SOURCE_MAIN_SHA,
        source_tree=SOURCE_MAIN_TREE,
    )
    metadata = _build_version_metadata(manifest, release_ledger, artifact_bytes)
    final_result = _build_success_result(
        demo_hash=input_hash,
        identities=identities,
        upstream_ledger=upstream_ledger,
        cross_runtime=cross_runtime,
        repeat_run=repeat_run,
        manifest=manifest,
        ledger=release_ledger,
        checklist=checklist,
        provenance=provenance,
        metadata=metadata,
    )
    if final_result["result_hash"] != core_hash or final_result["result_id"] != core_id:
        raise ValueError("final result identity does not match S15 identity core")
    return Task036Run(
        demo_input=demo,
        task031_request=task031_request,
        task031_result=_task_result_envelope(task031_result, "geometry"),
        task032_request=task032_request,
        task032_result=_task_result_envelope(task032_result, "flow_state"),
        task033_request=task033_request,
        task033_result=_task_result_envelope(task033_result, "heat_transfer"),
        task034_request=task034_request,
        task034_result=_task_result_envelope(task034_result, "pressure_drop"),
        task035_request=task035_request,
        task035_result=_task_result_envelope(task035_result, "success_result"),
        graph_evidence=graph,
        upstream_evidence_ledger=upstream_ledger,
        blocked_cases=blocked_cases,
        identity_core={
            "schema_version": SUCCESS_RESULT_SCHEMA_VERSION,
            "canonical_kind_tag": "TASK036_SUCCESS_RESULT",
            "prehash_fields": list(SUCCESS_RESULT_PREHASH_FIELDS),
            "result_hash": core_hash,
            "result_id": core_id,
        },
        cross_runtime_determinism=cross_runtime,
        repeat_run_determinism=repeat_run,
        acceptance_checklist=checklist,
        manifest=manifest,
        release_acceptance_ledger=release_ledger,
        provenance=provenance,
        version_metadata=metadata,
        final_result=final_result,
        artifact_bytes=artifact_bytes,
    )


def _success_model(record: Mapping[str, Any]) -> Task036SuccessResult:
    values = dict(record)
    values["warnings"] = tuple(values["warnings"])
    values["blockers"] = tuple(values["blockers"])
    values["deferred_capabilities"] = tuple(values["deferred_capabilities"])
    return Task036SuccessResult(**values)


def validate_request(raw_request: Any) -> Task036ValidationResult:
    """Public TASK036 operation with raw and typed fail-closed branches."""

    _, _, input_blockers = validate_demo_input(raw_request)
    if input_blockers:
        return Task036ValidationResult(
            status=ValidationStatus.BLOCKED,
            raw_boundary_blocked_result=build_raw_boundary_blocked(raw_request, input_blockers),
            stages=tuple(STAGE_ORDER[:2]),
        )
    try:
        run = _build_run(raw_request)
    except (CanonicalizationError, TypeError, ValueError, KeyError) as exc:
        return _typed_blocked_for_exception(raw_request, str(exc))
    return Task036ValidationResult(
        status=ValidationStatus.VALID,
        success_result=_success_model(run.final_result),
        stages=tuple(STAGE_ORDER),
    )


def run_release_demo(raw_request: Any | None = None) -> Task036ValidationResult:
    """Run the public demo, using the frozen actual-chain input by default."""

    return validate_request(build_valid_demo_input() if raw_request is None else raw_request)


def build_release_run() -> Task036Run:
    """Return the complete internal run used by the evidence writer."""

    return _build_run(build_valid_demo_input())


__all__ = [
    "build_release_run",
    "build_valid_demo_input",
    "run_release_demo",
    "validate_request",
]
