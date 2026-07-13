"""Binding fail-closed 21-stage validation pipeline for TASK-021 Slice A.

Stage ordinals (per §9 of the frozen design contract):
  1. raw top-level mapping and exact field-set validation
  2. raw value types before coercion
  3. schema versions
  4. TASK-020 configuration completeness and identity
  5. authority-mode match
  6. layout-rule profile, approval, snapshot hash, license, provenance, rule-pack
  7. tube-geometry approval, source, snapshot hash, dimensions
  8. envelope shape and positive effective radius
  9. origin and axis authorization
  10. exclusion-zone exact shapes, evidence arrays and duplicate zone IDs
  11. construction-family and U-tube presence/null prechecks
  12. inverse-basis construction, invertibility and candidate capacity
  13. enumeration and envelope filtering
  14. complete multi-zone exclusion evaluation and audit accumulation
  15. coordinate quantization and collision guard
  16. U-tube pairing validation and hash verification
  17. tube-hole and physical-tube counts
  18. deterministic warning emission
  19. provenance pre-hash projection
  20. request, layout, and output identity construction
  21. final output assembly
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hexagent.exchangers.shell_tube.models import ConstructionFamily

from .authority import (
    AuthorityFailure,
    verify_authority_mode_match,
    verify_geometry_snapshot,
    verify_layout_rule_profile,
    verify_task020_configuration,
)
from .canonical import (
    CanonicalizationError,
    dataclass_to_mapping,
    fragment_canonical,
    freeze_deeply,
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

# --------------------------------------------------------------------------- #
# Normalized-context accumulation
# --------------------------------------------------------------------------- #


class _NormalizedContext:
    """Mutable accumulator of fields successfully verified before a stage."""

    def __init__(self) -> None:
        self.payload: dict[str, Any] = {}

    def absorb(self, key: str, value: Any) -> None:
        if value is None:
            return
        self.payload[key] = freeze_deeply(value)

    # --------------------------------------------------------------------------- #


# Eligibility filtering per §§11.5-11.8
# --------------------------------------------------------------------------- #


def _filter_eligible_warnings(
    failure_stage: int,
    request: TubeLayoutRequest,
) -> tuple[MessageEntry, ...]:
    """Apply the §11.5-11.8 eligibility rules to the full warning set.

    A warning is emitted on a blocked result only if its prerequisite stage was
    passed before the failing stage.
    """

    collected: list[MessageEntry] = []
    rule = request.layout_rule_authority

    # §11.5 — INTERNAL_GENERIC_NO_STANDARD_CLAIM — requires stage 6+.
    if failure_stage > 6 and rule.authority_mode is AuthorityMode.INTERNAL_GENERIC:
        collected.append(
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

    # §11.6 — placement envelope+evidence verified — requires stage 8+.
    if failure_stage > 8:
        collected.append(
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

    # §11.7 — request.evidence_refs + tube_pass_count verified — requires stage 4+.
    if failure_stage > 4:
        collected.append(
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

    # §11.8 — U_TUBE + pairing plan + pairing evidence verified — requires stage 16+.
    if (
        failure_stage > 16
        and request.configuration.construction_family is ConstructionFamily.U_TUBE
        and request.u_tube_pairing_plan is not None
    ):
        collected.append(
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

    return tuple(collected)


# --------------------------------------------------------------------------- #
# Stage helpers (§11.2 retain complete blockers)
# --------------------------------------------------------------------------- #


def _geometry_stage_for(blocker_code: str) -> int:
    if blocker_code == BlockerCode.STL_COORDINATE_QUANTIZATION_COLLISION.value:
        return 15
    if blocker_code == BlockerCode.STL_NO_TUBE_POSITIONS.value:
        return 14
    # envelope-during-enumeration, default to stage 14
    return 14


def _blocked_result_payload(
    *,
    failure_stage: int,
    normalized_context: Mapping[str, Any],
    raw_failing_field: Any | None,
    eligible_warnings: tuple[MessageEntry, ...],
    blockers: tuple[MessageEntry, ...],
) -> dict[str, Any]:
    """Build the §12.8 blocked-result identity payload exactly per spec order."""

    canonical_blockers = sort_messages(blockers)
    canonical_warnings = sort_messages(eligible_warnings)
    frozen_context = freeze_deeply(dict(normalized_context))
    raw_frozen = None if raw_failing_field is None else fragment_canonical(raw_failing_field)
    blocker_records = tuple(
        freeze_deeply(dataclass_to_mapping(item)) for item in canonical_blockers
    )
    warning_records = tuple(
        freeze_deeply(dataclass_to_mapping(item)) for item in canonical_warnings
    )
    payload: dict[str, Any] = {
        "output_schema_version": LAYOUT_SCHEMA_VERSION,
        "failure_stage": failure_stage,
        "context": frozen_context,
        "raw_failing_field": raw_frozen,
        "eligible_warnings": warning_records,
        "blockers": blocker_records,
        "deferred_capabilities": list(DEFERRED_CAPABILITIES),
    }
    return payload


def _empty_blocked_payload(
    failure_stage: int,
    *,
    raw_failing_field: Any | None = None,
    normalized_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """A blocked payload with no blockers (defense-in-depth for unknown failures)."""

    context: dict[str, Any] = dict(normalized_context) if normalized_context else {}
    return _blocked_result_payload(
        failure_stage=failure_stage,
        normalized_context=context,
        raw_failing_field=raw_failing_field,
        eligible_warnings=(),
        blockers=(),
    )


def _build_blocked(
    failure_stage: int,
    blockers: tuple[MessageEntry, ...],
    *,
    raw_failing_field: Any | None = None,
    normalized_context: Mapping[str, Any] | None = None,
    eligible_warnings: tuple[MessageEntry, ...] = (),
) -> TubeLayoutValidationResult:
    context: dict[str, Any] = dict(normalized_context) if normalized_context else {}
    payload = _blocked_result_payload(
        failure_stage=failure_stage,
        normalized_context=context,
        raw_failing_field=raw_failing_field,
        eligible_warnings=eligible_warnings,
        blockers=blockers,
    )
    canonical_blockers = sort_messages(blockers)
    canonical_warnings = sort_messages(eligible_warnings)
    return TubeLayoutValidationResult(
        status=ValidationStatus.BLOCKED,
        layout=None,
        warnings=canonical_warnings,
        blockers=canonical_blockers,
        blocked_result_hash=sha256_hex(payload),
    )


# --------------------------------------------------------------------------- #
# Valid-pipeline helpers
# --------------------------------------------------------------------------- #


def _request_hash(request: TubeLayoutRequest) -> str:
    payload = dataclass_to_mapping(request)
    if request.u_tube_pairing_plan is not None:
        normalized_plan = request.u_tube_pairing_plan
        payload["u_tube_pairing_plan"]["pairs"] = [
            dataclass_to_mapping(pair) for pair in canonical_pairs(normalized_plan)
        ]
    return sha256_hex(payload)


def _warnings(request: TubeLayoutRequest) -> tuple[MessageEntry, ...]:
    rule = request.layout_rule_authority
    first: MessageEntry | None = (
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
        if rule.authority_mode is AuthorityMode.INTERNAL_GENERIC
        else None
    )
    collected: list[MessageEntry] = []
    if first is not None:
        collected.append(first)
    collected.append(
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
    collected.append(
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
        if request.u_tube_pairing_plan is None:
            raise AssertionError(
                "U_TUBE configuration requires u_tube_pairing_plan (defense-in-depth)"
            )
        collected.append(
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
    return sort_messages(tuple(collected))


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
        task020_case_authority=fragment_canonical(to_primitive(config.case_authority)),
        geometry_id=geometry.geometry_id,
        geometry_revision=geometry.revision,
        geometry_record_hash=geometry.record_hash,
        tube_geometry_snapshot_hash=geometry.snapshot_hash,
        geometry_source_binding=fragment_canonical(to_primitive(geometry.source_binding)),
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
        else fragment_canonical(to_primitive(rule.rule_pack_identity)),
        envelope_evidence_refs=request.placement_envelope.evidence_refs,
        exclusion_zone_evidence_refs=tuple(zone.evidence_refs for zone in request.exclusion_zones),
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


# --------------------------------------------------------------------------- #
# Main public entry — 21-stage pipeline
# --------------------------------------------------------------------------- #


def validate_request(
    payload: Any,
    *,
    software_version: str,
    git_commit: str,
) -> TubeLayoutValidationResult:
    """Validate one TASK-021 request and return a deterministic VALID/BLOCKED result.

    The pipeline follows §9 of the frozen design contract verbatim. On a blocked
    result the blocked_result_hash is SHA-256 over the §12.8 identity payload.
    """

    if not isinstance(software_version, str) or not software_version:
        raise ValueError("software_version must be a non-empty caller-supplied string")
    if not isinstance(git_commit, str) or not git_commit:
        raise ValueError("git_commit must be a non-empty caller-supplied string")

    normalized = _NormalizedContext()

    # --- Stages 1, 2, 3, 10 (raw schema) ---
    try:
        request = parse_request(payload)
        normalized.absorb("configuration", request.configuration)
    except SchemaFailure as exc:
        return _build_blocked(
            exc.stage,
            exc.blockers,
            raw_failing_field=exc.raw_failing_field,
            normalized_context=exc.normalized_context,
        )

    # All four core snapshots now verified (raw types, schema versions, top-level
    # mapping/field-set, exclusion zones). Capture them into the normalized
    # context so any later-stage blocked result reflects them faithfully.
    normalized.absorb("configuration", request.configuration)
    normalized.absorb("tube_geometry", request.tube_geometry)
    normalized.absorb("layout_rule_authority", request.layout_rule_authority)
    normalized.absorb("placement_envelope", request.placement_envelope)
    normalized.absorb("origin_mode", request.origin_mode.value)
    normalized.absorb("axis_orientation", request.axis_orientation.value)
    normalized.absorb(
        "exclusion_zones",
        [dataclass_to_mapping(z) for z in request.exclusion_zones],
    )
    normalized.absorb("u_tube_pairing_plan_present", request.u_tube_pairing_plan is not None)

    # --- Stage 4 — TASK-020 configuration completeness and identity ---
    try:
        verify_task020_configuration(request.configuration)
    except AuthorityFailure as exc:
        eligible = _filter_eligible_warnings(4, request)
        return _build_blocked(
            4,
            exc.blockers,
            raw_failing_field=request.configuration,
            normalized_context=normalized.payload,
            eligible_warnings=eligible,
        )

    # --- Stage 5 — authority-mode match ---
    try:
        verify_authority_mode_match(
            request.layout_rule_authority,
            request.configuration,
        )
    except AuthorityFailure as exc:
        eligible = _filter_eligible_warnings(5, request)
        return _build_blocked(
            5,
            exc.blockers,
            raw_failing_field=request.layout_rule_authority.authority_mode.value,
            normalized_context=normalized.payload,
            eligible_warnings=eligible,
        )

    # --- Stage 6 — layout-rule profile, approval, snapshot, license, provenance,
    #               rule-pack identity ---
    try:
        verify_layout_rule_profile(
            request.layout_rule_authority,
            request.configuration,
            request.tube_geometry,
        )
    except AuthorityFailure as exc:
        eligible = _filter_eligible_warnings(6, request)
        return _build_blocked(
            6,
            exc.blockers,
            raw_failing_field=request.layout_rule_authority,
            normalized_context=normalized.payload,
            eligible_warnings=eligible,
        )

    # --- Stage 7 — tube-geometry approval, source, snapshot hash, dimensions ---
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
        eligible = _filter_eligible_warnings(7, request)
        return _build_blocked(
            7,
            blockers,
            raw_failing_field=request.tube_geometry,
            normalized_context=normalized.payload,
            eligible_warnings=eligible,
        )

    # --- Stage 8 — envelope shape and positive effective radius ---
    construction_family = request.configuration.construction_family
    try:
        plan = build_plan(
            request.layout_rule_authority,
            request.tube_geometry,
            request.placement_envelope,
            request.origin_mode,
            request.axis_orientation,
        )
    except EnumerationFailure as exc:
        eligible = _filter_eligible_warnings(8, request)
        return _build_blocked(
            8,
            (exc.blocker,),
            raw_failing_field=request.placement_envelope,
            normalized_context=normalized.payload,
            eligible_warnings=eligible,
        )

    # --- Stage 9 — origin and axis authorization ---
    authorization_blockers = _validate_authorizations(request)
    if authorization_blockers:
        eligible = _filter_eligible_warnings(9, request)
        return _build_blocked(
            9,
            authorization_blockers,
            raw_failing_field={
                "origin_mode": request.origin_mode.value,
                "axis_orientation": request.axis_orientation.value,
            },
            normalized_context=normalized.payload,
            eligible_warnings=eligible,
        )

    # --- Stage 11 — construction-family and U-tube presence/null prechecks ---
    if construction_family is ConstructionFamily.U_TUBE and request.u_tube_pairing_plan is None:
        eligible = _filter_eligible_warnings(11, request)
        return _build_blocked(
            11,
            (
                MessageEntry(
                    code=BlockerCode.STL_UTUBE_PAIRING_REQUIRED.value,
                    field_path="u_tube_pairing_plan",
                    message_key="u_tube_pairing_required",
                ),
            ),
            raw_failing_field=None,
            normalized_context=normalized.payload,
            eligible_warnings=eligible,
        )
    if (
        construction_family is not ConstructionFamily.U_TUBE
        and request.u_tube_pairing_plan is not None
    ):
        eligible = _filter_eligible_warnings(11, request)
        return _build_blocked(
            11,
            (
                MessageEntry(
                    code=BlockerCode.STL_UTUBE_PAIRING_NOT_EXPECTED.value,
                    field_path="u_tube_pairing_plan",
                    message_key="u_tube_pairing_not_expected",
                ),
            ),
            raw_failing_field=request.u_tube_pairing_plan,
            normalized_context=normalized.payload,
            eligible_warnings=eligible,
        )

    # --- Stage 12 — inverse-basis, invertibility, candidate capacity ---
    try:
        candidates = enumerate_candidates(plan)
    except EnumerationFailure as exc:
        eligible = _filter_eligible_warnings(12, request)
        return _build_blocked(
            12,
            (exc.blocker,),
            raw_failing_field=plan.candidate_count,
            normalized_context=normalized.payload,
            eligible_warnings=eligible,
        )

    # --- Stages 13 / 14 / 15 — envelope filter / multi-zone exclusion / quantization ---
    try:
        geometry_result = evaluate_geometry(
            candidates,
            plan,
            request.tube_geometry,
            request.exclusion_zones,
        )
    except GeometryFailure as exc:
        stage = _geometry_stage_for(exc.blocker.code)
        eligible = _filter_eligible_warnings(stage, request)
        return _build_blocked(
            stage,
            (exc.blocker,),
            raw_failing_field=geometry_result_payload_safe(geometry_result),
            normalized_context=normalized.payload,
            eligible_warnings=eligible,
        )

    physical_tube_count = len(geometry_result.accepted)
    normalized_plan = request.u_tube_pairing_plan

    # --- Stage 16 — U-tube pairing validation and hash verification ---
    if construction_family is ConstructionFamily.U_TUBE:
        if request.u_tube_pairing_plan is None:
            raise AssertionError(
                "U_TUBE configuration requires u_tube_pairing_plan (defense-in-depth)"
            )
        try:
            normalized_plan, physical_tube_count = validate_pairing_plan(
                request.u_tube_pairing_plan,
                geometry_result.accepted,
            )
        except PairingFailure as exc:
            eligible = _filter_eligible_warnings(16, request)
            return _build_blocked(
                16,
                exc.blockers,
                raw_failing_field=request.u_tube_pairing_plan,
                normalized_context=normalized.payload,
                eligible_warnings=eligible,
            )
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

    # --- Stage 17 — tube-hole and physical-tube count ---
    tube_hole_count = len(geometry_result.accepted)
    normalized.absorb("tube_hole_count", tube_hole_count)
    normalized.absorb("physical_tube_count", physical_tube_count)

    # --- Stage 18 — deterministic warning emission ---
    warnings = _warnings(request)

    # --- Stage 19 — provenance pre-hash projection ---
    provenance_pre_hash = _provenance(
        request,
        _request_hash(request),
        warnings,
        software_version=software_version,
        git_commit=git_commit,
    )

    # --- Stage 20 — request, layout, and output identity construction ---
    request_hash = provenance_pre_hash.request_hash
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
    layout_hash_payload = {
        "schema_version": LAYOUT_SCHEMA_VERSION,
        "request_hash": request_hash,
        "positions": [dataclass_to_mapping(position) for position in positions],
        "tube_hole_count": len(positions),
        "physical_tube_count": physical_tube_count,
        "boundary_rejection_count": geometry_result.boundary_rejection_count,
        "exclusion_rejection_count": geometry_result.exclusion_rejection_count,
        "exclusion_audit": [dataclass_to_mapping(item) for item in geometry_result.exclusion_audit],
        "warnings": [dataclass_to_mapping(item) for item in warnings],
        "blockers": [],
        "deferred_capabilities": list(provenance_pre_hash.deferred_capabilities),
        "provenance_pre_hash": dataclass_to_mapping(provenance_pre_hash),
    }
    layout_hash = sha256_hex(layout_hash_payload)
    provenance = dataclass_to_mapping(provenance_pre_hash)
    provenance["layout_hash"] = layout_hash

    # --- Stage 21 — final output assembly ---
    layout = TubeLayout(
        schema_version=LAYOUT_SCHEMA_VERSION,
        layout_id=layout_id(layout_hash),
        layout_hash=layout_hash,
        request_hash=request_hash,
        task020_configuration_id=request.configuration.configuration_id,
        task020_configuration_hash=request.configuration.configuration_hash,
        case_authority=to_primitive(request.configuration.case_authority),
        construction_family=request.configuration.construction_family.value,
        equipment_orientation=request.configuration.orientation,
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


def geometry_result_payload_safe(
    geometry_result: object | None,
) -> Mapping[str, Any] | None:
    """Render a geometry result into a primitive mapping, or None on failure.

    Used as the raw_failing_field payload when a geometry-stage blocker fires
    before accepted coordinates are available. Returning None (rather than a
    half-formed primitive) keeps the §12.8 contract: raw_failing_field is null
    when canonical raw JSON for the failing field does not exist.
    """

    if geometry_result is None:
        return None
    try:
        mapping = dataclass_to_mapping(geometry_result)
    except (TypeError, ValueError):
        return None
    return mapping


__all__ = ["geometry_result_payload_safe", "validate_request"]
