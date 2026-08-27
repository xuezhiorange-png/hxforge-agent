"""TASK-034 canonical projections, upstream replay, hashes, and IDs."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import uuid
from collections.abc import Mapping
from decimal import Decimal
from enum import Enum
from typing import Any, cast

from .models import (
    RAW_BOUNDARY_BLOCKED_RESULT_FIELDS,
    REQUEST_FIELDS,
    SHELL_TYPE_AUTHORITY_PREHASH_FIELDS,
    SUCCESS_RESULT_FIELDS,
    TASK032_FLOW_STATE_EVIDENCE_FIELDS,
    TYPED_BLOCKED_RESULT_FIELDS,
    WALL_PROPERTY_AUTHORITY_PREHASH_FIELDS,
    BlockerEntry,
    ShellSidePressureDropBlockedResult,
    ShellSidePressureDropRawBoundaryBlockedResult,
    ShellSidePressureDropResult,
    Task034Request,
    WarningEntry,
)

REQUEST_HASH_NAMESPACE = "task034.request.v2"
SUCCESS_RESULT_HASH_NAMESPACE = "task034.success-result.v2"
TYPED_BLOCKED_RESULT_HASH_NAMESPACE = "task034.typed-blocked-result.v2"
RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE = "task034.raw-boundary-blocked-result.v2"
PROVENANCE_NAMESPACE = "task034.provenance.v2"
RAW_PROJECTION_NAMESPACE = "task034.raw-projection.v2"
WALL_PROPERTY_AUTHORITY_NAMESPACE = "task034.wall-property-authority.v2"
SHELL_TYPE_AUTHORITY_HASH_NAMESPACE = "task034.shell-type-authority.v2"
RESULT_ID_NAMESPACE = uuid.UUID("c8f1c1c4-a11b-596b-88ad-6e851a22b9fd")
RESULT_ID_NAME_PREFIX = "task034-shell-side-pressure-drop-id.v2:"

TASK032_REQUEST_HASH_NAMESPACE = "task032.request.v1"
TASK032_SUCCESS_RESULT_HASH_NAMESPACE = "task032.success-result.v1"
TASK032_RESULT_ID_NAMESPACE = uuid.UUID("96ab5cf6-204d-547a-9d27-8a5eff46f997")
TASK032_RESULT_ID_NAME_PREFIX = "task032-result-v1::"

TASK031_TUBE_LAYOUT_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "request_hash",
    "positions",
    "tube_hole_count",
    "physical_tube_count",
    "boundary_rejection_count",
    "exclusion_rejection_count",
    "exclusion_audit",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance_pre_hash",
)

TASK031_RESULT_BINDING_FIELDS: tuple[str, ...] = (
    "schema_version",
    "geometry_id",
    "geometry_hash",
    "request_hash",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task021_layout_id",
    "task021_layout_hash",
    "task022_geometry_id",
    "task022_geometry_hash",
    "construction_family",
    "shell_pass_count",
    "shell_inside_diameter_m",
    "tube_outer_diameter_m",
)

TASK031_ENGINEERING_AUTHORITY_FIELDS: tuple[str, ...] = (
    "schema_version",
    "authority_profile_id",
    "authority_hash",
    "evidence_refs",
)

NULL_KIND = b"n"
BOOL_KIND = b"b"
INTEGER_KIND = b"i"
STRING_KIND = b"s"
DECIMAL_KIND = b"d"
STRING_TUPLE_KIND = b"t"
STRING_MAPPING_KIND = b"m"
PROPERTY_SNAPSHOT_KIND = b"p"
MASS_FLOW_AUTHORITY_KIND = b"a"
TASK031_RESULT_KIND = b"h"
BLOCKER_TUPLE_KIND = b"k"
BLOCKER_ENTRY_KIND = b"c"
TASK032_FLOW_STATE_KIND = b"f"
TASK032_REQUEST_EVIDENCE_KIND = b"q"
PROVENANCE_KIND = b"v"

PROVENANCE_FIELDS: tuple[str, ...] = (
    "task_id",
    "profile_id",
    "design_contract_path",
    "implementation_software_version",
    "request_hash",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "shell_type",
    "shell_type_authority_hash",
    "shell_type_authority_record_id",
    "shell_type_authority_source_id",
    "shell_type_authority_source_version",
    "task031_request_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "task033_request_hash",
    "task033_result_hash",
    "task033_result_id",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "wall_property_schema_version",
    "wall_property_source_id",
    "wall_property_source_version",
    "wall_property_snapshot_hash",
    "wall_property_authority_hash",
    "correlation_id",
    "engineering_source_authority_record_id",
    "source_id",
    "source_version",
    "source_location",
    "frozen_source_artifact",
    "applicability_profile",
    "physical_boundary",
    "excluded_phenomena",
    "modeled_quantity",
    "formula_identity",
    "deterministic_algorithm_ids",
    "warnings",
    "deferred_capabilities",
    "evidence_refs",
    "source_definition_issue",
    "source_definition_freeze_comment_id",
    "provenance_hash",
)
PROVENANCE_HASH_FIELDS = tuple(field for field in PROVENANCE_FIELDS if field != "provenance_hash")
PROVENANCE_PREHASH_FIELDS = PROVENANCE_HASH_FIELDS
SUCCESS_PREHASH_FIELDS: tuple[str, ...] = tuple(
    field for field in SUCCESS_RESULT_FIELDS if field not in {"result_hash", "result_id"}
)
TYPED_BLOCKED_PREHASH_FIELDS: tuple[str, ...] = tuple(
    field for field in TYPED_BLOCKED_RESULT_FIELDS if field != "blocked_result_hash"
)
RAW_BOUNDARY_BLOCKED_PREHASH_FIELDS: tuple[str, ...] = tuple(
    field for field in RAW_BOUNDARY_BLOCKED_RESULT_FIELDS if field != "blocked_result_hash"
)


class CanonicalizationError(ValueError):
    """Raised when a value cannot enter the deterministic identity domain."""


def primitive(value: Any) -> Any:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError("non-finite Decimal")
        return str(value)
    if isinstance(value, float):
        raise CanonicalizationError("binary floating-point values are forbidden")
    if isinstance(value, Enum):
        return primitive(value.value)
    if isinstance(value, BlockerEntry):
        return {
            "code": value.code,
            "stage": value.stage,
            "field_path": value.field_path,
            "message_key": value.message_key,
            "details": [[k, v] for k, v in value.details],
        }
    if isinstance(value, WarningEntry):
        return {
            "code": value.code,
            "field_path": value.field_path,
            "message_key": value.message_key,
        }
    if dataclasses.is_dataclass(value):
        return {
            field.name: primitive(getattr(value, field.name)) for field in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise CanonicalizationError("canonical mapping keys must be strings")
        return {key: primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [primitive(item) for item in value]
    if value is None or isinstance(value, (bool, int, str)):
        return value
    raise CanonicalizationError(f"unsupported canonical value: {type(value).__name__}")


def canonical_bytes(namespace: str | bytes, projection: Any) -> bytes:
    ns = namespace.decode("ascii") if isinstance(namespace, bytes) else namespace
    return json.dumps(
        [ns, primitive(projection)], ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def hash_projection(namespace: str | bytes, projection: Any) -> str:
    return hashlib.sha256(canonical_bytes(namespace, projection)).hexdigest()


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            primitive(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    ).hexdigest()


def _pairs(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, (tuple, list)):
        return {
            item[0]: item[1] for item in value if isinstance(item, (tuple, list)) and len(item) == 2
        }
    return {}


def _message(value: Any) -> Any:
    return primitive(value)


def _mapping_pairs(value: Any, *, name: str) -> dict[str, Any]:
    """Return a public mapping or ordered pair mapping without inventing fields."""
    if isinstance(value, Mapping):
        result = dict(value)
    elif isinstance(value, (tuple, list)):
        if any(
            not isinstance(item, (tuple, list)) or len(item) != 2 or type(item[0]) is not str
            for item in value
        ):
            raise CanonicalizationError(f"invalid {name} pair mapping")
        result = {item[0]: item[1] for item in value}
    else:
        raise CanonicalizationError(f"invalid {name} mapping")
    if any(type(key) is not str for key in result):
        raise CanonicalizationError(f"invalid {name} mapping keys")
    return result


def _task020_case_authority_primitive(case: Any) -> dict[str, Any]:
    values = _mapping_pairs(case, name="TASK020 case authority")
    return {
        key: primitive(values[key])
        for key in ("revision_id", "payload_hash", "domain_snapshot_hash", "revision_status")
    }


def _task021_source_binding_primitive(source: Any) -> dict[str, Any]:
    values = _mapping_pairs(source, name="TASK021 geometry source binding")
    return {
        key: primitive(values[key])
        for key in (
            "source_id",
            "source_type",
            "source_revision",
            "source_location",
            "evidence_ref",
            "approved_by",
            "approved_at",
        )
    }


def _task021_rule_pack_identity_primitive(identity: Any) -> dict[str, Any]:
    values = _mapping_pairs(identity, name="TASK021 rule-pack identity")
    return {
        key: primitive(values[key])
        for key in ("rule_pack_id", "rule_pack_version", "rule_pack_canonical_hash")
    }


def _layout_provenance_pre_hash(layout: Mapping[str, Any]) -> dict[str, Any]:
    """Reproduce TASK031's internal provenance projection from public evidence."""
    provenance = _mapping_pairs(layout.get("provenance"), name="TASK021 provenance")
    try:
        rule_pack_raw = provenance["rule_pack_identity"]
        warnings_raw = provenance["warnings"]
        exclusion_refs_raw = provenance["exclusion_zone_evidence_refs"]
    except KeyError as exc:
        raise CanonicalizationError("incomplete TASK021 provenance") from exc
    if not isinstance(warnings_raw, (tuple, list)):
        raise CanonicalizationError("TASK021 provenance warnings must be a sequence")
    warnings = []
    for item in warnings_raw:
        warning = _mapping_pairs(item, name="TASK021 provenance warning")
        warnings.append(
            {
                key: primitive(warning[key])
                for key in ("code", "field_path", "message_key", "evidence_refs", "details")
            }
        )
    if not isinstance(exclusion_refs_raw, (tuple, list)):
        raise CanonicalizationError("TASK021 exclusion evidence refs must be a sequence")
    return {
        "task_id": primitive(provenance["task_id"]),
        "design_contract_path": primitive(provenance["design_contract_path"]),
        "task020_configuration_id": primitive(provenance["task020_configuration_id"]),
        "task020_configuration_hash": primitive(provenance["task020_configuration_hash"]),
        "task020_case_authority": _task020_case_authority_primitive(
            provenance["task020_case_authority"]
        ),
        "geometry_id": primitive(provenance["geometry_id"]),
        "geometry_revision": primitive(provenance["geometry_revision"]),
        "geometry_record_hash": primitive(provenance["geometry_record_hash"]),
        "tube_geometry_snapshot_hash": primitive(provenance["tube_geometry_snapshot_hash"]),
        "geometry_source_binding": _task021_source_binding_primitive(
            provenance["geometry_source_binding"]
        ),
        "layout_rule_profile_id": primitive(provenance["layout_rule_profile_id"]),
        "layout_rule_id": primitive(provenance["layout_rule_id"]),
        "layout_rule_version": primitive(provenance["layout_rule_version"]),
        "rule_artifact_canonical_hash": primitive(provenance["rule_artifact_canonical_hash"]),
        "layout_rule_snapshot_hash": primitive(provenance["layout_rule_snapshot_hash"]),
        "source_class": primitive(provenance["source_class"]),
        "approval_status": primitive(provenance["approval_status"]),
        "provenance_edge_ids": primitive(provenance["provenance_edge_ids"]),
        "layout_rule_evidence_refs": primitive(provenance["layout_rule_evidence_refs"]),
        "rule_pack_identity": (
            None if rule_pack_raw is None else _task021_rule_pack_identity_primitive(rule_pack_raw)
        ),
        "envelope_evidence_refs": primitive(provenance["envelope_evidence_refs"]),
        "exclusion_zone_evidence_refs": [primitive(refs) for refs in exclusion_refs_raw],
        "u_tube_pairing_evidence_refs": primitive(provenance["u_tube_pairing_evidence_refs"]),
        "software_version": primitive(provenance["software_version"]),
        "git_commit": primitive(provenance["git_commit"]),
        "request_hash": primitive(provenance["request_hash"]),
        "warnings": warnings,
        "deferred_capabilities": primitive(provenance["deferred_capabilities"]),
    }


