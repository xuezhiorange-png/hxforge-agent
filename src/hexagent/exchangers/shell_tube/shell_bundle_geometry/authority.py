"""Read-only upstream and authority verification for TASK-022 Slice A."""

from __future__ import annotations

import re
from typing import Any

from hexagent.exchangers.shell_tube.models import ConstructionFamily, EquipmentFamily
from hexagent.exchangers.shell_tube.tube_layout import authority as task021_authority
from hexagent.exchangers.shell_tube.tube_layout import canonical as task021_canonical
from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout

from .canonical import (
    CanonicalizationError,
    dataclass_to_mapping,
    internal_frozen_to_primitive,
    parse_decimal,
    sha256_hex,
    to_primitive,
)
from .models import (
    CALLER_SHELL_SCHEMA_VERSION,
    PROFILE_ID,
    RULE_SNAPSHOT_SCHEMA_VERSION,
    SHELL_SNAPSHOT_SCHEMA_VERSION,
    ApprovedShellGeometrySnapshot,
    BlockerCode,
    MessageEntry,
    RuleAuthorityMode,
    ShellBundleGeometryRequest,
    ShellBundleGeometryRuleAuthoritySnapshot,
    ShellInsideDiameterAuthorityMode,
)

_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
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
    def __init__(self, stage: int, *blockers: MessageEntry) -> None:
        super().__init__(blockers[0].message_key if blockers else "authority_failure")
        self.stage = stage
        self.blockers = blockers


