# ruff: noqa: E501
"""TASK-031 public validation producer."""

from __future__ import annotations

from typing import Any

from . import formulas
from .authority import (
    AuthorityFailure,
    verify_applicability,
    verify_cross_binding,
    verify_engineering_authority,
    verify_task021_layout,
    verify_task024_result,
)
from .canonical import (
    ENGINEERING_AUTHORITY_HASH,
    ENGINEERING_AUTHORITY_ID,
    CanonicalizationError,
    blocked_result_hash,
    final_provenance_tuple,
    geometry_id,
    parse_decimal,
    provenance_prehash_projection,
    request_hash,
    sha256_hex,
    sort_blockers,
    sort_warnings,
    success_geometry_canonical_projection,
)
from .models import (
    DEFERRED_CAPABILITIES,
    FLOW_REGION_IDENTITY,
    FORMULA_A_ID,
    FORMULA_B_ID,
    RESULT_SCHEMA_VERSION,
    BlockerCode,
    MessageEntry,
    ShellSideHydraulicGeometry,
    ShellSideHydraulicGeometryRequest,
    ShellSideHydraulicGeometryValidationResult,
    ValidationStatus,
    WarningCode,
)
from .schema import SchemaFailure, parse_request


def _message(
    code: BlockerCode | WarningCode,
    field_path: str | None,
    message_key: str,
) -> MessageEntry:
    return MessageEntry(
        code=code.value,
        field_path=field_path,
        message_key=message_key,
        evidence_refs=(),
        details=(),
    )


def _eligible_warnings(*, completed_stage: int) -> tuple[MessageEntry, ...]:
    warnings: list[MessageEntry] = []
    if completed_stage >= 6:
        warnings.extend(
            [
                _message(
                    WarningCode.SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY,
                    None,
                    "central_crossflow_screening_geometry_only",
                ),
                _message(
                    WarningCode.SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED,
                    None,
                    "leakage_bypass_corrections_excluded",
                ),
                _message(
                    WarningCode.SSHG_MINIMUM_AREA_SELECTION_DEFERRED,
                    None,
                    "minimum_area_selection_deferred",
                ),
                _message(
                    WarningCode.SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED,
                    None,
                    "window_inlet_outlet_flow_areas_deferred",
                ),
                _message(
                    WarningCode.SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED,
                    None,
                    "flow_state_thermal_pressure_drop_deferred",
                ),
                _message(
                    WarningCode.SSHG_NO_FULL_EXCHANGER_RATING_CLAIM,
                    None,
                    "no_full_exchanger_rating_claim",
                ),
            ]
        )
    if completed_stage >= 7:
        warnings.append(
            _message(
                WarningCode.SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY,
                None,
                "formula_authority_screening_model_only",
            )
        )
    return sort_warnings(warnings)


def _blocked(
    *,
    failure_stage: int,
    blockers: tuple[MessageEntry, ...],
    raw_failing_field: Any,
    warnings: tuple[MessageEntry, ...],
    normalized_context: Any,
) -> ShellSideHydraulicGeometryValidationResult:
    ordered = sort_blockers(
        blockers, stage_by_identity={id(item): failure_stage for item in blockers}
    )
    blocked_hash = blocked_result_hash(
        failure_stage=failure_stage,
        normalized_context=normalized_context,
        raw_failing_field=raw_failing_field,
        warnings=warnings,
        blockers=ordered,
    )
    return ShellSideHydraulicGeometryValidationResult(
        status=ValidationStatus.BLOCKED,
        geometry=None,
        warnings=warnings,
        blockers=ordered,
        deferred_capabilities=DEFERRED_CAPABILITIES,
        blocked_result_hash=blocked_hash,
    )


