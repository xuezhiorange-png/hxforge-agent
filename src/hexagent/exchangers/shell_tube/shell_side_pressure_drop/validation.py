"""Fail-closed 17-stage TASK-034 validation pipeline."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from typing import Any

from .authority import (
    AuthorityFailure,
    ReplayIdentity,
    replay_task032_and_upstreams,
    verify_applicability,
    verify_auxiliary_bindings,
    verify_engineering_authority,
    verify_same_case,
    verify_wall_property_authority,
)
from .blocker_registry import BlockerCode, make_blocker, sort_blockers
from .canonical import (
    raw_boundary_blocked_result_hash,
    result_id,
    success_result_hash,
    task034_request_hash,
    typed_blocked_result_hash,
)
from .decimal_quantization import (
    PublicQuantizationError,
    quantize_public_pressure_drop,
)
from .engineering_authority_snapshot import (
    CORRELATION_ID,
    ENGINEERING_SOURCE_AUTHORITY_RECORD_ID,
    SOURCE_ID,
    SOURCE_LOCATION,
    SOURCE_VERSION,
)
from .formulas import (
    EngineeringInputDomainError,
    FormulaCalculationError,
    evaluate_friction_and_wall_correction,
    evaluate_pressure_drop,
    validate_engineering_inputs,
)
from .models import (
    BLOCKED_RESULT_SCHEMA_VERSION,
    DEFERRED_CAPABILITIES,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROFILE_ID,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    ShellSidePressureDropBlockedResult,
    ShellSidePressureDropRawBoundaryBlockedResult,
    ShellSidePressureDropResult,
    ShellSidePressureDropValidationResult,
    Task034Request,
    ValidationStatus,
)
from .provenance import build_provenance_prehash, finalize_provenance
from .raw_projection import project_raw_request
from .schema import SchemaFailure, parse_request
from .warning_registry import all_warnings

VALIDATION_STAGES: tuple[str, ...] = (
    "RAW_BOUNDARY",
    "REQUEST_SCHEMA",
    "UPSTREAM_TYPED_BOUNDARY",
    "TASK033_RESULT_IDENTITY",
    "TASK033_REQUEST_IDENTITY",
    "TASK031_REQUEST_REPLAY",
    "TASK031_GEOMETRY_REPLAY",
    "AUXILIARY_VALUE_BINDING",
    "WALL_PROPERTY_AUTHORITY_REPLAY",
    "SAME_CASE_BINDING",
    "CORRELATION_AUTHORITY_AND_APPLICABILITY",
    "ENGINEERING_INPUT_DOMAIN",
    "FRICTION_FACTOR_AND_WALL_CORRECTION",
    "PRESSURE_DROP_EVALUATION",
    "PUBLIC_QUANTIZATION",
    "PROVENANCE_CANONICALIZATION",
    "RESULT_IDENTITY_FINALIZATION",
)
VALIDATION_STAGE_COUNT = 17


class ResultIdentityFinalizationError(ValueError):
    """A frozen result-identity blocker was reached before hashing."""

    def __init__(self, blocker_code: str) -> None:
        super().__init__(blocker_code)
        self.blocker_code = blocker_code


def _wrapper(
    *,
    success: ShellSidePressureDropResult | None = None,
    blocked: ShellSidePressureDropBlockedResult | None = None,
    raw: ShellSidePressureDropRawBoundaryBlockedResult | None = None,
) -> ShellSidePressureDropValidationResult:
    return ShellSidePressureDropValidationResult(
        status=ValidationStatus.VALID if success is not None else ValidationStatus.BLOCKED,
        pressure_drop=success,
        blocked_result=blocked,
        raw_boundary_blocked_result=raw,
    )


def _raw_blocked(
    raw_request: Any, blockers: tuple[Any, ...]
) -> ShellSidePressureDropValidationResult:
    ordered = sort_blockers(blockers)
    provisional = ShellSidePressureDropRawBoundaryBlockedResult(
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
    return _wrapper(
        raw=ShellSidePressureDropRawBoundaryBlockedResult(
            **{**provisional.__dict__, "blocked_result_hash": blocked_hash}
        )
    )


def _string(value: Any) -> str | None:
    return value if type(value) is str else None


def _typed_blocked(
    *,
    stage: str,
    request: Task034Request | None,
    blockers: tuple[Any, ...],
    identity: ReplayIdentity | None = None,
) -> ShellSidePressureDropValidationResult:
    flow = None if identity is None else identity.flow
    ordered = sort_blockers(blockers)
    warnings = all_warnings()
    provisional = ShellSidePressureDropBlockedResult(
        schema_version=BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=stage,
        shell_side_case_id=None if flow is None else _string(flow.get("shell_side_case_id")),
        shell_side_stream_id=None if flow is None else _string(flow.get("shell_side_stream_id")),
        shell_side_fluid_id=None if flow is None else _string(flow.get("shell_side_fluid_id")),
        task020_configuration_id=None
        if flow is None
        else _string(flow.get("task020_configuration_id")),
        task020_configuration_hash=None
        if flow is None
        else _string(flow.get("task020_configuration_hash")),
        task031_request_hash=None if identity is None else identity.task031_request_hash,
        task031_geometry_id=None if identity is None else identity.task031_geometry_id,
        task031_geometry_hash=None if identity is None else identity.task031_geometry_hash,
        property_snapshot_hash=None if identity is None else identity.property_hash,
        mass_flow_authority_hash=None if identity is None else identity.mass_flow_hash,
        task032_request_hash=None if identity is None else identity.task032_request_hash,
        task032_result_hash=None if identity is None else identity.task032_result_hash,
        task032_result_id=None if identity is None else identity.task032_result_id,
        task033_request_hash=None if request is None else _string(request.task033_request_hash),
        task033_result_hash=None if request is None else _string(request.task033_result_hash),
        task033_result_id=None if request is None else _string(request.task033_result_id),
        wall_property_schema_version=None
        if request is None
        else _string(request.wall_property_schema_version),
        wall_property_source_id=None
        if request is None
        else _string(request.wall_property_source_id),
        wall_property_source_version=None
        if request is None
        else _string(request.wall_property_source_version),
        wall_property_snapshot_hash=None
        if request is None
        else _string(request.wall_property_snapshot_hash),
        wall_property_authority_hash=None
        if request is None
        else _string(request.wall_property_authority_hash),
        request_hash=None if request is None else _safe_request_hash(request),
        blocked_result_hash="",
        warnings=warnings,
        blockers=ordered,
        deferred_capabilities=DEFERRED_CAPABILITIES,
        provenance=(),
    )
    try:
        prehash = build_provenance_prehash(
            request=request,
            request_hash=provisional.request_hash,
            flow=flow or {},
            task033={} if request is None else request.task033_upstream_evidence,
            task031_request_hash=provisional.task031_request_hash,
            task031_geometry_id=provisional.task031_geometry_id,
            task031_geometry_hash=provisional.task031_geometry_hash,
            warnings=warnings,
            deferred_capabilities=DEFERRED_CAPABILITIES,
        )
        with_provenance = ShellSidePressureDropBlockedResult(
            **{**provisional.__dict__, "provenance": finalize_provenance(prehash)}
        )
        blocked_hash = typed_blocked_result_hash(with_provenance)
        return _wrapper(
            blocked=ShellSidePressureDropBlockedResult(
                **{**with_provenance.__dict__, "blocked_result_hash": blocked_hash}
            )
        )
    except Exception:
        # A blocked result must remain structured even if its optional provenance
        # cannot be completed. The original blocker is never replaced by fallback.
        return _wrapper(
            blocked=ShellSidePressureDropBlockedResult(
                **{
                    **provisional.__dict__,
                    "blocked_result_hash": typed_blocked_result_hash(provisional),
                }
            )
        )


def _safe_request_hash(request: Task034Request) -> str | None:
    try:
        return task034_request_hash(request)
    except Exception:
        return None


def finalize_result_identity(result: ShellSidePressureDropResult) -> ShellSidePressureDropResult:
    """Finalize the result hash and UUID5 identity (B045 target)."""
    if result.blockers or result.modeled_shell_side_pressure_drop_pa is None:
        raise ResultIdentityFinalizationError(BlockerCode.SSPD_PARTIAL_RESULT_FORBIDDEN)
    if any(token not in DEFERRED_CAPABILITIES for token in result.deferred_capabilities):
        raise ResultIdentityFinalizationError(BlockerCode.SSPD_DEFERRED_CAPABILITY_TOKEN_INVALID)
    calculated_hash = success_result_hash(result)
    calculated_id = result_id(calculated_hash)
    return ShellSidePressureDropResult(
        **{**result.__dict__, "result_hash": calculated_hash, "result_id": calculated_id}
    )


def _failure(
    failure: AuthorityFailure, *, request: Task034Request, identity: ReplayIdentity | None
) -> ShellSidePressureDropValidationResult:
    return _typed_blocked(
        stage=failure.stage, request=request, blockers=failure.blockers, identity=identity
    )


def _formula_failure(
    exc: FormulaCalculationError,
    *,
    request: Task034Request,
    identity: ReplayIdentity,
) -> ShellSidePressureDropValidationResult:
    code = BlockerCode.SSPD_PRESSURE_DROP_CALCULATION_FAILURE
    stage = "S14"
    if exc.operation == "F13_DECIMAL_LN_FAILURE":
        code = BlockerCode.SSPD_DECIMAL_LN_FAILURE
        stage = "S13"
    elif exc.operation == "F13_DECIMAL_EXP_FAILURE":
        code = BlockerCode.SSPD_DECIMAL_EXP_FAILURE
        stage = "S13"
    elif exc.operation == "F13_DECIMAL_POWER_FAILURE":
        code = BlockerCode.SSPD_DECIMAL_POWER_FAILURE
        stage = "S13"
    elif exc.operation == "F15_PUBLIC_QUANTIZATION":
        code = BlockerCode.SSPD_PUBLIC_QUANTIZATION_FAILURE
        stage = "S15"
    return _typed_blocked(
        stage=stage,
        request=request,
        blockers=(make_blocker(code, stage=stage, field_path=exc.operation),),
        identity=identity,
    )


def validate_typed_request(request: Task034Request) -> ShellSidePressureDropValidationResult:
    identity: ReplayIdentity | None = None
    try:
        identity = replay_task032_and_upstreams(request)
        identity = verify_auxiliary_bindings(request, identity)
        verify_wall_property_authority(request)
        verify_same_case(request, identity)
        verify_applicability(request, identity)
        verify_engineering_authority(request)
    except AuthorityFailure as failure:
        return _failure(failure, request=request, identity=identity)

    flow = identity.flow
    geometry = identity.task032_request_evidence.get("task031_result", {}).get("geometry", {})
    snapshot = identity.task032_request_evidence.get("property_snapshot", {})
    try:
        values = {
            "Re_s": Decimal(str(flow.get("shell_side_reynolds_number"))),
            "G_s": Decimal(str(flow.get("shell_side_mass_velocity_kg_m2_s"))),
            "rho_s": Decimal(str(snapshot.get("density_kg_m3"))),
            "D_s": request.shell_inside_diameter_m,
            "D_e": Decimal(str(geometry.get("shell_side_equivalent_hydraulic_diameter_m"))),
            "N_b": request.baffle_count,
            "mu_b": Decimal(str(snapshot.get("dynamic_viscosity_pa_s"))),
            "mu_w": request.shell_side_wall_dynamic_viscosity_pa_s,
        }
        values = validate_engineering_inputs(**values)
    except EngineeringInputDomainError:
        return _typed_blocked(
            stage="S12",
            request=request,
            blockers=(
                make_blocker(
                    BlockerCode.SSPD_FORMULA_INPUT_INVALID,
                    stage="S12",
                    field_path="engineering_inputs",
                ),
            ),
            identity=identity,
        )
    try:
        correction = evaluate_friction_and_wall_correction(
            Re_s=values["Re_s"],
            mu_b=values["mu_b"],
            mu_w=values["mu_w"],
        )
    except FormulaCalculationError as exc:
        return _formula_failure(exc, request=request, identity=identity)
    try:
        evaluation = evaluate_pressure_drop(
            G_s=values["G_s"],
            rho_s=values["rho_s"],
            D_s=values["D_s"],
            D_e=values["D_e"],
            N_b=values["N_b"],
            f_s=correction.f_s,
            phi_s=correction.phi_s,
            mu_ratio=correction.mu_ratio,
        )
    except FormulaCalculationError as exc:
        return _formula_failure(exc, request=request, identity=identity)
    try:
        public_pressure_drop = quantize_public_pressure_drop(evaluation.raw)
    except FormulaCalculationError as exc:
        return _formula_failure(exc, request=request, identity=identity)
    except PublicQuantizationError:
        return _typed_blocked(
            stage="S15",
            request=request,
            blockers=(
                make_blocker(
                    BlockerCode.SSPD_PUBLIC_QUANTIZATION_FAILURE,
                    stage="S15",
                    field_path="F15_PUBLIC_QUANTIZATION",
                ),
            ),
            identity=identity,
        )

    request_hash = task034_request_hash(request)
    warnings = all_warnings()
    applicability_context = (
        ("reynolds_domain", "400 < Re_s < 1000000"),
        ("phase", "SINGLE_PHASE_LIQUID"),
        ("rheology", "NEWTONIAN"),
    )
    physical_boundary_context = (
        ("modeled_quantity", "modeled_shell_side_pressure_drop_pa"),
        ("total_shell_side_pressure_drop", False),
        ("excluded_phenomena_are_zero", False),
    )
    try:
        prehash = build_provenance_prehash(
            request=request,
            request_hash=request_hash,
            flow=flow,
            task033=request.task033_upstream_evidence,
            task031_request_hash=identity.task031_request_hash,
            task031_geometry_id=identity.task031_geometry_id,
            task031_geometry_hash=identity.task031_geometry_hash,
            warnings=warnings,
            deferred_capabilities=DEFERRED_CAPABILITIES,
        )
        provenance = finalize_provenance(prehash)
    except Exception:
        return _typed_blocked(
            stage="S16",
            request=request,
            blockers=(
                make_blocker(
                    BlockerCode.SSPD_PROVENANCE_CANONICALIZATION_FAILURE,
                    stage="S16",
                    field_path="provenance",
                ),
            ),
            identity=identity,
        )
    result = ShellSidePressureDropResult(
        schema_version=RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        first_slice_profile_id=CORRELATION_ID,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        shell_side_case_id=_string(flow.get("shell_side_case_id")),
        shell_side_stream_id=_string(flow.get("shell_side_stream_id")),
        shell_side_fluid_id=_string(flow.get("shell_side_fluid_id")),
        task020_configuration_id=_string(flow.get("task020_configuration_id")),
        task020_configuration_hash=_string(flow.get("task020_configuration_hash")),
        task031_request_hash=identity.task031_request_hash,
        task031_geometry_id=identity.task031_geometry_id,
        task031_geometry_hash=identity.task031_geometry_hash,
        property_snapshot_hash=identity.property_hash,
        mass_flow_authority_hash=identity.mass_flow_hash,
        task032_request_hash=identity.task032_request_hash,
        task032_result_hash=identity.task032_result_hash,
        task032_result_id=identity.task032_result_id,
        task033_request_hash=request.task033_request_hash,
        task033_result_hash=request.task033_result_hash,
        task033_result_id=request.task033_result_id,
        correlation_id=CORRELATION_ID,
        engineering_source_authority_record_id=ENGINEERING_SOURCE_AUTHORITY_RECORD_ID,
        source_id=SOURCE_ID,
        source_version=SOURCE_VERSION,
        source_location=SOURCE_LOCATION,
        wall_property_schema_version=_string(request.wall_property_schema_version),
        wall_property_source_id=_string(request.wall_property_source_id),
        wall_property_source_version=_string(request.wall_property_source_version),
        wall_property_snapshot_hash=_string(request.wall_property_snapshot_hash),
        wall_property_authority_hash=_string(request.wall_property_authority_hash),
        modeled_shell_side_pressure_drop_pa=public_pressure_drop,
        request_hash=request_hash,
        result_hash="",
        result_id="",
        warnings=warnings,
        blockers=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        applicability_context=applicability_context,
        physical_boundary_context=physical_boundary_context,
        provenance=provenance,
    )
    try:
        return _wrapper(success=finalize_result_identity(result))
    except ResultIdentityFinalizationError as exc:
        return _typed_blocked(
            stage="S17",
            request=request,
            blockers=(make_blocker(exc.blocker_code, stage="S17", field_path="result"),),
            identity=identity,
        )
    except Exception:
        return _typed_blocked(
            stage="S17",
            request=request,
            blockers=(
                make_blocker(
                    BlockerCode.SSPD_RESULT_ID_FINALIZATION_FAILURE,
                    stage="S17",
                    field_path="result_hash",
                ),
            ),
            identity=identity,
        )


def _walk_raw(value: Any) -> Iterator[Any]:
    yield value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_raw(key)
            yield from _walk_raw(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_raw(item)


def validate_request(raw_request: Any) -> ShellSidePressureDropValidationResult:
    if type(raw_request) is not dict:
        return _raw_blocked(
            raw_request,
            (
                make_blocker(
                    BlockerCode.SSPD_RAW_REQUEST_TYPE_INVALID, stage="S01", field_path="raw_request"
                ),
            ),
        )
    if any(type(value) is float for value in _walk_raw(raw_request)):
        return _raw_blocked(
            raw_request,
            (
                make_blocker(
                    BlockerCode.SSPD_RAW_BINARY_FLOAT_FORBIDDEN,
                    stage="S01",
                    field_path="raw_request",
                ),
            ),
        )
    if any(
        isinstance(value, dict) and any(type(key) is not str for key in value)
        for value in _walk_raw(raw_request)
    ):
        return _raw_blocked(
            raw_request,
            (
                make_blocker(
                    BlockerCode.SSPD_RAW_CANONICALIZATION_FAILURE,
                    stage="S01",
                    field_path="raw_request",
                ),
            ),
        )
    allowed = (type(None), bool, int, str, list, dict, tuple)
    if any(type(value) not in allowed for value in _walk_raw(raw_request)):
        return _raw_blocked(
            raw_request,
            (
                make_blocker(
                    BlockerCode.SSPD_RAW_UNSUPPORTED_PRIMITIVE,
                    stage="S01",
                    field_path="raw_request",
                ),
            ),
        )
    try:
        request = parse_request(raw_request)
    except SchemaFailure as failure:
        return (
            _raw_blocked(raw_request, failure.blockers)
            if failure.stage == "S01"
            else _typed_blocked(stage=failure.stage, request=None, blockers=failure.blockers)
        )
    return validate_typed_request(request)


__all__ = [
    "ResultIdentityFinalizationError",
    "finalize_result_identity",
    "validate_request",
    "validate_typed_request",
]