def _message(
    code: BlockerCode,
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


def _primitive(value: Any) -> Any:
    return to_primitive(value)


def _contains_token(value: Any, token: str) -> bool:
    primitive = internal_frozen_to_primitive(value)
    if primitive == token:
        return True
    if isinstance(primitive, list):
        return any(_contains_token_from_primitive(item, token) for item in primitive)
    if isinstance(primitive, dict):
        return any(
            key == token or _contains_token_from_primitive(item, token)
            for key, item in primitive.items()
        )
    return False


def _contains_token_from_primitive(value: Any, token: str) -> bool:
    if value == token:
        return True
    if isinstance(value, list):
        return any(_contains_token_from_primitive(item, token) for item in value)
    if isinstance(value, dict):
        return any(
            key == token or _contains_token_from_primitive(item, token)
            for key, item in value.items()
        )
    return False


def verify_task020_configuration(request: ShellBundleGeometryRequest) -> None:
    configuration = request.configuration
    blockers: list[MessageEntry] = []
    if configuration.equipment_family is not EquipmentFamily.SHELL_AND_TUBE:
        blockers.append(
            _message(
                BlockerCode.SBG_TASK020_CONFIGURATION_INVALID,
                "configuration.equipment_family",
                "task020_equipment_family_invalid",
            )
        )
    if configuration.construction_family not in {
        ConstructionFamily.FIXED_TUBESHEET,
        ConstructionFamily.U_TUBE,
        ConstructionFamily.FLOATING_HEAD,
    }:
        blockers.append(
            _message(
                BlockerCode.SBG_TASK020_CONFIGURATION_INVALID,
                "configuration.construction_family",
                "task020_construction_family_invalid",
            )
        )
    if configuration.blockers:
        blockers.append(
            _message(
                BlockerCode.SBG_TASK020_CONFIGURATION_INVALID,
                "configuration.blockers",
                "task020_configuration_has_blockers",
                details={
                    "blockers": [_primitive(item) for item in configuration.blockers]
                },
            )
        )
    if blockers:
        raise AuthorityFailure(4, *blockers)
    try:
        task021_authority.verify_task020_configuration(configuration)
    except task021_authority.AuthorityFailure as exc:
        translated: list[MessageEntry] = []
        for blocker in exc.blockers:
            code = (
                BlockerCode.SBG_TASK020_CONFIGURATION_IDENTITY_MISMATCH
                if "IDENTITY_MISMATCH" in blocker.code
                else BlockerCode.SBG_TASK020_CONFIGURATION_INVALID
            )
            translated.append(
                _message(
                    code,
                    f"configuration.{blocker.field_path}"
                    if blocker.field_path
                    else "configuration",
                    blocker.message_key,
                    evidence_refs=tuple(blocker.evidence_refs),
                    details={"upstream_blocker": _primitive(blocker)},
                )
            )
        raise AuthorityFailure(4, *translated) from exc


def _layout_provenance(layout: TubeLayout) -> dict[str, Any]:
    primitive = task021_canonical.to_primitive(layout.provenance)
    if not isinstance(primitive, dict):
        raise CanonicalizationError("layout provenance must reduce to an object")
    return primitive


def verify_task021_layout(layout: TubeLayout) -> None:
    blockers: list[MessageEntry] = []
    if layout.schema_version != "task021.tube-layout.v1":
        blockers.append(
            _message(
                BlockerCode.SBG_TASK021_LAYOUT_INVALID,
                "tube_layout.schema_version",
                "task021_layout_schema_version_invalid",
                details={"actual": layout.schema_version},
            )
        )
    if layout.blockers:
        blockers.append(
            _message(
                BlockerCode.SBG_TASK021_LAYOUT_HAS_BLOCKERS,
                "tube_layout.blockers",
                "task021_layout_has_blockers",
                details={"blockers": [_primitive(item) for item in layout.blockers]},
            )
        )
    if not layout.positions:
        blockers.append(
            _message(
                BlockerCode.SBG_LAYOUT_HAS_NO_POSITIONS,
                "tube_layout.positions",
                "task021_layout_has_no_positions",
            )
        )
    try:
        task021_authority.verify_geometry_snapshot(layout.tube_geometry)
    except task021_authority.AuthorityFailure as exc:
        blockers.append(
            _message(
                BlockerCode.SBG_TUBE_GEOMETRY_SNAPSHOT_INVALID,
                "tube_layout.tube_geometry",
                "task021_tube_geometry_snapshot_invalid",
                details={
                    "upstream_blockers": [_primitive(item) for item in exc.blockers]
                },
            )
        )
    if blockers:
        raise AuthorityFailure(5, *blockers)

    identity_blockers: list[MessageEntry] = []
    for position in layout.positions:
        expected_position_id = task021_canonical.position_id(
            layout.request_hash, position.u, position.v
        )
        if expected_position_id != position.position_id:
            identity_blockers.append(
                _message(
                    BlockerCode.SBG_TASK021_LAYOUT_IDENTITY_MISMATCH,
                    f"tube_layout.positions.{position.position_id}",
                    "task021_position_identity_mismatch",
                    details={"expected_position_id": expected_position_id},
                )
            )
    provenance = _layout_provenance(layout)
    provenance_layout_hash = provenance.get("layout_hash")
    if provenance_layout_hash != layout.layout_hash:
        identity_blockers.append(
            _message(
                BlockerCode.SBG_TASK021_LAYOUT_IDENTITY_MISMATCH,
                "tube_layout.provenance.layout_hash",
                "task021_provenance_layout_hash_mismatch",
                details={
                    "expected": layout.layout_hash,
                    "actual": provenance_layout_hash,
                },
            )
        )
    provenance_pre_hash = dict(provenance)
    provenance_pre_hash.pop("layout_hash", None)
    payload = {
        "schema_version": layout.schema_version,
        "request_hash": layout.request_hash,
        "positions": [
            {
                "position_id": item.position_id,
                "u": item.u,
                "v": item.v,
                "x_m": item.x_m,
                "y_m": item.y_m,
            }
            for item in layout.positions
        ],
        "tube_hole_count": layout.tube_hole_count,
        "physical_tube_count": layout.physical_tube_count,
        "boundary_rejection_count": layout.boundary_rejection_count,
        "exclusion_rejection_count": layout.exclusion_rejection_count,
        "exclusion_audit": [_primitive(item) for item in layout.exclusion_audit],
        "warnings": [_primitive(item) for item in layout.warnings],
        "blockers": [],
        "deferred_capabilities": list(layout.deferred_capabilities),
        "provenance_pre_hash": provenance_pre_hash,
    }
    expected_hash = task021_canonical.sha256_hex(payload)
    expected_id = task021_canonical.layout_id(expected_hash)
    if expected_hash != layout.layout_hash or expected_id != layout.layout_id:
        identity_blockers.append(
            _message(
                BlockerCode.SBG_TASK021_LAYOUT_IDENTITY_MISMATCH,
                "tube_layout",
                "task021_layout_identity_mismatch",
                details={"expected_hash": expected_hash, "expected_id": expected_id},
            )
        )
    if identity_blockers:
        raise AuthorityFailure(5, *identity_blockers)


def verify_cross_binding(request: ShellBundleGeometryRequest) -> None:
    configuration = request.configuration
    layout = request.tube_layout
    mismatches: dict[str, Any] = {}
    comparisons = {
        "configuration_id": (
            configuration.configuration_id,
            layout.task020_configuration_id,
        ),
        "configuration_hash": (
            configuration.configuration_hash,
            layout.task020_configuration_hash,
        ),
        "construction_family": (
            configuration.construction_family.value,
            layout.construction_family,
        ),
        "equipment_orientation": (
            configuration.orientation,
            layout.equipment_orientation,
        ),
        "shell_pass_count": (configuration.shell_pass_count, layout.shell_pass_count),
        "tube_pass_count": (configuration.tube_pass_count, layout.tube_pass_count),
    }
    for name, (expected, actual) in comparisons.items():
        if expected != actual:
            mismatches[name] = {
                "expected": expected.value if hasattr(expected, "value") else expected,
                "actual": actual.value if hasattr(actual, "value") else actual,
            }
    if mismatches:
        raise AuthorityFailure(
            6,
            _message(
                BlockerCode.SBG_LAYOUT_CONFIGURATION_BINDING_MISMATCH,
                "tube_layout",
                "task020_task021_cross_binding_mismatch",
                details={"mismatches": mismatches},
            ),
        )


def _hash_without(value: Any, field_name: str) -> str:
    payload = dataclass_to_mapping(value)
    payload.pop(field_name)
    return sha256_hex(payload)


def verify_rule_authority(snapshot: ShellBundleGeometryRuleAuthoritySnapshot) -> None:
    blockers: list[MessageEntry] = []
    if snapshot.schema_version != RULE_SNAPSHOT_SCHEMA_VERSION:
        blockers.append(
            _message(
                BlockerCode.SBG_RULE_PROFILE_UNSUPPORTED,
                "geometry_rule_authority.schema_version",
                "rule_schema_version_unsupported",
            )
        )
    if snapshot.profile_id != PROFILE_ID:
        blockers.append(
            _message(
                BlockerCode.SBG_RULE_PROFILE_UNSUPPORTED,
                "geometry_rule_authority.profile_id",
                "rule_profile_unsupported",
            )
        )
    if snapshot.approval_status != "approved":
        blockers.append(
            _message(
                BlockerCode.SBG_RULE_UNAPPROVED,
                "geometry_rule_authority.approval_status",
                "rule_authority_unapproved",
            )
        )
    if snapshot.source_class not in _RECOGNIZED_SOURCE_CLASSES:
        blockers.append(
            _message(
                BlockerCode.SBG_RULE_LICENSE_BLOCKED,
                "geometry_rule_authority.source_class",
                "rule_source_class_unrecognized",
            )
        )
    if snapshot.source_class == "REFERENCE_ONLY_RESTRICTED_STANDARD":
        blockers.append(
            _message(
                BlockerCode.SBG_RULE_LICENSE_BLOCKED,
                "geometry_rule_authority.source_class",
                "restricted_standard_runtime_forbidden",
            )
        )
    if not snapshot.provenance_edge_ids or not snapshot.evidence_refs:
        blockers.append(
            _message(
                BlockerCode.SBG_RULE_PROVENANCE_INCOMPLETE,
                "geometry_rule_authority",
                "rule_provenance_incomplete",
            )
        )
    if snapshot.authority_mode is RuleAuthorityMode.INTERNAL_GENERIC:
        if snapshot.source_class != "INTERNAL_ENGINEERING_RULE" or not _contains_token(
            snapshot.license_evidence, "NO_STANDARD_CLAIM"
        ):
            blockers.append(
                _message(
                    BlockerCode.SBG_RULE_LICENSE_BLOCKED,
                    "geometry_rule_authority.license_evidence",
                    "internal_generic_no_standard_claim_required",
                )
            )
        if snapshot.rule_pack_identity is not None:
            blockers.append(
                _message(
                    BlockerCode.SBG_RULE_LICENSE_BLOCKED,
                    "geometry_rule_authority.rule_pack_identity",
                    "rule_pack_identity_not_expected",
                )
            )
    else:
        if snapshot.rule_pack_identity is None:
            blockers.append(
                _message(
                    BlockerCode.SBG_RULE_LICENSE_BLOCKED,
                    "geometry_rule_authority.rule_pack_identity",
                    "rule_pack_identity_required",
                )
            )
        elif not _HEX_RE.fullmatch(
            snapshot.rule_pack_identity.rule_pack_canonical_hash
        ):
            blockers.append(
                _message(
                    BlockerCode.SBG_RULE_LICENSE_BLOCKED,
                    "geometry_rule_authority.rule_pack_identity.rule_pack_canonical_hash",
                    "rule_pack_hash_invalid",
                )
            )
    if snapshot.source_class == "VENDOR_PERMISSIONED" and not (
        _contains_token(
            snapshot.license_evidence, "REPOSITORY_REDISTRIBUTION_PERMITTED"
        )
        and _contains_token(snapshot.license_evidence, "RUNTIME_USE_PERMITTED")
    ):
        blockers.append(
            _message(
                BlockerCode.SBG_RULE_LICENSE_BLOCKED,
                "geometry_rule_authority.license_evidence",
                "vendor_permission_scope_incomplete",
            )
        )
    try:
        parse_decimal(snapshot.minimum_bundle_peripheral_allowance_m, positive=False)
        parse_decimal(snapshot.minimum_radial_clearance_m, positive=False)
    except CanonicalizationError:
        blockers.append(
            _message(
                BlockerCode.SBG_DECIMAL_LEXICAL_INVALID,
                "geometry_rule_authority",
                "rule_minimum_decimal_invalid",
            )
        )
    if (
        isinstance(snapshot.maximum_position_count, bool)
        or snapshot.maximum_position_count <= 0
    ):
        blockers.append(
            _message(
                BlockerCode.SBG_RULE_AUTHORITY_MODE_INVALID,
                "geometry_rule_authority.maximum_position_count",
                "maximum_position_count_invalid",
            )
        )
    expected_hash = _hash_without(snapshot, "snapshot_hash")
    if expected_hash != snapshot.snapshot_hash:
        blockers.append(
            _message(
                BlockerCode.SBG_RULE_SNAPSHOT_HASH_MISMATCH,
                "geometry_rule_authority.snapshot_hash",
                "rule_snapshot_hash_mismatch",
                evidence_refs=snapshot.evidence_refs,
                details={"expected_hash": expected_hash},
            )
        )
    if blockers:
        raise AuthorityFailure(7, *blockers)


def _source_binding_complete(snapshot: ApprovedShellGeometrySnapshot) -> bool:
    values = dataclass_to_mapping(snapshot.source_binding).values()
    return all(isinstance(item, str) and bool(item) for item in values)


def verify_shell_authority(request: ShellBundleGeometryRequest) -> str:
    mode = request.shell_authority_mode
    rule = request.geometry_rule_authority
    blockers: list[MessageEntry] = []
    if mode not in rule.allowed_shell_authority_modes:
        blockers.append(
            _message(
                BlockerCode.SBG_SHELL_AUTHORITY_MODE_NOT_ALLOWED,
                "shell_authority_mode",
                "shell_authority_mode_not_allowed",
                details={"mode": mode.value},
            )
        )
    if mode is ShellInsideDiameterAuthorityMode.CALLER_SUPPLIED_EXPLICIT:
        if request.caller_supplied_shell is None:
            blockers.append(
                _message(
                    BlockerCode.SBG_CALLER_SHELL_DIAMETER_MISSING,
                    "caller_supplied_shell",
                    "caller_shell_diameter_missing",
                )
            )
        if request.approved_shell_geometry is not None:
            blockers.append(
                _message(
                    BlockerCode.SBG_APPROVED_SHELL_GEOMETRY_NOT_EXPECTED,
                    "approved_shell_geometry",
                    "approved_shell_geometry_not_expected",
                )
            )
        if blockers:
            raise AuthorityFailure(8, *blockers)
        assert request.caller_supplied_shell is not None
        caller = request.caller_supplied_shell
        if caller.schema_version != CALLER_SHELL_SCHEMA_VERSION:
            blockers.append(
                _message(
                    BlockerCode.SBG_SHELL_INSIDE_DIAMETER_INVALID,
                    "caller_supplied_shell.schema_version",
                    "caller_shell_schema_version_invalid",
                )
            )
        try:
            parse_decimal(caller.shell_inside_diameter_m, positive=True)
        except CanonicalizationError:
            blockers.append(
                _message(
                    BlockerCode.SBG_SHELL_INSIDE_DIAMETER_INVALID,
                    "caller_supplied_shell.shell_inside_diameter_m",
                    "shell_inside_diameter_invalid",
                )
            )
        expected_hash = _hash_without(caller, "authority_hash")
        if expected_hash != caller.authority_hash:
            blockers.append(
                _message(
                    BlockerCode.SBG_CALLER_SHELL_AUTHORITY_HASH_MISMATCH,
                    "caller_supplied_shell.authority_hash",
                    "caller_shell_authority_hash_mismatch",
                    evidence_refs=caller.evidence_refs,
                    details={"expected_hash": expected_hash},
                )
            )
        if blockers:
            raise AuthorityFailure(8, *blockers)
        return caller.shell_inside_diameter_m

    if request.approved_shell_geometry is None:
        blockers.append(
            _message(
                BlockerCode.SBG_APPROVED_SHELL_GEOMETRY_MISSING,
                "approved_shell_geometry",
                "approved_shell_geometry_missing",
            )
        )
    if request.caller_supplied_shell is not None:
        blockers.append(
            _message(
                BlockerCode.SBG_CALLER_SHELL_DIAMETER_NOT_EXPECTED,
                "caller_supplied_shell",
                "caller_shell_not_expected",
            )
        )
    if blockers:
        raise AuthorityFailure(8, *blockers)
    assert request.approved_shell_geometry is not None
    approved = request.approved_shell_geometry
    if approved.schema_version != SHELL_SNAPSHOT_SCHEMA_VERSION:
        blockers.append(
            _message(
                BlockerCode.SBG_APPROVED_SHELL_GEOMETRY_TYPE_INVALID,
                "approved_shell_geometry.schema_version",
                "approved_shell_schema_version_invalid",
            )
        )
    if approved.geometry_type != "shell":
        blockers.append(
            _message(
                BlockerCode.SBG_APPROVED_SHELL_GEOMETRY_TYPE_INVALID,
                "approved_shell_geometry.geometry_type",
                "approved_shell_geometry_type_invalid",
            )
        )
    if approved.approval_state != "approved":
        blockers.append(
            _message(
                BlockerCode.SBG_APPROVED_SHELL_GEOMETRY_UNAPPROVED,
                "approved_shell_geometry.approval_state",
                "approved_shell_geometry_unapproved",
            )
        )
    if not _source_binding_complete(approved):
        blockers.append(
            _message(
                BlockerCode.SBG_APPROVED_SHELL_SOURCE_INCOMPLETE,
                "approved_shell_geometry.source_binding",
                "approved_shell_source_incomplete",
            )
        )
    if not _HEX_RE.fullmatch(approved.record_hash):
        blockers.append(
            _message(
                BlockerCode.SBG_APPROVED_SHELL_SOURCE_INCOMPLETE,
                "approved_shell_geometry.record_hash",
                "approved_shell_record_hash_invalid",
            )
        )
    try:
        parse_decimal(approved.shell_inside_diameter_m, positive=True)
    except CanonicalizationError:
        blockers.append(
            _message(
                BlockerCode.SBG_SHELL_INSIDE_DIAMETER_INVALID,
                "approved_shell_geometry.shell_inside_diameter_m",
                "shell_inside_diameter_invalid",
            )
        )
    expected_hash = _hash_without(approved, "snapshot_hash")
    if expected_hash != approved.snapshot_hash:
        blockers.append(
            _message(
                BlockerCode.SBG_APPROVED_SHELL_SNAPSHOT_HASH_MISMATCH,
                "approved_shell_geometry.snapshot_hash",
                "approved_shell_snapshot_hash_mismatch",
                evidence_refs=(approved.source_binding.evidence_ref,),
                details={"expected_hash": expected_hash},
            )
        )
    if blockers:
        raise AuthorityFailure(8, *blockers)
    return approved.shell_inside_diameter_m


__all__ = [
    "AuthorityFailure",
    "verify_cross_binding",
    "verify_rule_authority",
    "verify_shell_authority",
    "verify_task020_configuration",
    "verify_task021_layout",
]