def _geometry_projection(geometry: Mapping[str, Any]) -> list[Any]:
    return [
        geometry.get("schema_version"),
        geometry.get("geometry_id"),
        geometry.get("geometry_hash"),
        geometry.get("request_hash"),
        geometry.get("task020_configuration_id"),
        geometry.get("task020_configuration_hash"),
        geometry.get("task021_layout_id"),
        geometry.get("task021_layout_hash"),
        geometry.get("task022_geometry_id"),
        geometry.get("task022_geometry_hash"),
        geometry.get("task024_geometry_id"),
        geometry.get("task024_geometry_hash"),
        geometry.get("engineering_authority_id"),
        geometry.get("engineering_authority_hash"),
        geometry.get("formula_a_id"),
        geometry.get("formula_b_id"),
        geometry.get("pattern_family"),
        geometry.get("flow_region_identity"),
        geometry.get("central_inter_baffle_spacing_m"),
        geometry.get("central_crossflow_flow_area_m2"),
        geometry.get("shell_side_equivalent_hydraulic_diameter_m"),
        primitive(geometry.get("warnings", [])),
        primitive(geometry.get("blockers", [])),
        list(geometry.get("deferred_capabilities", [])),
        primitive(geometry.get("provenance", [])),
    ]


def task031_result_projection(result: Mapping[str, Any]) -> list[Any]:
    geometry = result.get("geometry")
    return [
        result.get("status"),
        None if geometry is None else _geometry_projection(geometry),
        primitive(result.get("warnings", [])),
        primitive(result.get("blockers", [])),
        list(result.get("deferred_capabilities", [])),
        result.get("blocked_result_hash"),
    ]


