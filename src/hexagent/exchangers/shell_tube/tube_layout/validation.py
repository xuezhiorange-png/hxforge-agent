"""Binding fail-closed 21-stage validation pipeline for TASK-021 Slice A.

Stage ordinals (per §9 of the frozen design contract):
  1. raw top-level mapping and exact field-set validation
  2. raw value types before coercion
  3. schema versions
  4. TASK-020 configuration completeness and identity
  5. authority-mode match
  6. layout-rule profile, approval, snapshot hash, license, provenance and
     rule-pack identity
  7. tube-geometry approval, source binding, snapshot hash and dimensions
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

Each stage is enforced in order. A failure at any stage aborts the pipeline;
**no later stage runs**, all complete blockers from that stage are retained
(§11.2), and the §12.8 blocked-result identity is computed exactly once.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from hexagent.exchangers.shell_tube.models import (
    ConstructionFamily,
)

from .authority import (
    AuthorityFailure,
    verify_authority_mode_match,
    verify_geometry_snapshot,
    verify_layout_rule_profile,
    verify_task020_configuration,
)
from .canonical import (
    CanonicalizationError,
    canonical_raw_json_or_none,
    dataclass_to_mapping,
    frozen_fragment_to_primitive,
    layout_id,
    position_id,
    refreeze_internal_fragment,
    sha256_hex,
    snapshot_then_to_primitive,
    sort_messages,
)
from .enumeration import (
    Candidate,
    EnumerationFailure,
    enumerate_candidates,
    verify_envelope_shape_and_radius,
    verify_inverse_basis_and_candidate_capacity,
)
from .geometry import (
    GeometryFailure,
    coordinate_quantization_collision_guard,
    enumeration_envelope_filter,
    multi_zone_exclusion_evaluation,
)
from .models import (
    DEFERRED_CAPABILITIES,
    DESIGN_CONTRACT_PATH,
    ENVELOPE_SCHEMA_VERSION,
    LAYOUT_SCHEMA_VERSION,
    PAIRING_SCHEMA_VERSION,
    AuthorityMode,
    BlockerCode,
    CircularTubeCenterEnvelope,
    ExclusionZone,
    MessageEntry,
    ProvenancePreHashProjection,
    TubeLayout,
    TubeLayoutRequest,
    TubeLayoutValidationResult,
    TubePosition,
    UTubePairingPlan,
    ValidationStatus,
    WarningCode,
)
from .pairing import PairingFailure, canonical_pairs, validate_pairing_plan
from .schema import (
    REQUEST_SCHEMA_VERSION,
    SchemaFailure,
    Stage2Result,
    Stage3Result,
    canonical_mapping,
    collect_stage2,
    validate_all_schema_versions,
    validate_top_level_mapping,
)

# --------------------------------------------------------------------------- #
# §11.5-11.8 warning eligibility
# --------------------------------------------------------------------------- #


def _filter_eligible_warnings(
    failure_stage: int,
    request: TubeLayoutRequest,
) -> tuple[MessageEntry, ...]:
    """Apply the §11.5-11.8 eligibility rules to the full warning set.

    A warning is emitted on a blocked result only if its prerequisite stage was
    passed before the failing stage. Round-3 §3 (P0-1) requires this gating to
    operate on the actual stage ordinal.
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


def _build_partial_request(
    *,
    configuration: Any,
    tube_geometry: Any,
    layout_rule_authority: Any,
    placement_envelope: Any,
    origin_mode: Any,
    axis_orientation: Any,
    u_tube_pairing_plan: Any,
    evidence_refs: Any,
) -> TubeLayoutRequest:
    """Build a request skeleton for §11.5-11.8 eligibility checks.

    The pipeline fails-fast at each stage, so the failing-stage branch does
    not have a fully-constructed ``TubeLayoutRequest``. This helper assembles
    one with the verified fragments so ``_filter_eligible_warnings`` can read
    the prerequisite fields (e.g. ``layout_rule_authority.authority_mode``,
    ``placement_envelope.evidence_refs``) before deciding whether to emit each
    warning.
    """

    from .models import TubeLayoutRequest as _TLR

    return _TLR(
        schema_version=REQUEST_SCHEMA_VERSION,
        configuration=configuration,
        tube_geometry=tube_geometry,
        layout_rule_authority=layout_rule_authority,
        placement_envelope=placement_envelope,
        origin_mode=origin_mode,
        axis_orientation=axis_orientation,
        exclusion_zones=(),
        u_tube_pairing_plan=u_tube_pairing_plan,
        evidence_refs=evidence_refs,
    )


# --------------------------------------------------------------------------- #
# Round 4 P0-3 — unified `build_stage_blocked` helper for Stages 4-16
# --------------------------------------------------------------------------- #


def build_stage_blocked(
    *,
    failure_stage: int,
    blockers: tuple[MessageEntry, ...],
    verified_request_context: TubeLayoutRequest,
    raw_failing_field: Any | None = None,
    normalized_context: Mapping[str, Any] | None = None,
) -> TubeLayoutValidationResult:
    """Round 4 P0-3 unified Stage 4-16 blocked-result constructor.

    Computes the eligible warning set per §11.5-§11.8 against the verified
    request skeleton, then funnels both into :func:`_build_blocked` to build
    the final ``TubeLayoutValidationResult``. ``eligible_warnings`` is
    included in the §12.8 blocked_result_hash so any eligibility-rule change
    changes the hash.

    This is the single source of truth for blocked-result identity across
    Stages 4-16; no branch may bypass it.
    """

    eligible = _filter_eligible_warnings(failure_stage, verified_request_context)
    return _build_blocked(
        failure_stage,
        blockers,
        raw_failing_field=raw_failing_field,
        normalized_context=normalized_context,
        eligible_warnings=eligible,
    )