def validate_typed_request(
    request: ShellSideHydraulicGeometryRequest,
) -> ShellSideHydraulicGeometryValidationResult:
    try:
        verify_task021_layout(request.tube_layout)
    except AuthorityFailure as exc:
        return _blocked(
            failure_stage=exc.stage,
            blockers=tuple(exc.blockers),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=exc.stage - 1),
            normalized_context=[],
        )
    try:
        verify_task024_result(request.baffle_geometry_result)
    except AuthorityFailure as exc:
        return _blocked(
            failure_stage=exc.stage,
            blockers=tuple(exc.blockers),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=exc.stage - 1),
            normalized_context=[],
        )
    try:
        verify_cross_binding(request)
    except AuthorityFailure as exc:
        return _blocked(
            failure_stage=exc.stage,
            blockers=tuple(exc.blockers),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=exc.stage - 1),
            normalized_context=[],
        )
    try:
        central_spacing = verify_applicability(request)
    except AuthorityFailure as exc:
        return _blocked(
            failure_stage=exc.stage,
            blockers=tuple(exc.blockers),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=6),
            normalized_context=[],
        )
    try:
        verify_engineering_authority(request.engineering_authority)
    except AuthorityFailure as exc:
        return _blocked(
            failure_stage=exc.stage,
            blockers=tuple(exc.blockers),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=6),
            normalized_context=[],
        )
    layout = request.tube_layout
    geometry = request.baffle_geometry_result.geometry
    assert geometry is not None
    pattern = layout.layout_rule_authority.pattern_family
    blockers: list[MessageEntry] = []
    try:
        shell_id = parse_decimal(geometry.shell_inside_diameter_m, positive=True)
        pitch = parse_decimal(layout.layout_rule_authority.pitch_m, positive=True)
        tube_od = parse_decimal(geometry.tube_outer_diameter_m, positive=True)
    except Exception:
        blockers.append(
            _message(
                BlockerCode.SSHG_FORMULA_CALCULATION_FAILED,
                "engineering inputs",
                "formula_calculation_failed",
            )
        )
        return _blocked(
            failure_stage=8,
            blockers=tuple(blockers),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=6),
            normalized_context=[],
        )
    if pitch <= tube_od:
        blockers.append(
            _message(
                BlockerCode.SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD,
                "pitch / tube OD",
                "pitch_not_greater_than_tube_od",
            )
        )
    if blockers:
        return _blocked(
            failure_stage=8,
            blockers=tuple(blockers),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=6),
            normalized_context=[],
        )
    try:
        raw_area = formulas.evaluate_formula_a(
            shell_inside_diameter_m=shell_id,
            central_inter_baffle_spacing_m=central_spacing,
            pitch_m=pitch,
            tube_outside_diameter_m=tube_od,
        )
        raw_diameter = formulas.evaluate_formula_b(
            pattern_family=pattern,
            pitch_m=pitch,
            tube_outside_diameter_m=tube_od,
        )
    except Exception:
        blockers.append(
            _message(
                BlockerCode.SSHG_FORMULA_CALCULATION_FAILED,
                "engineering outputs",
                "formula_calculation_failed",
            )
        )
        return _blocked(
            failure_stage=8,
            blockers=tuple(blockers),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=6),
            normalized_context=[],
        )
    if (
        not raw_area.is_finite()
        or raw_area <= 0
        or not raw_diameter.is_finite()
        or raw_diameter <= 0
    ):
        blockers.append(
            _message(
                BlockerCode.SSHG_FORMULA_CALCULATION_FAILED,
                "engineering outputs",
                "formula_calculation_failed",
            )
        )
        return _blocked(
            failure_stage=8,
            blockers=tuple(blockers),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=6),
            normalized_context=[],
        )
    if formulas.area_quantization_collision(raw_area):
        return _blocked(
            failure_stage=9,
            blockers=(
                _message(
                    BlockerCode.SSHG_PUBLIC_AREA_QUANTIZATION_COLLISION,
                    "central_crossflow_flow_area_m2",
                    "public_area_quantization_collision",
                ),
            ),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=6),
            normalized_context=[],
        )
    if formulas.diameter_quantization_collision(raw_diameter):
        return _blocked(
            failure_stage=9,
            blockers=(
                _message(
                    BlockerCode.SSHG_PUBLIC_DIAMETER_QUANTIZATION_COLLISION,
                    "shell_side_equivalent_hydraulic_diameter_m",
                    "public_diameter_quantization_collision",
                ),
            ),
            raw_failing_field=None,
            warnings=_eligible_warnings(completed_stage=6),
            normalized_context=[],
        )
    public_area = formulas.quantize_area(raw_area)
    public_diameter = formulas.quantize_diameter(raw_diameter)
    warnings = _eligible_warnings(completed_stage=7)
    request_hash_value = request_hash(request)
    central_spacing_public = formulas.quantize_diameter(central_spacing)
    try:
        prehash = provenance_prehash_projection(
            request=request,
            request_hash_value=request_hash_value,
            warnings=warnings,
            pattern_family=pattern.value,
        )
        provenance = final_provenance_tuple(prehash)
        geometry_without_hashes = ShellSideHydraulicGeometry(
            schema_version=RESULT_SCHEMA_VERSION,
            geometry_id="",
            geometry_hash="",
            request_hash=request_hash_value,
            task020_configuration_id=layout.task020_configuration_id,
            task020_configuration_hash=layout.task020_configuration_hash,
            task021_layout_id=layout.layout_id,
            task021_layout_hash=layout.layout_hash,
            task022_geometry_id=geometry.task022_geometry_id,
            task022_geometry_hash=geometry.task022_geometry_hash,
            task024_geometry_id=geometry.geometry_id,
            task024_geometry_hash=geometry.geometry_hash,
            engineering_authority_id=ENGINEERING_AUTHORITY_ID,
            engineering_authority_hash=ENGINEERING_AUTHORITY_HASH,
            formula_a_id=FORMULA_A_ID,
            formula_b_id=FORMULA_B_ID,
            pattern_family=pattern.value,
            flow_region_identity=FLOW_REGION_IDENTITY,
            central_inter_baffle_spacing_m=central_spacing_public,
            central_crossflow_flow_area_m2=public_area,
            shell_side_equivalent_hydraulic_diameter_m=public_diameter,
            warnings=warnings,
            blockers=(),
            deferred_capabilities=DEFERRED_CAPABILITIES,
            provenance=provenance,
        )
        geometry_hash_value = sha256_hex(
            success_geometry_canonical_projection(geometry_without_hashes)
        )
        geometry_id_value = geometry_id(geometry_hash_value)
        result_geometry = ShellSideHydraulicGeometry(
            schema_version=geometry_without_hashes.schema_version,
            geometry_id=geometry_id_value,
            geometry_hash=geometry_hash_value,
            request_hash=geometry_without_hashes.request_hash,
            task020_configuration_id=geometry_without_hashes.task020_configuration_id,
            task020_configuration_hash=geometry_without_hashes.task020_configuration_hash,
            task021_layout_id=geometry_without_hashes.task021_layout_id,
            task021_layout_hash=geometry_without_hashes.task021_layout_hash,
            task022_geometry_id=geometry_without_hashes.task022_geometry_id,
            task022_geometry_hash=geometry_without_hashes.task022_geometry_hash,
            task024_geometry_id=geometry_without_hashes.task024_geometry_id,
            task024_geometry_hash=geometry_without_hashes.task024_geometry_hash,
            engineering_authority_id=geometry_without_hashes.engineering_authority_id,
            engineering_authority_hash=geometry_without_hashes.engineering_authority_hash,
            formula_a_id=geometry_without_hashes.formula_a_id,
            formula_b_id=geometry_without_hashes.formula_b_id,
            pattern_family=geometry_without_hashes.pattern_family,
            flow_region_identity=geometry_without_hashes.flow_region_identity,
            central_inter_baffle_spacing_m=geometry_without_hashes.central_inter_baffle_spacing_m,
            central_crossflow_flow_area_m2=geometry_without_hashes.central_crossflow_flow_area_m2,
            shell_side_equivalent_hydraulic_diameter_m=geometry_without_hashes.shell_side_equivalent_hydraulic_diameter_m,
            warnings=geometry_without_hashes.warnings,
            blockers=geometry_without_hashes.blockers,
            deferred_capabilities=geometry_without_hashes.deferred_capabilities,
            provenance=geometry_without_hashes.provenance,
        )
    except (CanonicalizationError, ArithmeticError, TypeError, ValueError):
        return _blocked(
            failure_stage=10,
            blockers=(
                _message(
                    BlockerCode.SSHG_CANONICALIZATION_FAILED,
                    None,
                    "canonicalization_failed",
                ),
            ),
            raw_failing_field=None,
            warnings=warnings,
            normalized_context=[],
        )
    return ShellSideHydraulicGeometryValidationResult(
        status=ValidationStatus.VALID,
        geometry=result_geometry,
        warnings=warnings,
        blockers=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        blocked_result_hash=None,
    )


def validate_request(raw_request: Any) -> ShellSideHydraulicGeometryValidationResult:
    try:
        request = parse_request(raw_request)
    except SchemaFailure as exc:
        return _blocked(
            failure_stage=exc.stage,
            blockers=exc.blockers,
            raw_failing_field=exc.raw_failing_field,
            warnings=(),
            normalized_context=exc.normalized_context,
        )
    return validate_typed_request(request)


__all__ = ["validate_request", "validate_typed_request"]
