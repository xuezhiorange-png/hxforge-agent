"""TASK-032 S00-S12 deterministic validation pipeline."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from . import formulas
from .authority import (
    AuthorityFailure,
    verify_applicability,
    verify_engineering_authority,
    verify_mass_flow_authority,
    verify_property_snapshot,
    verify_same_case,
    verify_task031_result,
)
from .blocker_registry import make_blocker, sort_blockers
from .canonical import (
    ENGINEERING_AUTHORITY_HASH,
    ENGINEERING_AUTHORITY_ID,
    mass_flow_authority_hash,
    raw_boundary_blocked_result_hash,
    request_hash,
    result_id,
    success_result_hash,
    typed_blocked_result_hash,
)
from .models import (
    BLOCKED_RESULT_SCHEMA_VERSION,
    DEFERRED_CAPABILITIES,
    FLOW_MODEL,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROFILE_ID,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    RHEOLOGY_MODEL,
    BlockerCode,
    ShellSideFlowState,
    ShellSideFlowStateBlockedResult,
    ShellSideFlowStateRawBoundaryBlockedResult,
    ShellSideFlowStateRequest,
    ShellSideFlowStateValidationResult,
    Task031GeometryBinding,
    ValidationStatus,
)
from .provenance import build_provenance_prehash, finalize_provenance
from .raw_projection import project_raw_request
from .schema import SchemaFailure, parse_request
from .warning_registry import eligible_warnings


def _stage_number(stage: str) -> int:
    try:
        return int(stage[1:])
    except (ValueError, IndexError):
        return 0


def _result(
    *,
    flow_state: ShellSideFlowState | None = None,
    blocked_result: ShellSideFlowStateBlockedResult | None = None,
    raw_boundary: ShellSideFlowStateRawBoundaryBlockedResult | None = None,
) -> ShellSideFlowStateValidationResult:
    return ShellSideFlowStateValidationResult(
        status=ValidationStatus.VALID if flow_state is not None else ValidationStatus.BLOCKED,
        flow_state=flow_state,
        blocked_result=blocked_result,
        raw_boundary_blocked_result=raw_boundary,
    )


def _raw_boundary_blocked(
    raw_request: Any,
    *,
    blockers: tuple[Any, ...],
) -> ShellSideFlowStateValidationResult:
    ordered = sort_blockers(blockers)
    projection = project_raw_request(raw_request)
    blocked_hash = raw_boundary_blocked_result_hash(
        schema_version=RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        raw_request_projection=projection,
        blockers=ordered,
        warnings=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
    )
    blocked = ShellSideFlowStateRawBoundaryBlockedResult(
        schema_version=RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        raw_request_projection=projection,
        blocked_result_hash=blocked_hash,
        blockers=ordered,
        warnings=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
    )
    return _result(raw_boundary=blocked)


def _typed_blocked(
    *,
    failure_stage: str,
    request: ShellSideFlowStateRequest | None,
    request_hash_value: str | None,
    task031_geometry_id: str | None,
    task031_geometry_hash: str | None,
    property_snapshot_hash: str | None,
    mass_flow_authority_hash_value: str | None,
    blockers: tuple[Any, ...],
) -> ShellSideFlowStateValidationResult:
    completed_stage = _stage_number(failure_stage) - 1
    warnings = eligible_warnings(completed_stage=completed_stage)
    ordered = sort_blockers(blockers)
    phase = None if request is None else request.property_snapshot.phase_region
    authority = None if request is None else request.mass_flow_authority
    prehash = build_provenance_prehash(
        request=request,
        request_hash=request_hash_value,
        task031_geometry_id=task031_geometry_id,
        task031_geometry_hash=task031_geometry_hash,
        property_snapshot_hash=property_snapshot_hash,
        mass_flow_authority_hash=mass_flow_authority_hash_value,
        engineering_authority_id=ENGINEERING_AUTHORITY_ID if completed_stage >= 7 else None,
        engineering_authority_hash=ENGINEERING_AUTHORITY_HASH if completed_stage >= 7 else None,
        phase_region=phase,
        shell_side_case_id=None if authority is None else authority.shell_side_case_id,
        shell_side_stream_id=None if authority is None else authority.shell_side_stream_id,
        shell_side_fluid_id=None if authority is None else authority.shell_side_fluid_id,
        warnings=warnings,
    )
    provenance = finalize_provenance(prehash)
    without_identity = ShellSideFlowStateBlockedResult(
        schema_version=BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=failure_stage,
        task031_geometry_id=task031_geometry_id,
        task031_geometry_hash=task031_geometry_hash,
        property_snapshot_hash=property_snapshot_hash,
        mass_flow_authority_hash=mass_flow_authority_hash_value,
        request_hash=request_hash_value,
        result_hash="",
        result_id="",
        blockers=ordered,
        warnings=warnings,
        deferred_capabilities=DEFERRED_CAPABILITIES,
        provenance=provenance,
    )
    try:
        blocked_hash = typed_blocked_result_hash(without_identity)
        blocked_id = result_id(blocked_hash)
    except Exception:
        fallback = make_blocker(
            BlockerCode.SSFS_RESULT_IDENTITY_FINALIZATION_FAILED,
            stage="S12",
            field_path="result_hash",
        )
        ordered = sort_blockers((*ordered, fallback))
        blocked_hash = typed_blocked_result_hash(
            ShellSideFlowStateBlockedResult(**{**without_identity.__dict__, "blockers": ordered})
        )
        blocked_id = result_id(blocked_hash)
    blocked = ShellSideFlowStateBlockedResult(
        schema_version=without_identity.schema_version,
        profile_id=without_identity.profile_id,
        implementation_software_version=without_identity.implementation_software_version,
        failure_stage=without_identity.failure_stage,
        task031_geometry_id=without_identity.task031_geometry_id,
        task031_geometry_hash=without_identity.task031_geometry_hash,
        property_snapshot_hash=without_identity.property_snapshot_hash,
        mass_flow_authority_hash=without_identity.mass_flow_authority_hash,
        request_hash=without_identity.request_hash,
        result_hash=blocked_hash,
        result_id=blocked_id,
        blockers=ordered,
        warnings=without_identity.warnings,
        deferred_capabilities=without_identity.deferred_capabilities,
        provenance=without_identity.provenance,
    )
    return _result(blocked_result=blocked)


def _authority_failure(
    failure: AuthorityFailure,
    *,
    request: ShellSideFlowStateRequest,
    request_hash_value: str,
    task031_geometry_id: str | None,
    task031_geometry_hash: str | None,
    property_snapshot_hash: str | None,
    mass_flow_authority_hash_value: str | None,
) -> ShellSideFlowStateValidationResult:
    return _typed_blocked(
        failure_stage=failure.stage,
        request=request,
        request_hash_value=request_hash_value,
        task031_geometry_id=task031_geometry_id,
        task031_geometry_hash=task031_geometry_hash,
        property_snapshot_hash=property_snapshot_hash,
        mass_flow_authority_hash_value=mass_flow_authority_hash_value,
        blockers=failure.blockers,
    )


def validate_typed_request(
    request: ShellSideFlowStateRequest,
) -> ShellSideFlowStateValidationResult:
    try:
        request_hash_value = request_hash(request)
    except Exception:
        return _typed_blocked(
            failure_stage="S11",
            request=request,
            request_hash_value=None,
            task031_geometry_id=None,
            task031_geometry_hash=None,
            property_snapshot_hash=None,
            mass_flow_authority_hash_value=None,
            blockers=(
                make_blocker(
                    BlockerCode.SSFS_CANONICALIZATION_FAILED,
                    stage="S11",
                    field_path="request",
                ),
            ),
        )

    geometry: Task031GeometryBinding | None = None
    geometry_id: str | None = None
    geometry_hash: str | None = None
    property_hash: str | None = None
    mass_hash: str | None = None
    try:
        geometry = verify_task031_result(request.task031_result)
    except AuthorityFailure as failure:
        return _authority_failure(
            failure,
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=None,
            task031_geometry_hash=None,
            property_snapshot_hash=None,
            mass_flow_authority_hash_value=None,
        )
    geometry_id = geometry.geometry_id
    geometry_hash = geometry.geometry_hash

    try:
        verify_property_snapshot(request)
    except AuthorityFailure as failure:
        return _authority_failure(
            failure,
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=geometry_id,
            task031_geometry_hash=geometry_hash,
            property_snapshot_hash=None,
            mass_flow_authority_hash_value=None,
        )
    property_hash = request.property_snapshot.property_snapshot_hash

    try:
        verify_mass_flow_authority(request)
    except AuthorityFailure as failure:
        return _authority_failure(
            failure,
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=geometry_id,
            task031_geometry_hash=geometry_hash,
            property_snapshot_hash=property_hash,
            mass_flow_authority_hash_value=None,
        )
    mass_hash = mass_flow_authority_hash(request.mass_flow_authority)

    try:
        verify_same_case(request, geometry)
    except AuthorityFailure as failure:
        return _authority_failure(
            failure,
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=geometry_id,
            task031_geometry_hash=geometry_hash,
            property_snapshot_hash=property_hash,
            mass_flow_authority_hash_value=mass_hash,
        )

    try:
        verify_applicability(request, geometry)
    except AuthorityFailure as failure:
        return _authority_failure(
            failure,
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=geometry_id,
            task031_geometry_hash=geometry_hash,
            property_snapshot_hash=property_hash,
            mass_flow_authority_hash_value=mass_hash,
        )

    try:
        verify_engineering_authority()
    except AuthorityFailure as failure:
        return _authority_failure(
            failure,
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=geometry_id,
            task031_geometry_hash=geometry_hash,
            property_snapshot_hash=property_hash,
            mass_flow_authority_hash_value=mass_hash,
        )

    snapshot = request.property_snapshot
    authority = request.mass_flow_authority
    try:
        raw = formulas.evaluate_raw(
            mass_flow_rate=authority.mass_flow_rate_kg_s,
            flow_area=Decimal(geometry.central_crossflow_flow_area_m2),
            hydraulic_diameter=Decimal(geometry.shell_side_equivalent_hydraulic_diameter_m),
            density=snapshot.density_kg_m3,
            dynamic_viscosity=snapshot.dynamic_viscosity_pa_s,
            specific_heat_capacity=snapshot.specific_heat_capacity_j_kg_k,
            thermal_conductivity=snapshot.thermal_conductivity_w_m_k,
        )
    except Exception:
        return _authority_failure(
            AuthorityFailure(
                "S08",
                (
                    make_blocker(
                        BlockerCode.SSFS_FORMULA_CALCULATION_FAILED,
                        stage="S08",
                        field_path="engineering_outputs",
                    ),
                ),
            ),
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=geometry_id,
            task031_geometry_hash=geometry_hash,
            property_snapshot_hash=property_hash,
            mass_flow_authority_hash_value=mass_hash,
        )
    if any(
        not value.is_finite() or value <= 0
        for value in (raw.mass_velocity, raw.bulk_velocity, raw.reynolds, raw.prandtl)
    ):
        return _authority_failure(
            AuthorityFailure(
                "S08",
                (
                    make_blocker(
                        BlockerCode.SSFS_FORMULA_CALCULATION_FAILED,
                        stage="S08",
                        field_path="engineering_outputs",
                    ),
                ),
            ),
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=geometry_id,
            task031_geometry_hash=geometry_hash,
            property_snapshot_hash=property_hash,
            mass_flow_authority_hash_value=mass_hash,
        )

    collision_map = (
        (
            raw.mass_velocity,
            formulas.MASS_VELOCITY_QUANTUM,
            BlockerCode.SSFS_PUBLIC_MASS_VELOCITY_QUANTIZATION_COLLISION,
            "shell_side_mass_velocity_kg_m2_s",
        ),
        (
            raw.bulk_velocity,
            formulas.BULK_VELOCITY_QUANTUM,
            BlockerCode.SSFS_PUBLIC_BULK_VELOCITY_QUANTIZATION_COLLISION,
            "shell_side_bulk_velocity_m_s",
        ),
        (
            raw.reynolds,
            formulas.REYNOLDS_QUANTUM,
            BlockerCode.SSFS_PUBLIC_REYNOLDS_QUANTIZATION_COLLISION,
            "shell_side_reynolds_number",
        ),
        (
            raw.prandtl,
            formulas.PRANDTL_QUANTUM,
            BlockerCode.SSFS_PUBLIC_PRANDTL_QUANTIZATION_COLLISION,
            "shell_side_prandtl_number",
        ),
    )
    collisions = tuple(
        make_blocker(code, stage="S09", field_path=field_path)
        for raw_value, quantum, code, field_path in collision_map
        if formulas.quantization_collision(raw_value, quantum)
    )
    if collisions:
        return _authority_failure(
            AuthorityFailure("S09", collisions),
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=geometry_id,
            task031_geometry_hash=geometry_hash,
            property_snapshot_hash=property_hash,
            mass_flow_authority_hash_value=mass_hash,
        )

    warnings = eligible_warnings(completed_stage=7)
    phase = snapshot.phase_region
    prehash = build_provenance_prehash(
        request=request,
        request_hash=request_hash_value,
        task031_geometry_id=geometry_id,
        task031_geometry_hash=geometry_hash,
        property_snapshot_hash=property_hash,
        mass_flow_authority_hash=mass_hash,
        engineering_authority_id=ENGINEERING_AUTHORITY_ID,
        engineering_authority_hash=ENGINEERING_AUTHORITY_HASH,
        phase_region=phase,
        shell_side_case_id=authority.shell_side_case_id,
        shell_side_stream_id=authority.shell_side_stream_id,
        shell_side_fluid_id=authority.shell_side_fluid_id,
        warnings=warnings,
    )
    provenance = finalize_provenance(prehash)
    try:
        without_identity = ShellSideFlowState(
            schema_version=RESULT_SCHEMA_VERSION,
            profile_id=PROFILE_ID,
            implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
            shell_side_case_id=authority.shell_side_case_id,
            shell_side_stream_id=authority.shell_side_stream_id,
            shell_side_fluid_id=authority.shell_side_fluid_id,
            task020_configuration_id=geometry.task020_configuration_id,
            task020_configuration_hash=geometry.task020_configuration_hash,
            task031_geometry_id=geometry.geometry_id,
            task031_geometry_hash=geometry.geometry_hash,
            property_snapshot_hash=property_hash,
            mass_flow_authority_hash=mass_hash,
            engineering_authority_id=ENGINEERING_AUTHORITY_ID,
            engineering_authority_hash=ENGINEERING_AUTHORITY_HASH,
            flow_model=FLOW_MODEL,
            phase_region=phase,
            rheology_model=RHEOLOGY_MODEL,
            shell_side_mass_flow_rate_kg_s=authority.mass_flow_rate_kg_s,
            shell_side_mass_velocity_kg_m2_s=formulas.quantize_mass_velocity(raw.mass_velocity),
            shell_side_bulk_velocity_m_s=formulas.quantize_bulk_velocity(raw.bulk_velocity),
            shell_side_reynolds_number=formulas.quantize_reynolds(raw.reynolds),
            shell_side_prandtl_number=formulas.quantize_prandtl(raw.prandtl),
            request_hash=request_hash_value,
            result_hash="",
            result_id="",
            warnings=warnings,
            blockers=(),
            deferred_capabilities=DEFERRED_CAPABILITIES,
            provenance=provenance,
        )
        calculated_hash = success_result_hash(without_identity)
    except Exception:
        return _authority_failure(
            AuthorityFailure(
                "S11",
                (
                    make_blocker(
                        BlockerCode.SSFS_CANONICALIZATION_FAILED,
                        stage="S11",
                        field_path="result",
                    ),
                ),
            ),
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=geometry_id,
            task031_geometry_hash=geometry_hash,
            property_snapshot_hash=property_hash,
            mass_flow_authority_hash_value=mass_hash,
        )
    try:
        calculated_id = result_id(calculated_hash)
    except Exception:
        return _authority_failure(
            AuthorityFailure(
                "S12",
                (
                    make_blocker(
                        BlockerCode.SSFS_RESULT_IDENTITY_FINALIZATION_FAILED,
                        stage="S12",
                        field_path="result_id",
                    ),
                ),
            ),
            request=request,
            request_hash_value=request_hash_value,
            task031_geometry_id=geometry_id,
            task031_geometry_hash=geometry_hash,
            property_snapshot_hash=property_hash,
            mass_flow_authority_hash_value=mass_hash,
        )
    flow_state = ShellSideFlowState(
        schema_version=without_identity.schema_version,
        profile_id=without_identity.profile_id,
        implementation_software_version=without_identity.implementation_software_version,
        shell_side_case_id=without_identity.shell_side_case_id,
        shell_side_stream_id=without_identity.shell_side_stream_id,
        shell_side_fluid_id=without_identity.shell_side_fluid_id,
        task020_configuration_id=without_identity.task020_configuration_id,
        task020_configuration_hash=without_identity.task020_configuration_hash,
        task031_geometry_id=without_identity.task031_geometry_id,
        task031_geometry_hash=without_identity.task031_geometry_hash,
        property_snapshot_hash=without_identity.property_snapshot_hash,
        mass_flow_authority_hash=without_identity.mass_flow_authority_hash,
        engineering_authority_id=without_identity.engineering_authority_id,
        engineering_authority_hash=without_identity.engineering_authority_hash,
        flow_model=without_identity.flow_model,
        phase_region=without_identity.phase_region,
        rheology_model=without_identity.rheology_model,
        shell_side_mass_flow_rate_kg_s=without_identity.shell_side_mass_flow_rate_kg_s,
        shell_side_mass_velocity_kg_m2_s=without_identity.shell_side_mass_velocity_kg_m2_s,
        shell_side_bulk_velocity_m_s=without_identity.shell_side_bulk_velocity_m_s,
        shell_side_reynolds_number=without_identity.shell_side_reynolds_number,
        shell_side_prandtl_number=without_identity.shell_side_prandtl_number,
        request_hash=without_identity.request_hash,
        result_hash=calculated_hash,
        result_id=calculated_id,
        warnings=without_identity.warnings,
        blockers=without_identity.blockers,
        deferred_capabilities=without_identity.deferred_capabilities,
        provenance=without_identity.provenance,
    )
    return _result(flow_state=flow_state)


def validate_request(raw_request: Any) -> ShellSideFlowStateValidationResult:
    try:
        request = parse_request(raw_request)
    except SchemaFailure as failure:
        if failure.stage in {"S00", "S01"}:
            return _raw_boundary_blocked(raw_request, blockers=failure.blockers)
        return _typed_blocked(
            failure_stage=failure.stage,
            request=None,
            request_hash_value=None,
            task031_geometry_id=None,
            task031_geometry_hash=None,
            property_snapshot_hash=None,
            mass_flow_authority_hash_value=None,
            blockers=failure.blockers,
        )
    return validate_typed_request(request)


__all__ = ["validate_request", "validate_typed_request"]