def property_snapshot_projection(snapshot: Mapping[str, Any]) -> list[Any]:
    return [
        str(snapshot.get("density_kg_m3")),
        str(snapshot.get("dynamic_viscosity_pa_s")),
        str(snapshot.get("thermal_conductivity_w_m_k")),
        str(snapshot.get("specific_heat_capacity_j_kg_k")),
        str(snapshot.get("bulk_temperature_k")),
        str(snapshot.get("bulk_pressure_pa")),
        snapshot.get("phase_region"),
        snapshot.get("property_source_id"),
        snapshot.get("property_source_version"),
        snapshot.get("property_snapshot_hash"),
    ]


def mass_flow_authority_projection(
    authority: Mapping[str, Any], *, include_hash: bool = True
) -> list[Any]:
    values: list[Any] = [
        authority.get("schema_version"),
        authority.get("authority_profile_id"),
        authority.get("shell_side_case_id"),
        authority.get("shell_side_stream_id"),
        authority.get("shell_side_fluid_id"),
        authority.get("rheology_model"),
        authority.get("task020_configuration_id"),
        authority.get("task020_configuration_hash"),
        authority.get("task031_geometry_id"),
        authority.get("task031_geometry_hash"),
        authority.get("property_snapshot_hash"),
        authority.get("property_state_role"),
        str(authority.get("mass_flow_rate_kg_s")),
        authority.get("mass_flow_sign_convention"),
        authority.get("authority_source_id"),
        authority.get("authority_source_version"),
        sorted(authority.get("evidence_refs", [])),
    ]
    if include_hash:
        values.append(authority.get("authority_hash"))
    return values


