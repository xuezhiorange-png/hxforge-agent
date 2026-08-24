"""Fail-closed TASK-033 validation pipeline."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .authority import (
    AuthorityFailure,
    ReplayIdentity,
    replay_task032_identity,
    verify_applicability,
    verify_engineering_authority,
    verify_same_case,
)
from .blocker_registry import BlockerCode, make_blocker, sort_blockers
from .canonical import (
    raw_boundary_blocked_result_hash,
    result_id,
    success_result_hash,
    task033_request_hash,
    typed_blocked_result_hash,
)
from .decimal_quantization import quantization_collision
from .engineering_authority_snapshot import (
    ENGINEERING_SOURCE_AUTHORITY_RECORD_ID,
)
from .formulas import FormulaCalculationError, evaluate_htc
from .models import (
    BLOCKED_RESULT_SCHEMA_VERSION,
    CORRELATION_ID,
    DEFERRED_CAPABILITIES,
    FIRST_SLICE_PROFILE_ID,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROFILE_ID,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    ShellSideHeatTransferBlockedResult,
    ShellSideHeatTransferRawBoundaryBlockedResult,
    ShellSideHeatTransferRequest,
    ShellSideHeatTransferResult,
    ShellSideHeatTransferValidationResult,
    ValidationStatus,
)
from .models import (
    HEAT_TRANSFER_SURFACE as MODEL_HEAT_TRANSFER_SURFACE,
)
from .provenance import build_provenance_prehash, finalize_provenance
from .raw_projection import project_raw_request
from .schema import SchemaFailure, parse_request
from .warning_registry import all_warnings


def _wrapper(
    *,
    heat_transfer: ShellSideHeatTransferResult | None = None,
    blocked_result: ShellSideHeatTransferBlockedResult | None = None,
    raw_boundary: ShellSideHeatTransferRawBoundaryBlockedResult | None = None,
) -> ShellSideHeatTransferValidationResult:
    return ShellSideHeatTransferValidationResult(
        status=ValidationStatus.VALID if heat_transfer is not None else ValidationStatus.BLOCKED,
        heat_transfer=heat_transfer,
        blocked_result=blocked_result,
        raw_boundary_blocked_result=raw_boundary,
    )


def _raw_blocked(
    raw_request: Any, blockers: tuple[Any, ...]
) -> ShellSideHeatTransferValidationResult:
    ordered = sort_blockers(blockers)
    provisional = ShellSideHeatTransferRawBoundaryBlockedResult(
        schema_version=RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        request_hash=None,
        blocked_result_hash="",
        blockers=ordered,
        warnings=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        raw_projection=project_raw_request(raw_request),
    )
    blocked_hash = raw_boundary_blocked_result_hash(provisional)
    blocked = ShellSideHeatTransferRawBoundaryBlockedResult(
        schema_version=provisional.schema_version,
        profile_id=provisional.profile_id,
        request_hash=provisional.request_hash,
        blocked_result_hash=blocked_hash,
        blockers=provisional.blockers,
        warnings=provisional.warnings,
        deferred_capabilities=provisional.deferred_capabilities,
        raw_projection=provisional.raw_projection,
    )
    return _wrapper(raw_boundary=blocked)


def _provenance(
    request: ShellSideHeatTransferRequest | None,
    flow: Any,
    *,
    request_hash: str | None,
    identity: ReplayIdentity | None,
    warnings: Any,
) -> tuple[tuple[str, Any], ...]:
    prehash = build_provenance_prehash(
        request_hash=request_hash,
        flow=flow,
        request=request,
        task032_request_hash=None if identity is None else identity.request_hash,
        task032_result_hash=None if identity is None else identity.result_hash,
        task032_result_id=None if identity is None else identity.result_id,
        warnings=warnings,
    )
    return finalize_provenance(prehash)


def _typed_blocked(
    *,
    stage: str,
    request: ShellSideHeatTransferRequest | None,
    blockers: tuple[Any, ...],
    identity: ReplayIdentity | None = None,
) -> ShellSideHeatTransferValidationResult:
    flow = None if request is None else request.task032_flow_state
    ordered = sort_blockers(blockers)
    warnings = all_warnings() if int(stage[1:]) >= 9 else ()
    provisional = ShellSideHeatTransferBlockedResult(
        schema_version=BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=stage,
        shell_side_case_id=None if flow is None else _string_or_none(flow.shell_side_case_id),
        shell_side_stream_id=None if flow is None else _string_or_none(flow.shell_side_stream_id),
        shell_side_fluid_id=None if flow is None else _string_or_none(flow.shell_side_fluid_id),
        task020_configuration_id=None
        if flow is None
        else _string_or_none(flow.task020_configuration_id),
        task020_configuration_hash=None
        if flow is None
        else _string_or_none(flow.task020_configuration_hash),
        task031_geometry_id=None if flow is None else _string_or_none(flow.task031_geometry_id),
        task031_geometry_hash=None if flow is None else _string_or_none(flow.task031_geometry_hash),
        property_snapshot_hash=None
        if flow is None
        else _string_or_none(flow.property_snapshot_hash),
        mass_flow_authority_hash=None
        if flow is None
        else _string_or_none(flow.mass_flow_authority_hash),
        task032_request_hash=None if identity is None else identity.request_hash,
        task032_result_hash=None if identity is None else identity.result_hash,
        task032_result_id=None if identity is None else identity.result_id,
        request_hash=None if request is None else task033_request_hash(request),
        blocked_result_hash="",
        warnings=warnings,
        blockers=ordered,
        deferred_capabilities=DEFERRED_CAPABILITIES,
        provenance=(),
    )
    try:
        provenance = _provenance(
            request,
            flow,
            request_hash=provisional.request_hash,
            identity=identity,
            warnings=warnings,
        )
        provisional = ShellSideHeatTransferBlockedResult(
            **{**provisional.__dict__, "provenance": provenance}
        )
        blocked_hash = typed_blocked_result_hash(provisional)
    except Exception:
        ordered = sort_blockers(
            (
                *ordered,
                make_blocker(
                    BlockerCode.SSHT_CANONICALIZATION_FAILED,
                    stage="S13",
                    field_path="blocked_result",
                ),
            )
        )
        provisional = ShellSideHeatTransferBlockedResult(
            **{**provisional.__dict__, "blockers": ordered}
        )
        blocked_hash = typed_blocked_result_hash(provisional)
    blocked = ShellSideHeatTransferBlockedResult(
        **{**provisional.__dict__, "blocked_result_hash": blocked_hash}
    )
    return _wrapper(blocked_result=blocked)


def _string_or_none(value: Any) -> str | None:
    return value if type(value) is str else None


def _failure(
    failure: AuthorityFailure,
    *,
    request: ShellSideHeatTransferRequest,
    identity: ReplayIdentity | None,
) -> ShellSideHeatTransferValidationResult:
    return _typed_blocked(
        stage=failure.stage, request=request, blockers=failure.blockers, identity=identity
    )


def validate_typed_request(
    request: ShellSideHeatTransferRequest,
) -> ShellSideHeatTransferValidationResult:
    identity: ReplayIdentity | None = None
    try:
        identity = replay_task032_identity(request)
    except AuthorityFailure as failure:
        return _failure(failure, request=request, identity=None)
    try:
        verify_same_case(request, identity)
        verify_applicability(request, identity)
        verify_engineering_authority()
    except AuthorityFailure as failure:
        return _failure(failure, request=request, identity=identity)

    flow = request.task032_flow_state
    evidence = request.task032_request_evidence
    geometry = evidence.task031_result["geometry"]
    try:
        reynolds = Decimal(str(flow.shell_side_reynolds_number))
        prandtl = Decimal(str(flow.shell_side_prandtl_number))
        conductivity = Decimal(str(evidence.property_snapshot["thermal_conductivity_w_m_k"]))
        diameter = Decimal(str(geometry["shell_side_equivalent_hydraulic_diameter_m"]))
    except Exception:
        return _typed_blocked(
            stage="S10",
            request=request,
            blockers=(
                make_blocker(
                    BlockerCode.SSHT_FORMULA_INPUT_DOMAIN_VIOLATION,
                    stage="S10",
                    field_path="engineering_inputs",
                ),
            ),
            identity=identity,
        )
    try:
        evaluation = evaluate_htc(
            reynolds=reynolds,
            prandtl=prandtl,
            thermal_conductivity=conductivity,
            equivalent_diameter=diameter,
        )
    except FormulaCalculationError as exc:
        code = BlockerCode.SSHT_FORMULA_CALCULATION_FAILED
        if "INPUT_DOMAIN" in str(exc):
            code = BlockerCode.SSHT_FORMULA_INPUT_DOMAIN_VIOLATION
        return _typed_blocked(
            stage="S11",
            request=request,
            blockers=(
                make_blocker(
                    code,
                    stage="S11",
                    field_path="modeled_shell_side_heat_transfer_coefficient_w_m2_k",
                ),
            ),
            identity=identity,
        )
    if quantization_collision(evaluation.raw):
        return _typed_blocked(
            stage="S12",
            request=request,
            blockers=(
                make_blocker(
                    BlockerCode.SSHT_PUBLIC_HTC_QUANTIZATION_COLLISION,
                    stage="S12",
                    field_path="modeled_shell_side_heat_transfer_coefficient_w_m2_k",
                ),
            ),
            identity=identity,
        )
    try:
        request_hash_value = task033_request_hash(request)
        provenance = _provenance(
            request,
            flow,
            request_hash=request_hash_value,
            identity=identity,
            warnings=all_warnings(),
        )
        applicability_context = (
            ("reynolds", str(reynolds)),
            ("prandtl", str(prandtl)),
            ("thermal_conductivity_w_m_k", str(conductivity)),
            ("shell_side_equivalent_hydraulic_diameter_m", str(diameter)),
            ("reynolds_domain", "2e3 < Re_s < 1e6"),
        )
        provisional = ShellSideHeatTransferResult(
            schema_version=RESULT_SCHEMA_VERSION,
            profile_id=PROFILE_ID,
            first_slice_profile_id=FIRST_SLICE_PROFILE_ID,
            implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
            shell_side_case_id=str(flow.shell_side_case_id),
            shell_side_stream_id=str(flow.shell_side_stream_id),
            shell_side_fluid_id=str(flow.shell_side_fluid_id),
            task020_configuration_id=_string_or_none(flow.task020_configuration_id),
            task020_configuration_hash=_string_or_none(flow.task020_configuration_hash),
            task031_geometry_id=identity.geometry_id,
            task031_geometry_hash=identity.geometry_hash,
            property_snapshot_hash=identity.property_hash,
            mass_flow_authority_hash=identity.mass_flow_hash,
            task032_request_hash=identity.request_hash,
            task032_result_hash=identity.result_hash,
            task032_result_id=identity.result_id,
            correlation_id=CORRELATION_ID,
            engineering_source_authority_record_id=ENGINEERING_SOURCE_AUTHORITY_RECORD_ID,
            heat_transfer_surface=MODEL_HEAT_TRANSFER_SURFACE,
            modeled_shell_side_heat_transfer_coefficient_w_m2_k=evaluation.public,
            request_hash=request_hash_value,
            result_hash="",
            result_id="",
            warnings=all_warnings(),
            blockers=(),
            deferred_capabilities=DEFERRED_CAPABILITIES,
            applicability_context=applicability_context,
            provenance=provenance,
        )
        calculated_hash = success_result_hash(provisional)
        calculated_id = result_id(calculated_hash)
        result = ShellSideHeatTransferResult(
            **{**provisional.__dict__, "result_hash": calculated_hash, "result_id": calculated_id}
        )
    except Exception:
        return _typed_blocked(
            stage="S13",
            request=request,
            blockers=(
                make_blocker(
                    BlockerCode.SSHT_CANONICALIZATION_FAILED, stage="S13", field_path="result"
                ),
            ),
            identity=identity,
        )
    return _wrapper(heat_transfer=result)


def validate_request(raw_request: Any) -> ShellSideHeatTransferValidationResult:
    try:
        request = parse_request(raw_request)
    except SchemaFailure as failure:
        if failure.stage == "S00":
            return _raw_blocked(raw_request, failure.blockers)
        return _typed_blocked(stage=failure.stage, request=None, blockers=failure.blockers)
    return validate_typed_request(request)


__all__ = ["validate_request", "validate_typed_request"]