# --------------------------------------------------------------------------- #
# §12.8 blocked-result identity payload
# --------------------------------------------------------------------------- #


def _blocked_result_payload(
    *,
    failure_stage: int,
    normalized_context: Mapping[str, Any],
    raw_failing_field: Any | None,
    eligible_warnings: tuple[MessageEntry, ...],
    blockers: tuple[MessageEntry, ...],
) -> dict[str, Any]:
    """Build the §12.8 blocked-result identity payload exactly per spec order.

    Round-3 §5 (P0-3): ``raw_failing_field`` uses ``canonical_raw_json_or_none``
    so that non-canonical inputs (float, bytes, Decimal, non-string-keyed
    mapping, arbitrary object) become ``None`` rather than re-raising
    CanonicalizationError during blocked-result construction.
    """

    canonical_blockers = sort_messages(blockers)
    canonical_warnings = sort_messages(eligible_warnings)

    # Round-3 §6 (P1-1): every canonical JSON fragment must traverse the
    # public boundary `strict_public_json_snapshot`. Then hash reduction uses
    # `frozen_fragment_to_primitive`. `canonical_json` itself rejects out-of-
    # domain types (float, Decimal, bytes, tuple, frozenset, set, arbitrary).
    from .canonical import (
        frozen_fragment_to_primitive as _reduce_frozen,
    )
    from .canonical import (
        strict_public_json_snapshot as _snapshot_public,
    )

    def _entry_primitive(entry: MessageEntry) -> dict[str, Any]:
        # Convert the dataclass into a literal canonical dict, then route it
        # through the public snapshot boundary so a mutation in entry after
        # capture cannot influence the blocked_result_hash. Round-4 §6
        # P0-4 deep-freezes ``details`` in MessageEntry.__post_init__; that
        # means at this point ``entry.details`` is already a public-boundary
        # frozen shape (MappingProxyType) OR None. Reduce it via the
        # fragment-to-primitive path so re-snapshotting does not reject it.
        details = entry.details
        if details is None:
            details_primitive: Any = None
        elif isinstance(details, MappingProxyType):
            details_primitive = _reduce_frozen(details)
        else:
            details_primitive = _reduce_frozen(_snapshot_public(details))
        primitive = {
            "code": entry.code,
            "field_path": entry.field_path,
            "message_key": entry.message_key,
            "evidence_refs": list(entry.evidence_refs),
            "details": details_primitive,
        }
        frozen = _snapshot_public(primitive)
        return _reduce_frozen(frozen)  # type: ignore[no-any-return]  # _reduce_frozen returns dict-like at this point.

    # Failure-stage ordering matters even for the normalized context. The
    # context is itself a canonical mapping of already-verified primitives
    # plus some dataclass instances (e.g. configuration, basis). Reduce each
    # value via ``to_primitive`` so the snapshot boundary only sees canonical
    # JSON-domain inputs.
    def _reduce_context_value(value: Any) -> Any:
        # Round 5 §4.1 + §4.3: this reducer is the single entry point for
        # every value that flows into the frozen ``normalized_context``.
        # It MUST:
        #   * accept only canonical JSON-domain primitives (null / bool /
        #     int / str / list of canonical values / string-keyed dict
        #     of canonical values); and
        #   * reject Decimal / float / bytes / tuple / set / frozenset /
        #     arbitrary object / non-string-keyed mapping AT THIS BOUNDARY
        #     rather than silently coercing them.
        # Internal callers that need Decimal or other non-JSON-domain
        # values MUST convert them to canonical decimal strings BEFORE
        # they reach this reducer — that's the round 5 §4.3 contract.
        if value is None or isinstance(value, (bool, int, str)):
            return value
        if dataclasses.is_dataclass(value):
            return _reduce_context_value(dataclass_to_mapping(value))
        if isinstance(value, MappingProxyType):
            # Already-frozen fragment: reduce to a sorted-key primitive
            # mapping so the public snapshot boundary accepts it.
            return {key: _reduce_context_value(item) for key, item in sorted(value.items())}
        if isinstance(value, (tuple, list)):
            return [_reduce_context_value(item) for item in value]
        if isinstance(value, dict):
            primitive: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise CanonicalizationError("normalized_context mapping keys must be strings")
                primitive[key] = _reduce_context_value(item)
            return primitive
        # Round 5 §4.3: Decimal, float, bytes, arbitrary objects — fail
        # closed rather than silently coercing.
        if isinstance(value, Decimal):
            raise CanonicalizationError(
                "Decimal must be converted to a canonical decimal string before "
                "reaching normalized_context"
            )
        if isinstance(value, float):
            raise CanonicalizationError(
                "binary floating-point values are forbidden at context boundary"
            )
        if isinstance(value, (bytes, bytearray, memoryview)):
            raise CanonicalizationError("byte strings are forbidden at context boundary")
        raise CanonicalizationError(f"unsupported canonical context value: {type(value).__name__}")

    context_primitive: dict[str, Any] = {}
    for key, item in dict(normalized_context).items():
        context_primitive[key] = _reduce_context_value(item)
    frozen_context = _snapshot_public(context_primitive)
    raw_primitive = canonical_raw_json_or_none(raw_failing_field)
    if raw_primitive is None:
        raw_reduced: Any = None
    else:
        raw_reduced = _reduce_frozen(_snapshot_public(raw_primitive))

    blocker_records = tuple(_entry_primitive(item) for item in canonical_blockers)
    warning_records = tuple(_entry_primitive(item) for item in canonical_warnings)
    return {
        "output_schema_version": LAYOUT_SCHEMA_VERSION,
        "failure_stage": failure_stage,
        "context": _reduce_frozen(frozen_context),
        "raw_failing_field": raw_reduced,
        "eligible_warnings": list(warning_records),
        "blockers": list(blocker_records),
        "deferred_capabilities": list(DEFERRED_CAPABILITIES),
    }


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
# Valid-pipeline helpers (Stages 17-21)
# --------------------------------------------------------------------------- #