def mass_flow_authority_hash(authority: Mapping[str, Any]) -> str:
    return sha256_hex(
        [
            "task032.shell-side-mass-flow-authority.v1",
            mass_flow_authority_projection(authority, include_hash=False),
        ]
    )


def task032_request_projection(evidence: Mapping[str, Any]) -> list[Any]:
    return [
        evidence.get("schema_version"),
        evidence.get("profile_id"),
        task031_result_projection(evidence.get("task031_result", {})),
        evidence.get("property_snapshot_hash"),
        property_snapshot_projection(evidence.get("property_snapshot", {})),
        mass_flow_authority_projection(evidence.get("mass_flow_authority", {})),
        sorted(evidence.get("evidence_refs", [])),
    ]


def task032_request_hash(evidence: Mapping[str, Any]) -> str:
    return sha256_hex([TASK032_REQUEST_HASH_NAMESPACE, task032_request_projection(evidence)])


def _task031_tube_layout_projection(layout: Mapping[str, Any]) -> dict[str, Any]:
    required_fields = set(TASK031_TUBE_LAYOUT_PUBLIC_FIELDS) - {"provenance_pre_hash"}
    if not required_fields.issubset(layout) or "provenance" not in layout:
        raise CanonicalizationError("incomplete TASK031 tube-layout projection")
    projected = {
        field: primitive(layout[field])
        for field in TASK031_TUBE_LAYOUT_PUBLIC_FIELDS
        if field != "provenance_pre_hash"
    }
    projected["provenance_pre_hash"] = primitive(_layout_provenance_pre_hash(layout))
    return projected


