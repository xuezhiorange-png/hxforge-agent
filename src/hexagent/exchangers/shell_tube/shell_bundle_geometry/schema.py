"""Strict raw schema parsing for TASK-022 Slice A."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hexagent.exchangers.shell_tube.models import ShellAndTubeConfiguration
from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout

from .canonical import canonical_string_array, freeze_known_fragment
from .models import (
    ApprovedShellGeometrySnapshot,
    BlockerCode,
    CallerSuppliedShellInsideDiameter,
    MessageEntry,
    RuleAuthorityMode,
    RulePackIdentitySnapshot,
    ShellBundleGeometryRequest,
    ShellBundleGeometryRuleAuthoritySnapshot,
    ShellInsideDiameterAuthorityMode,
    SourceBindingSnapshot,
)

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "configuration",
    "tube_layout",
    "geometry_rule_authority",
    "shell_authority_mode",
    "caller_supplied_shell",
    "approved_shell_geometry",
    "bundle_peripheral_allowance_m",
    "bundle_peripheral_allowance_evidence_refs",
    "required_minimum_radial_clearance_m",
    "minimum_clearance_evidence_refs",
    "evidence_refs",
}
_SOURCE_FIELDS = {
    "source_id",
    "source_type",
    "source_revision",
    "source_location",
    "evidence_ref",
    "approved_by",
    "approved_at",
}
_RULE_PACK_FIELDS = {
    "rule_pack_id",
    "rule_pack_version",
    "rule_pack_canonical_hash",
}
_RULE_FIELDS = {
    "schema_version",
    "profile_id",
    "authority_mode",
    "rule_id",
    "rule_version",
    "rule_artifact_canonical_hash",
    "source_class",
    "license_evidence",
    "approval_status",
    "provenance_edge_ids",
    "evidence_refs",
    "rule_pack_identity",
    "allowed_shell_authority_modes",
    "minimum_bundle_peripheral_allowance_m",
    "minimum_radial_clearance_m",
    "maximum_position_count",
    "snapshot_hash",
}
_CALLER_FIELDS = {
    "schema_version",
    "shell_inside_diameter_m",
    "evidence_refs",
    "authority_hash",
}
_APPROVED_SHELL_FIELDS = {
    "schema_version",
    "geometry_id",
    "geometry_type",
    "revision",
    "approval_state",
    "shell_inside_diameter_m",
    "record_hash",
    "source_binding",
    "snapshot_hash",
}


class SchemaFailure(ValueError):
    def __init__(
        self,
        stage: int,
        blockers: tuple[MessageEntry, ...],
        *,
        raw_failing_field: Any | None = None,
        normalized_context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(blockers[0].message_key if blockers else "schema_failure")
        self.stage = stage
        self.blockers = blockers
        self.raw_failing_field = raw_failing_field
        self.normalized_context = normalized_context or {}


def _message(
    code: BlockerCode,
    field_path: str | None,
    message_key: str,
    *,
    details: dict[str, Any] | None = None,
) -> MessageEntry:
    return MessageEntry(
        code=code.value,
        field_path=field_path,
        message_key=message_key,
        details=details,
    )


def _mapping(value: Any, field_path: str, *, stage: int) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise SchemaFailure(
            stage,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID,
                    field_path,
                    "mapping_with_string_keys_required",
                ),
            ),
            raw_failing_field=value,
        )
    return value


def _exact_fields(
    value: Mapping[str, Any], expected: set[str], field_path: str, *, stage: int
) -> None:
    blockers: list[MessageEntry] = []
    for key in sorted(set(value) - expected):
        blockers.append(
            _message(
                BlockerCode.SBG_UNKNOWN_FIELD,
                f"{field_path}.{key}" if field_path else key,
                "unknown_field",
                details={"field": key},
            )
        )
    for key in sorted(expected - set(value)):
        blockers.append(
            _message(
                BlockerCode.SBG_UNKNOWN_FIELD,
                f"{field_path}.{key}" if field_path else key,
                "required_field_missing",
                details={"field": key},
            )
        )
    if blockers:
        raise SchemaFailure(stage, tuple(blockers), raw_failing_field=dict(value))


def _string(value: Any, field_path: str, *, non_empty: bool = True) -> str:
    if not isinstance(value, str) or (non_empty and not value):
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID, field_path, "string_required"
                ),
            ),
            raw_failing_field=value,
        )
    return value


def _enum(enum_type: type[Any], value: Any, field_path: str) -> Any:
    if not isinstance(value, str):
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID, field_path, "enum_string_required"
                ),
            ),
            raw_failing_field=value,
        )
    try:
        return enum_type(value)
    except ValueError as exc:
        code = (
            BlockerCode.SBG_RULE_AUTHORITY_MODE_INVALID
            if enum_type is RuleAuthorityMode
            else BlockerCode.SBG_SHELL_AUTHORITY_MODE_INVALID
        )
        raise SchemaFailure(
            3,
            (
                _message(
                    code,
                    field_path,
                    "closed_enum_value_invalid",
                    details={"value": value},
                ),
            ),
            raw_failing_field=value,
        ) from exc


def _array(value: Any, field_path: str, *, non_empty: bool) -> tuple[str, ...]:
    try:
        return canonical_string_array(value, non_empty=non_empty, field_path=field_path)
    except (TypeError, ValueError) as exc:
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID, field_path, "string_array_invalid"
                ),
            ),
            raw_failing_field=value,
        ) from exc


def _source_binding(raw: Any, field_path: str) -> SourceBindingSnapshot:
    value = _mapping(raw, field_path, stage=3)
    _exact_fields(value, _SOURCE_FIELDS, field_path, stage=3)
    return SourceBindingSnapshot(
        source_id=_string(value["source_id"], f"{field_path}.source_id"),
        source_type=_string(value["source_type"], f"{field_path}.source_type"),
        source_revision=_string(
            value["source_revision"], f"{field_path}.source_revision"
        ),
        source_location=_string(
            value["source_location"], f"{field_path}.source_location"
        ),
        evidence_ref=_string(value["evidence_ref"], f"{field_path}.evidence_ref"),
        approved_by=_string(value["approved_by"], f"{field_path}.approved_by"),
        approved_at=_string(value["approved_at"], f"{field_path}.approved_at"),
    )


def _rule_pack(raw: Any, field_path: str) -> RulePackIdentitySnapshot | None:
    if raw is None:
        return None
    value = _mapping(raw, field_path, stage=3)
    _exact_fields(value, _RULE_PACK_FIELDS, field_path, stage=3)
    return RulePackIdentitySnapshot(
        rule_pack_id=_string(value["rule_pack_id"], f"{field_path}.rule_pack_id"),
        rule_pack_version=_string(
            value["rule_pack_version"], f"{field_path}.rule_pack_version"
        ),
        rule_pack_canonical_hash=_string(
            value["rule_pack_canonical_hash"], f"{field_path}.rule_pack_canonical_hash"
        ),
    )


def _rule_authority(raw: Any) -> ShellBundleGeometryRuleAuthoritySnapshot:
    if raw is None:
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_RULE_AUTHORITY_MISSING,
                    "geometry_rule_authority",
                    "rule_authority_missing",
                ),
            ),
        )
    value = _mapping(raw, "geometry_rule_authority", stage=3)
    _exact_fields(value, _RULE_FIELDS, "geometry_rule_authority", stage=3)
    raw_modes = value["allowed_shell_authority_modes"]
    if not isinstance(raw_modes, list) or not raw_modes:
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID,
                    "geometry_rule_authority.allowed_shell_authority_modes",
                    "non_empty_array_required",
                ),
            ),
            raw_failing_field=raw_modes,
        )
    parsed_modes = tuple(
        _enum(
            ShellInsideDiameterAuthorityMode,
            item,
            f"geometry_rule_authority.allowed_shell_authority_modes[{index}]",
        )
        for index, item in enumerate(raw_modes)
    )
    if len(set(parsed_modes)) != len(parsed_modes):
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID,
                    "geometry_rule_authority.allowed_shell_authority_modes",
                    "duplicate_array_item",
                ),
            ),
        )
    maximum_position_count = value["maximum_position_count"]
    if isinstance(maximum_position_count, bool) or not isinstance(
        maximum_position_count, int
    ):
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID,
                    "geometry_rule_authority.maximum_position_count",
                    "integer_required",
                ),
            ),
            raw_failing_field=maximum_position_count,
        )
    try:
        frozen_license = freeze_known_fragment(value["license_evidence"])
    except Exception as exc:
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID,
                    "geometry_rule_authority.license_evidence",
                    "canonical_json_value_required",
                ),
            ),
            raw_failing_field=value["license_evidence"],
        ) from exc
    return ShellBundleGeometryRuleAuthoritySnapshot(
        schema_version=_string(
            value["schema_version"], "geometry_rule_authority.schema_version"
        ),
        profile_id=_string(value["profile_id"], "geometry_rule_authority.profile_id"),
        authority_mode=_enum(
            RuleAuthorityMode,
            value["authority_mode"],
            "geometry_rule_authority.authority_mode",
        ),
        rule_id=_string(value["rule_id"], "geometry_rule_authority.rule_id"),
        rule_version=_string(
            value["rule_version"], "geometry_rule_authority.rule_version"
        ),
        rule_artifact_canonical_hash=_string(
            value["rule_artifact_canonical_hash"],
            "geometry_rule_authority.rule_artifact_canonical_hash",
        ),
        source_class=_string(
            value["source_class"], "geometry_rule_authority.source_class"
        ),
        license_evidence=frozen_license,
        approval_status=_string(
            value["approval_status"], "geometry_rule_authority.approval_status"
        ),
        provenance_edge_ids=_array(
            value["provenance_edge_ids"],
            "geometry_rule_authority.provenance_edge_ids",
            non_empty=True,
        ),
        evidence_refs=_array(
            value["evidence_refs"],
            "geometry_rule_authority.evidence_refs",
            non_empty=True,
        ),
        rule_pack_identity=_rule_pack(
            value["rule_pack_identity"], "geometry_rule_authority.rule_pack_identity"
        ),
        allowed_shell_authority_modes=tuple(
            sorted(parsed_modes, key=lambda item: item.value)
        ),
        minimum_bundle_peripheral_allowance_m=_string(
            value["minimum_bundle_peripheral_allowance_m"],
            "geometry_rule_authority.minimum_bundle_peripheral_allowance_m",
        ),
        minimum_radial_clearance_m=_string(
            value["minimum_radial_clearance_m"],
            "geometry_rule_authority.minimum_radial_clearance_m",
        ),
        maximum_position_count=maximum_position_count,
        snapshot_hash=_string(
            value["snapshot_hash"], "geometry_rule_authority.snapshot_hash"
        ),
    )


def _caller_shell(raw: Any) -> CallerSuppliedShellInsideDiameter | None:
    if raw is None:
        return None
    value = _mapping(raw, "caller_supplied_shell", stage=3)
    _exact_fields(value, _CALLER_FIELDS, "caller_supplied_shell", stage=3)
    return CallerSuppliedShellInsideDiameter(
        schema_version=_string(
            value["schema_version"], "caller_supplied_shell.schema_version"
        ),
        shell_inside_diameter_m=_string(
            value["shell_inside_diameter_m"],
            "caller_supplied_shell.shell_inside_diameter_m",
        ),
        evidence_refs=_array(
            value["evidence_refs"],
            "caller_supplied_shell.evidence_refs",
            non_empty=True,
        ),
        authority_hash=_string(
            value["authority_hash"], "caller_supplied_shell.authority_hash"
        ),
    )


def _approved_shell(raw: Any) -> ApprovedShellGeometrySnapshot | None:
    if raw is None:
        return None
    value = _mapping(raw, "approved_shell_geometry", stage=3)
    _exact_fields(value, _APPROVED_SHELL_FIELDS, "approved_shell_geometry", stage=3)
    return ApprovedShellGeometrySnapshot(
        schema_version=_string(
            value["schema_version"], "approved_shell_geometry.schema_version"
        ),
        geometry_id=_string(
            value["geometry_id"], "approved_shell_geometry.geometry_id"
        ),
        geometry_type=_string(
            value["geometry_type"], "approved_shell_geometry.geometry_type"
        ),
        revision=_string(value["revision"], "approved_shell_geometry.revision"),
        approval_state=_string(
            value["approval_state"], "approved_shell_geometry.approval_state"
        ),
        shell_inside_diameter_m=_string(
            value["shell_inside_diameter_m"],
            "approved_shell_geometry.shell_inside_diameter_m",
        ),
        record_hash=_string(
            value["record_hash"], "approved_shell_geometry.record_hash"
        ),
        source_binding=_source_binding(
            value["source_binding"], "approved_shell_geometry.source_binding"
        ),
        snapshot_hash=_string(
            value["snapshot_hash"], "approved_shell_geometry.snapshot_hash"
        ),
    )


def parse_request(payload: Any) -> ShellBundleGeometryRequest:
    if not isinstance(payload, Mapping) or any(
        not isinstance(key, str) for key in payload
    ):
        raise SchemaFailure(
            1,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID,
                    None,
                    "top_level_mapping_with_string_keys_required",
                ),
            ),
            raw_failing_field=payload,
        )
    _exact_fields(payload, _TOP_LEVEL_FIELDS, "", stage=1)

    configuration = payload["configuration"]
    if configuration is None:
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_TASK020_CONFIGURATION_MISSING,
                    "configuration",
                    "task020_configuration_missing",
                ),
            ),
        )
    if not isinstance(configuration, ShellAndTubeConfiguration):
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID,
                    "configuration",
                    "complete_task020_configuration_instance_required",
                ),
            ),
            raw_failing_field=configuration,
        )

    tube_layout = payload["tube_layout"]
    if tube_layout is None:
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_TASK021_LAYOUT_MISSING,
                    "tube_layout",
                    "task021_layout_missing",
                ),
            ),
        )
    if not isinstance(tube_layout, TubeLayout):
        raise SchemaFailure(
            3,
            (
                _message(
                    BlockerCode.SBG_RAW_TYPE_INVALID,
                    "tube_layout",
                    "complete_task021_layout_instance_required",
                ),
            ),
            raw_failing_field=tube_layout,
        )

    return ShellBundleGeometryRequest(
        schema_version=_string(payload["schema_version"], "schema_version"),
        configuration=configuration,
        tube_layout=tube_layout,
        geometry_rule_authority=_rule_authority(payload["geometry_rule_authority"]),
        shell_authority_mode=_enum(
            ShellInsideDiameterAuthorityMode,
            payload["shell_authority_mode"],
            "shell_authority_mode",
        ),
        caller_supplied_shell=_caller_shell(payload["caller_supplied_shell"]),
        approved_shell_geometry=_approved_shell(payload["approved_shell_geometry"]),
        bundle_peripheral_allowance_m=_string(
            payload["bundle_peripheral_allowance_m"], "bundle_peripheral_allowance_m"
        ),
        bundle_peripheral_allowance_evidence_refs=_array(
            payload["bundle_peripheral_allowance_evidence_refs"],
            "bundle_peripheral_allowance_evidence_refs",
            non_empty=True,
        ),
        required_minimum_radial_clearance_m=_string(
            payload["required_minimum_radial_clearance_m"],
            "required_minimum_radial_clearance_m",
        ),
        minimum_clearance_evidence_refs=_array(
            payload["minimum_clearance_evidence_refs"],
            "minimum_clearance_evidence_refs",
            non_empty=True,
        ),
        evidence_refs=_array(payload["evidence_refs"], "evidence_refs", non_empty=True),
    )


__all__ = ["SchemaFailure", "parse_request"]