def _request_hash(request: TubeLayoutRequest) -> str:
    payload = dataclass_to_mapping(request)
    if request.u_tube_pairing_plan is not None:
        canonical_plan = request.u_tube_pairing_plan
        payload["u_tube_pairing_plan"]["pairs"] = [
            dataclass_to_mapping(pair) for pair in canonical_pairs(canonical_plan)
        ]
    return sha256_hex(payload)


def _warnings(request: TubeLayoutRequest) -> tuple[MessageEntry, ...]:
    rule = request.layout_rule_authority
    collected: list[MessageEntry] = []
    if rule.authority_mode is AuthorityMode.INTERNAL_GENERIC:
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


def _build_provenance_projection(
    request: TubeLayoutRequest,
    request_hash: str,
    warnings: tuple[MessageEntry, ...],
    *,
    software_version: str,
    git_commit: str,
) -> ProvenancePreHashProjection:
    """Build the §12.6 provenance pre-hash projection.

    All canonical JSON fragments MUST be passed through
    ``strict_public_json_snapshot`` so that post-capture mutation cannot
    influence the captured value.
    """

    config = request.configuration
    rule = request.layout_rule_authority
    geometry = request.tube_geometry
    # canonical_mapping accepts only canonical JSON domain inputs; convert the
    # upstream dataclasses to a primitive mapping first so the public boundary
    # only sees frozen shapes.
    case_authority_primitive: dict[str, Any] = dataclass_to_mapping(config.case_authority)
    geometry_source_primitive: dict[str, Any] = dataclass_to_mapping(geometry.source_binding)
    rule_pack_primitive: dict[str, Any] | None = (
        None if rule.rule_pack_identity is None else dataclass_to_mapping(rule.rule_pack_identity)
    )
    # Each public boundary snapshot is taken from the ORDINARY primitive
    # mapping produced above, so callers cannot mutate the captured value.
    case_authority_frozen = canonical_mapping(case_authority_primitive)
    geometry_source_frozen = canonical_mapping(geometry_source_primitive)
    rule_pack_frozen: Any = (
        None if rule_pack_primitive is None else canonical_mapping(rule_pack_primitive)
    )
    return ProvenancePreHashProjection(
        task_id="TASK-021",
        design_contract_path=DESIGN_CONTRACT_PATH,
        task020_configuration_id=config.configuration_id,
        task020_configuration_hash=config.configuration_hash,
        task020_case_authority=case_authority_frozen,
        geometry_id=geometry.geometry_id,
        geometry_revision=geometry.revision,
        geometry_record_hash=geometry.record_hash,
        tube_geometry_snapshot_hash=geometry.snapshot_hash,
        geometry_source_binding=geometry_source_frozen,
        layout_rule_profile_id=rule.profile_id,
        layout_rule_id=rule.rule_id,
        layout_rule_version=rule.rule_version,
        rule_artifact_canonical_hash=rule.rule_artifact_canonical_hash,
        layout_rule_snapshot_hash=rule.snapshot_hash,
        source_class=rule.source_class,
        approval_status=rule.approval_status,
        provenance_edge_ids=rule.provenance_edge_ids,
        layout_rule_evidence_refs=rule.evidence_refs,
        rule_pack_identity=rule_pack_frozen,
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


def _validate_authorizations(
    request: TubeLayoutRequest,
    zones: tuple[ExclusionZone, ...],
) -> tuple[MessageEntry, ...]:
    """Stage 9 — origin, axis, and exclusion-zone-type authorization."""

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
    for zone in zones:
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


def _parse_zones_for_stage_10(
    raw_zones: Any,
) -> tuple[ExclusionZone, ...]:
    """Stage 10 — exclusion-zone exact shapes + duplicate ID detection.

    Round 5 §5.4 mandates that this stage:
        1. Verify ``raw_zones`` is a list (array_required blocker if not);
        2. Validate every zone INDEPENDENTLY through ``parse_zone``;
        3. Collect every per-zone ``SchemaFailure`` blocker;
        4. Run duplicate-ID detection ONLY against zones that successfully
           parsed and have a non-empty ``zone_id``;
        5. Surface the COMPLETE blocker set on any failure;
        6. Abort at stage 10 — no Stage 11+ work runs.
    """

    from .schema import StageAccumulator

    if not isinstance(raw_zones, list):
        raise SchemaFailure(
            10,
            (
                MessageEntry(
                    code=BlockerCode.STL_RAW_TYPE_INVALID.value,
                    field_path="exclusion_zones",
                    message_key="array_required",
                ),
            ),
            raw_failing_field=raw_zones,
        )

    acc = StageAccumulator()
    parsed_zones: list[ExclusionZone] = []

    from .schema import parse_zone as _parse_zone_helper

    for index, item in enumerate(raw_zones):
        inner_field_path = f"exclusion_zones[{index}]"
        try:
            zone = _parse_zone_helper(item, index)
        except SchemaFailure as exc:
            # Per-zone failure → collect blocker but continue with the
            # rest of the zones. Round 5 §5.4 forbids short-circuiting
            # the entire zone list because one zone had a shape failure.
            acc.blockers.extend(exc.blockers)
            continue
        parsed_zones.append(zone)
        acc.values[inner_field_path] = zone

    # Round 5 §5.4: duplicate-ID detection only against the zones that
    # successfully parsed and have a non-empty zone_id.
    seen_ids: dict[str, int] = {}
    for zone in parsed_zones:
        if not zone.zone_id:
            continue
        if zone.zone_id in seen_ids:
            acc.blockers.append(
                MessageEntry(
                    code=BlockerCode.STL_EXCLUSION_ZONE_DUPLICATE_ID.value,
                    field_path=f"exclusion_zones.{zone.zone_id}",
                    message_key="duplicate_zone_id",
                )
            )
        else:
            seen_ids[zone.zone_id] = 1

    if acc.blockers:
        raise SchemaFailure(
            10,
            tuple(acc.blockers),
            raw_failing_field=None,
        )

    # Round 5 §5.4: deterministic ordering by zone_id (canonical).
    return tuple(sorted(parsed_zones, key=lambda z: z.zone_id))


# --------------------------------------------------------------------------- #
# Main public entry — strict 21-stage pipeline
# --------------------------------------------------------------------------- #


def validate_request(
    payload: Any,
    *,
    software_version: str,
    git_commit: str,
) -> TubeLayoutValidationResult:
    """Validate one TASK-021 request and return a deterministic VALID/BLOCKED result.

    Strict §9 ordering; a stage failure aborts the pipeline and later stages
    do not run. The blocked_result_hash is SHA-256 over the §12.8 identity
    payload, built only once when an abort happens.
    """

    if not isinstance(software_version, str) or not software_version:
        raise ValueError("software_version must be a non-empty caller-supplied string")
    if not isinstance(git_commit, str) or not git_commit:
        raise ValueError("git_commit must be a non-empty caller-supplied string")

    # --- Stage 1 — top-level mapping and exact field set ---
    try:
        data = validate_top_level_mapping(payload)
    except SchemaFailure as exc:
        return _build_blocked(
            exc.stage,
            exc.blockers,
            raw_failing_field=exc.raw_failing_field,
            normalized_context=exc.normalized_context,
        )

    # --- Stage 2 — raw value types, COMPLETE-blocker per-field collection ---
    stage2: Stage2Result = collect_stage2(data)
    if not stage2.passed:
        # Round 5 §4.2: ``normalized_context`` MUST NOT carry raw failing
        # values. Only canonical metadata describing which fields failed
        # is allowed; raw values are surfaced via §12.8 identity through
        # ``raw_failing_field`` (single primary raw) only.
        blockers_2 = tuple(stage2.all_blockers)
        failed_paths = stage2.failed_field_paths
        primary_raw = stage2.primary_raw_failing_field
        return _build_blocked(
            2,
            blockers_2,
            raw_failing_field=primary_raw,
            normalized_context={
                "stage2_blockers": blockers_2,
                "failed_field_paths": failed_paths,
            },
        )

    # --- Stage 3 — schema versions, ALL three checks atomically AFTER Stage 2 ---
    # Round 5 §3.1: every Stage-2 raw check already validated the
    # schema_version string's raw type and non-emptiness. We now use the
    # validated strings from the Stage-2 results — NOT raw access of the
    # payload dict — so Stage 3 only does version equality comparison.
    from .schema import EnvelopeRaw as _EnvelopeRawT
    from .schema import PairingPlanRaw as _PairingPlanRawT

    envelope_raw_obj = stage2.placement_envelope.value
    pairing_raw_obj = stage2.u_tube_pairing_plan.value
    assert isinstance(envelope_raw_obj, _EnvelopeRawT)
    envelope_schema_version: str = envelope_raw_obj.schema_version
    pairing_schema_version: str | None
    pairing_field_path: str | None
    if pairing_raw_obj is None:
        pairing_schema_version = None
        pairing_field_path = None
    else:
        assert isinstance(pairing_raw_obj, _PairingPlanRawT)
        pairing_schema_version = pairing_raw_obj.schema_version
        pairing_field_path = "u_tube_pairing_plan.schema_version"
    stage3: Stage3Result = validate_all_schema_versions(
        request_schema_version=stage2.request_schema_version.value,
        envelope_schema_version=envelope_schema_version,
        envelope_field_path="placement_envelope.schema_version",
        pairing_schema_version=pairing_schema_version,
        pairing_field_path=pairing_field_path,
    )
    if not stage3.passed:
        # Stage 3 BLOCKED: no Stage 4+ work runs.
        return _build_blocked(
            3,
            stage3.blockers,
            raw_failing_field=None,
            normalized_context={
                "stage3_blockers": stage3.blockers,
                "failed_field_paths": stage3.failed_field_paths,
            },
        )

    # --- Build canonical fragments from the Stage 2/3-validated intermediates ---
    from .schema import EnvelopeRaw, PairingPlanRaw

    configuration = stage2.configuration.value
    tube_geometry = stage2.tube_geometry.value
    layout_rule_authority = stage2.layout_rule_authority.value
    envelope_raw = stage2.placement_envelope.value
    assert isinstance(envelope_raw, EnvelopeRaw)
    # Round 4: schema_version already verified at Stage 3; build the canonical
    # envelope directly from the Stage-2-preserved raw without re-running
    # Stage 2 shape checks.
    placement_envelope = CircularTubeCenterEnvelope(
        schema_version=ENVELOPE_SCHEMA_VERSION,
        tube_center_envelope_diameter_m=envelope_raw.tube_center_envelope_diameter_m,
        evidence_refs=envelope_raw.evidence_refs,
    )
    origin_mode = stage2.origin_mode.value
    axis_orientation = stage2.axis_orientation.value
    pairing_raw = stage2.u_tube_pairing_plan.value
    if pairing_raw is None:
        u_tube_pairing_plan = None
    else:
        assert isinstance(pairing_raw, PairingPlanRaw)
        # Round 4: schema_version already verified at Stage 3; build the
        # canonical pairing plan directly from Stage-2-preserved raw.
        u_tube_pairing_plan = UTubePairingPlan(
            schema_version=PAIRING_SCHEMA_VERSION,
            pairs=pairing_raw.pairs,
            evidence_refs=pairing_raw.evidence_refs,
            pairing_plan_hash=pairing_raw.pairing_plan_hash,
        )
    evidence_refs = stage2.evidence_refs.value

    # Helper: build a Stage-4+ blocked result from the Stage-2 + verified
    # partial-request skeleton, falling through to ``_build_blocked`` so the
    # eligibility warning set is always computed (round-4 P0-3).
    def _partial_then_block(
        *,
        failure_stage: int,
        blockers: tuple[MessageEntry, ...],
        raw_failing_field: Any | None = None,
        normalized_context: Mapping[str, Any] | None = None,
        zones: tuple[ExclusionZone, ...] = (),
    ) -> TubeLayoutValidationResult:
        partial = _build_partial_request(
            configuration=configuration,
            tube_geometry=tube_geometry,
            layout_rule_authority=layout_rule_authority,
            placement_envelope=placement_envelope,
            origin_mode=origin_mode,
            axis_orientation=axis_orientation,
            u_tube_pairing_plan=u_tube_pairing_plan,
            evidence_refs=evidence_refs,
        )
        # If the failing stage runs after Zone parsing (Stage 10+), the
        # caller may pass ``zones``; rebuild the partial with zones too.
        if zones:
            partial = TubeLayoutRequest(
                schema_version=REQUEST_SCHEMA_VERSION,
                configuration=configuration,
                tube_geometry=tube_geometry,
                layout_rule_authority=layout_rule_authority,
                placement_envelope=placement_envelope,
                origin_mode=origin_mode,
                axis_orientation=axis_orientation,
                exclusion_zones=zones,
                u_tube_pairing_plan=u_tube_pairing_plan,
                evidence_refs=evidence_refs,
            )
        return build_stage_blocked(
            failure_stage=failure_stage,
            blockers=blockers,
            verified_request_context=partial,
            raw_failing_field=raw_failing_field,
            normalized_context=normalized_context,
        )

    # --- Stage 4 — TASK-020 configuration completeness and identity ---
    try:
        verify_task020_configuration(configuration)
    except AuthorityFailure as exc:
        return _partial_then_block(
            failure_stage=4,
            blockers=exc.blockers,
            raw_failing_field=configuration,
            normalized_context={"configuration": configuration},
        )

    # --- Stage 5 — authority-mode match ---
    try:
        verify_authority_mode_match(layout_rule_authority, configuration)
    except AuthorityFailure as exc:
        return _partial_then_block(
            failure_stage=5,
            blockers=exc.blockers,
            raw_failing_field=layout_rule_authority.authority_mode.value,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority_authority_mode": layout_rule_authority.authority_mode.value,
            },
        )

    # --- Stage 6 — layout-rule profile, approval, snapshot, license, provenance,
    #               rule-pack identity ---
    try:
        verify_layout_rule_profile(layout_rule_authority, configuration, tube_geometry)
    except AuthorityFailure as exc:
        return _partial_then_block(
            failure_stage=6,
            blockers=exc.blockers,
            raw_failing_field=layout_rule_authority,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
            },
        )

    # --- Stage 7 — tube-geometry approval, source, snapshot hash, dimensions ---
    try:
        verify_geometry_snapshot(tube_geometry)
    except AuthorityFailure as exc:
        return _partial_then_block(
            failure_stage=7,
            blockers=exc.blockers,
            raw_failing_field=tube_geometry,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
                "tube_geometry": tube_geometry,
            },
        )

    # --- Stage 8 — envelope shape and positive effective radius ONLY ---
    try:
        stage8 = verify_envelope_shape_and_radius(
            layout_rule_authority,
            tube_geometry,
            placement_envelope,
            origin_mode,
            axis_orientation,
        )
    except EnumerationFailure as exc:
        return _partial_then_block(
            failure_stage=8,
            blockers=(exc.blocker,),
            raw_failing_field=placement_envelope,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
                "tube_geometry": tube_geometry,
                "placement_envelope": placement_envelope,
                "origin_mode": origin_mode.value,
                "axis_orientation": axis_orientation.value,
            },
        )

    # --- Stage 9 — origin and axis authorization (zones not yet parsed) ---
    # We must check origin/axis BEFORE zone parsing per §9 ordering; zone type
    # authorization runs in Stage 10 once zones exist.
    rule = layout_rule_authority
    blockers_9: list[MessageEntry] = []
    if origin_mode not in rule.allowed_origin_modes:
        blockers_9.append(
            MessageEntry(
                code=BlockerCode.STL_ORIGIN_MODE_NOT_AUTHORIZED.value,
                field_path="origin_mode",
                message_key="origin_mode_not_authorized",
            )
        )
    if axis_orientation not in rule.allowed_axis_orientations:
        blockers_9.append(
            MessageEntry(
                code=BlockerCode.STL_AXIS_ORIENTATION_NOT_AUTHORIZED.value,
                field_path="axis_orientation",
                message_key="axis_orientation_not_authorized",
            )
        )
    if blockers_9:
        return _partial_then_block(
            failure_stage=9,
            blockers=tuple(blockers_9),
            raw_failing_field={
                "origin_mode": origin_mode.value,
                "axis_orientation": axis_orientation.value,
            },
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
                "tube_geometry": tube_geometry,
                "placement_envelope": placement_envelope,
                "origin_mode": origin_mode.value,
                "axis_orientation": axis_orientation.value,
            },
        )

    # --- Stage 10 — exclusion-zone exact shapes + duplicate zone IDs ---
    try:
        zones = _parse_zones_for_stage_10(data["exclusion_zones"])
    except SchemaFailure as exc:
        return _partial_then_block(
            failure_stage=10,
            blockers=exc.blockers,
            raw_failing_field=exc.raw_failing_field,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
                "tube_geometry": tube_geometry,
                "placement_envelope": placement_envelope,
                "origin_mode": origin_mode.value,
                "axis_orientation": axis_orientation.value,
            },
        )
    zone_type_blockers = [
        MessageEntry(
            code=BlockerCode.STL_EXCLUSION_ZONE_TYPE_NOT_AUTHORIZED.value,
            field_path=f"exclusion_zones.{zone.zone_id}.zone_type",
            message_key="exclusion_zone_type_not_authorized",
            evidence_refs=zone.evidence_refs,
        )
        for zone in zones
        if zone.zone_type not in rule.allowed_exclusion_zone_types
    ]
    if zone_type_blockers:
        return _partial_then_block(
            failure_stage=10,
            blockers=tuple(zone_type_blockers),
            raw_failing_field=[zone.zone_type.value for zone in zones],
            zones=zones,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
                "tube_geometry": tube_geometry,
                "placement_envelope": placement_envelope,
                "origin_mode": origin_mode.value,
                "axis_orientation": axis_orientation.value,
                "exclusion_zones": zones,
            },
        )

    # Rebuild the request with zones populated. This completes the
    # Stage-1..Stage-10 verified request skeleton.
    request = TubeLayoutRequest(
        schema_version=REQUEST_SCHEMA_VERSION,
        configuration=configuration,
        tube_geometry=tube_geometry,
        layout_rule_authority=layout_rule_authority,
        placement_envelope=placement_envelope,
        origin_mode=origin_mode,
        axis_orientation=axis_orientation,
        exclusion_zones=zones,
        u_tube_pairing_plan=u_tube_pairing_plan,
        evidence_refs=evidence_refs,
    )

    # --- Stage 11 — construction-family + U-tube presence/null prechecks ---
    if (
        configuration.construction_family is ConstructionFamily.U_TUBE
        and request.u_tube_pairing_plan is None
    ):
        return build_stage_blocked(
            failure_stage=11,
            blockers=(
                MessageEntry(
                    code=BlockerCode.STL_UTUBE_PAIRING_REQUIRED.value,
                    field_path="u_tube_pairing_plan",
                    message_key="u_tube_pairing_required",
                ),
            ),
            verified_request_context=request,
            raw_failing_field=None,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
                "tube_geometry": tube_geometry,
                "placement_envelope": placement_envelope,
                "origin_mode": origin_mode.value,
                "axis_orientation": axis_orientation.value,
                "exclusion_zones": zones,
            },
        )
    if (
        configuration.construction_family is not ConstructionFamily.U_TUBE
        and request.u_tube_pairing_plan is not None
    ):
        return build_stage_blocked(
            failure_stage=11,
            blockers=(
                MessageEntry(
                    code=BlockerCode.STL_UTUBE_PAIRING_NOT_EXPECTED.value,
                    field_path="u_tube_pairing_plan",
                    message_key="u_tube_pairing_not_expected",
                ),
            ),
            verified_request_context=request,
            raw_failing_field=request.u_tube_pairing_plan,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
                "tube_geometry": tube_geometry,
                "placement_envelope": placement_envelope,
                "origin_mode": origin_mode.value,
                "axis_orientation": axis_orientation.value,
                "exclusion_zones": zones,
            },
        )

    # --- Stage 12 — inverse basis + candidate capacity (P0-2 split) ---
    try:
        plan = verify_inverse_basis_and_candidate_capacity(
            layout_rule_authority,
            tube_geometry,
            placement_envelope,
            origin_mode,
            axis_orientation,
            stage8,
        )
    except EnumerationFailure as exc:
        return build_stage_blocked(
            failure_stage=12,
            blockers=(exc.blocker,),
            verified_request_context=request,
            raw_failing_field=stage8,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
                "tube_geometry": tube_geometry,
                "placement_envelope": placement_envelope,
                "origin_mode": origin_mode.value,
                "axis_orientation": axis_orientation.value,
                "exclusion_zones": zones,
            },
        )

    candidates: tuple[Candidate, ...] = enumerate_candidates(plan)

    # --- Stage 13 — envelope filtering ---
    inside_13, boundary_rejection_count_13 = enumeration_envelope_filter(candidates, plan)

    # --- Stage 14 — complete multi-zone exclusion evaluation + audit ---
    try:
        accepted_14, exclusion_rejection_count_14, exclusion_audit = (
            multi_zone_exclusion_evaluation(inside_13, tube_geometry, zones)
        )
    except GeometryFailure as exc:
        return build_stage_blocked(
            failure_stage=14,
            blockers=(exc.blocker,),
            verified_request_context=request,
            raw_failing_field=None,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
                "tube_geometry": tube_geometry,
                "placement_envelope": placement_envelope,
                "origin_mode": origin_mode.value,
                "axis_orientation": axis_orientation.value,
                "exclusion_zones": zones,
            },
        )

    # --- Stage 15 — coordinate quantization + collision guard ---
    try:
        accepted_coords = coordinate_quantization_collision_guard(accepted_14)
    except GeometryFailure as exc:
        return build_stage_blocked(
            failure_stage=15,
            blockers=(exc.blocker,),
            verified_request_context=request,
            raw_failing_field=None,
            normalized_context={
                "configuration": configuration,
                "layout_rule_authority": layout_rule_authority,
                "tube_geometry": tube_geometry,
                "placement_envelope": placement_envelope,
                "origin_mode": origin_mode.value,
                "axis_orientation": axis_orientation.value,
                "exclusion_zones": zones,
            },
        )

    # --- Stage 16 — U-tube pairing validation + hash verification ---
    physical_tube_count: int
    if configuration.construction_family is ConstructionFamily.U_TUBE:
        if request.u_tube_pairing_plan is None:
            raise AssertionError(
                "U_TUBE configuration requires u_tube_pairing_plan (defense-in-depth)"
            )
        try:
            normalized_plan, physical_tube_count = validate_pairing_plan(
                request.u_tube_pairing_plan, accepted_coords
            )
        except PairingFailure as exc:
            return build_stage_blocked(
                failure_stage=16,
                blockers=exc.blockers,
                verified_request_context=request,
                raw_failing_field=request.u_tube_pairing_plan,
                normalized_context={
                    "configuration": configuration,
                    "layout_rule_authority": layout_rule_authority,
                    "tube_geometry": tube_geometry,
                    "placement_envelope": placement_envelope,
                    "origin_mode": origin_mode.value,
                    "axis_orientation": axis_orientation.value,
                    "exclusion_zones": zones,
                },
            )
        # Re-bind request with normalized pairing plan so downstream stages
        # see the canonicalized pairs.
        request = TubeLayoutRequest(
            schema_version=REQUEST_SCHEMA_VERSION,
            configuration=configuration,
            tube_geometry=tube_geometry,
            layout_rule_authority=layout_rule_authority,
            placement_envelope=placement_envelope,
            origin_mode=origin_mode,
            axis_orientation=axis_orientation,
            exclusion_zones=zones,
            u_tube_pairing_plan=normalized_plan,
            evidence_refs=evidence_refs,
        )
    else:
        physical_tube_count = len(accepted_coords)

    # --- Stage 17 — tube-hole + physical-tube counts ---
    tube_hole_count = len(accepted_coords)

    # --- Stage 18 — deterministic warning emission ---
    warnings = _warnings(request)

    # --- Stage 19 — provenance pre-hash projection ---
    request_hash_for_provenance = _request_hash(request)
    provenance_pre_hash = _build_provenance_projection(
        request,
        request_hash_for_provenance,
        warnings,
        software_version=software_version,
        git_commit=git_commit,
    )
    # Final primitive provenance uses the actual layout_hash; build that first.

    # --- Stage 20 — request, layout, and output identity construction ---
    positions = tuple(
        TubePosition(
            position_id=position_id(request_hash_for_provenance, item.u, item.v),
            u=item.u,
            v=item.v,
            x_m=item.x_m,
            y_m=item.y_m,
        )
        for item in accepted_coords
    )

    # Build the provenance primitive exactly once and freeze it. Use the
    # already-frozen fragments from the projection dataclass and produce a
    # primitive detached mapping.
    case_authority_primitive = frozen_fragment_to_primitive(
        provenance_pre_hash.task020_case_authority
    )
    geometry_source_primitive = frozen_fragment_to_primitive(
        provenance_pre_hash.geometry_source_binding
    )
    rule_pack_primitive = (
        None
        if provenance_pre_hash.rule_pack_identity is None
        else frozen_fragment_to_primitive(provenance_pre_hash.rule_pack_identity)
    )

    # Round 6 §5: ``snapshot_then_to_primitive`` no longer accepts an
    # already-frozen fragment as a no-op bypass; the public Layer-A
    # boundary rejects internal markers outright. Internal canonicalization
    # of an already-frozen MessageEntry ``details`` (a
    # ``MappingProxyType`` constructed by ``MessageEntry.__post_init__``)
    # must go through ``frozen_fragment_to_primitive`` (Layer-B) directly.
    def _details_primitive(details: Any) -> Any:
        if details is None:
            return None
        if isinstance(details, MappingProxyType):
            return frozen_fragment_to_primitive(details)
        # Public-domain input — must traverse the strict snapshot path.
        return snapshot_then_to_primitive(details)

    provenance_primitive: dict[str, Any] = {
        "task_id": provenance_pre_hash.task_id,
        "design_contract_path": provenance_pre_hash.design_contract_path,
        "task020_configuration_id": provenance_pre_hash.task020_configuration_id,
        "task020_configuration_hash": provenance_pre_hash.task020_configuration_hash,
        "task020_case_authority": case_authority_primitive,
        "geometry_id": provenance_pre_hash.geometry_id,
        "geometry_revision": provenance_pre_hash.geometry_revision,
        "geometry_record_hash": provenance_pre_hash.geometry_record_hash,
        "tube_geometry_snapshot_hash": provenance_pre_hash.tube_geometry_snapshot_hash,
        "geometry_source_binding": geometry_source_primitive,
        "layout_rule_profile_id": provenance_pre_hash.layout_rule_profile_id,
        "layout_rule_id": provenance_pre_hash.layout_rule_id,
        "layout_rule_version": provenance_pre_hash.layout_rule_version,
        "rule_artifact_canonical_hash": provenance_pre_hash.rule_artifact_canonical_hash,
        "layout_rule_snapshot_hash": provenance_pre_hash.layout_rule_snapshot_hash,
        "source_class": provenance_pre_hash.source_class,
        "approval_status": provenance_pre_hash.approval_status,
        "provenance_edge_ids": list(provenance_pre_hash.provenance_edge_ids),
        "layout_rule_evidence_refs": list(provenance_pre_hash.layout_rule_evidence_refs),
        "rule_pack_identity": rule_pack_primitive,
        "envelope_evidence_refs": list(provenance_pre_hash.envelope_evidence_refs),
        "exclusion_zone_evidence_refs": [
            list(refs) for refs in provenance_pre_hash.exclusion_zone_evidence_refs
        ],
        "u_tube_pairing_evidence_refs": (
            None
            if provenance_pre_hash.u_tube_pairing_evidence_refs is None
            else list(provenance_pre_hash.u_tube_pairing_evidence_refs)
        ),
        "software_version": provenance_pre_hash.software_version,
        "git_commit": provenance_pre_hash.git_commit,
        "request_hash": provenance_pre_hash.request_hash,
        "warnings": [
            {
                "code": w.code,
                "field_path": w.field_path,
                "message_key": w.message_key,
                "evidence_refs": list(w.evidence_refs),
                "details": _details_primitive(w.details),
            }
            for w in provenance_pre_hash.warnings
        ],
        "deferred_capabilities": list(provenance_pre_hash.deferred_capabilities),
    }

    # Round 6 §5 above also applies to layout_hash_payload's warnings
    # below; the helper is shared.

    layout_hash_payload: dict[str, Any] = {
        "schema_version": LAYOUT_SCHEMA_VERSION,
        "request_hash": provenance_pre_hash.request_hash,
        "positions": [
            {
                "position_id": p.position_id,
                "u": p.u,
                "v": p.v,
                "x_m": p.x_m,
                "y_m": p.y_m,
            }
            for p in positions
        ],
        "tube_hole_count": tube_hole_count,
        "physical_tube_count": physical_tube_count,
        "boundary_rejection_count": boundary_rejection_count_13,
        "exclusion_rejection_count": exclusion_rejection_count_14,
        "exclusion_audit": [
            {
                "zone_id": audit.zone_id,
                "rejected_position_count": audit.rejected_position_count,
                "reason_code": audit.reason_code,
                "evidence_refs": list(audit.evidence_refs),
            }
            for audit in exclusion_audit
        ],
        "warnings": [
            {
                "code": w.code,
                "field_path": w.field_path,
                "message_key": w.message_key,
                "evidence_refs": list(w.evidence_refs),
                "details": _details_primitive(w.details),
            }
            for w in warnings
        ],
        "blockers": [],
        "deferred_capabilities": list(provenance_pre_hash.deferred_capabilities),
        "provenance_pre_hash": provenance_primitive,
    }
    layout_hash = sha256_hex(layout_hash_payload)

    # Final provenance: add the freshly computed layout_hash.
    # Round 5 §6.2: provenance is built from internal dataclass tuple
    # fields, so we MUST go through refreeze_internal_fragment instead
    # of force_frozen_canonical / freeze_deeply.
    provenance_primitive_frozen = refreeze_internal_fragment(provenance_primitive)
    provenance_primitive_final = refreeze_internal_fragment(
        {
            **frozen_fragment_to_primitive(provenance_primitive_frozen),
            "layout_hash": layout_hash,
        }
    )

    # --- Stage 21 — final output assembly ---
    # All canonical JSON fragments are deep-frozen in-place via the snapshot
    # boundary so the result cannot be mutated by callers after return.
    layout = TubeLayout(
        schema_version=LAYOUT_SCHEMA_VERSION,
        layout_id=layout_id(layout_hash),
        layout_hash=layout_hash,
        request_hash=provenance_pre_hash.request_hash,
        task020_configuration_id=configuration.configuration_id,
        task020_configuration_hash=configuration.configuration_hash,
        case_authority=case_authority_primitive,
        construction_family=configuration.construction_family.value,
        equipment_orientation=configuration.orientation,
        shell_pass_count=configuration.shell_pass_count,
        tube_pass_count=configuration.tube_pass_count,
        tube_geometry=tube_geometry,
        layout_rule_authority=layout_rule_authority,
        placement_envelope=placement_envelope,
        origin_mode=origin_mode,
        axis_orientation=axis_orientation,
        exclusion_zones=zones,
        positions=positions,
        tube_hole_count=tube_hole_count,
        physical_tube_count=physical_tube_count,
        boundary_rejection_count=boundary_rejection_count_13,
        exclusion_rejection_count=exclusion_rejection_count_14,
        exclusion_audit=exclusion_audit,
        warnings=warnings,
        blockers=(),
        deferred_capabilities=provenance_pre_hash.deferred_capabilities,
        provenance=provenance_primitive_final,
    )
    return TubeLayoutValidationResult(
        status=ValidationStatus.VALID,
        layout=layout,
        warnings=warnings,
        blockers=(),
        blocked_result_hash=None,
    )


__all__ = ["build_stage_blocked", "validate_request"]