def _task031_result_binding_projection(result: Mapping[str, Any]) -> list[Any]:
    status = result.get("status")
    geometry = result.get("geometry")
    if status == "BLOCKED" or geometry is None:
        return [status, None]
    if not isinstance(geometry, Mapping):
        raise CanonicalizationError("invalid TASK031 geometry projection")
    design = geometry.get("design_authority")
    if not isinstance(design, Mapping):
        raise CanonicalizationError("missing TASK024 design authority projection")
    geometry_values = [geometry[field] for field in TASK031_RESULT_BINDING_FIELDS]
    design_values = [
        design[field]
        for field in (
            "schema_version",
            "baffle_type",
            "baffle_count",
            "spacing_sequence_m",
            "authority_hash",
        )
    ]
    return [status, *map(primitive, geometry_values), *map(primitive, design_values)]


def _task031_engineering_authority_projection(binding: Mapping[str, Any]) -> list[list[Any]]:
    if not all(field in binding for field in TASK031_ENGINEERING_AUTHORITY_FIELDS):
        raise CanonicalizationError("incomplete TASK031 engineering-authority projection")
    return [[field, primitive(binding[field])] for field in TASK031_ENGINEERING_AUTHORITY_FIELDS]


def task031_request_projection(evidence: Mapping[str, Any]) -> list[Any]:
    task031_result = evidence.get("baffle_geometry_result")
    tube_layout = evidence.get("tube_layout")
    engineering_authority = evidence.get("engineering_authority")
    if not isinstance(task031_result, Mapping):
        raise CanonicalizationError("missing TASK031 result projection")
    if not isinstance(tube_layout, Mapping):
        raise CanonicalizationError("missing TASK021 layout projection")
    if not isinstance(engineering_authority, Mapping):
        raise CanonicalizationError("missing TASK031 engineering authority projection")
    return [
        evidence.get("schema_version"),
        _task031_tube_layout_projection(tube_layout),
        _task031_result_binding_projection(task031_result),
        _task031_engineering_authority_projection(engineering_authority),
        list(evidence.get("evidence_refs", [])),
    ]


def task031_request_hash(evidence: Mapping[str, Any]) -> str:
    return sha256_hex(task031_request_projection(evidence))


