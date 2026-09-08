"""TASK-166 deterministic content identity.

The repository's TASK-021 canonical JSON primitive is reused as the final
serialization primitive.  This module only supplies TASK-166 domains and
projections; it does not alter the shared framework.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import uuid
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_json

from .authority import (
    BLOCKED_RESULT_SCHEMA_VERSION,
    IMPLEMENTATION_SOFTWARE_VERSION,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
)
from .errors import Blocker

REQUEST_HASH_NAMESPACE = "task166.bell-delaware.request.v1"
RESULT_HASH_NAMESPACE = "task166.bell-delaware.result.v1"
BLOCKED_HASH_NAMESPACE = "task166.bell-delaware.typed-blocked.v1"
RAW_BLOCKED_HASH_NAMESPACE = "task166.bell-delaware.raw-boundary-blocked.v1"
PROVENANCE_HASH_NAMESPACE = "task166.bell-delaware.provenance.v1"
RESULT_ID_NAMESPACE = uuid.UUID("a1660000-0000-5000-8000-000000000166")
RESULT_ID_NAME_PREFIX = "task166-bell-delaware-result-v1::"
BLOCKED_ID_NAMESPACE = uuid.UUID("a1660000-0000-5000-8000-000000000167")
BLOCKED_ID_NAME_PREFIX = "task166-bell-delaware-blocked-v1::"
RAW_BLOCKED_ID_NAMESPACE = uuid.UUID("a1660000-0000-5000-8000-000000000168")
RAW_BLOCKED_ID_NAME_PREFIX = "task166-bell-delaware-raw-blocked-v1::"


def _primitive(value: Any) -> Any:
    """Reduce a trusted result fragment to the repository JSON domain."""
    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal cannot be canonicalized")
        return str(value)
    if isinstance(value, enum.Enum):
        return _primitive(value.value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _primitive(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("canonical mapping keys must be exact strings")
            result[key] = _primitive(item)
        return {key: result[key] for key in sorted(result)}
    if type(value) is tuple or type(value) is list:
        return [_primitive(item) for item in value]
    raise ValueError(f"unsupported canonical value {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(_primitive(value)).encode("utf-8")


def sha256_domain_hex(domain: str, value: Any) -> str:
    return hashlib.sha256(canonical_bytes([domain, value])).hexdigest()


def _blocker_projection(blocker: Blocker) -> list[Any]:
    return [
        blocker.code.value,
        blocker.stage.value,
        blocker.field_path,
        blocker.message,
        list(sorted(blocker.evidence_refs)),
    ]


def evidence_projection(value: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """Extract only stable producer identity fields for result evidence."""
    fields = (
        "schema_version",
        "profile_id",
        "result_id",
        "result_hash",
        "request_hash",
        "geometry_id",
        "geometry_hash",
        "configuration_id",
        "configuration_hash",
        "property_snapshot_hash",
        "engineering_authority_id",
        "engineering_authority_hash",
        "shell_side_case_id",
        "shell_side_stream_id",
        "shell_side_fluid_id",
    )
    pairs: list[tuple[str, str]] = []
    for field in fields:
        value_item = value.get(field)
        if value_item is not None and type(value_item) is str:
            pairs.append((field, value_item))
    return tuple(pairs)


def request_projection(request: Any) -> dict[str, Any]:
    return {
        "schema_version": request.schema_version,
        "task166_version": request.task166_version,
        "source_definition_id": request.source_definition_id,
        "task020_configuration": _primitive(request.task020_configuration),
        "tube_layout": _primitive(request.tube_layout),
        "shell_bundle_geometry": _primitive(request.shell_bundle_geometry),
        "baffle_geometry": _primitive(request.baffle_geometry),
        "shell_side_hydraulic_geometry": _primitive(request.shell_side_hydraulic_geometry),
        "shell_side_flow_state": _primitive(request.shell_side_flow_state),
        "shell_side_flow_state_request": _primitive(request.shell_side_flow_state_request),
        "request_metadata": [list(item) for item in sorted(request.request_metadata)],
    }


def request_hash(request: Any) -> str:
    return sha256_domain_hex(REQUEST_HASH_NAMESPACE, request_projection(request))


def factor_projection(factor: Any) -> dict[str, Any]:
    return {
        "factor_id": factor.factor_id,
        "factor_version": factor.factor_version,
        "source_id": factor.source_id,
        "source_location": factor.source_location,
        "applicability": list(factor.applicability),
        "input_projection": [list(pair) for pair in factor.input_projection],
        "value": str(factor.value),
    }


def result_projection(result: Any, *, include_hashes: bool = False) -> dict[str, Any]:
    geometry = result.bell_geometry
    payload: dict[str, Any] = {
        "schema_version": result.schema_version,
        "task166_version": result.task166_version,
        "implementation_software_version": result.implementation_software_version,
        "source_definition_id": result.source_definition_id,
        "request_hash": result.request_hash,
        "task020_evidence": [list(item) for item in result.task020_evidence],
        "tube_layout_evidence": [list(item) for item in result.tube_layout_evidence],
        "shell_bundle_evidence": [list(item) for item in result.shell_bundle_evidence],
        "baffle_evidence": [list(item) for item in result.baffle_evidence],
        "shell_side_hydraulic_evidence": [
            list(item) for item in result.shell_side_hydraulic_evidence
        ],
        "shell_side_flow_evidence": [list(item) for item in result.shell_side_flow_evidence],
        "bell_geometry": None if geometry is None else _primitive(geometry),
        "ideal_crossflow_heat_transfer_coefficient": str(
            result.ideal_crossflow_heat_transfer_coefficient
        ),
        "j_c": str(result.j_c),
        "j_l": str(result.j_l),
        "j_b": str(result.j_b),
        "j_s": str(result.j_s),
        "j_r": str(result.j_r),
        "corrected_shell_side_heat_transfer_coefficient": str(
            result.corrected_shell_side_heat_transfer_coefficient
        ),
        "ideal_crossflow_pressure_drop": str(result.ideal_crossflow_pressure_drop),
        "crossflow_pressure_drop": str(result.crossflow_pressure_drop),
        "window_pressure_drop": str(result.window_pressure_drop),
        "end_zone_pressure_drop": str(result.end_zone_pressure_drop),
        "central_crossflow_contribution": str(result.central_crossflow_contribution),
        "window_contribution": str(result.window_contribution),
        "entrance_zone_contribution": str(result.entrance_zone_contribution),
        "exit_zone_contribution": str(result.exit_zone_contribution),
        "r_l": str(result.r_l),
        "r_b": str(result.r_b),
        "r_s": str(result.r_s),
        "total_shell_pressure_drop": str(result.total_shell_pressure_drop),
        "heat_transfer_parameter_row_identity": result.heat_transfer_parameter_row_identity,
        "heat_transfer_parameter_source_id": result.heat_transfer_parameter_source_id,
        "heat_transfer_a1": str(result.heat_transfer_a1),
        "heat_transfer_a2": str(result.heat_transfer_a2),
        "heat_transfer_a3": str(result.heat_transfer_a3),
        "heat_transfer_a4": str(result.heat_transfer_a4),
        "pressure_drop_parameter_row_identity": result.pressure_drop_parameter_row_identity,
        "pressure_drop_parameter_source_id": result.pressure_drop_parameter_source_id,
        "pressure_drop_b1": str(result.pressure_drop_b1),
        "pressure_drop_b2": str(result.pressure_drop_b2),
        "pressure_drop_b3": str(result.pressure_drop_b3),
        "pressure_drop_b4": str(result.pressure_drop_b4),
        "factor_evidence": [factor_projection(item) for item in result.factor_evidence],
        "applicability": _primitive(result.applicability),
        "completeness": _primitive(result.completeness),
        "warnings": list(result.warnings),
        "blockers": [_blocker_projection(item) for item in result.blockers],
        "provenance_semantic_inputs": [list(item) for item in result.provenance_semantic_inputs],
    }
    if include_hashes:
        payload["provenance"] = _primitive(result.provenance)
        payload["result_hash"] = result.result_hash
        payload["result_id"] = result.result_id
    return payload


def result_hash(result: Any) -> str:
    return sha256_domain_hex(RESULT_HASH_NAMESPACE, result_projection(result))


def result_id(hash_value: str) -> str:
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, RESULT_ID_NAME_PREFIX + hash_value))


def blocked_projection(result: Any) -> dict[str, Any]:
    return {
        "schema_version": result.schema_version,
        "task166_version": result.task166_version,
        "implementation_software_version": result.implementation_software_version,
        "failure_stage": result.failure_stage.value,
        "request_hash": result.request_hash,
        "blockers": [_blocker_projection(item) for item in result.blockers],
        "warnings": list(result.warnings),
    }


def blocked_hash(result: Any) -> str:
    return sha256_domain_hex(BLOCKED_HASH_NAMESPACE, blocked_projection(result))


def blocked_id(hash_value: str) -> str:
    return str(uuid.uuid5(BLOCKED_ID_NAMESPACE, BLOCKED_ID_NAME_PREFIX + hash_value))


def raw_blocked_projection(result: Any) -> dict[str, Any]:
    return {
        "schema_version": result.schema_version,
        "task166_version": result.task166_version,
        "implementation_software_version": result.implementation_software_version,
        "raw_request_projection_hash": result.raw_request_projection_hash,
        "blockers": [_blocker_projection(item) for item in result.blockers],
        "warnings": list(result.warnings),
    }


def raw_blocked_hash(result: Any) -> str:
    return sha256_domain_hex(RAW_BLOCKED_HASH_NAMESPACE, raw_blocked_projection(result))


def raw_blocked_id(hash_value: str) -> str:
    return str(uuid.uuid5(RAW_BLOCKED_ID_NAMESPACE, RAW_BLOCKED_ID_NAME_PREFIX + hash_value))


def provenance_hash(payload: Any) -> str:
    return sha256_domain_hex(PROVENANCE_HASH_NAMESPACE, payload)


__all__ = [
    "BLOCKED_ID_NAMESPACE",
    "BLOCKED_ID_NAME_PREFIX",
    "BLOCKED_RESULT_SCHEMA_VERSION",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "PROVENANCE_HASH_NAMESPACE",
    "RAW_BLOCKED_ID_NAMESPACE",
    "RAW_BLOCKED_ID_NAME_PREFIX",
    "RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION",
    "REQUEST_HASH_NAMESPACE",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_HASH_NAMESPACE",
    "RESULT_ID_NAMESPACE",
    "RESULT_ID_NAME_PREFIX",
    "RESULT_SCHEMA_VERSION",
    "blocked_hash",
    "blocked_id",
    "canonical_bytes",
    "evidence_projection",
    "factor_projection",
    "provenance_hash",
    "raw_blocked_hash",
    "raw_blocked_id",
    "request_hash",
    "request_projection",
    "result_hash",
    "result_id",
    "result_projection",
    "sha256_domain_hex",
]
