"""Binding fail-closed validation pipeline for TASK-021 Slice A."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hexagent.exchangers.shell_tube.models import ConstructionFamily

from .authority import (
    AuthorityFailure,
    verify_geometry_snapshot,
    verify_layout_rule_snapshot,
    verify_task020_configuration,
)
from .canonical import (
    CanonicalizationError,
    dataclass_to_mapping,
    layout_id,
    position_id,
    sha256_hex,
    sort_messages,
    to_primitive,
)
from .enumeration import EnumerationFailure, build_plan, enumerate_candidates
from .geometry import GeometryFailure, evaluate_geometry
from .models import (
    DEFERRED_CAPABILITIES,
    DESIGN_CONTRACT_PATH,
    LAYOUT_SCHEMA_VERSION,
    AuthorityMode,
    BlockerCode,
    MessageEntry,
    ProvenancePreHashProjection,
    TubeLayout,
    TubeLayoutRequest,
    TubeLayoutValidationResult,
    TubePosition,
    ValidationStatus,
    WarningCode,
)
from .pairing import PairingFailure, canonical_pairs, validate_pairing_plan
from .schema import SchemaFailure, parse_request


def _blocked(
    stage: int,
    blockers: tuple[MessageEntry, ...],
    *,
    warnings: tuple[MessageEntry, ...] = (),
    context: Mapping[str, Any] | None = None,
) -> TubeLayoutValidationResult:
    canonical_blockers = sort_messages(blockers)
    canonical_warnings = sort_messages(warnings)
    payload = {
        "output_schema_version": LAYOUT_SCHEMA_VERSION,
        "failure_stage": stage,
        "context": {} if context is None else dict(context),
        "warnings": [dataclass_to_mapping(item) for item in canonical_warnings],
        "blockers": [dataclass_to_mapping(item) for item in canonical_blockers],
        "deferred_capabilities": list(DEFERRED_CAPABILITIES),
    }
    return TubeLayoutValidationResult(
        status=ValidationStatus.BLOCKED,
        layout=None,
        warnings=canonical_warnings,
        blockers=canonical_blockers,
        blocked_result_hash=sha256_hex(payload),
    )


def _request_hash(request: TubeLayoutRequest) -> str:
    payload = dataclass_to_mapping(request)
    if request.u_tube_pairing_plan is not None:
        normalized_plan = request.u_tube_pairing_plan
        payload["u_tube_pairing_plan"]["pairs"] = [
            dataclass_to_mapping(pair) for pair in canonical_pairs(normalized_plan)
        ]
    return sha256_hex(payload)


def _warnings(request: TubeLayoutRequest) -> tuple[MessageEntry, ...]:
    result: list[MessageEntry] = []
    rule = request.layout_rule_authority
    if rule.authority_mode is AuthorityMode.INTERNAL_GENERIC:
        result.append(
            MessageEntry(
                code=WarningCode.STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM.value,
                field_path="layout_rule_authority.authority_mode",
                message_key="internal_generic_no_standard_claim",
                evidence_refs=rule.evidence_refs,
                details={
                    "authority_mode": "INTERNAL_GENERIC",
                    "standard_claim_status": "NO_STANDARD_CLAIM",
                },
            )
        )
    result.append(
        MessageEntry(
            code=WarningCode.STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER.value,
            field_path="placement_envelope.tube_center_envelope_diameter_m",
            message_key="caller_supplied_envelope_not_shell_diameter",
            evidence_refs=request.placement_envelope.evidence_refs,
            details={
                "semantic_role": "tube_center_placement_constraint",
                "shell_diameter_status": "NOT_COMPUTABLE",
            },
        )
    )
    result.append(
        MessageEntry(
            code=WarningCode.STL_PASS_PARTITION_ASSIGNMENT_DEFERRED.value,
            field_path="configuration.tube_pass_count",
            message_key="pass_partition_assignment_deferred",
            evidence_refs=request.evidence_refs,
            details={
                "assignment_status": "NOT_COMPUTABLE",
                "tube_pass_count": request.configuration.tube_pass_count,
            },
        )
    )
    if request.configuration.construction_family is ConstructionFamily.U_TUBE:
        assert request.u_tube_pairing_plan is not None
        result.append(
            MessageEntry(
                code=WarningCode.STL_UTUBE_BEND_GEOMETRY_DEFERRED.value,
                field_path="u_tube_pairing_plan",
                message_key="u_tube_bend_geometry_deferred",
                evidence_refs=request.u_tube_pairing_plan.evidence_refs,
                details={
                    "bend_geometry_status": "NOT_COMPUTABLE",
                    "construction_family": "U_TUBE",
                },
            )
        )
    return sort_messages(result)


def _provenance(
    request: TubeLayoutRequest,
    request_hash: str,
    warnings: tuple[MessageEntry, ...],
    *,
    software_version: str,
    git_commit: str,
) -> ProvenancePreHashProjection:
    config = request.configuration
    rule = request.layout_rule_authority
    geometry = request.tube_geometry
    return ProvenancePreHashProjection(
        task_id="TASK-021",
        design_contract_path=DESIGN_CONTRACT_PATH,
        task020_configuration_id=config.configuration_id,
        task020_configuration_hash=config.configuration_hash,
        task020_case_authority=to_primitive(config.case_authority),
        geometry_id=geometry.geometry_id,
        geometry_revision=geometry.revision,
        geometry_record_hash=geometry.record_hash,
        tube_geometry_snapshot_hash=geometry.snapshot_hash,
        geometry_source_binding=to_primitive(geometry.source_binding),
        layout_rule_profile_id=rule.profile_id,
        layout_rule_id=rule.rule_id,
        layout_rule_version=rule.rule_version,
        rule_artifact_canonical_hash=rule.rule_artifact_canonical_hash,
        layout_rule_snapshot_hash=rule.snapshot_hash,
        source_class=rule.source_class,
        approval_status=rule.approval_status,
        provenance_edge_ids=rule.provenance_edge_ids,
        layout_rule_evidence_refs=rule.evidence_refs,
        rule_pack_identity=None
        if rule.rule_pack_identity is None
        else to_primitive(rule.rule_pack_identity),
        envelope_evidence_refs=request.placement_envelope.evidence_refs,
        exclusion_zone_evidence_refs=tuple(
            zone.evidence_refs for zone in request.exclusion_zones
        ),
        u_tube_pairing_evidence_refs=None
        if request.u_tube_pairing_plan is None
        else request.u_tube_pairing_plan.evidence_refs,
        software_version=software_version,
        git_commit=git_commit,
        request_hash=request_hash,
        warnings=warnings,
        deferred_capabilities=DEFERRED_CAPABILITIES,
    )


def _validate_authorizations(request: TubeLayoutRequest) -> tuple[MessageEntry, ...]:
    blockers: list[MessageEntry] = []
    rule = request.layout_rule_authority
    if request.origin_mode not in rule.allowed_origin_modes:
        blockers.append(
            MessageEntry(
                code=BlockerCode.STL_ORIGIN_MODE_NOT_AUTHORIZED.value,
                field_path="origin_mode",
                message_key="origin_mode_not_authorized",
            )
        )
    if request.axis_orientation not in rule.allowed_axis_orientations:
        blockers.append(
            MessageEntry(
                code=BlockerCode.STL_AXIS_ORIENTATION_NOT_AUTHORIZED.value,
                field_path="axis_orientation",
                message_key="axis_orientation_not_authorized",
            )
        )
    for zone in request.exclusion_zones:
        if zone.zone_type not in rule.allowed_exclusion_zone_types:
            blockers.append(
                MessageEntry(
                    code=BlockerCode.STL_EXCLUSION_ZONE_TYPE_NOT_AUTHORIZED.value,
                    field_path=f"exclusion_zones.{zone.zone_id}.zone_type",
                    message_key="exclusion_zone_type_not_authorized",
                    evidence_refs=zone.evidence_refs,
                )
            )
    return tuple(blockers)


def validate_request(
    payload: Any,
    *,
    software_version: str,
    git_commit: str,
) -> TubeLayoutValidationResult:
    """Validate one TASK-021 request and return a deterministic VALID/BLOCKED result."""

    if not isinstance(software_version, str) or not software_version:
        raise ValueError("software_version must be a non-empty caller-supplied string")
    if not isinstance(git_commit, str) or not git_commit:
        raise ValueError("git_commit must be a non-empty caller-supplied string")
    try:
        request = parse_request(payload)
    except SchemaFailure as exc:
        return _blocked(1, exc.blockers)
    try:
        verify_task020_configuration(request.configuration)
    except AuthorityFailure as exc:
        return _blocked(4, exc.blockers)
    try:
        verify_layout_rule_snapshot(
            request.layout_rule_authority,
            request.configuration,
            request.tube_geometry,
        )
    except AuthorityFailure as exc:
        return _blocked(6, exc.blockers)
    try:
        verify_geometry_snapshot(request.tube_geometry)
    except (AuthorityFailure, CanonicalizationError) as exc:
        blockers = (
            exc.blockers
            if isinstance(exc, AuthorityFailure)
            else (
                MessageEntry(
                    code=BlockerCode.STL_DECIMAL_LEXICAL_INVALID.value,
                    field_path="tube_geometry",
                    message_key="tube_geometry_decimal_invalid",
                ),
            )
        )
        return _blocked(7, blockers)
    authorization_blockers = _validate_authorizations(request)
    if authorization_blockers:
        return _blocked(9, authorization_blockers)
    construction_family = request.configuration.construction_family
    if construction_family is ConstructionFamily.U_TUBE and request.u_tube_pairing_plan is None:
        return _blocked(
            11,
            (
                MessageEntry(
                    code=BlockerCode.STL_UTUBE_PAIRING_REQUIRED.value,
                    field_path="u_tube_pairing_plan",
                    message_key="u_tube_pairing_required",
                ),
            ),
        )
    if construction_family is not ConstructionFamily.U_TUBE and request.u_tube_pairing_plan is not None:
        return _blocked(
            11,
            (
                MessageEntry(
                    code=BlockerCode.STL_UTUBE_PAIRING_NOT_EXPECTED.value,
                    field_path="u_tube_pairing_plan",
                    message_key="u_tube_pairing_not_expected",
                ),
            ),
        )
    try:
        plan = build_plan(
            request.layout_rule_authority,
            request.tube_geometry,
            request.placement_envelope,
            request.origin_mode,
            request.axis_orientation,
        )
        candidates = enumerate_candidates(plan)
    except EnumerationFailure as exc:
        return _blocked(12, (exc.blocker,))
    try:
        geometry_result = evaluate_geometry(
            candidates,
            plan,
            request.tube_geometry,
            request.exclusion_zones,
        )
    except GeometryFailure as exc:
        return _blocked(15, (exc.blocker,))
    physical_tube_count = len(geometry_result.accepted)
    normalized_plan = request.u_tube_pairing_plan
    if construction_family is ConstructionFamily.U_TUBE:
        assert request.u_tube_pairing_plan is not None
        try:
            normalized_plan, physical_tube_count = validate_pairing_plan(
                request.u_tube_pairing_plan,
                geometry_result.accepted,
            )
        except PairingFailure as exc:
            return _blocked(16, exc.blockers)
        request = TubeLayoutRequest(
            schema_version=request.schema_version,
            configuration=request.configuration,
            tube_geometry=request.tube_geometry,
            layout_rule_authority=request.layout_rule_authority,
            placement_envelope=request.placement_envelope,
            origin_mode=request.origin_mode,
            axis_orientation=request.axis_orientation,
            exclusion_zones=request.exclusion_zones,
            u_tube_pairing_plan=normalized_plan,
            evidence_refs=request.evidence_refs,
        )
    request_hash = _request_hash(request)
    positions = tuple(
        TubePosition(
            position_id=position_id(request_hash, item.u, item.v),
            u=item.u,
            v=item.v,
            x_m=item.x_m,
            y_m=item.y_m,
        )
        for item in geometry_result.accepted
    )
    warnings = _warnings(request)
    provenance_pre_hash = _provenance(
        request,
        request_hash,
        warnings,
        software_version=software_version,
        git_commit=git_commit,
    )
    layout_hash_payload = {
        "schema_version": LAYOUT_SCHEMA_VERSION,
        "request_hash": request_hash,
        "positions": [dataclass_to_mapping(position) for position in positions],
        "tube_hole_count": len(positions),
        "physical_tube_count": physical_tube_count,
        "boundary_rejection_count": geometry_result.boundary_rejection_count,
        "exclusion_rejection_count": geometry_result.exclusion_rejection_count,
        "exclusion_audit": [
            dataclass_to_mapping(item) for item in geometry_result.exclusion_audit
        ],
        "warnings": [dataclass_to_mapping(item) for item in warnings],
        "blockers": [],
        "deferred_capabilities": list(provenance_pre_hash.deferred_capabilities),
        "provenance_pre_hash": dataclass_to_mapping(provenance_pre_hash),
    }
    layout_hash = sha256_hex(layout_hash_payload)
    provenance = dataclass_to_mapping(provenance_pre_hash)
    provenance["layout_hash"] = layout_hash
    layout = TubeLayout(
        schema_version=LAYOUT_SCHEMA_VERSION,
        layout_id=layout_id(layout_hash),
        layout_hash=layout_hash,
        request_hash=request_hash,
        task020_configuration_id=request.configuration.configuration_id,
        task020_configuration_hash=request.configuration.configuration_hash,
        case_authority=to_primitive(request.configuration.case_authority),
        construction_family=request.configuration.construction_family.value,
        equipment_orientation=request.configuration.orientation.value,
        shell_pass_count=request.configuration.shell_pass_count,
        tube_pass_count=request.configuration.tube_pass_count,
        tube_geometry=request.tube_geometry,
        layout_rule_authority=request.layout_rule_authority,
        placement_envelope=request.placement_envelope,
        origin_mode=request.origin_mode,
        axis_orientation=request.axis_orientation,
        exclusion_zones=request.exclusion_zones,
        positions=positions,
        tube_hole_count=len(positions),
        physical_tube_count=physical_tube_count,
        boundary_rejection_count=geometry_result.boundary_rejection_count,
        exclusion_rejection_count=geometry_result.exclusion_rejection_count,
        exclusion_audit=geometry_result.exclusion_audit,
        warnings=warnings,
        blockers=(),
        deferred_capabilities=provenance_pre_hash.deferred_capabilities,
        provenance=provenance,
    )
    return TubeLayoutValidationResult(
        status=ValidationStatus.VALID,
        layout=layout,
        warnings=warnings,
        blockers=(),
        blocked_result_hash=None,
    )


__all__ = ["validate_request"]
