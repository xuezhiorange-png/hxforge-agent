"""Fail-closed, projection-only TASK-035 validation pipeline."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .blocker_registry import make_blocker
from .canonical import (
    CanonicalizationError,
    canonical_json,
    mapping,
    primitive,
    raw_boundary_blocked_result_hash,
    request_hash,
    result_id,
    success_result_hash,
    task031_geometry_hash,
    task031_geometry_id,
    task032_result_id,
    task032_success_hash,
    task033_result_id,
    task033_success_hash,
    task034_result_id,
    task034_success_hash,
    typed_blocked_result_hash,
)
from .models import (
    Task035RawBoundaryBlockedResult,
    Task035Request,
    Task035SuccessResult,
    Task035TypedBlockedResult,
    Task035ValidationResult,
    ValidationStatus,
)
from .provenance import build_provenance
from .raw_projection import project_raw_request
from .schema import (
    APPLICABILITY_LEDGER_FIELDS,
    APPLICABILITY_PROFILE_ID,
    BLOCKED_RESULT_SCHEMA_VERSION,
    COMPLETENESS_CLASSIFICATION_UNIVERSE,
    COMPLETENESS_PROFILE_ID,
    DEFERRED_CAPABILITIES,
    FIRST_SLICE_PROFILE_ID,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROFILE_ID,
    PROVENANCE_FIELDS,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    REQUEST_FIELDS,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
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
)
from .warning_registry import all_warnings

_MISSING = object()
_HASH_LENGTH = 64

_TASK031_RESULT_SCHEMA = "task031.shell-side-hydraulic-geometry.v1"
_TASK032_RESULT_SCHEMA = "task032.shell-side-flow-state.v1"
_TASK032_BLOCKED_SCHEMA = "task032.shell-side-flow-state-blocked.v1"
_TASK032_RAW_SCHEMA = "task032.shell-side-flow-state-raw-boundary-blocked.v1"
_TASK033_RESULT_SCHEMA = "task033.shell-side-heat-transfer.v1"
_TASK033_BLOCKED_SCHEMA = "task033.shell-side-heat-transfer-blocked.v1"
_TASK033_RAW_SCHEMA = "task033.shell-side-heat-transfer-raw-boundary-blocked.v1"
_TASK034_RESULT_SCHEMA = "task034.shell-side-pressure-drop-success.v1"
_TASK034_BLOCKED_SCHEMA = "task034.shell-side-pressure-drop-blocked.v1"
_TASK034_RAW_SCHEMA = "task034.shell-side-pressure-drop-raw-boundary-blocked.v1"

_TASK032_FLOW_PROFILE = "hxforge.shell_tube.shell_side_flow_state.v1"
_TASK032_FIRST_SLICE_PROFILE = "SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1"
_TASK032_FLOW_MODEL = "SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING"
_TASK033_PROFILE = "hxforge.shell_tube.shell_side_heat_transfer.v1"
_TASK033_FIRST_SLICE_PROFILE = (
    "SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_KERN_KHARAJI_2021_EQ58_OUTER_TUBE_SURFACE_HTC_SCREENING_V1"
)
_TASK033_CORRELATION = "TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1"
_TASK034_PROFILE = "hxforge.shell_tube.shell_side_pressure_drop.v1"
_TASK034_FIRST_SLICE_PROFILE = (
    "TASK034_KERN_BAYRAM_SEVILGEN_2017_EQ15_EQ16_EQ17_WALL_VISCOSITY_CORRECTION_V1"
)
_TASK034_CORRELATION = _TASK034_FIRST_SLICE_PROFILE
_DECIMAL_SUCCESS_FIELDS: dict[str, frozenset[str]] = {
    _TASK032_RESULT_SCHEMA: frozenset(
        {
            "shell_side_mass_flow_rate_kg_s",
            "shell_side_mass_velocity_kg_m2_s",
            "shell_side_bulk_velocity_m_s",
            "shell_side_reynolds_number",
            "shell_side_prandtl_number",
        }
    ),
    _TASK033_RESULT_SCHEMA: frozenset({"modeled_shell_side_heat_transfer_coefficient_w_m2_k"}),
    _TASK034_RESULT_SCHEMA: frozenset({"modeled_shell_side_pressure_drop_pa"}),
}


@dataclass(frozen=True)
class _Accepted:
    """Producer projections accepted by the stages reached so far."""

    task031: dict[str, Any] | None = None
    task032: dict[str, Any] | None = None
    task033: dict[str, Any] | None = None
    task034: dict[str, Any] | None = None


def _as_mapping(value: Any) -> dict[str, Any] | None:
    try:
        return mapping(value)
    except CanonicalizationError:
        return None


def _status(value: Any) -> str | None:
    if type(value) is str:
        return value
    return None


def _exact_fields(value: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return set(value) == set(fields) and all(type(key) is str for key in value)


def _sequence(value: Any) -> bool:
    return isinstance(value, list)


def _messages(value: Any, *, blockers: bool, require_stage: bool = False) -> bool:
    if not _sequence(value):
        return False
    for item in value:
        record = _as_mapping(item)
        if record is None or type(record.get("code")) is not str:
            return False
        if blockers and require_stage and type(record.get("stage")) is not str:
            return False
    return True


def _pairs(value: Any) -> bool:
    if not _sequence(value):
        return False
    for item in value:
        if not isinstance(item, list) or len(item) != 2 or type(item[0]) is not str:
            return False
    return True


def _hash(value: Any) -> bool:
    if type(value) is not str or len(value) != _HASH_LENGTH:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _nonempty_text(value: Any) -> bool:
    return type(value) is str and bool(value)


def _valid_sequence_of_strings(value: Any) -> bool:
    return _sequence(value) and all(type(item) is str for item in value)


def _valid_geometry(value: Any) -> bool:
    geometry = _as_mapping(value)
    if geometry is None or not _exact_fields(geometry, TASK031_GEOMETRY_FIELDS):
        return False
    if geometry.get("schema_version") != _TASK031_RESULT_SCHEMA:
        return False
    for field in (
        "geometry_id",
        "geometry_hash",
        "request_hash",
        "task020_configuration_id",
        "task020_configuration_hash",
        "task021_layout_id",
        "task021_layout_hash",
        "task022_geometry_id",
        "task022_geometry_hash",
        "task024_geometry_id",
        "task024_geometry_hash",
        "engineering_authority_id",
        "engineering_authority_hash",
        "formula_a_id",
        "formula_b_id",
        "pattern_family",
        "flow_region_identity",
        "central_inter_baffle_spacing_m",
        "central_crossflow_flow_area_m2",
        "shell_side_equivalent_hydraulic_diameter_m",
    ):
        if not _nonempty_text(geometry.get(field)):
            return False
    return (
        _messages(geometry.get("warnings"), blockers=False)
        and _messages(geometry.get("blockers"), blockers=True)
        and _valid_sequence_of_strings(geometry.get("deferred_capabilities"))
        and _pairs(geometry.get("provenance"))
    )


def _valid_success(value: Any, fields: tuple[str, ...], schema: str) -> dict[str, Any] | None:
    payload = _as_mapping(value)
    if payload is None or not _exact_fields(payload, fields):
        return None
    if payload.get("schema_version") != schema or not _nonempty_text(payload.get("profile_id")):
        return None
    if not _nonempty_text(payload.get("implementation_software_version")):
        return None
    if not _messages(payload.get("warnings"), blockers=False):
        return None
    if not _messages(payload.get("blockers"), blockers=True):
        return None
    if payload.get("blockers"):
        return None
    if not _valid_sequence_of_strings(payload.get("deferred_capabilities")):
        return None
    if not _pairs(payload.get("provenance")):
        return None
    structured_fields = {
        "warnings",
        "blockers",
        "deferred_capabilities",
        "provenance",
        "applicability_context",
        "physical_boundary_context",
    }
    decimal_fields = _DECIMAL_SUCCESS_FIELDS.get(schema, frozenset())
    for field in fields:
        if field in structured_fields:
            continue
        if field in decimal_fields:
            value_at_field = payload.get(field)
            if not isinstance(value_at_field, Decimal) or not value_at_field.is_finite():
                return None
        elif not _nonempty_text(payload.get(field)):
            return None
    for field in ("applicability_context", "physical_boundary_context"):
        if field in fields and _pair_dict(payload.get(field)) is None:
            return None
    return payload


def _valid_typed_blocked(
    value: Any,
    fields: tuple[str, ...],
    schema: str,
    hash_field: str,
) -> dict[str, Any] | None:
    payload = _as_mapping(value)
    if payload is None or not _exact_fields(payload, fields):
        return None
    if payload.get("schema_version") != schema or not _nonempty_text(payload.get("profile_id")):
        return None
    if not _nonempty_text(payload.get("implementation_software_version")):
        return None
    if not _nonempty_text(payload.get("failure_stage")):
        return None
    if not _messages(payload.get("blockers"), blockers=True) or not payload.get("blockers"):
        return None
    if not _messages(payload.get("warnings"), blockers=False):
        return None
    if not _valid_sequence_of_strings(payload.get("deferred_capabilities")):
        return None
    if not _pairs(payload.get("provenance")) or not _hash(payload.get(hash_field)):
        return None
    structured_fields = {"blockers", "warnings", "deferred_capabilities", "provenance"}
    for field in fields:
        if field in structured_fields or field in {"schema_version", "profile_id", "failure_stage"}:
            continue
        value_at_field = payload.get(field)
        if value_at_field is not None and type(value_at_field) is not str:
            return None
    return payload


def _valid_raw_blocked(
    value: Any,
    fields: tuple[str, ...],
    schema: str,
    projection_field: str,
) -> dict[str, Any] | None:
    payload = _as_mapping(value)
    if payload is None or not _exact_fields(payload, fields):
        return None
    if payload.get("schema_version") != schema or not _nonempty_text(payload.get("profile_id")):
        return None
    if not _hash(payload.get("blocked_result_hash")):
        return None
    if not _messages(payload.get("blockers"), blockers=True) or not payload.get("blockers"):
        return None
    if not _messages(payload.get("warnings"), blockers=False):
        return None
    if not _valid_sequence_of_strings(payload.get("deferred_capabilities")):
        return None
    return payload if payload.get(projection_field) is not None else None


def _validate_task031(value: Any) -> tuple[str, dict[str, Any] | None]:
    if value is None:
        return "missing", None
    envelope = _as_mapping(value)
    if envelope is None or not _exact_fields(envelope, TASK031_ENVELOPE_FIELDS):
        return "invalid", None
    status = _status(envelope.get("status"))
    if status not in {"VALID", "BLOCKED"}:
        return "invalid", None
    if not _messages(envelope.get("warnings"), blockers=False):
        return "invalid", None
    if not _messages(envelope.get("blockers"), blockers=True):
        return "invalid", None
    if not _valid_sequence_of_strings(envelope.get("deferred_capabilities")):
        return "invalid", None
    geometry = envelope.get("geometry")
    if status == "VALID":
        if envelope.get("blocked_result_hash") is not None or envelope.get("blockers"):
            return "invalid", None
        if not _valid_geometry(geometry):
            return "invalid", None
        return "success", envelope
    if geometry is not None or not envelope.get("blockers"):
        return "invalid", None
    if not _hash(envelope.get("blocked_result_hash")):
        return "invalid", None
    return "blocked", envelope


def _validate_producer(
    value: Any,
    *,
    envelope_fields: tuple[str, ...],
    success_field: str,
    success_fields: tuple[str, ...],
    success_schema: str,
    blocked_fields: tuple[str, ...],
    blocked_schema: str,
    raw_fields: tuple[str, ...],
    raw_schema: str,
    raw_projection_field: str,
) -> tuple[str, dict[str, Any] | None]:
    if value is None:
        return "missing", None
    envelope = _as_mapping(value)
    if envelope is None or not _exact_fields(envelope, envelope_fields):
        return "invalid", None
    status = _status(envelope.get("status"))
    if status not in {"VALID", "BLOCKED"}:
        return "invalid", None
    success = envelope.get(success_field)
    blocked = envelope.get("blocked_result")
    raw_blocked = envelope.get("raw_boundary_blocked_result")
    if status == "VALID":
        if success is None or blocked is not None or raw_blocked is not None:
            return "invalid", None
        payload = _valid_success(success, success_fields, success_schema)
        return ("success", payload) if payload is not None else ("invalid", None)
    if success is not None:
        return "invalid", None
    selected = (blocked is not None) + (raw_blocked is not None)
    if selected != 1:
        return "invalid", None
    if blocked is not None:
        blocked_hash_field = (
            "result_hash" if "result_hash" in blocked_fields else "blocked_result_hash"
        )
        payload = _valid_typed_blocked(blocked, blocked_fields, blocked_schema, blocked_hash_field)
        return ("blocked", payload) if payload is not None else ("invalid", None)
    payload = _valid_raw_blocked(raw_blocked, raw_fields, raw_schema, raw_projection_field)
    return ("blocked", payload) if payload is not None else ("invalid", None)


def _valid_evidence_refs(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(type(item) is str and bool(item) for item in value)
        and len(value) == len(set(value))
    )


def _request_from_raw(raw_request: dict[str, Any]) -> Task035Request:
    return Task035Request(
        schema_version=raw_request.get("schema_version", ""),
        profile_id=raw_request.get("profile_id", ""),
        task031_result=raw_request.get("task031_result"),
        task032_result=raw_request.get("task032_result"),
        task033_result=raw_request.get("task033_result"),
        task034_result=raw_request.get("task034_result"),
        evidence_refs=tuple(raw_request.get("evidence_refs", [])),
    )


def parse_request(raw_request: Any) -> Task035Request:
    """Parse only the exact seven-field TASK035 request shape."""

    if type(raw_request) is not dict:
        raise ValueError("S01")
    if set(raw_request) - set(REQUEST_FIELDS):
        raise ValueError("S01_UNKNOWN")
    if not _valid_evidence_refs(raw_request.get("evidence_refs")):
        raise ValueError("S01_EVIDENCE")
    if raw_request.get("schema_version") != REQUEST_SCHEMA_VERSION:
        raise ValueError("S02_SCHEMA")
    if raw_request.get("profile_id") != PROFILE_ID:
        raise ValueError("S02_PROFILE")
    missing = [field for field in REQUEST_FIELDS if field not in raw_request]
    if missing:
        raise ValueError("S02_REQUIRED")
    return _request_from_raw(raw_request)


def _raw_blocked(
    raw_request: Any,
    code: str,
    field_path: str | None = None,
) -> Task035ValidationResult:
    blocker = make_blocker(code, field_path=field_path)
    provisional = Task035RawBoundaryBlockedResult(
        schema_version=RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        raw_request_projection=project_raw_request(raw_request),
        blocked_result_hash="",
        blockers=(blocker,),
        warnings=all_warnings(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
    )
    digest = raw_boundary_blocked_result_hash(provisional)
    blocked = Task035RawBoundaryBlockedResult(
        schema_version=provisional.schema_version,
        profile_id=provisional.profile_id,
        implementation_software_version=provisional.implementation_software_version,
        raw_request_projection=provisional.raw_request_projection,
        blocked_result_hash=digest,
        blockers=provisional.blockers,
        warnings=provisional.warnings,
        deferred_capabilities=provisional.deferred_capabilities,
    )
    return Task035ValidationResult(ValidationStatus.BLOCKED, None, None, blocked)


def _level(stage: str) -> int:
    number = int(stage[1:])
    if number <= 4:
        return 0
    if number <= 6:
        return 1
    if number <= 8:
        return 2
    if number <= 10:
        return 3
    return 4


def _geometry(accepted: _Accepted) -> dict[str, Any] | None:
    if accepted.task031 is None:
        return None
    value = accepted.task031.get("geometry")
    return value if isinstance(value, dict) else None


def _flow(accepted: _Accepted) -> dict[str, Any] | None:
    return None if accepted.task032 is None else accepted.task032


def _heat(accepted: _Accepted) -> dict[str, Any] | None:
    return None if accepted.task033 is None else accepted.task033


def _pressure(accepted: _Accepted) -> dict[str, Any] | None:
    return None if accepted.task034 is None else accepted.task034


def _provenance_values(request: Task035Request, accepted: _Accepted, stage: str) -> dict[str, Any]:
    level = _level(stage)
    geometry = _geometry(accepted) if level >= 1 else None
    flow = _flow(accepted) if level >= 2 else None
    heat = _heat(accepted) if level >= 3 else None
    pressure = _pressure(accepted) if level >= 4 else None
    return {
        "task_id": "TASK035",
        "profile_id": PROFILE_ID,
        "first_slice_profile_id": FIRST_SLICE_PROFILE_ID,
        "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
        "request_hash": None,
        "task031_request_hash": None if geometry is None else geometry.get("request_hash"),
        "task031_geometry_hash": None if geometry is None else geometry.get("geometry_hash"),
        "task031_geometry_id": None if geometry is None else geometry.get("geometry_id"),
        "task021_layout_hash": None if geometry is None else geometry.get("task021_layout_hash"),
        "task021_layout_id": None if geometry is None else geometry.get("task021_layout_id"),
        "task024_geometry_hash": (
            None if geometry is None else geometry.get("task024_geometry_hash")
        ),
        "task024_geometry_id": None if geometry is None else geometry.get("task024_geometry_id"),
        "task032_request_hash": None if flow is None else flow.get("request_hash"),
        "task032_result_hash": None if flow is None else flow.get("result_hash"),
        "task032_result_id": None if flow is None else flow.get("result_id"),
        "task033_request_hash": None if heat is None else heat.get("request_hash"),
        "task033_result_hash": None if heat is None else heat.get("result_hash"),
        "task033_result_id": None if heat is None else heat.get("result_id"),
        "task033_correlation_id": None if heat is None else heat.get("correlation_id"),
        "task034_request_hash": None if pressure is None else pressure.get("request_hash"),
        "task034_result_hash": None if pressure is None else pressure.get("result_hash"),
        "task034_result_id": None if pressure is None else pressure.get("result_id"),
        "task034_correlation_id": None if pressure is None else pressure.get("correlation_id"),
        "task020_configuration_hash": (
            None if geometry is None else geometry.get("task020_configuration_hash")
        ),
        "task020_configuration_id": (
            None if geometry is None else geometry.get("task020_configuration_id")
        ),
        "property_snapshot_hash": None if flow is None else flow.get("property_snapshot_hash"),
        "mass_flow_authority_hash": (
            None if flow is None else flow.get("mass_flow_authority_hash")
        ),
        "applicability_profile_id": APPLICABILITY_PROFILE_ID,
        "completeness_profile_id": COMPLETENESS_PROFILE_ID,
        "warnings": all_warnings(),
        "deferred_capabilities": DEFERRED_CAPABILITIES,
        "evidence_refs": request.evidence_refs,
        "source_definition_issue": 201,
    }


def _make_typed_blocked(
    request: Task035Request,
    stage: str,
    code: str,
    accepted: _Accepted,
    *,
    field_path: str | None = None,
) -> Task035ValidationResult:
    level = _level(stage)
    geometry = _geometry(accepted) if level >= 1 else None
    flow = _flow(accepted) if level >= 2 else None
    heat = _heat(accepted) if level >= 3 else None
    pressure = _pressure(accepted) if level >= 4 else None
    try:
        request_hash_value = request_hash(request)
    except CanonicalizationError:
        request_hash_value = None
    values = _provenance_values(request, accepted, stage)
    values["request_hash"] = request_hash_value
    try:
        provenance = build_provenance(values)
    except CanonicalizationError:
        provenance = tuple((field, None) for field in PROVENANCE_FIELDS[:-1]) + (
            ("provenance_hash", ""),
        )
    blocker = make_blocker(code, stage=stage, field_path=field_path)
    provisional = Task035TypedBlockedResult(
        schema_version=BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=stage,
        shell_side_case_id=None if flow is None else flow.get("shell_side_case_id"),
        shell_side_stream_id=None if flow is None else flow.get("shell_side_stream_id"),
        shell_side_fluid_id=None if flow is None else flow.get("shell_side_fluid_id"),
        task031_geometry_id=None if geometry is None else geometry.get("geometry_id"),
        task031_geometry_hash=None if geometry is None else geometry.get("geometry_hash"),
        task032_request_hash=None if flow is None else flow.get("request_hash"),
        task032_result_hash=None if flow is None else flow.get("result_hash"),
        task032_result_id=None if flow is None else flow.get("result_id"),
        task033_result_hash=None if heat is None else heat.get("result_hash"),
        task033_result_id=None if heat is None else heat.get("result_id"),
        task034_result_hash=None if pressure is None else pressure.get("result_hash"),
        task034_result_id=None if pressure is None else pressure.get("result_id"),
        property_snapshot_hash=None if flow is None else flow.get("property_snapshot_hash"),
        mass_flow_authority_hash=None if flow is None else flow.get("mass_flow_authority_hash"),
        request_hash=request_hash_value,
        blocked_result_hash="",
        result_id="",
        blockers=(blocker,),
        warnings=all_warnings(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        provenance=provenance,
    )
    try:
        digest = typed_blocked_result_hash(provisional)
        blocked_id = result_id(digest)
    except CanonicalizationError:
        fallback = tuple((field, None) for field in PROVENANCE_FIELDS[:-1]) + (
            ("provenance_hash", ""),
        )
        digest = typed_blocked_result_hash(
            Task035TypedBlockedResult(
                **{**provisional.__dict__, "provenance": fallback},
            )
        )
        blocked_id = result_id(digest)
    blocked = Task035TypedBlockedResult(
        **{**provisional.__dict__, "blocked_result_hash": digest, "result_id": blocked_id}
    )
    return Task035ValidationResult(ValidationStatus.BLOCKED, None, blocked, None)


def _bad(
    request: Task035Request,
    stage: str,
    code: str,
    accepted: _Accepted,
    *,
    field_path: str | None = None,
) -> Task035ValidationResult:
    return _make_typed_blocked(request, stage, code, accepted, field_path=field_path)


def _identity_task031(geometry: dict[str, Any]) -> bool:
    try:
        calculated_hash = task031_geometry_hash(geometry)
    except CanonicalizationError:
        return False
    return (
        _hash(geometry.get("request_hash"))
        and geometry.get("geometry_hash") == calculated_hash
        and geometry.get("geometry_id") == task031_geometry_id(calculated_hash)
    )


def _identity_task032(flow: dict[str, Any], geometry: dict[str, Any]) -> bool:
    try:
        calculated_hash = task032_success_hash(flow)
    except CanonicalizationError:
        return False
    return (
        _hash(flow.get("request_hash"))
        and flow.get("result_hash") == calculated_hash
        and flow.get("result_id") == task032_result_id(calculated_hash)
        and flow.get("task031_geometry_id") == geometry.get("geometry_id")
        and flow.get("task031_geometry_hash") == geometry.get("geometry_hash")
    )


def _identity_task033(heat: dict[str, Any], flow: dict[str, Any], geometry: dict[str, Any]) -> bool:
    try:
        calculated_hash = task033_success_hash(heat)
    except CanonicalizationError:
        return False
    return (
        _hash(heat.get("request_hash"))
        and heat.get("result_hash") == calculated_hash
        and heat.get("result_id") == task033_result_id(calculated_hash)
        and heat.get("task032_request_hash") == flow.get("request_hash")
        and heat.get("task032_result_hash") == flow.get("result_hash")
        and heat.get("task032_result_id") == flow.get("result_id")
        and heat.get("task031_geometry_id") == geometry.get("geometry_id")
        and heat.get("task031_geometry_hash") == geometry.get("geometry_hash")
    )


def _identity_task034(
    pressure: dict[str, Any],
    heat: dict[str, Any],
    flow: dict[str, Any],
    geometry: dict[str, Any],
) -> bool:
    try:
        calculated_hash = task034_success_hash(pressure)
    except CanonicalizationError:
        return False
    return (
        _hash(pressure.get("request_hash"))
        and pressure.get("result_hash") == calculated_hash
        and pressure.get("result_id") == task034_result_id(calculated_hash)
        and pressure.get("task033_request_hash") == heat.get("request_hash")
        and pressure.get("task033_result_hash") == heat.get("result_hash")
        and pressure.get("task033_result_id") == heat.get("result_id")
        and pressure.get("task032_request_hash") == flow.get("request_hash")
        and pressure.get("task032_result_hash") == flow.get("result_hash")
        and pressure.get("task032_result_id") == flow.get("result_id")
        and pressure.get("task031_request_hash") == geometry.get("request_hash")
        and pressure.get("task031_geometry_id") == geometry.get("geometry_id")
        and pressure.get("task031_geometry_hash") == geometry.get("geometry_hash")
    )


def _same(values: list[Any]) -> bool:
    if not values:
        return True
    try:
        first = canonical_json(primitive(values[0]))
        return all(canonical_json(primitive(value)) == first for value in values[1:])
    except CanonicalizationError:
        return False


def _configuration_joins(accepted: _Accepted) -> str | None:
    geometry = _geometry(accepted)
    flow = _flow(accepted)
    heat = _heat(accepted)
    pressure = _pressure(accepted)
    if geometry is None or flow is None or heat is None or pressure is None:
        return "SSTHC_CONFIGURATION_MISMATCH"
    if not _same(
        [
            geometry.get("task020_configuration_id"),
            flow.get("task020_configuration_id"),
            heat.get("task020_configuration_id"),
            pressure.get("task020_configuration_id"),
        ]
    ) or not _same(
        [
            geometry.get("task020_configuration_hash"),
            flow.get("task020_configuration_hash"),
            heat.get("task020_configuration_hash"),
            pressure.get("task020_configuration_hash"),
        ]
    ):
        return "SSTHC_CONFIGURATION_MISMATCH"
    if not _nonempty_text(geometry.get("task021_layout_id")) or not _hash(
        geometry.get("task021_layout_hash")
    ):
        return "SSTHC_TASK021_LAYOUT_MISMATCH"
    if not _nonempty_text(geometry.get("task024_geometry_id")) or not _hash(
        geometry.get("task024_geometry_hash")
    ):
        return "SSTHC_TASK024_GEOMETRY_MISMATCH"
    if not _same(
        [
            geometry.get("geometry_id"),
            flow.get("task031_geometry_id"),
            heat.get("task031_geometry_id"),
            pressure.get("task031_geometry_id"),
        ]
    ) or not _same(
        [
            geometry.get("geometry_hash"),
            flow.get("task031_geometry_hash"),
            heat.get("task031_geometry_hash"),
            pressure.get("task031_geometry_hash"),
        ]
    ):
        return "SSTHC_TASK031_GEOMETRY_MISMATCH"
    return None


def _pair_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        reduced = _as_mapping(value)
        return reduced
    if not _sequence(value):
        return None
    result: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, list) or len(item) != 2 or type(item[0]) is not str:
            return None
        if item[0] in result:
            return None
        result[item[0]] = item[1]
    return result


def _applicability_ledger(accepted: _Accepted) -> tuple[tuple[str, Any], ...] | None:
    geometry = _geometry(accepted)
    flow = _flow(accepted)
    heat = _heat(accepted)
    pressure = _pressure(accepted)
    if geometry is None or flow is None or heat is None or pressure is None:
        return None
    heat_context = _pair_dict(heat.get("applicability_context"))
    pressure_context = _pair_dict(pressure.get("applicability_context"))
    physical_context = _pair_dict(pressure.get("physical_boundary_context"))
    if heat_context is None or pressure_context is None or physical_context is None:
        return None
    for key in sorted(set(heat_context) & set(pressure_context)):
        if not _same([heat_context[key], pressure_context[key]]):
            return None
    case_values = [
        flow.get("shell_side_case_id"),
        heat.get("shell_side_case_id"),
        pressure.get("shell_side_case_id"),
    ]
    task031_profile = (
        _TASK031_RESULT_SCHEMA,
        geometry.get("pattern_family"),
        geometry.get("flow_region_identity"),
        geometry.get("engineering_authority_id"),
        geometry.get("engineering_authority_hash"),
    )
    task032_profile = (
        flow.get("profile_id"),
        flow.get("flow_model"),
        flow.get("phase_region"),
        flow.get("rheology_model"),
        flow.get("engineering_authority_id"),
        flow.get("engineering_authority_hash"),
    )
    task033_profile = (
        heat.get("profile_id"),
        heat.get("first_slice_profile_id"),
        heat.get("correlation_id"),
        heat.get("heat_transfer_surface"),
        tuple(sorted(heat_context.items())),
    )
    task034_profile = (
        pressure.get("profile_id"),
        pressure.get("first_slice_profile_id"),
        pressure.get("correlation_id"),
        tuple(sorted(pressure_context.items())),
        tuple(sorted(physical_context.items())),
    )
    return (
        (APPLICABILITY_LEDGER_FIELDS[0], task031_profile),
        (APPLICABILITY_LEDGER_FIELDS[1], task032_profile),
        (APPLICABILITY_LEDGER_FIELDS[2], task033_profile),
        (APPLICABILITY_LEDGER_FIELDS[3], task034_profile),
        (APPLICABILITY_LEDGER_FIELDS[4], tuple(case_values)),
        (
            APPLICABILITY_LEDGER_FIELDS[5],
            (geometry.get("task020_configuration_id"), geometry.get("task020_configuration_hash")),
        ),
        (
            APPLICABILITY_LEDGER_FIELDS[6],
            (geometry.get("geometry_id"), geometry.get("geometry_hash")),
        ),
        (APPLICABILITY_LEDGER_FIELDS[7], flow.get("property_snapshot_hash")),
        (APPLICABILITY_LEDGER_FIELDS[8], flow.get("mass_flow_authority_hash")),
        (APPLICABILITY_LEDGER_FIELDS[9], "SUPPORTED"),
    )


def _completeness_ledger() -> tuple[tuple[str, Any], ...]:
    return (
        ("classification_universe", COMPLETENESS_CLASSIFICATION_UNIVERSE),
        (
            "required_producers",
            (
                ("TASK031", "DELIVERED_AND_PRESENT"),
                ("TASK032", "DELIVERED_AND_PRESENT"),
                ("TASK033", "DELIVERED_AND_PRESENT"),
                ("TASK034", "DELIVERED_AND_PRESENT"),
            ),
        ),
        ("success_admissibility", "ALL_REQUIRED_PRODUCERS_DELIVERED_AND_PRESENT"),
        ("deferred_capabilities", DEFERRED_CAPABILITIES),
        ("applicability_profile_id", APPLICABILITY_PROFILE_ID),
        ("completeness_profile_id", COMPLETENESS_PROFILE_ID),
    )


def _compose_success_payload(request: Task035Request, accepted: _Accepted) -> Task035SuccessResult:
    geometry = _geometry(accepted)
    flow = _flow(accepted)
    heat = _heat(accepted)
    pressure = _pressure(accepted)
    assert geometry is not None and flow is not None and heat is not None and pressure is not None
    applicability = _applicability_ledger(accepted)
    if applicability is None:
        raise CanonicalizationError("applicability ledger unavailable")
    completeness = _completeness_ledger()
    request_hash_value = request_hash(request)
    values: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "first_slice_profile_id": FIRST_SLICE_PROFILE_ID,
        "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
        "shell_side_case_id": flow.get("shell_side_case_id"),
        "shell_side_stream_id": flow.get("shell_side_stream_id"),
        "shell_side_fluid_id": flow.get("shell_side_fluid_id"),
        "task020_configuration_id": flow.get("task020_configuration_id"),
        "task020_configuration_hash": flow.get("task020_configuration_hash"),
        "task021_layout_id": geometry.get("task021_layout_id"),
        "task021_layout_hash": geometry.get("task021_layout_hash"),
        "task024_geometry_id": geometry.get("task024_geometry_id"),
        "task024_geometry_hash": geometry.get("task024_geometry_hash"),
        "task031_request_hash": geometry.get("request_hash"),
        "task031_geometry_id": geometry.get("geometry_id"),
        "task031_geometry_hash": geometry.get("geometry_hash"),
        "task032_request_hash": flow.get("request_hash"),
        "task032_result_hash": flow.get("result_hash"),
        "task032_result_id": flow.get("result_id"),
        "task033_request_hash": heat.get("request_hash"),
        "task033_result_hash": heat.get("result_hash"),
        "task033_result_id": heat.get("result_id"),
        "task034_request_hash": pressure.get("request_hash"),
        "task034_result_hash": pressure.get("result_hash"),
        "task034_result_id": pressure.get("result_id"),
        "property_snapshot_hash": flow.get("property_snapshot_hash"),
        "mass_flow_authority_hash": flow.get("mass_flow_authority_hash"),
        "task033_correlation_id": heat.get("correlation_id"),
        "task034_correlation_id": pressure.get("correlation_id"),
        "heat_transfer_surface": heat.get("heat_transfer_surface"),
        "modeled_shell_side_heat_transfer_coefficient_w_m2_k": heat.get(
            "modeled_shell_side_heat_transfer_coefficient_w_m2_k"
        ),
        "modeled_shell_side_pressure_drop_pa": pressure.get("modeled_shell_side_pressure_drop_pa"),
        "applicability_ledger": applicability,
        "completeness_ledger": completeness,
        "request_hash": request_hash_value,
        "result_hash": "",
        "result_id": "",
        "warnings": all_warnings(),
        "blockers": (),
        "deferred_capabilities": DEFERRED_CAPABILITIES,
        "provenance": (),
    }
    return Task035SuccessResult(**values)


def _finalize_provenance(
    request: Task035Request,
    accepted: _Accepted,
    payload: Task035SuccessResult,
) -> Task035SuccessResult:
    """Apply the frozen provenance canonicalization step."""

    provenance_values = _provenance_values(request, accepted, "S19")
    provenance_values["request_hash"] = payload.request_hash
    provenance = build_provenance(provenance_values)
    return dataclasses.replace(payload, provenance=provenance)


def _finalize_result_identity(payload: Task035SuccessResult) -> Task035SuccessResult:
    """Apply the frozen result hash and UUID derivation step."""

    digest = success_result_hash(payload)
    return dataclasses.replace(
        payload,
        result_hash=digest,
        result_id=result_id(digest),
    )


def validate_request(raw_request: Any) -> Task035ValidationResult:
    """Validate the exact TASK035 19-stage projection-only pipeline."""

    if type(raw_request) is not dict:
        return _raw_blocked(raw_request, "SSTHC_RAW_TYPE_INVALID", "raw_request")
    if set(raw_request) - set(REQUEST_FIELDS):
        return _raw_blocked(raw_request, "SSTHC_UNKNOWN_FIELD", "raw_request")
    if not _valid_evidence_refs(raw_request.get("evidence_refs")):
        return _raw_blocked(raw_request, "SSTHC_EVIDENCE_REFS_INVALID", "evidence_refs")
    if raw_request.get("schema_version") != REQUEST_SCHEMA_VERSION:
        request = _request_from_raw(raw_request)
        return _bad(
            request,
            "S02",
            "SSTHC_SCHEMA_VERSION_UNSUPPORTED",
            _Accepted(),
            field_path="schema_version",
        )
    if raw_request.get("profile_id") != PROFILE_ID:
        request = _request_from_raw(raw_request)
        return _bad(
            request,
            "S02",
            "SSTHC_PROFILE_ID_UNSUPPORTED",
            _Accepted(),
            field_path="profile_id",
        )
    missing = [field for field in REQUEST_FIELDS if field not in raw_request]
    if missing:
        request = _request_from_raw(raw_request)
        return _bad(
            request,
            "S02",
            "SSTHC_REQUIRED_FIELD_MISSING",
            _Accepted(),
            field_path="request",
        )
    request = _request_from_raw(raw_request)
    accepted = _Accepted()

    task031_state, task031 = _validate_task031(request.task031_result)
    if task031_state == "missing":
        return _bad(
            request,
            "S03",
            "SSTHC_TASK031_RESULT_MISSING",
            accepted,
            field_path="task031_result",
        )
    if task031_state == "invalid":
        return _bad(request, "S03", "SSTHC_TASK031_RESULT_INVALID", accepted)
    if task031_state == "blocked":
        return _bad(request, "S03", "SSTHC_TASK031_RESULT_BLOCKED", accepted)
    assert task031 is not None
    accepted = _Accepted(task031=task031)
    geometry = _geometry(accepted)
    assert geometry is not None
    if not _identity_task031(geometry):
        return _bad(request, "S04", "SSTHC_TASK031_IDENTITY_MISMATCH", accepted)

    task032_state, task032 = _validate_producer(
        request.task032_result,
        envelope_fields=TASK032_ENVELOPE_FIELDS,
        success_field="flow_state",
        success_fields=TASK032_SUCCESS_RESULT_FIELDS,
        success_schema=_TASK032_RESULT_SCHEMA,
        blocked_fields=TASK032_TYPED_BLOCKED_RESULT_FIELDS,
        blocked_schema=_TASK032_BLOCKED_SCHEMA,
        raw_fields=(
            "schema_version",
            "profile_id",
            "implementation_software_version",
            "raw_request_projection",
            "blocked_result_hash",
            "blockers",
            "warnings",
            "deferred_capabilities",
        ),
        raw_schema=_TASK032_RAW_SCHEMA,
        raw_projection_field="raw_request_projection",
    )
    if task032_state == "missing":
        return _bad(
            request,
            "S05",
            "SSTHC_TASK032_RESULT_MISSING",
            accepted,
            field_path="task032_result",
        )
    if task032_state == "invalid":
        return _bad(request, "S05", "SSTHC_TASK032_RESULT_INVALID", accepted)
    if task032_state == "blocked":
        return _bad(request, "S05", "SSTHC_TASK032_RESULT_BLOCKED", accepted)
    assert task032 is not None
    accepted = _Accepted(task031=task031, task032=task032)
    if not _identity_task032(task032, geometry):
        return _bad(request, "S06", "SSTHC_TASK032_IDENTITY_MISMATCH", accepted)

    task033_state, task033 = _validate_producer(
        request.task033_result,
        envelope_fields=TASK033_ENVELOPE_FIELDS,
        success_field="heat_transfer",
        success_fields=TASK033_SUCCESS_RESULT_FIELDS,
        success_schema=_TASK033_RESULT_SCHEMA,
        blocked_fields=TASK033_TYPED_BLOCKED_RESULT_FIELDS,
        blocked_schema=_TASK033_BLOCKED_SCHEMA,
        raw_fields=(
            "schema_version",
            "profile_id",
            "request_hash",
            "blocked_result_hash",
            "blockers",
            "warnings",
            "deferred_capabilities",
            "raw_projection",
        ),
        raw_schema=_TASK033_RAW_SCHEMA,
        raw_projection_field="raw_projection",
    )
    if task033_state == "missing":
        return _bad(
            request,
            "S07",
            "SSTHC_TASK033_RESULT_MISSING",
            accepted,
            field_path="task033_result",
        )
    if task033_state == "invalid":
        return _bad(request, "S07", "SSTHC_TASK033_RESULT_INVALID", accepted)
    if task033_state == "blocked":
        return _bad(request, "S07", "SSTHC_TASK033_RESULT_BLOCKED", accepted)
    assert task033 is not None
    accepted = _Accepted(task031=task031, task032=task032, task033=task033)
    if not _identity_task033(task033, task032, geometry):
        return _bad(request, "S08", "SSTHC_TASK033_IDENTITY_MISMATCH", accepted)

    task034_state, task034 = _validate_producer(
        request.task034_result,
        envelope_fields=TASK034_ENVELOPE_FIELDS,
        success_field="pressure_drop",
        success_fields=TASK034_SUCCESS_RESULT_FIELDS,
        success_schema=_TASK034_RESULT_SCHEMA,
        blocked_fields=TASK034_TYPED_BLOCKED_RESULT_FIELDS,
        blocked_schema=_TASK034_BLOCKED_SCHEMA,
        raw_fields=(
            "schema_version",
            "profile_id",
            "request_hash",
            "blocked_result_hash",
            "blockers",
            "warnings",
            "deferred_capabilities",
            "raw_projection",
        ),
        raw_schema=_TASK034_RAW_SCHEMA,
        raw_projection_field="raw_projection",
    )
    if task034_state == "missing":
        return _bad(
            request,
            "S09",
            "SSTHC_TASK034_RESULT_MISSING",
            accepted,
            field_path="task034_result",
        )
    if task034_state == "invalid":
        return _bad(request, "S09", "SSTHC_TASK034_RESULT_INVALID", accepted)
    if task034_state == "blocked":
        return _bad(request, "S09", "SSTHC_TASK034_RESULT_BLOCKED", accepted)
    assert task034 is not None
    accepted = _Accepted(task031=task031, task032=task032, task033=task033, task034=task034)
    if not _identity_task034(task034, task033, task032, geometry):
        return _bad(request, "S10", "SSTHC_TASK034_IDENTITY_MISMATCH", accepted)

    join_failure = _configuration_joins(accepted)
    if join_failure is not None:
        return _bad(request, "S11", join_failure, accepted)
    if not _same(
        [
            task032.get("property_snapshot_hash"),
            task033.get("property_snapshot_hash"),
            task034.get("property_snapshot_hash"),
        ]
    ):
        return _bad(request, "S12", "SSTHC_PROPERTY_SNAPSHOT_MISMATCH", accepted)
    if not _same(
        [
            task032.get("mass_flow_authority_hash"),
            task033.get("mass_flow_authority_hash"),
            task034.get("mass_flow_authority_hash"),
        ]
    ):
        return _bad(request, "S12", "SSTHC_MASS_FLOW_AUTHORITY_MISMATCH", accepted)
    if not _same(
        [
            task032.get("shell_side_case_id"),
            task033.get("shell_side_case_id"),
            task034.get("shell_side_case_id"),
        ]
    ):
        return _bad(request, "S13", "SSTHC_CASE_IDENTITY_MISMATCH", accepted)
    if not _same(
        [
            task032.get("shell_side_stream_id"),
            task033.get("shell_side_stream_id"),
            task034.get("shell_side_stream_id"),
        ]
    ):
        return _bad(request, "S13", "SSTHC_STREAM_IDENTITY_MISMATCH", accepted)
    if not _same(
        [
            task032.get("shell_side_fluid_id"),
            task033.get("shell_side_fluid_id"),
            task034.get("shell_side_fluid_id"),
        ]
    ):
        return _bad(request, "S13", "SSTHC_FLUID_IDENTITY_MISMATCH", accepted)

    if (
        task032.get("profile_id") != _TASK032_FLOW_PROFILE
        or task032.get("flow_model") != _TASK032_FLOW_MODEL
        or not str(task032.get("phase_region", "")).startswith("SINGLE_PHASE_")
        or task032.get("rheology_model") != "NEWTONIAN"
        or task033.get("profile_id") != _TASK033_PROFILE
        or task033.get("first_slice_profile_id") != _TASK033_FIRST_SLICE_PROFILE
        or task034.get("profile_id") != _TASK034_PROFILE
        or task034.get("first_slice_profile_id") != _TASK034_FIRST_SLICE_PROFILE
    ):
        return _bad(request, "S14", "SSTHC_PROFILE_COMPATIBILITY_MISMATCH", accepted)
    if task033.get("heat_transfer_surface") != "OUTER_TUBE_SURFACE":
        return _bad(request, "S14", "SSTHC_HEAT_TRANSFER_SURFACE_MISMATCH", accepted)
    if (
        task033.get("correlation_id") != _TASK033_CORRELATION
        or task034.get("correlation_id") != _TASK034_CORRELATION
    ):
        return _bad(request, "S14", "SSTHC_CORRELATION_IDENTITY_MISMATCH", accepted)
    if _applicability_ledger(accepted) is None:
        return _bad(request, "S15", "SSTHC_APPLICABILITY_INCOMPATIBLE", accepted)

    completeness = _completeness_ledger()
    required_producers = dict(dict(completeness).get("required_producers", ()))
    required_names = {"TASK031", "TASK032", "TASK033", "TASK034"}
    if not completeness or any(producer not in required_producers for producer in required_names):
        return _bad(request, "S16", "SSTHC_REQUIRED_CAPABILITY_MISSING", accepted)
    if any(required_producers[producer] != "DELIVERED_AND_PRESENT" for producer in required_names):
        return _bad(request, "S16", "SSTHC_REQUIRED_PRODUCER_NOT_DELIVERED", accepted)
    if any(producer is None for producer in (task031, task032, task033, task034)):
        return _bad(request, "S16", "SSTHC_REQUIRED_CAPABILITY_MISSING", accepted)
    try:
        payload = _compose_success_payload(request, accepted)
    except CanonicalizationError:
        return _bad(request, "S17", "SSTHC_SUCCESS_PAYLOAD_COMPOSITION_FAILED", accepted)
    if payload.blockers or payload.modeled_shell_side_heat_transfer_coefficient_w_m2_k is None:
        return _bad(request, "S17", "SSTHC_PARTIAL_SUCCESS_FORBIDDEN", accepted)
    if payload.modeled_shell_side_pressure_drop_pa is None:
        return _bad(request, "S17", "SSTHC_PARTIAL_SUCCESS_FORBIDDEN", accepted)
    try:
        with_provenance = _finalize_provenance(request, accepted, payload)
    except CanonicalizationError:
        return _bad(request, "S18", "SSTHC_PROVENANCE_CANONICALIZATION_FAILED", accepted)
    try:
        success = _finalize_result_identity(with_provenance)
    except CanonicalizationError:
        return _bad(request, "S18", "SSTHC_CANONICALIZATION_FAILED", accepted)
    if not _hash(success.result_hash) or not _nonempty_text(success.result_id):
        return _bad(request, "S19", "SSTHC_RESULT_IDENTITY_FINALIZATION_FAILED", accepted)
    return Task035ValidationResult(ValidationStatus.VALID, success, None, None)


__all__ = ["parse_request", "validate_request"]
