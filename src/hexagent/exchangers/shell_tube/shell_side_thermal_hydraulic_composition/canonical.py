"""Canonical projections and identity helpers for TASK-035.

The functions in this module operate on public structural projections.  They
do not import or call any upstream producer model or canonicalization helper.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import uuid
from collections.abc import Mapping
from decimal import Decimal
from enum import Enum
from typing import Any

from .schema import (
    BLOCKED_RESULT_SCHEMA_VERSION,
    FIRST_SLICE_PROFILE_ID,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROVENANCE_FIELDS,
    PROVENANCE_PREHASH_FIELDS,
    RAW_BOUNDARY_BLOCKED_RESULT_FIELDS,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    REQUEST_FIELDS,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    SUCCESS_RESULT_FIELDS,
    TASK031_ENVELOPE_FIELDS,
    TASK031_GEOMETRY_FIELDS,
    TASK032_ENVELOPE_FIELDS,
    TASK032_SUCCESS_RESULT_FIELDS,
    TASK032_TYPED_BLOCKED_RESULT_FIELDS,
    TASK033_ENVELOPE_FIELDS,
    TASK033_SUCCESS_RESULT_FIELDS,
    TASK033_TYPED_BLOCKED_RESULT_FIELDS,
    TASK034_ENVELOPE_FIELDS,
    TASK034_SUCCESS_RESULT_FIELDS,
    TASK034_TYPED_BLOCKED_RESULT_FIELDS,
    TYPED_BLOCKED_RESULT_FIELDS,
)

REQUEST_HASH_NAMESPACE = "task035.request.v1"
SUCCESS_RESULT_HASH_NAMESPACE = "task035.success-result.v1"
TYPED_BLOCKED_RESULT_HASH_NAMESPACE = "task035.typed-blocked-result.v1"
RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE = "task035.raw-boundary-blocked-result.v1"
PROVENANCE_NAMESPACE = "task035.provenance.v1"
RAW_PROJECTION_NAMESPACE = "task035.raw-projection.v1"
HASH_ALGORITHM = "SHA-256"
RESULT_ID_NAMESPACE = uuid.UUID("f4a7c7b3-100e-5f54-97e4-678c14fa4044")
RESULT_ID_NAME_PREFIX = "task035-shell-side-thermal-hydraulic-composition-id.v1:"

SUCCESS_PREHASH_FIELDS: tuple[str, ...] = tuple(
    field for field in SUCCESS_RESULT_FIELDS if field not in {"result_hash", "result_id"}
)
TYPED_BLOCKED_PREHASH_FIELDS: tuple[str, ...] = tuple(
    field
    for field in TYPED_BLOCKED_RESULT_FIELDS
    if field not in {"blocked_result_hash", "result_id"}
)
RAW_BOUNDARY_BLOCKED_PREHASH_FIELDS: tuple[str, ...] = tuple(
    field for field in RAW_BOUNDARY_BLOCKED_RESULT_FIELDS if field != "blocked_result_hash"
)


class CanonicalizationError(ValueError):
    """Raised when a value cannot enter the frozen canonical domain."""


def _primitive(value: Any) -> Any:
    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError("non-finite Decimal is not canonical")
        return str(value)
    if isinstance(value, float):
        raise CanonicalizationError("binary floating-point values are forbidden")
    if isinstance(value, Enum):
        return _primitive(value.value)
    if dataclasses.is_dataclass(value):
        return {
            item.name: _primitive(getattr(value, item.name)) for item in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise CanonicalizationError("canonical mapping keys must be strings")
            result[key] = _primitive(item)
        return result
    if isinstance(value, (tuple, list)):
        return [_primitive(item) for item in value]
    if isinstance(value, (set, frozenset)):
        raise CanonicalizationError("unordered collections are not canonical")
    raise CanonicalizationError(f"unsupported canonical value: {type(value).__name__}")


def primitive(value: Any) -> Any:
    """Reduce an accepted public value to JSON-compatible primitives."""

    return _primitive(value)


def canonical_bytes(namespace: str, projection: Any) -> bytes:
    """Encode ``[namespace, projection]`` under the frozen JSON rules."""

    return json.dumps(
        [namespace, _primitive(projection)],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json(value: Any) -> str:
    return json.dumps(
        _primitive(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def hash_projection(namespace: str, projection: Any) -> str:
    return hashlib.sha256(canonical_bytes(namespace, projection)).hexdigest()


def mapping(value: Any) -> dict[str, Any]:
    """Detach a dataclass or mapping into a public structural mapping."""

    reduced = _primitive(value)
    if not isinstance(reduced, dict):
        raise CanonicalizationError("expected a mapping or dataclass")
    return reduced


def pairs_mapping(value: Any) -> dict[str, Any]:
    """Reduce a mapping or ordered pair sequence to a string-keyed mapping."""

    if isinstance(value, Mapping):
        return {key: item for key, item in value.items() if type(key) is str}
    if isinstance(value, (tuple, list)):
        result: dict[str, Any] = {}
        for item in value:
            if isinstance(item, (tuple, list)) and len(item) == 2 and type(item[0]) is str:
                result[item[0]] = item[1]
        return result
    return {}


def _ordered_projection(value: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: value.get(field) for field in fields}


def _geometry_projection(geometry: Mapping[str, Any]) -> dict[str, Any]:
    return _ordered_projection(geometry, TASK031_GEOMETRY_FIELDS)


def task031_envelope_projection(result: Any) -> dict[str, Any]:
    value = mapping(result)
    geometry = value.get("geometry")
    return {
        "status": _primitive(value.get("status")),
        "geometry": None if geometry is None else _geometry_projection(mapping(geometry)),
        "warnings": _primitive(value.get("warnings", [])),
        "blockers": _primitive(value.get("blockers", [])),
        "deferred_capabilities": _primitive(value.get("deferred_capabilities", [])),
        "blocked_result_hash": value.get("blocked_result_hash"),
    }


def _payload_projection(
    value: Any,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    return _ordered_projection(mapping(value), fields)


def task032_envelope_projection(result: Any) -> dict[str, Any]:
    value = mapping(result)
    return {
        "status": _primitive(value.get("status")),
        "flow_state": (
            None
            if value.get("flow_state") is None
            else _payload_projection(value["flow_state"], TASK032_SUCCESS_RESULT_FIELDS)
        ),
        "blocked_result": (
            None
            if value.get("blocked_result") is None
            else _payload_projection(value["blocked_result"], TASK032_TYPED_BLOCKED_RESULT_FIELDS)
        ),
        "raw_boundary_blocked_result": _primitive(value.get("raw_boundary_blocked_result")),
    }


def task033_envelope_projection(result: Any) -> dict[str, Any]:
    value = mapping(result)
    return {
        "status": _primitive(value.get("status")),
        "heat_transfer": (
            None
            if value.get("heat_transfer") is None
            else _payload_projection(value["heat_transfer"], TASK033_SUCCESS_RESULT_FIELDS)
        ),
        "blocked_result": (
            None
            if value.get("blocked_result") is None
            else _payload_projection(value["blocked_result"], TASK033_TYPED_BLOCKED_RESULT_FIELDS)
        ),
        "raw_boundary_blocked_result": _primitive(value.get("raw_boundary_blocked_result")),
    }


def task034_envelope_projection(result: Any) -> dict[str, Any]:
    value = mapping(result)
    return {
        "status": _primitive(value.get("status")),
        "pressure_drop": (
            None
            if value.get("pressure_drop") is None
            else _payload_projection(value["pressure_drop"], TASK034_SUCCESS_RESULT_FIELDS)
        ),
        "blocked_result": (
            None
            if value.get("blocked_result") is None
            else _payload_projection(value["blocked_result"], TASK034_TYPED_BLOCKED_RESULT_FIELDS)
        ),
        "raw_boundary_blocked_result": _primitive(value.get("raw_boundary_blocked_result")),
    }


def producer_envelope_projection(task: str, result: Any) -> dict[str, Any]:
    if task == "TASK031":
        return task031_envelope_projection(result)
    if task == "TASK032":
        return task032_envelope_projection(result)
    if task == "TASK033":
        return task033_envelope_projection(result)
    if task == "TASK034":
        return task034_envelope_projection(result)
    raise CanonicalizationError(f"unknown producer {task}")


def task031_result_projection(result: Any) -> list[Any]:
    value = task031_envelope_projection(result)
    return [value[field] for field in TASK031_ENVELOPE_FIELDS]


def _property_snapshot_projection(snapshot: Mapping[str, Any]) -> list[Any]:
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


def _task031_geometry_hash(geometry: Mapping[str, Any]) -> str:
    provenance = pairs_mapping(geometry.get("provenance", ()))
    freeze_key = (
        "source_authority_freeze_comment_id"
        if "source_authority_freeze_comment_id" in provenance
        else "freeze_comment_id"
    )
    prehash = [
        provenance.get(field)
        for field in (
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
        _primitive(geometry.get("warnings", [])),
        list(geometry.get("deferred_capabilities", [])),
        prehash,
    ]
    return sha256_hex(projection)


def task031_geometry_hash(geometry: Any) -> str:
    return _task031_geometry_hash(mapping(geometry))


def task031_geometry_id(geometry_hash: str) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "urn:hxforge:task031:shell-side-hydraulic-geometry:v1:" + geometry_hash,
        )
    )


def task032_success_projection(flow: Any) -> list[Any]:
    value = mapping(flow)
    fields = tuple(
        field
        for field in TASK032_SUCCESS_RESULT_FIELDS
        if field not in {"result_hash", "result_id"}
    )
    values: dict[str, Any] = {field: value.get(field) for field in fields}
    for field in (
        "shell_side_mass_flow_rate_kg_s",
        "shell_side_mass_velocity_kg_m2_s",
        "shell_side_bulk_velocity_m_s",
        "shell_side_reynolds_number",
        "shell_side_prandtl_number",
    ):
        values[field] = str(value.get(field))
    provenance = pairs_mapping(value.get("provenance", ()))
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
    values["provenance"] = [provenance.get(field) for field in provenance_fields]
    return [_primitive(values[field]) for field in fields]


def task032_success_hash(flow: Any) -> str:
    return sha256_hex(["task032.success-result.v1", task032_success_projection(flow)])


def task032_result_id(result_hash: str) -> str:
    return str(
        uuid.uuid5(
            uuid.UUID("96ab5cf6-204d-547a-9d27-8a5eff46f997"),
            "task032-result-v1::" + result_hash,
        )
    )


def task033_success_hash(result: Any) -> str:
    value = mapping(result)
    fields = tuple(
        field
        for field in TASK033_SUCCESS_RESULT_FIELDS
        if field not in {"result_hash", "result_id"}
    )
    return sha256_hex(
        [
            # TASK033's delivered canonical helper uses its result schema
            # token as the success-hash namespace.
            "task033.shell-side-heat-transfer.v1",
            [_primitive(value.get(field)) for field in fields],
        ]
    )


def task033_result_id(result_hash: str) -> str:
    return str(
        uuid.uuid5(
            uuid.UUID("6d4de79e-3e04-5160-93e4-725c3f308a22"),
            "task033-shell-side-heat-transfer-id.v1:" + result_hash,
        )
    )


def task034_success_hash(result: Any) -> str:
    value = mapping(result)
    fields = tuple(
        field
        for field in TASK034_SUCCESS_RESULT_FIELDS
        if field not in {"result_hash", "result_id"}
    )
    return hash_projection(
        "task034.success-result.v1",
        [_primitive(value.get(field)) for field in fields],
    )


def task034_result_id(result_hash: str) -> str:
    return str(
        uuid.uuid5(
            uuid.UUID("c8f1c1c4-a11b-596b-88ad-6e851a22b9fc"),
            "task034-shell-side-pressure-drop-id.v1:" + result_hash,
        )
    )


def request_canonical_projection(request: Any) -> list[Any]:
    value = mapping(request)
    return [
        value.get("schema_version"),
        value.get("profile_id"),
        task031_envelope_projection(value.get("task031_result")),
        task032_envelope_projection(value.get("task032_result")),
        task033_envelope_projection(value.get("task033_result")),
        task034_envelope_projection(value.get("task034_result")),
        list(value.get("evidence_refs", ())),
    ]


def request_hash(request: Any) -> str:
    return hash_projection(REQUEST_HASH_NAMESPACE, request_canonical_projection(request))


def _fields_projection(value: Any, fields: tuple[str, ...]) -> list[Any]:
    mapping_value = mapping(value)
    return [_primitive(mapping_value.get(field)) for field in fields]


def success_result_canonical_projection(result: Any) -> list[Any]:
    return _fields_projection(result, SUCCESS_PREHASH_FIELDS)


def success_result_hash(result: Any) -> str:
    return hash_projection(
        SUCCESS_RESULT_HASH_NAMESPACE, success_result_canonical_projection(result)
    )


def typed_blocked_result_canonical_projection(result: Any) -> list[Any]:
    return _fields_projection(result, TYPED_BLOCKED_PREHASH_FIELDS)


def typed_blocked_result_hash(result: Any) -> str:
    return hash_projection(
        TYPED_BLOCKED_RESULT_HASH_NAMESPACE,
        typed_blocked_result_canonical_projection(result),
    )


def raw_boundary_blocked_result_canonical_projection(result: Any) -> list[Any]:
    return _fields_projection(result, RAW_BOUNDARY_BLOCKED_PREHASH_FIELDS)


def raw_boundary_blocked_result_hash(result: Any) -> str:
    return hash_projection(
        RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE,
        raw_boundary_blocked_result_canonical_projection(result),
    )


def result_id(result_hash: str) -> str:
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, RESULT_ID_NAME_PREFIX + result_hash))


def provenance_prehash_projection(provenance: Any) -> list[Any]:
    value = pairs_mapping(provenance)
    return [_primitive(value.get(field)) for field in PROVENANCE_PREHASH_FIELDS]


def provenance_hash(provenance: Any) -> str:
    return hash_projection(PROVENANCE_NAMESPACE, provenance_prehash_projection(provenance))


def envelope_fields(task: str) -> tuple[str, ...]:
    return {
        "TASK031": TASK031_ENVELOPE_FIELDS,
        "TASK032": TASK032_ENVELOPE_FIELDS,
        "TASK033": TASK033_ENVELOPE_FIELDS,
        "TASK034": TASK034_ENVELOPE_FIELDS,
    }[task]


__all__ = [
    "BLOCKED_RESULT_SCHEMA_VERSION",
    "CanonicalizationError",
    "FIRST_SLICE_PROFILE_ID",
    "HASH_ALGORITHM",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "PROVENANCE_FIELDS",
    "PROVENANCE_NAMESPACE",
    "PROVENANCE_PREHASH_FIELDS",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION",
    "RAW_PROJECTION_NAMESPACE",
    "REQUEST_FIELDS",
    "REQUEST_HASH_NAMESPACE",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_ID_NAME_PREFIX",
    "RESULT_ID_NAMESPACE",
    "RESULT_SCHEMA_VERSION",
    "SUCCESS_PREHASH_FIELDS",
    "SUCCESS_RESULT_HASH_NAMESPACE",
    "TYPED_BLOCKED_PREHASH_FIELDS",
    "TYPED_BLOCKED_RESULT_HASH_NAMESPACE",
    "canonical_bytes",
    "canonical_json",
    "envelope_fields",
    "hash_projection",
    "mapping",
    "pairs_mapping",
    "primitive",
    "producer_envelope_projection",
    "provenance_hash",
    "provenance_prehash_projection",
    "raw_boundary_blocked_result_canonical_projection",
    "raw_boundary_blocked_result_hash",
    "request_canonical_projection",
    "request_hash",
    "result_id",
    "sha256_hex",
    "success_result_canonical_projection",
    "success_result_hash",
    "task031_envelope_projection",
    "task031_geometry_hash",
    "task031_geometry_id",
    "task031_result_projection",
    "task032_envelope_projection",
    "task032_result_id",
    "task032_success_hash",
    "task032_success_projection",
    "task033_envelope_projection",
    "task033_result_id",
    "task033_success_hash",
    "task034_envelope_projection",
    "task034_result_id",
    "task034_success_hash",
    "typed_blocked_result_canonical_projection",
    "typed_blocked_result_hash",
]
