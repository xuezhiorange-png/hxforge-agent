"""Authority and identity verification for TASK-021 Slice A."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any

from hexagent.exchangers.shell_tube import canonical as task020_canonical
from hexagent.exchangers.shell_tube.models import (
    EquipmentFamily,
    ShellAndTubeConfiguration,
)

from .canonical import (
    DECIMAL_PRECISION,
    dataclass_to_mapping,
    parse_decimal,
    sha256_hex,
    to_primitive,
)
from .models import (
    PROFILE_ID,
    ApprovedTubeGeometrySnapshot,
    AuthorityMode,
    BlockerCode,
    LayoutRuleAuthoritySnapshot,
    MessageEntry,
)

_RECOGNIZED_SOURCE_CLASSES = {
    "PUBLIC_DOMAIN",
    "OPEN_LICENSE",
    "USER_PROVIDED_LICENSED_SUMMARY",
    "INTERNAL_ENGINEERING_RULE",
    "DERIVED_ENGINEERING_RULE",
    "REFERENCE_ONLY_RESTRICTED_STANDARD",
    "VENDOR_PERMISSIONED",
}


class AuthorityFailure(ValueError):
    def __init__(self, *blockers: MessageEntry) -> None:
        super().__init__(blockers[0].message_key if blockers else "authority_failure")
        self.blockers = blockers


def _message(
    code: BlockerCode,
    field_path: str,
    message_key: str,
    *,
    details: Mapping[str, Any] | None = None,
    evidence_refs: tuple[str, ...] = (),
) -> MessageEntry:
    return MessageEntry(
        code=code.value,
        field_path=field_path,
        message_key=message_key,
        evidence_refs=evidence_refs,
        details=details,
    )


def verify_task020_configuration(configuration: ShellAndTubeConfiguration) -> None:
    blockers: list[MessageEntry] = []
    if configuration.equipment_family is not EquipmentFamily.SHELL_AND_TUBE:
        blockers.append(
            _message(
                BlockerCode.STL_TASK020_CONFIGURATION_INVALID,
                "configuration.equipment_family",
                "task020_equipment_family_invalid",
            )
        )
    if configuration.blockers:
        blockers.append(
            _message(
                BlockerCode.STL_TASK020_CONFIGURATION_INVALID,
                "configuration.blockers",
                "task020_configuration_has_blockers",
                details={"blocker_count": len(configuration.blockers)},
            )
        )
    primitive = dataclass_to_mapping(configuration)
    authority_binding = primitive["authority_binding"]
    if not isinstance(authority_binding, Mapping):
        blockers.append(
            _message(
                BlockerCode.STL_TASK020_CONFIGURATION_INVALID,
                "configuration.authority_binding",
                "task020_authority_binding_invalid",
            )
        )
    if blockers:
        raise AuthorityFailure(*blockers)

    evaluated_rule_pack = authority_binding.get("evaluated_rule_pack_authority")
    payload = task020_canonical.canonical_payload(
        primitive,
        case_authority=primitive["case_authority"],
        evaluated_rule_pack_authority=evaluated_rule_pack,
        canonical_warnings=primitive["warnings"],
        canonical_blockers=primitive["blockers"],
        deferred_capabilities=primitive["deferred_capabilities"],
        authority_binding=authority_binding,
        schema_version=configuration.schema_version,
    )
    actual_hash = task020_canonical.configuration_hash(payload)
    actual_id = task020_canonical.configuration_id(actual_hash)
    if (
        actual_hash != configuration.configuration_hash
        or actual_id != configuration.configuration_id
    ):
        raise AuthorityFailure(
            _message(
                BlockerCode.STL_TASK020_CONFIGURATION_IDENTITY_MISMATCH,
                "configuration",
                "task020_configuration_identity_mismatch",
                details={"expected_hash": actual_hash, "expected_id": actual_id},
            )
        )


def verify_geometry_snapshot(snapshot: ApprovedTubeGeometrySnapshot) -> None:
    blockers: list[MessageEntry] = []
    if snapshot.geometry_type != "tube":
        blockers.append(
            _message(
                BlockerCode.STL_TUBE_GEOMETRY_TYPE_INVALID,
                "tube_geometry.geometry_type",
                "tube_geometry_type_invalid",
            )
        )
    if snapshot.approval_state != "approved":
        blockers.append(
            _message(
                BlockerCode.STL_TUBE_GEOMETRY_UNAPPROVED,
                "tube_geometry.approval_state",
                "tube_geometry_unapproved",
            )
        )
    source_values = tuple(to_primitive(snapshot.source_binding).values())
    if any(not isinstance(value, str) or not value for value in source_values):
        blockers.append(
            _message(
                BlockerCode.STL_TUBE_GEOMETRY_SOURCE_INCOMPLETE,
                "tube_geometry.source_binding",
                "tube_geometry_source_incomplete",
            )
        )
    outer = parse_decimal(snapshot.outer_diameter_m, positive=True)
    inner = parse_decimal(snapshot.inner_diameter_m, positive=True)
    wall = parse_decimal(snapshot.wall_thickness_m, positive=True)
    if inner >= outer:
        blockers.append(
            _message(
                BlockerCode.STL_TUBE_DIMENSION_INVALID,
                "tube_geometry.inner_diameter_m",
                "tube_inner_not_smaller_than_outer",
            )
        )
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        expected_wall = (outer - inner) / Decimal(2)
    if wall != expected_wall:
        blockers.append(
            _message(
                BlockerCode.STL_TUBE_DIMENSION_INCONSISTENT,
                "tube_geometry.wall_thickness_m",
                "tube_wall_thickness_inconsistent",
            )
        )
    payload = dataclass_to_mapping(snapshot)
    payload.pop("snapshot_hash")
    expected_hash = sha256_hex(payload)
    if expected_hash != snapshot.snapshot_hash:
        blockers.append(
            _message(
                BlockerCode.STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH,
                "tube_geometry.snapshot_hash",
                "tube_geometry_snapshot_hash_mismatch",
                evidence_refs=(snapshot.source_binding.evidence_ref,),
                details={"expected_hash": expected_hash},
            )
        )
    if blockers:
        raise AuthorityFailure(*blockers)


def verify_authority_mode_match(
    snapshot: LayoutRuleAuthoritySnapshot,
    configuration: ShellAndTubeConfiguration,
) -> None:
    """Stage 5 — authority-mode match between snapshot and TASK-020 configuration."""

    if snapshot.authority_mode.value != configuration.authority_mode.value:
        raise AuthorityFailure(
            _message(
                BlockerCode.STL_AUTHORITY_MODE_MISMATCH,
                "layout_rule_authority.authority_mode",
                "authority_mode_mismatch",
            )
        )


def verify_layout_rule_profile(
    snapshot: LayoutRuleAuthoritySnapshot,
    configuration: ShellAndTubeConfiguration,
    tube_geometry: ApprovedTubeGeometrySnapshot,
) -> None:
    """Stage 6 — layout-rule profile, approval, snapshot, license, provenance, rule-pack."""

    blockers: list[MessageEntry] = []
    if snapshot.profile_id != PROFILE_ID:
        blockers.append(
            _message(
                BlockerCode.STL_LAYOUT_RULE_PROFILE_UNSUPPORTED,
                "layout_rule_authority.profile_id",
                "layout_rule_profile_unsupported",
            )
        )
    if snapshot.approval_status != "approved":
        blockers.append(
            _message(
                BlockerCode.STL_LAYOUT_RULE_UNAPPROVED,
                "layout_rule_authority.approval_status",
                "layout_rule_unapproved",
            )
        )
    if snapshot.source_class not in _RECOGNIZED_SOURCE_CLASSES:
        blockers.append(
            _message(
                BlockerCode.STL_LAYOUT_RULE_LICENSE_BLOCKED,
                "layout_rule_authority.source_class",
                "source_class_unrecognized",
            )
        )
    if snapshot.license_evidence is None:
        blockers.append(
            _message(
                BlockerCode.STL_LAYOUT_RULE_LICENSE_BLOCKED,
                "layout_rule_authority.license_evidence",
                "license_evidence_missing",
            )
        )
    if not snapshot.provenance_edge_ids or not snapshot.evidence_refs:
        blockers.append(
            _message(
                BlockerCode.STL_LAYOUT_RULE_PROVENANCE_INCOMPLETE,
                "layout_rule_authority",
                "layout_rule_provenance_incomplete",
            )
        )
    if snapshot.authority_mode is AuthorityMode.INTERNAL_GENERIC:
        if snapshot.source_class != "INTERNAL_ENGINEERING_RULE":
            blockers.append(
                _message(
                    BlockerCode.STL_LAYOUT_RULE_LICENSE_BLOCKED,
                    "layout_rule_authority.source_class",
                    "internal_generic_source_class_invalid",
                )
            )
        if snapshot.rule_pack_identity is not None:
            blockers.append(
                _message(
                    BlockerCode.STL_RULE_PACK_IDENTITY_NOT_EXPECTED,
                    "layout_rule_authority.rule_pack_identity",
                    "rule_pack_identity_not_expected",
                )
            )
    elif snapshot.rule_pack_identity is None:
        blockers.append(
            _message(
                BlockerCode.STL_RULE_PACK_IDENTITY_MISSING,
                "layout_rule_authority.rule_pack_identity",
                "rule_pack_identity_missing",
            )
        )
    pitch = parse_decimal(snapshot.pitch_m, positive=True)
    outer = parse_decimal(tube_geometry.outer_diameter_m, positive=True)
    if pitch < outer:
        blockers.append(
            _message(
                BlockerCode.STL_PITCH_BELOW_TUBE_OD,
                "layout_rule_authority.pitch_m",
                "pitch_below_tube_od",
            )
        )
    if snapshot.maximum_candidate_positions > 100000:
        blockers.append(
            _message(
                BlockerCode.STL_ENUMERATION_LIMIT_EXCEEDED,
                "layout_rule_authority.maximum_candidate_positions",
                "maximum_candidate_positions_above_contract_limit",
            )
        )
    payload = dataclass_to_mapping(snapshot)
    payload.pop("snapshot_hash")
    expected_hash = sha256_hex(payload)
    if expected_hash != snapshot.snapshot_hash:
        blockers.append(
            _message(
                BlockerCode.STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH,
                "layout_rule_authority.snapshot_hash",
                "layout_rule_snapshot_hash_mismatch",
                evidence_refs=snapshot.evidence_refs,
                details={"expected_hash": expected_hash},
            )
        )
    if blockers:
        raise AuthorityFailure(*blockers)


def verify_layout_rule_snapshot(
    snapshot: LayoutRuleAuthoritySnapshot,
    configuration: ShellAndTubeConfiguration,
    tube_geometry: ApprovedTubeGeometrySnapshot,
) -> None:
    """Full layout-rule verification (used by tests that pre-date the stage split)."""

    verify_authority_mode_match(snapshot, configuration)
    verify_layout_rule_profile(snapshot, configuration, tube_geometry)


__all__ = [
    "AuthorityFailure",
    "verify_authority_mode_match",
    "verify_geometry_snapshot",
    "verify_layout_rule_profile",
    "verify_layout_rule_snapshot",
    "verify_task020_configuration",
]