def _task032_success_projection(flow: Mapping[str, Any]) -> list[Any]:
    provenance = _pairs(flow.get("provenance", []))
    fields = [
        field
        for field in TASK032_FLOW_STATE_EVIDENCE_FIELDS
        if field not in {"result_hash", "result_id"}
    ]
    values = [flow.get(field) for field in fields]
    # The producer result projection uses lexical Decimal values and a 25-field provenance preimage.
    for field in (
        "shell_side_mass_flow_rate_kg_s",
        "shell_side_mass_velocity_kg_m2_s",
        "shell_side_bulk_velocity_m_s",
        "shell_side_reynolds_number",
        "shell_side_prandtl_number",
    ):
        values[fields.index(field)] = str(flow.get(field))
    provenance_fields = (
        "task_id",
        "design_contract_path",
        "implementation_software_version",
        "request_hash",
        "task020_configuration_id",
        "task020_configuration_hash",
        "task031_geometry_id",
        "task031_geometry_hash",
        "property_snapshot_hash",
        "mass_flow_authority_hash",
        "engineering_authority_id",
        "engineering_authority_hash",
        "formula_ids",
        "source_ids",
        "flow_model",
        "phase_region",
        "rheology_model",
        "shell_side_case_id",
        "shell_side_stream_id",
        "shell_side_fluid_id",
        "warnings",
        "deferred_capabilities",
        "evidence_refs",
        "engineering_source_formula_freeze_comment_id",
        "source_definition_issue",
    )
    values[fields.index("provenance")] = [
        primitive(provenance.get(field)) for field in provenance_fields
    ]
    return values


def task032_success_hash(flow: Mapping[str, Any]) -> str:
    return sha256_hex([TASK032_SUCCESS_RESULT_HASH_NAMESPACE, _task032_success_projection(flow)])


def task032_result_id(result_hash: str) -> str:
    return str(uuid.uuid5(TASK032_RESULT_ID_NAMESPACE, TASK032_RESULT_ID_NAME_PREFIX + result_hash))


def task031_geometry_hash(geometry: Mapping[str, Any]) -> str:
    provenance = _pairs(geometry.get("provenance", []))
    freeze_key = (
        "source_authority_freeze_comment_id"
        if "source_authority_freeze_comment_id" in provenance
        else "freeze_comment_id"
    )
    prehash = [
        primitive(provenance.get(key))
        for key in (
            "task_id",
            "design_contract_path",
            "task020_configuration_id",
            "task020_configuration_hash",
            "task021_layout_id",
            "task021_layout_hash",
            "task022_geometry_id",
            "task022_geometry_hash",
            "task024_geometry_id",
            "task024_geometry_hash",
            "engineering_authority_profile_id",
            "engineering_authority_hash",
            "formula_a_id",
            "formula_b_id",
            freeze_key,
            "source_ids",
            "pattern_family",
            "flow_region_identity",
            "software_version",
            "git_commit",
            "request_hash",
            "warnings",
            "deferred_capabilities",
        )
    ]
    projection = [
        geometry.get("schema_version"),
        geometry.get("request_hash"),
        geometry.get("task020_configuration_id"),
        geometry.get("task020_configuration_hash"),
        geometry.get("task021_layout_id"),
        geometry.get("task021_layout_hash"),
        geometry.get("task022_geometry_id"),
        geometry.get("task022_geometry_hash"),
        geometry.get("task024_geometry_id"),
        geometry.get("task024_geometry_hash"),
        geometry.get("pattern_family"),
        geometry.get("central_inter_baffle_spacing_m"),
        geometry.get("central_crossflow_flow_area_m2"),
        geometry.get("shell_side_equivalent_hydraulic_diameter_m"),
        geometry.get("flow_region_identity"),
        geometry.get("engineering_authority_id"),
        geometry.get("engineering_authority_hash"),
        geometry.get("formula_a_id"),
        geometry.get("formula_b_id"),
        primitive(geometry.get("warnings", [])),
        list(geometry.get("deferred_capabilities", [])),
        prehash,
    ]
    return sha256_hex(projection)


def task031_geometry_id(geometry_hash_value: str) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "urn:hxforge:task031:shell-side-hydraulic-geometry:v1:" + geometry_hash_value,
        )
    )


