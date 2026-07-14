"""Binding 19-stage TASK-022 Slice A validation pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_HALF_EVEN, localcontext
from typing import Any

from hexagent.exchangers.shell_tube.models import ConstructionFamily

from .authority import (
    AuthorityFailure,
    verify_cross_binding,
    verify_rule_authority,
    verify_shell_authority,
    verify_task020_configuration,
    verify_task021_layout,
)
from .canonical import (
    DECIMAL_PRECISION,
    CanonicalizationError,
    canonical_raw_json_or_none,
    dataclass_to_mapping,
    decimal_string,
    geometry_id,
    message_to_primitive,
    sha256_hex,
    sort_messages,
    to_primitive,
)
from .geometry import (
    GeometryFailure,
    compute_bundle_envelope,
    compute_clearance,
    parse_explicit_constraints,
)
from .models import (
    DEFERRED_CAPABILITIES,
    DESIGN_CONTRACT_PATH,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    BlockerCode,
    MessageEntry,
    RuleAuthorityMode,
    ShellBundleGeometry,
    ShellBundleGeometryRequest,
    ShellBundleGeometryValidationResult,
    ShellInsideDiameterAuthorityMode,
    ValidationStatus,
    WarningCode,
)
from .schema import SchemaFailure, parse_request


def _message(
    code: BlockerCode | WarningCode,
    field_path: str | None,
    message_key: str,
    *,
    evidence_refs: tuple[str, ...] = (),
    details: dict[str, Any] | None = None,
) -> MessageEntry:
    return MessageEntry(
        code=code.value,
        field_path=field_path,
        message_key=message_key,
        evidence_refs=evidence_refs,
        details=details,
    )


def _request_primitive(request: ShellBundleGeometryRequest) -> dict[str, Any]:
    return dataclass_to_mapping(request)


def _eligible_warnings(
    request: ShellBundleGeometryRequest,
    *,
    failure_stage: int | None = None,
) -> tuple[MessageEntry, ...]:
    passed = 99 if failure_stage is None else failure_stage - 1
    warnings: list[MessageEntry] = []
    rule = request.geometry_rule_authority
    if passed >= 7 and rule.authority_mode is RuleAuthorityMode.INTERNAL_GENERIC:
        warnings.append(
            _message(
                WarningCode.SBG_INTERNAL_GENERIC_NO_STANDARD_CLAIM,
                "geometry_rule_authority.authority_mode",
                "internal_generic_no_standard_claim",
                evidence_refs=rule.evidence_refs,
                details={
                    "authority_mode": RuleAuthorityMode.INTERNAL_GENERIC.value,
                    "standard_claim_status": "NO_STANDARD_CLAIM",
                },
            )
        )
    if (
        passed >= 8
        and request.shell_authority_mode
        is ShellInsideDiameterAuthorityMode.CALLER_SUPPLIED_EXPLICIT
        and request.caller_supplied_shell is not None
    ):
        warnings.append(
            _message(
                WarningCode.SBG_CALLER_SUPPLIED_SHELL_DIAMETER_NO_CATALOG_SELECTION,
                "caller_supplied_shell.shell_inside_diameter_m",
                "caller_supplied_shell_diameter_no_catalog_selection",
                evidence_refs=request.caller_supplied_shell.evidence_refs,
                details={"catalog_selection_status": "NOT_PERFORMED"},
            )
        )
    if passed >= 9:
        if request.bundle_peripheral_allowance_m == "0":
            warnings.append(
                _message(
                    WarningCode.SBG_ZERO_BUNDLE_PERIPHERAL_ALLOWANCE,
                    "bundle_peripheral_allowance_m",
                    "zero_bundle_peripheral_allowance",
                    evidence_refs=request.bundle_peripheral_allowance_evidence_refs,
                )
            )
        if request.required_minimum_radial_clearance_m == "0":
            warnings.append(
                _message(
                    WarningCode.SBG_ZERO_REQUIRED_MINIMUM_RADIAL_CLEARANCE,
                    "required_minimum_radial_clearance_m",
                    "zero_required_minimum_radial_clearance",
                    evidence_refs=request.minimum_clearance_evidence_refs,
                )
            )
    if passed >= 12:
        warnings.append(
            _message(
                WarningCode.SBG_GEOMETRIC_CLEARANCE_NOT_MECHANICAL_ADEQUACY,
                "shell_inside_diameter_m",
                "geometric_clearance_not_mechanical_adequacy",
                evidence_refs=request.evidence_refs,
                details={"mechanical_adequacy_status": "NOT_COMPUTABLE"},
            )
        )
    if passed >= 6:
        family = request.configuration.construction_family
        if family is ConstructionFamily.FIXED_TUBESHEET:
            warnings.append(
                _message(
                    WarningCode.SBG_FIXED_TUBESHEET_THERMAL_EXPANSION_DEFERRED,
                    "configuration.construction_family",
                    "fixed_tubesheet_thermal_expansion_deferred",
                    evidence_refs=request.evidence_refs,
                )
            )
        elif family is ConstructionFamily.U_TUBE:
            warnings.append(
                _message(
                    WarningCode.SBG_UTUBE_BEND_AND_PULL_CLEARANCE_DEFERRED,
                    "configuration.construction_family",
                    "utube_bend_and_pull_clearance_deferred",
                    evidence_refs=request.evidence_refs,
                )
            )
        elif family is ConstructionFamily.FLOATING_HEAD:
            warnings.append(
                _message(
                    WarningCode.SBG_FLOATING_HEAD_HARDWARE_AND_PULL_CLEARANCE_DEFERRED,
                    "configuration.construction_family",
                    "floating_head_hardware_and_pull_clearance_deferred",
                    evidence_refs=request.evidence_refs,
                )
            )
        warnings.append(
            _message(
                WarningCode.SBG_BAFFLE_GEOMETRY_DEFERRED,
                "tube_layout",
                "baffle_geometry_deferred",
                evidence_refs=request.evidence_refs,
            )
        )
        warnings.append(
            _message(
                WarningCode.SBG_PASS_PARTITION_ASSIGNMENT_DEFERRED,
                "configuration.tube_pass_count",
                "pass_partition_assignment_deferred",
                evidence_refs=request.evidence_refs,
                details={"tube_pass_count": request.configuration.tube_pass_count},
            )
        )
    return sort_messages(warnings)


def _blocked(
    *,
    failure_stage: int,
    blockers: tuple[MessageEntry, ...],
    raw_failing_field: Any | None = None,
    request: ShellBundleGeometryRequest | None = None,
    normalized_context: Mapping[str, Any] | None = None,
) -> ShellBundleGeometryValidationResult:
    warnings = () if request is None else _eligible_warnings(request, failure_stage=failure_stage)
    ranks = {id(item): failure_stage for item in blockers}
    ordered_blockers = sort_messages(blockers, stage_by_identity=ranks)
    if normalized_context is not None:
        try:
            normalized: Any = to_primitive(normalized_context)
        except CanonicalizationError:
            normalized = {}
    elif request is not None:
        normalized = _request_primitive(request)
    else:
        normalized = {}
    payload = {
        "task_id": "TASK-022",
        "design_contract_path": DESIGN_CONTRACT_PATH,
        "schema_version": RESULT_SCHEMA_VERSION,
        "failure_stage": failure_stage,
        "normalized_context": normalized,
        "raw_failing_field": canonical_raw_json_or_none(raw_failing_field),
        "warnings": [message_to_primitive(item) for item in warnings],
        "blockers": [message_to_primitive(item) for item in ordered_blockers],
        "deferred_capabilities": list(DEFERRED_CAPABILITIES),
    }
    return ShellBundleGeometryValidationResult(
        status=ValidationStatus.BLOCKED,
        geometry=None,
        warnings=warnings,
        blockers=ordered_blockers,
        deferred_capabilities=DEFERRED_CAPABILITIES,
        blocked_result_hash=sha256_hex(payload),
    )


def _provenance_pre_hash(
    request: ShellBundleGeometryRequest,
    *,
    request_hash: str,
    warnings: tuple[MessageEntry, ...],
    software_version: str,
    git_commit: str,
) -> dict[str, Any]:
    shell_identity: dict[str, Any]
    if request.caller_supplied_shell is not None:
        shell_identity = {
            "authority_hash": request.caller_supplied_shell.authority_hash,
            "evidence_refs": list(request.caller_supplied_shell.evidence_refs),
        }
    else:
        assert request.approved_shell_geometry is not None
        shell_identity = {
            "geometry_id": request.approved_shell_geometry.geometry_id,
            "record_hash": request.approved_shell_geometry.record_hash,
            "snapshot_hash": request.approved_shell_geometry.snapshot_hash,
            "source_binding": dataclass_to_mapping(request.approved_shell_geometry.source_binding),
        }
    return {
        "task_id": "TASK-022",
        "design_contract_path": DESIGN_CONTRACT_PATH,
        "task020_configuration_id": request.configuration.configuration_id,
        "task020_configuration_hash": request.configuration.configuration_hash,
        "task020_case_authority": to_primitive(request.configuration.case_authority),
        "task021_layout_id": request.tube_layout.layout_id,
        "task021_layout_hash": request.tube_layout.layout_hash,
        "tube_geometry_snapshot_hash": request.tube_layout.tube_geometry.snapshot_hash,
        "rule_profile_id": request.geometry_rule_authority.profile_id,
        "rule_id": request.geometry_rule_authority.rule_id,
        "rule_version": request.geometry_rule_authority.rule_version,
        "rule_artifact_canonical_hash": (
            request.geometry_rule_authority.rule_artifact_canonical_hash
        ),
        "rule_snapshot_hash": request.geometry_rule_authority.snapshot_hash,
        "shell_authority_mode": request.shell_authority_mode.value,
        "shell_authority_identity": shell_identity,
        "evidence_refs": list(request.evidence_refs),
        "request_hash": request_hash,
        "software_version": software_version,
        "git_commit": git_commit,
        "warnings": [message_to_primitive(item) for item in warnings],
        "deferred_capabilities": list(DEFERRED_CAPABILITIES),
    }


def validate_request(
    payload: object,
    *,
    software_version: str,
    git_commit: str,
) -> ShellBundleGeometryValidationResult:
    if not isinstance(software_version, str) or not software_version:
        raise ValueError("software_version must be a non-empty caller-supplied string")
    if not isinstance(git_commit, str) or not git_commit:
        raise ValueError("git_commit must be a non-empty caller-supplied string")

    try:
        request = parse_request(payload)
    except SchemaFailure as exc:
        return _blocked(
            failure_stage=exc.stage,
            blockers=exc.blockers,
            raw_failing_field=exc.raw_failing_field,
            normalized_context=exc.normalized_context,
        )

    if request.schema_version != REQUEST_SCHEMA_VERSION:
        return _blocked(
            failure_stage=2,
            blockers=(
                _message(
                    BlockerCode.SBG_SCHEMA_VERSION_UNSUPPORTED,
                    "schema_version",
                    "request_schema_version_unsupported",
                    details={"actual": request.schema_version},
                ),
            ),
            request=request,
        )

    for verifier in (
        verify_task020_configuration,
        lambda item: verify_task021_layout(item.tube_layout),
        verify_cross_binding,
        lambda item: verify_rule_authority(item.geometry_rule_authority),
    ):
        try:
            verifier(request)
        except AuthorityFailure as exc:
            return _blocked(
                failure_stage=exc.stage,
                blockers=tuple(exc.blockers),
                request=request,
            )

    try:
        shell_inside_diameter_m = verify_shell_authority(request)
    except AuthorityFailure as exc:
        return _blocked(
            failure_stage=exc.stage,
            blockers=tuple(exc.blockers),
            request=request,
        )

    try:
        allowance, required_minimum = parse_explicit_constraints(request)
    except GeometryFailure as exc:
        return _blocked(
            failure_stage=exc.stage,
            blockers=tuple(exc.blockers),
            request=request,
        )

    if len(request.tube_layout.positions) > request.geometry_rule_authority.maximum_position_count:
        return _blocked(
            failure_stage=10,
            blockers=(
                _message(
                    BlockerCode.SBG_LAYOUT_POSITION_COUNT_EXCEEDED,
                    "tube_layout.positions",
                    "layout_position_count_exceeded",
                    details={
                        "actual": len(request.tube_layout.positions),
                        "maximum": request.geometry_rule_authority.maximum_position_count,
                    },
                ),
            ),
            request=request,
        )

    try:
        (
            bare_radius,
            bare_diameter,
            outer_radius,
            outer_diameter,
            limiting_position_ids,
        ) = compute_bundle_envelope(request, allowance)
        shell_inside_diameter, shell_radius, radial, diametral = compute_clearance(
            shell_inside_diameter_m=shell_inside_diameter_m,
            bundle_outer_envelope_radius=outer_radius,
            bundle_outer_envelope_diameter=outer_diameter,
            required_minimum=required_minimum,
        )
    except GeometryFailure as exc:
        return _blocked(
            failure_stage=exc.stage,
            blockers=tuple(exc.blockers),
            request=request,
        )

    warnings = _eligible_warnings(request)
    try:
        request_hash = sha256_hex(_request_primitive(request))
        provenance_pre_hash = _provenance_pre_hash(
            request,
            request_hash=request_hash,
            warnings=warnings,
            software_version=software_version,
            git_commit=git_commit,
        )
        with localcontext() as margin_ctx:
            margin_ctx.prec = DECIMAL_PRECISION
            margin_ctx.rounding = ROUND_HALF_EVEN
            margin = radial - required_minimum
        geometry_payload = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "request_hash": request_hash,
            "task020_configuration_id": request.configuration.configuration_id,
            "task020_configuration_hash": request.configuration.configuration_hash,
            "task021_layout_id": request.tube_layout.layout_id,
            "task021_layout_hash": request.tube_layout.layout_hash,
            "construction_family": request.configuration.construction_family.value,
            "equipment_orientation": request.configuration.orientation.value,
            "shell_pass_count": request.configuration.shell_pass_count,
            "tube_pass_count": request.configuration.tube_pass_count,
            "tube_geometry_snapshot_hash": request.tube_layout.tube_geometry.snapshot_hash,
            "geometry_rule_authority": dataclass_to_mapping(request.geometry_rule_authority),
            "shell_authority_mode": request.shell_authority_mode.value,
            "caller_supplied_shell": (
                None
                if request.caller_supplied_shell is None
                else dataclass_to_mapping(request.caller_supplied_shell)
            ),
            "approved_shell_geometry": (
                None
                if request.approved_shell_geometry is None
                else dataclass_to_mapping(request.approved_shell_geometry)
            ),
            "shell_inside_diameter_m": decimal_string(shell_inside_diameter),
            "shell_radius_m": decimal_string(shell_radius),
            "bare_tube_bundle_radius_m": decimal_string(bare_radius),
            "bare_tube_bundle_diameter_m": decimal_string(bare_diameter),
            "bundle_peripheral_allowance_m": decimal_string(allowance),
            "bundle_outer_envelope_radius_m": decimal_string(outer_radius),
            "bundle_outer_envelope_diameter_m": decimal_string(outer_diameter),
            "shell_to_bundle_radial_clearance_m": decimal_string(radial),
            "shell_to_bundle_diametral_clearance_m": decimal_string(diametral),
            "required_minimum_radial_clearance_m": decimal_string(required_minimum),
            "radial_clearance_margin_m": decimal_string(margin),
            "limiting_position_ids": list(limiting_position_ids),
            "position_count": len(request.tube_layout.positions),
            "warnings": [message_to_primitive(item) for item in warnings],
            "deferred_capabilities": list(DEFERRED_CAPABILITIES),
            "provenance_pre_hash": provenance_pre_hash,
        }
        geometry_hash_value = sha256_hex(geometry_payload)
        geometry_id_value = geometry_id(geometry_hash_value)
        provenance = {**provenance_pre_hash, "geometry_hash": geometry_hash_value}
    except (CanonicalizationError, ArithmeticError, TypeError, ValueError) as exc:
        return _blocked(
            failure_stage=17,
            blockers=(
                _message(
                    BlockerCode.SBG_CANONICALIZATION_FAILED,
                    None,
                    "geometry_canonicalization_failed",
                    details={"error_type": type(exc).__name__},
                ),
            ),
            request=request,
        )

    geometry = ShellBundleGeometry(
        schema_version=RESULT_SCHEMA_VERSION,
        geometry_id=geometry_id_value,
        geometry_hash=geometry_hash_value,
        request_hash=request_hash,
        task020_configuration_id=request.configuration.configuration_id,
        task020_configuration_hash=request.configuration.configuration_hash,
        task021_layout_id=request.tube_layout.layout_id,
        task021_layout_hash=request.tube_layout.layout_hash,
        construction_family=request.configuration.construction_family.value,
        equipment_orientation=request.configuration.orientation,
        shell_pass_count=request.configuration.shell_pass_count,
        tube_pass_count=request.configuration.tube_pass_count,
        tube_geometry_snapshot_hash=request.tube_layout.tube_geometry.snapshot_hash,
        geometry_rule_authority=request.geometry_rule_authority,
        shell_authority_mode=request.shell_authority_mode,
        caller_supplied_shell=request.caller_supplied_shell,
        approved_shell_geometry=request.approved_shell_geometry,
        shell_inside_diameter_m=decimal_string(shell_inside_diameter),
        shell_radius_m=decimal_string(shell_radius),
        bare_tube_bundle_radius_m=decimal_string(bare_radius),
        bare_tube_bundle_diameter_m=decimal_string(bare_diameter),
        bundle_peripheral_allowance_m=decimal_string(allowance),
        bundle_outer_envelope_radius_m=decimal_string(outer_radius),
        bundle_outer_envelope_diameter_m=decimal_string(outer_diameter),
        shell_to_bundle_radial_clearance_m=decimal_string(radial),
        shell_to_bundle_diametral_clearance_m=decimal_string(diametral),
        required_minimum_radial_clearance_m=decimal_string(required_minimum),
        radial_clearance_margin_m=decimal_string(margin),
        limiting_position_ids=limiting_position_ids,
        position_count=len(request.tube_layout.positions),
        warnings=warnings,
        blockers=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        provenance=provenance,
    )

    if geometry.geometry_id != geometry_id(geometry.geometry_hash) or geometry.blockers:
        return _blocked(
            failure_stage=19,
            blockers=(
                _message(
                    BlockerCode.SBG_CANONICALIZATION_FAILED,
                    None,
                    "final_geometry_invariant_failed",
                ),
            ),
            request=request,
        )
    return ShellBundleGeometryValidationResult(
        status=ValidationStatus.VALID,
        geometry=geometry,
        warnings=warnings,
        blockers=(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        blocked_result_hash=None,
    )


__all__ = ["validate_request"]
