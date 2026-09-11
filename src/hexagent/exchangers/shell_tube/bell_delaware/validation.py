"""TASK-166 fail-closed validation and Bell--Delaware calculation service."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal, DecimalException
from typing import Any

from . import authority
from .canonical import (
    blocked_hash,
    blocked_id,
    evidence_projection,
    raw_blocked_hash,
    raw_blocked_id,
    request_hash,
    result_hash,
    result_id,
    sha256_domain_hex,
)
from .errors import BellDelawareFailure, Blocker, BlockerCode, FailureStage
from .geometry import derive_geometry
from .heat_transfer import calculate_heat_transfer
from .models import (
    ApplicabilityCheck,
    ApplicabilityLedger,
    ApplicabilityStatus,
    CompletenessLedger,
    Task166BlockedResult,
    Task166RawBoundaryBlockedResult,
    Task166Request,
    Task166Result,
    Task166ValidationResult,
    ValidationStatus,
)
from .pressure_drop import calculate_pressure_drop
from .provenance import build_provenance
from .raw_projection import RawProjectionFailure, project_raw
from .schema import SchemaFailure, parse_request

_SUCCESS_CHECK_IDS: tuple[str, ...] = (
    "TASK020_CONFIGURATION_ACCEPTED",
    "TUBE_LAYOUT_ACCEPTED",
    "SHELL_BUNDLE_GEOMETRY_ACCEPTED",
    "BAFFLE_GEOMETRY_ACCEPTED",
    "SHELL_SIDE_FLOW_STATE_ACCEPTED",
    "BELL_SOURCE_APPLICABLE",
    "NUMERICAL_DOMAIN_VALID",
)
_COMPLETE_FIELDS: tuple[str, ...] = (
    "ideal_crossflow_heat_transfer_coefficient",
    "Jc",
    "Jl",
    "Jb",
    "Js",
    "Jr",
    "corrected_shell_side_heat_transfer_coefficient",
    "ideal_crossflow_pressure_drop",
    "crossflow_pressure_drop",
    "window_pressure_drop",
    "end_zone_pressure_drop",
    "central_crossflow_contribution",
    "window_contribution",
    "entrance_zone_contribution",
    "exit_zone_contribution",
    "Rl",
    "Rb",
    "Rs",
    "total_shell_pressure_drop",
    "bell_geometry",
    "factor_evidence",
    "applicability",
    "provenance",
)


def _blocker(
    code: BlockerCode,
    stage: FailureStage,
    field_path: str | None = None,
    message: str = "",
) -> Blocker:
    return Blocker(code=code, stage=stage, field_path=field_path, message=message)


def _ordered(blockers: list[Blocker]) -> tuple[Blocker, ...]:
    # The validation pipeline emits the first failing stage first.  Within a
    # stage, declaration order is retained (rather than a set or hash order).
    return tuple(blockers)


def _raw_branch(code: str, raw_projection_hash: str) -> Task166ValidationResult:
    try:
        blocker_code = BlockerCode(code)
    except ValueError:
        blocker_code = BlockerCode.UNSUPPORTED_RAW_VALUE
    item = Task166RawBoundaryBlockedResult(
        raw_request_projection_hash=raw_projection_hash,
        blockers=(_blocker(blocker_code, FailureStage.RAW_BOUNDARY),),
    )
    item = replace(item, result_hash=raw_blocked_hash(item))
    item = replace(item, result_id=raw_blocked_id(item.result_hash))
    return Task166ValidationResult(
        status=ValidationStatus.RAW_BOUNDARY_BLOCKED,
        raw_boundary_blocked=item,
    )


def _typed_branch(
    request_hash_value: str,
    blockers: list[Blocker],
) -> Task166ValidationResult:
    ordered = _ordered(blockers)
    item = Task166BlockedResult(request_hash=request_hash_value, blockers=ordered)
    item = replace(item, result_hash=blocked_hash(item))
    item = replace(item, result_id=blocked_id(item.result_hash))
    return Task166ValidationResult(status=ValidationStatus.TYPED_BLOCKED, typed_blocked=item)


def _field(mapping: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    return None


def _require_identity(mapping: Mapping[str, Any], path: str) -> None:
    if type(mapping) is not dict:
        raise BellDelawareFailure(BlockerCode.UPSTREAM_AUTHORITY_INVALID, path)
    result_hash_value = _field(mapping, "result_hash", "geometry_hash", "layout_hash", "hash")
    result_id_value = _field(mapping, "result_id", "geometry_id", "layout_id", "id")
    if type(result_hash_value) is not str or not result_hash_value:
        raise BellDelawareFailure(
            BlockerCode.UPSTREAM_IDENTITY_REPLAY_FAILED, f"{path}.result_hash"
        )
    if type(result_id_value) is not str or not result_id_value:
        raise BellDelawareFailure(BlockerCode.UPSTREAM_IDENTITY_REPLAY_FAILED, f"{path}.result_id")
    status = _field(mapping, "status", "validation_status")
    if status is not None and status not in {"VALID", "SUCCESS", "APPLICABLE", "COMPLETE"}:
        raise BellDelawareFailure(BlockerCode.UPSTREAM_AUTHORITY_INVALID, f"{path}.status")
    completeness = mapping.get("completeness")
    if type(completeness) is dict and completeness.get("status") not in {None, "COMPLETE"}:
        raise BellDelawareFailure(BlockerCode.UPSTREAM_AUTHORITY_INVALID, f"{path}.completeness")
    applicability = mapping.get("applicability")
    if type(applicability) is dict and applicability.get("status") not in {None, "APPLICABLE"}:
        raise BellDelawareFailure(BlockerCode.UPSTREAM_AUTHORITY_INVALID, f"{path}.applicability")


def _case_id(mapping: Mapping[str, Any]) -> str | None:
    value = _field(mapping, "physical_exchanger_case_id", "shell_side_case_id", "case_id")
    return value if type(value) is str and value else None


def _validate_upstream(request: Task166Request) -> None:
    upstream = (
        (request.task020_configuration, "task020_configuration"),
        (request.tube_layout, "tube_layout"),
        (request.shell_bundle_geometry, "shell_bundle_geometry"),
        (request.baffle_geometry, "baffle_geometry"),
        (request.shell_side_hydraulic_geometry, "shell_side_hydraulic_geometry"),
        (request.shell_side_flow_state, "shell_side_flow_state"),
    )
    for mapping, path in upstream:
        _require_identity(mapping, path)
    case_ids = [_case_id(mapping) for mapping, _ in upstream]
    if any(value is None for value in case_ids) or len(set(case_ids)) != 1:
        raise BellDelawareFailure(
            BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH, "physical_exchanger_case_id"
        )
    flow = request.shell_side_flow_state
    phase = _field(flow, "phase", "phase_region")
    if phase not in {"SINGLE_PHASE", "SINGLE_PHASE_LIQUID", "SINGLE_PHASE_GAS"}:
        raise BellDelawareFailure(
            BlockerCode.PHASE_UNSUPPORTED, "shell_side_flow_state.phase_region"
        )
    rheology = _field(flow, "rheology", "rheology_model")
    if rheology != authority.SUPPORTED_RHEOLOGY:
        raise BellDelawareFailure(
            BlockerCode.RHEOLOGY_UNSUPPORTED, "shell_side_flow_state.rheology_model"
        )


def _validate_configuration(request: Task166Request) -> None:
    config = request.task020_configuration
    construction = _field(config, "construction_family", "construction_family_id")
    if construction not in authority.SUPPORTED_CONSTRUCTION_FAMILIES:
        raise BellDelawareFailure(BlockerCode.CONFIGURATION_UNSUPPORTED, "construction_family")
    shell_type = _field(config, "shell_type", "shell_type_authority")
    if shell_type != authority.SUPPORTED_SHELL_TYPE:
        raise BellDelawareFailure(BlockerCode.SHELL_TYPE_UNSUPPORTED, "shell_type")
    shell_passes = _field(config, "shell_pass_count", "shell_pass_count_authority")
    if shell_passes != authority.SUPPORTED_SHELL_PASS_COUNT:
        raise BellDelawareFailure(BlockerCode.SHELL_PASS_COUNT_UNSUPPORTED, "shell_pass_count")
    baffle = request.baffle_geometry
    baffle_type = _field(baffle, "baffle_type", "baffle_type_authority")
    if baffle_type is None and type(baffle.get("design_authority")) is dict:
        baffle_type = _field(baffle["design_authority"], "baffle_type", "baffle_type_authority")
    if baffle_type != authority.SUPPORTED_BAFFLE_TYPE:
        raise BellDelawareFailure(BlockerCode.BAFFLE_TYPE_UNSUPPORTED, "baffle_type")


def _flow_metrics(request: Task166Request) -> dict[str, Any]:
    flow = dict(request.shell_side_flow_state)
    snapshot = request.shell_side_flow_state_request.get("property_snapshot")
    if type(snapshot) is dict:
        for key, value in snapshot.items():
            flow.setdefault(key, value)
    mass_authority = request.shell_side_flow_state_request.get("mass_flow_authority")
    if type(mass_authority) is dict:
        for key in ("mass_flow_rate_kg_s", "shell_side_mass_flow_rate_kg_s"):
            if key in mass_authority:
                flow.setdefault("shell_side_mass_flow_rate_kg_s", mass_authority[key])
    return flow


def _check_reynolds(flow: Mapping[str, Any]) -> None:
    value = _field(flow, "shell_side_reynolds_number", "reynolds_number", "Re_s")
    if value is None:
        raise BellDelawareFailure(
            BlockerCode.REQUIRED_PROPERTY_MISSING, "shell_side_reynolds_number"
        )
    try:
        reynolds = Decimal(value) if type(value) is str else value
    except DecimalException as exc:
        raise BellDelawareFailure(
            BlockerCode.REQUIRED_PROPERTY_MISSING, "shell_side_reynolds_number"
        ) from exc
    if type(reynolds) is not Decimal or not reynolds.is_finite() or reynolds <= Decimal("0"):
        raise BellDelawareFailure(BlockerCode.REYNOLDS_OUT_OF_RANGE, "shell_side_reynolds_number")
    if reynolds > Decimal(authority.MAX_REYNOLDS):
        raise BellDelawareFailure(BlockerCode.REYNOLDS_OUT_OF_RANGE, "shell_side_reynolds_number")


def _applicability() -> ApplicabilityLedger:
    return ApplicabilityLedger(
        checks=tuple(
            ApplicabilityCheck(check_id=check_id, status="PASS") for check_id in _SUCCESS_CHECK_IDS
        ),
        status=ApplicabilityStatus.APPLICABLE,
    )


def _completeness() -> CompletenessLedger:
    return CompletenessLedger(
        required_fields=_COMPLETE_FIELDS,
        present_fields=_COMPLETE_FIELDS,
        status="COMPLETE",
    )


def _calculate(request: Task166Request) -> Task166Result:
    _validate_upstream(request)
    _validate_configuration(request)
    flow = _flow_metrics(request)
    _check_reynolds(flow)
    try:
        geometry = derive_geometry(request)
    except BellDelawareFailure:
        raise
    except DecimalException as exc:
        raise BellDelawareFailure(BlockerCode.NUMERICAL_OPERATION_FAILED, "geometry") from exc
    try:
        heat = calculate_heat_transfer(geometry, flow)
    except BellDelawareFailure:
        raise
    except DecimalException as exc:
        raise BellDelawareFailure(BlockerCode.NUMERICAL_OPERATION_FAILED, "heat_transfer") from exc
    try:
        pressure = calculate_pressure_drop(geometry, flow)
    except BellDelawareFailure:
        raise
    except DecimalException as exc:
        raise BellDelawareFailure(BlockerCode.NUMERICAL_OPERATION_FAILED, "pressure_drop") from exc
    evidence = evidence_projection(request.task020_configuration)
    layout_evidence = evidence_projection(request.tube_layout)
    bundle_evidence = evidence_projection(request.shell_bundle_geometry)
    baffle_evidence = evidence_projection(request.baffle_geometry)
    hydraulic_evidence = evidence_projection(request.shell_side_hydraulic_geometry)
    flow_evidence = evidence_projection(request.shell_side_flow_state)
    request_hash_value = request_hash(request)
    result = Task166Result(
        source_definition_id=request.source_definition_id,
        request_hash=request_hash_value,
        task020_evidence=evidence,
        tube_layout_evidence=layout_evidence,
        shell_bundle_evidence=bundle_evidence,
        baffle_evidence=baffle_evidence,
        shell_side_hydraulic_evidence=hydraulic_evidence,
        shell_side_flow_evidence=flow_evidence,
        bell_geometry=geometry,
        ideal_crossflow_heat_transfer_coefficient=heat.ideal_crossflow_heat_transfer_coefficient,
        j_c=heat.j_c,
        j_l=heat.j_l,
        j_b=heat.j_b,
        j_s=heat.j_s,
        j_r=heat.j_r,
        corrected_shell_side_heat_transfer_coefficient=heat.corrected_shell_side_heat_transfer_coefficient,
        ideal_crossflow_pressure_drop=pressure.ideal_crossflow_pressure_drop,
        crossflow_pressure_drop=pressure.crossflow_pressure_drop,
        window_pressure_drop=pressure.window_pressure_drop,
        end_zone_pressure_drop=pressure.end_zone_pressure_drop,
        central_crossflow_contribution=pressure.central_crossflow_contribution,
        window_contribution=pressure.window_contribution,
        entrance_zone_contribution=pressure.entrance_zone_contribution,
        exit_zone_contribution=pressure.exit_zone_contribution,
        r_l=pressure.r_l,
        r_b=pressure.r_b,
        r_s=pressure.r_s,
        total_shell_pressure_drop=pressure.total_shell_pressure_drop,
        heat_transfer_parameter_row_identity=heat.parameter_row_identity,
        heat_transfer_parameter_source_id=authority.JAMIL_PARAMETER_SOURCE_ID,
        heat_transfer_a1=heat.a1,
        heat_transfer_a2=heat.a2,
        heat_transfer_a3=heat.a3,
        heat_transfer_a4=heat.a4,
        pressure_drop_parameter_row_identity=pressure.parameter_row_identity,
        pressure_drop_parameter_source_id=authority.JAMIL_PARAMETER_SOURCE_ID,
        pressure_drop_b1=pressure.b1,
        pressure_drop_b2=pressure.b2,
        pressure_drop_b3=pressure.b3,
        pressure_drop_b4=pressure.b4,
        factor_evidence=heat.factor_evidence + pressure.factor_evidence,
        applicability=_applicability(),
        completeness=_completeness(),
        warnings=(),
        blockers=(),
        provenance_semantic_inputs=(),
    )
    semantic, _ = build_provenance(
        request, request_hash_value=request_hash_value, result_hash_value="pending"
    )
    result = replace(result, provenance_semantic_inputs=semantic)
    calculated_hash = result_hash(result)
    result = replace(result, result_hash=calculated_hash, result_id=result_id(calculated_hash))
    _, graph = build_provenance(
        request,
        request_hash_value=request_hash_value,
        result_hash_value=calculated_hash,
    )
    if graph.self_edge_count != 0 or graph.cycle_count != 0:
        raise BellDelawareFailure(BlockerCode.PROVENANCE_INVALID, "provenance.graph")
    return replace(result, provenance=graph)


def validate_request(raw_request: object) -> Task166ValidationResult:
    """Admit exactly one raw/typed/valid branch and never leak raw exceptions."""
    try:
        raw_value = project_raw(raw_request)
    except RawProjectionFailure as exc:
        error_hash = sha256_domain_hex("task166.raw-error.v1", {"code": exc.code})
        return _raw_branch(exc.code, error_hash)
    try:
        request = parse_request(raw_request)
    except SchemaFailure as exc:
        hash_value = sha256_domain_hex("task166.typed-schema.v1", raw_value)
        return _typed_branch(
            hash_value,
            [_blocker(exc.code, FailureStage.TYPED_VALIDATION, exc.field_path, str(exc))],
        )
    request_hash_value = ""
    try:
        request_hash_value = request_hash(request)
        result = _calculate(request)
        return Task166ValidationResult(status=ValidationStatus.VALID, valid=result)
    except BellDelawareFailure as exc:
        stage = FailureStage.UPSTREAM_AUTHORITY
        if exc.code in {
            BlockerCode.REQUIRED_GEOMETRY_MISSING,
            BlockerCode.INVALID_GEOMETRY_DOMAIN,
            BlockerCode.TUBE_LAYOUT_UNSUPPORTED,
        }:
            stage = FailureStage.GEOMETRY
        elif exc.code in {
            BlockerCode.INVALID_PARAMETER_ROW,
            BlockerCode.REYNOLDS_OUT_OF_RANGE,
            BlockerCode.REQUIRED_PROPERTY_MISSING,
            BlockerCode.PHASE_UNSUPPORTED,
            BlockerCode.RHEOLOGY_UNSUPPORTED,
            BlockerCode.NONFINITE_ENGINEERING_RESULT,
        }:
            stage = FailureStage.HEAT_TRANSFER
        elif exc.code in {BlockerCode.INVALID_PRESSURE_DROP_DECOMPOSITION}:
            stage = FailureStage.PRESSURE_DROP
        elif exc.code is BlockerCode.PROVENANCE_INVALID:
            stage = FailureStage.PROVENANCE
        return _typed_branch(
            request_hash_value,
            [_blocker(exc.code, stage, str(exc) or None)],
        )
    except BaseException:
        return _typed_branch(
            request_hash_value,
            [_blocker(BlockerCode.INTERNAL_INVARIANT_VIOLATION, FailureStage.IDENTITY)],
        )


__all__ = ["validate_request"]