def _task033_payload(evidence: Mapping[str, Any]) -> Mapping[str, Any]:
    validation_result = evidence.get("task033_validation_result")
    if isinstance(validation_result, Mapping):
        payload = validation_result.get("heat_transfer")
        if not isinstance(payload, Mapping):
            raise CanonicalizationError("TASK033 validation result has no success payload")
        return payload
    payload = evidence.get("heat_transfer")
    if isinstance(payload, Mapping):
        return payload
    payload = evidence.get("result", evidence)
    return cast(Mapping[str, Any], payload) if isinstance(payload, Mapping) else evidence


def task033_request_hash(evidence: Mapping[str, Any]) -> str:
    request_evidence = evidence.get(
        "task032_request_evidence", evidence.get("request_evidence", {})
    )
    if isinstance(request_evidence, Mapping):
        request_evidence = dict(request_evidence)
        if isinstance(request_evidence.get("evidence_refs"), (list, tuple)):
            request_evidence["evidence_refs"] = sorted(request_evidence["evidence_refs"])
    flow = evidence.get("task032_flow_state", evidence.get("flow_state", {}))
    return sha256_hex(
        [
            "task033.shell-side-heat-transfer-request.v1",
            "hxforge.shell_tube.shell_side_heat_transfer.v1",
            primitive(flow),
            primitive(request_evidence),
            sorted(evidence.get("evidence_refs", [])),
        ]
    )


def task033_result_hash(evidence: Mapping[str, Any]) -> str:
    result = _task033_payload(evidence)
    fields = (
        "schema_version",
        "profile_id",
        "first_slice_profile_id",
        "implementation_software_version",
        "shell_side_case_id",
        "shell_side_stream_id",
        "shell_side_fluid_id",
        "task020_configuration_id",
        "task020_configuration_hash",
        "task031_geometry_id",
        "task031_geometry_hash",
        "property_snapshot_hash",
        "mass_flow_authority_hash",
        "task032_request_hash",
        "task032_result_hash",
        "task032_result_id",
        "correlation_id",
        "engineering_source_authority_record_id",
        "heat_transfer_surface",
        "modeled_shell_side_heat_transfer_coefficient_w_m2_k",
        "request_hash",
        "warnings",
        "blockers",
        "deferred_capabilities",
        "applicability_context",
        "provenance",
    )
    return sha256_hex(
        [
            "task033.shell-side-heat-transfer.v1",
            [primitive(result.get(field)) for field in fields],
        ]
    )


def task033_result_id(result_hash_value: str) -> str:
    return str(
        uuid.uuid5(
            uuid.UUID("6d4de79e-3e04-5160-93e4-725c3f308a22"),
            "task033-shell-side-heat-transfer-id.v1:" + result_hash_value,
        )
    )


def property_snapshot_hash(snapshot: Mapping[str, Any]) -> str:
    # TASK-026's frozen nine-field framed record, replayed locally to keep TASK034
    # independent of upstream private modules.
    fields = (
        ("density_kg_m3", b"DECIMAL", str(snapshot.get("density_kg_m3"))),
        ("dynamic_viscosity_pa_s", b"DECIMAL", str(snapshot.get("dynamic_viscosity_pa_s"))),
        ("thermal_conductivity_w_m_k", b"DECIMAL", str(snapshot.get("thermal_conductivity_w_m_k"))),
        (
            "specific_heat_capacity_j_kg_k",
            b"DECIMAL",
            str(snapshot.get("specific_heat_capacity_j_kg_k")),
        ),
        ("bulk_temperature_k", b"DECIMAL", str(snapshot.get("bulk_temperature_k"))),
        ("bulk_pressure_pa", b"DECIMAL", str(snapshot.get("bulk_pressure_pa"))),
        ("phase_region", b"ENUM", str(snapshot.get("phase_region"))),
        ("property_source_id", b"STRING", str(snapshot.get("property_source_id"))),
        ("property_source_version", b"STRING", str(snapshot.get("property_source_version"))),
    )
    return hashlib.sha256(_frame_record("task026.property-snapshot.v1", fields)).hexdigest()


def _u32(value: int) -> bytes:
    return value.to_bytes(4, "big")


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "big")


def _frame_value(kind: bytes, payload: bytes) -> bytes:
    return _u32(len(kind)) + kind + _u64(len(payload)) + payload


def _frame_record(namespace: str, fields: tuple[tuple[str, bytes, str], ...]) -> bytes:
    encoded = namespace.encode("utf-8")
    output = _u32(len(encoded)) + encoded + _u32(len(fields))
    for name, kind, payload in fields:
        name_bytes = name.encode("utf-8")
        output += _u32(len(name_bytes)) + name_bytes + _frame_value(kind, payload.encode("ascii"))
    return output


def shell_type_authority_hash(authority: Mapping[str, Any]) -> str:
    values = _mapping_pairs(authority, name="shell-type authority")
    return hash_projection(
        SHELL_TYPE_AUTHORITY_HASH_NAMESPACE,
        [[field, primitive(values.get(field))] for field in SHELL_TYPE_AUTHORITY_PREHASH_FIELDS],
    )


def wall_property_authority_hash(request: Task034Request | Mapping[str, Any]) -> str:
    get = request.get if isinstance(request, Mapping) else lambda key: getattr(request, key)
    values = {
        "schema_version": get("wall_property_schema_version"),
        "shell_side_case_id": get("shell_side_case_id"),
        "shell_side_stream_id": get("shell_side_stream_id"),
        "shell_side_fluid_id": get("shell_side_fluid_id"),
        "task031_geometry_id": get("task031_geometry_id"),
        "task031_geometry_hash": get("task031_geometry_hash"),
        "task032_result_id": get("task032_result_id"),
        "task032_result_hash": get("task032_result_hash"),
        "property_snapshot_hash": get("property_snapshot_hash"),
        "shell_side_wall_dynamic_viscosity_pa_s": get("shell_side_wall_dynamic_viscosity_pa_s"),
        "source_id": get("wall_property_source_id"),
        "source_version": get("wall_property_source_version"),
        "evidence_refs": get("wall_property_evidence_refs"),
        "wall_property_snapshot_hash": get("wall_property_snapshot_hash"),
    }
    return hash_projection(
        WALL_PROPERTY_AUTHORITY_NAMESPACE,
        [[field, primitive(values[field])] for field in WALL_PROPERTY_AUTHORITY_PREHASH_FIELDS],
    )


def task034_request_projection(request: Task034Request) -> list[Any]:
    return [primitive(getattr(request, field)) for field in REQUEST_FIELDS]


def task034_request_hash(request: Task034Request) -> str:
    return hash_projection(REQUEST_HASH_NAMESPACE, task034_request_projection(request))


def _field_values(value: Any, fields: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for field in fields:
        raw = getattr(value, field)
        if field == "raw_projection":
            from .raw_projection import projection_primitive

            values.append(projection_primitive(raw))
        else:
            values.append(primitive(raw))
    return values


def success_result_hash(result: ShellSidePressureDropResult) -> str:
    return hash_projection(
        SUCCESS_RESULT_HASH_NAMESPACE, _field_values(result, SUCCESS_PREHASH_FIELDS)
    )


def typed_blocked_result_hash(result: ShellSidePressureDropBlockedResult) -> str:
    return hash_projection(
        TYPED_BLOCKED_RESULT_HASH_NAMESPACE,
        _field_values(result, TYPED_BLOCKED_PREHASH_FIELDS),
    )


def raw_boundary_blocked_result_hash(result: ShellSidePressureDropRawBoundaryBlockedResult) -> str:
    return hash_projection(
        RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE,
        _field_values(result, RAW_BOUNDARY_BLOCKED_PREHASH_FIELDS),
    )


def result_id(result_hash_value: str) -> str:
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, RESULT_ID_NAME_PREFIX + result_hash_value))


def provenance_hash(prehash: Mapping[str, Any]) -> str:
    return hash_projection(
        PROVENANCE_NAMESPACE, [primitive(prehash.get(field)) for field in PROVENANCE_HASH_FIELDS]
    )


__all__ = [name for name in globals() if not name.startswith("_")]
