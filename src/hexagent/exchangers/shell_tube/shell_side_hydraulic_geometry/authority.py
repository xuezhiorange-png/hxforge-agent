# ruff: noqa: E501
"""TASK-031 upstream replay and authority verification (stages 3-7)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.baffle_geometry import models as task024_models
from hexagent.exchangers.shell_tube.baffle_geometry.validation import to_canonical_primitive
from hexagent.exchangers.shell_tube.tube_layout import canonical as task021_canonical
from hexagent.exchangers.shell_tube.tube_layout.canonical import internal_frozen_to_primitive
from hexagent.exchangers.shell_tube.tube_layout.models import PatternFamily, TubeLayout

from .canonical import ENGINEERING_AUTHORITY_HASH, parse_decimal, sha256_hex
from .models import (
    AGGREGATE_AUTHORITY_PROFILE_ID,
    BlockerCode,
    EngineeringAuthorityRequestBinding,
    MessageEntry,
    ShellSideHydraulicGeometryRequest,
)

_TASK024_GEOMETRY_URN_PREFIX = "urn:hxforge:task024:baffle-geometry:v1:"


class AuthorityFailure(Exception):
    def __init__(self, stage: int, *blockers: MessageEntry) -> None:
        super().__init__(blockers[0].message_key if blockers else "authority_failure")
        self.stage = stage
        self.blockers = blockers


def _message(
    code: BlockerCode,
    field_path: str | None,
    message_key: str,
    *,
    details: tuple[tuple[str, str], ...] = (),
) -> MessageEntry:
    return MessageEntry(
        code=code.value,
        field_path=field_path,
        message_key=message_key,
        evidence_refs=(),
        details=details,
    )


def layout_hash_payload(layout: TubeLayout) -> dict[str, Any]:
    positions = [
        {
            "position_id": pos.position_id,
            "u": pos.u,
            "v": pos.v,
            "x_m": pos.x_m,
            "y_m": pos.y_m,
        }
        for pos in layout.positions
    ]
    exclusion_audit = [
        {
            "zone_id": audit.zone_id,
            "rejected_position_count": audit.rejected_position_count,
            "reason_code": audit.reason_code,
            "evidence_refs": list(audit.evidence_refs),
        }
        for audit in layout.exclusion_audit
    ]
    warnings = [
        {
            "code": item.code,
            "field_path": item.field_path,
            "message_key": item.message_key,
            "evidence_refs": list(item.evidence_refs),
            "details": (
                None if item.details is None else internal_frozen_to_primitive(item.details)
            ),
        }
        for item in layout.warnings
    ]
    return {
        "schema_version": layout.schema_version,
        "request_hash": layout.request_hash,
        "positions": positions,
        "tube_hole_count": layout.tube_hole_count,
        "physical_tube_count": layout.physical_tube_count,
        "boundary_rejection_count": layout.boundary_rejection_count,
        "exclusion_rejection_count": layout.exclusion_rejection_count,
        "exclusion_audit": exclusion_audit,
        "warnings": warnings,
        "blockers": [],
        "deferred_capabilities": list(layout.deferred_capabilities),
        "provenance_pre_hash": _layout_provenance_pre_hash(layout),
    }


def _layout_provenance_pre_hash(layout: TubeLayout) -> dict[str, Any]:
    prov = internal_frozen_to_primitive(layout.provenance)
    case_authority = _task020_case_authority_primitive(prov["task020_case_authority"])
    geometry_source = _task021_source_binding_primitive(prov["geometry_source_binding"])
    rule_pack_raw = prov["rule_pack_identity"]
    rule_pack = (
        None if rule_pack_raw is None else _task021_rule_pack_identity_primitive(rule_pack_raw)
    )
    warnings_list = [
        {
            "code": w["code"],
            "field_path": w["field_path"],
            "message_key": w["message_key"],
            "evidence_refs": list(w["evidence_refs"]),
            "details": w["details"],
        }
        for w in prov["warnings"]
    ]
    return {
        "task_id": prov["task_id"],
        "design_contract_path": prov["design_contract_path"],
        "task020_configuration_id": prov["task020_configuration_id"],
        "task020_configuration_hash": prov["task020_configuration_hash"],
        "task020_case_authority": case_authority,
        "geometry_id": prov["geometry_id"],
        "geometry_revision": prov["geometry_revision"],
        "geometry_record_hash": prov["geometry_record_hash"],
        "tube_geometry_snapshot_hash": prov["tube_geometry_snapshot_hash"],
        "geometry_source_binding": geometry_source,
        "layout_rule_profile_id": prov["layout_rule_profile_id"],
        "layout_rule_id": prov["layout_rule_id"],
        "layout_rule_version": prov["layout_rule_version"],
        "rule_artifact_canonical_hash": prov["rule_artifact_canonical_hash"],
        "layout_rule_snapshot_hash": prov["layout_rule_snapshot_hash"],
        "source_class": prov["source_class"],
        "approval_status": prov["approval_status"],
        "provenance_edge_ids": list(prov["provenance_edge_ids"]),
        "layout_rule_evidence_refs": list(prov["layout_rule_evidence_refs"]),
        "rule_pack_identity": rule_pack,
        "envelope_evidence_refs": list(prov["envelope_evidence_refs"]),
        "exclusion_zone_evidence_refs": [
            list(refs) for refs in prov["exclusion_zone_evidence_refs"]
        ],
        "u_tube_pairing_evidence_refs": prov["u_tube_pairing_evidence_refs"],
        "software_version": prov["software_version"],
        "git_commit": prov["git_commit"],
        "request_hash": prov["request_hash"],
        "warnings": warnings_list,
        "deferred_capabilities": list(prov["deferred_capabilities"]),
    }


def _task020_case_authority_primitive(case: Any) -> dict[str, Any]:
    return {
        "revision_id": case["revision_id"],
        "payload_hash": case["payload_hash"],
        "domain_snapshot_hash": case["domain_snapshot_hash"],
        "revision_status": case["revision_status"],
    }


def _task021_source_binding_primitive(source: Any) -> dict[str, Any]:
    return {
        "source_id": source["source_id"],
        "source_type": source["source_type"],
        "source_revision": source["source_revision"],
        "source_location": source["source_location"],
        "evidence_ref": source["evidence_ref"],
        "approved_by": source["approved_by"],
        "approved_at": source["approved_at"],
    }


def _task021_rule_pack_identity_primitive(identity: Any) -> dict[str, Any]:
    return {
        "rule_pack_id": identity["rule_pack_id"],
        "rule_pack_version": identity["rule_pack_version"],
        "rule_pack_canonical_hash": identity["rule_pack_canonical_hash"],
    }


def _task024_message_projection(entry: task024_models.MessageEntry) -> dict[str, Any]:
    return {
        "code": entry.code,
        "field_path": entry.field_path,
        "message_key": entry.message_key,
        "evidence_refs": list(entry.evidence_refs),
        "details": [[key, value] for key, value in entry.details],
    }


def _task024_geometry_hash_payload(geometry: task024_models.BaffleGeometry) -> dict[str, Any]:
    provenance_dict = {key: value for key, value in geometry.provenance}
    return {
        "schema_version": geometry.schema_version,
        "request_hash": geometry.request_hash,
        "task020_configuration_id": geometry.task020_configuration_id,
        "task020_configuration_hash": geometry.task020_configuration_hash,
        "task021_layout_id": geometry.task021_layout_id,
        "task021_layout_hash": geometry.task021_layout_hash,
        "task022_geometry_id": geometry.task022_geometry_id,
        "task022_geometry_hash": geometry.task022_geometry_hash,
        "construction_family": geometry.construction_family,
        "equipment_orientation": geometry.equipment_orientation,
        "shell_pass_count": geometry.shell_pass_count,
        "tube_pass_count": geometry.tube_pass_count,
        "shell_inside_diameter_m": geometry.shell_inside_diameter_m,
        "tube_outer_diameter_m": geometry.tube_outer_diameter_m,
        "axial_span": to_canonical_primitive(geometry.axial_span),
        "design_authority": to_canonical_primitive(geometry.design_authority),
        "usable_baffle_span_m": geometry.usable_baffle_span_m,
        "baffle_diameter_m": geometry.baffle_diameter_m,
        "baffle_radius_m": geometry.baffle_radius_m,
        "baffle_hole_diameter_m": geometry.baffle_hole_diameter_m,
        "baffle_hole_radius_m": geometry.baffle_hole_radius_m,
        "cut_height_m": geometry.cut_height_m,
        "chord_offset_from_center_m": geometry.chord_offset_from_center_m,
        "baffle_planes": [to_canonical_primitive(plane) for plane in geometry.baffle_planes],
        "position_count": geometry.position_count,
        "warnings": [_task024_message_projection(item) for item in geometry.warnings],
        "blockers": [_task024_message_projection(item) for item in geometry.blockers],
        "deferred_capabilities": list(geometry.deferred_capabilities),
        "provenance": provenance_dict,
    }


def _task024_geometry_id_from_hash(geometry_hash: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, _TASK024_GEOMETRY_URN_PREFIX + geometry_hash))


def verify_task021_layout(layout: TubeLayout) -> None:
    blockers: list[MessageEntry] = []
    if layout.schema_version != "task021.tube-layout.v1":
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK021_LAYOUT_INVALID,
                "tube_layout.schema_version",
                "task021_layout_schema_version_unsupported",
            )
        )
    if layout.blockers:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK021_LAYOUT_HAS_BLOCKERS,
                "tube_layout.blockers",
                "task021_layout_has_blockers",
            )
        )
    if blockers:
        raise AuthorityFailure(3, *blockers)
    expected_hash = sha256_hex(layout_hash_payload(layout))
    expected_id = task021_canonical.layout_id(expected_hash)
    if expected_hash != layout.layout_hash or expected_id != layout.layout_id:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK021_LAYOUT_IDENTITY_MISMATCH,
                "tube_layout",
                "task021_layout_identity_mismatch",
            )
        )
        raise AuthorityFailure(3, *blockers)


def verify_task024_result(result: task024_models.BaffleGeometryValidationResult) -> None:
    blockers: list[MessageEntry] = []
    if result.blockers:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_HAS_BLOCKERS,
                "baffle_geometry_result.blockers",
                "task024_result_has_blockers",
            )
        )
        raise AuthorityFailure(4, *blockers)
    if result.status is task024_models.ValidationStatus.VALID and result.geometry is None:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_GEOMETRY_MISSING,
                "baffle_geometry_result.geometry",
                "task024_geometry_missing",
            )
        )
        raise AuthorityFailure(4, *blockers)
    if result.geometry is None:
        return
    geometry = result.geometry
    expected_hash = sha256_hex(_task024_geometry_hash_payload(geometry))
    expected_id = _task024_geometry_id_from_hash(expected_hash)
    if expected_hash != geometry.geometry_hash or expected_id != geometry.geometry_id:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_IDENTITY_MISMATCH,
                "baffle_geometry_result",
                "task024_identity_mismatch",
            )
        )
        raise AuthorityFailure(4, *blockers)


def verify_cross_binding(request: ShellSideHydraulicGeometryRequest) -> None:
    layout = request.tube_layout
    result = request.baffle_geometry_result
    geometry = result.geometry
    blockers: list[MessageEntry] = []
    if geometry is None:
        return
    if layout.task020_configuration_id != geometry.task020_configuration_id:
        blockers.append(
            _message(
                BlockerCode.SSHG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH,
                "tube_layout",
                "upstream_configuration_binding_mismatch",
            )
        )
    if layout.task020_configuration_hash != geometry.task020_configuration_hash:
        blockers.append(
            _message(
                BlockerCode.SSHG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH,
                "tube_layout",
                "upstream_configuration_binding_mismatch",
            )
        )
    if layout.layout_id != geometry.task021_layout_id:
        blockers.append(
            _message(
                BlockerCode.SSHG_UPSTREAM_LAYOUT_BINDING_MISMATCH,
                "tube_layout",
                "upstream_layout_binding_mismatch",
            )
        )
    if layout.layout_hash != geometry.task021_layout_hash:
        blockers.append(
            _message(
                BlockerCode.SSHG_UPSTREAM_LAYOUT_BINDING_MISMATCH,
                "tube_layout",
                "upstream_layout_binding_mismatch",
            )
        )
    # task022 transitive binding via geometry fields
    if parse_decimal(layout.tube_geometry.outer_diameter_m) != parse_decimal(
        geometry.tube_outer_diameter_m
    ):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK021_TASK024_TUBE_OD_MISMATCH,
                "tube_layout",
                "task021_task024_tube_od_mismatch",
            )
        )
    if blockers:
        raise AuthorityFailure(5, *blockers)


def extract_central_spacing(
    design_authority: task024_models.CallerSuppliedBaffleDesignAuthority,
) -> tuple[Decimal | None, list[MessageEntry]]:
    blockers: list[MessageEntry] = []
    spacing = design_authority.spacing_sequence_m
    baffle_count = design_authority.baffle_count
    if len(spacing) != baffle_count + 1:
        blockers.append(
            _message(
                BlockerCode.SSHG_SPACING_SEQUENCE_INVALID,
                "baffle_geometry_result.geometry.design_authority.spacing_sequence_m",
                "spacing_sequence_invalid",
            )
        )
        return None, blockers
    central = spacing[1:baffle_count]
    if not central:
        blockers.append(
            _message(
                BlockerCode.SSHG_CENTRAL_INTER_BAFFLE_SPACING_ABSENT,
                "baffle_geometry_result.geometry.design_authority.spacing_sequence_m",
                "central_inter_baffle_spacing_absent",
            )
        )
        return None, blockers
    if len(set(central)) != 1:
        blockers.append(
            _message(
                BlockerCode.SSHG_CENTRAL_INTER_BAFFLE_SPACING_NONUNIFORM,
                "baffle_geometry_result.geometry.design_authority.spacing_sequence_m",
                "central_inter_baffle_spacing_nonuniform",
            )
        )
        return None, blockers
    return parse_decimal(central[0], positive=True), blockers


def verify_applicability(request: ShellSideHydraulicGeometryRequest) -> Decimal:
    layout = request.tube_layout
    geometry = request.baffle_geometry_result.geometry
    assert geometry is not None
    design = geometry.design_authority
    blockers: list[MessageEntry] = []
    if geometry.construction_family != "FIXED_TUBESHEET":
        blockers.append(
            _message(
                BlockerCode.SSHG_CONSTRUCTION_FAMILY_UNSUPPORTED,
                "baffle_geometry_result.geometry.construction_family",
                "construction_family_unsupported",
            )
        )
    if geometry.shell_pass_count != 1:
        blockers.append(
            _message(
                BlockerCode.SSHG_SHELL_PASS_COUNT_UNSUPPORTED,
                "baffle_geometry_result.geometry.shell_pass_count",
                "shell_pass_count_unsupported",
            )
        )
    if design.baffle_type is not task024_models.BaffleType.SINGLE_SEGMENTAL:
        blockers.append(
            _message(
                BlockerCode.SSHG_BAFFLE_TYPE_UNSUPPORTED,
                "baffle_geometry_result.geometry.design_authority.baffle_type",
                "baffle_type_unsupported",
            )
        )
    if design.baffle_count < 2:
        blockers.append(
            _message(
                BlockerCode.SSHG_BAFFLE_COUNT_INSUFFICIENT,
                "baffle_geometry_result.geometry.design_authority.baffle_count",
                "baffle_count_insufficient",
            )
        )
    pattern = layout.layout_rule_authority.pattern_family
    if pattern not in {PatternFamily.SQUARE, PatternFamily.TRIANGULAR}:
        blockers.append(
            _message(
                BlockerCode.SSHG_PATTERN_FAMILY_UNSUPPORTED,
                "tube_layout.layout_rule_authority.pattern_family",
                "pattern_family_unsupported",
            )
        )
    central_spacing, spacing_blockers = extract_central_spacing(design)
    blockers.extend(spacing_blockers)
    if blockers:
        raise AuthorityFailure(6, *blockers)
    assert central_spacing is not None
    return central_spacing


def verify_engineering_authority(binding: EngineeringAuthorityRequestBinding) -> None:
    blockers: list[MessageEntry] = []
    if binding.authority_profile_id != AGGREGATE_AUTHORITY_PROFILE_ID:
        blockers.append(
            _message(
                BlockerCode.SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH,
                "engineering_authority",
                "engineering_authority_identity_mismatch",
            )
        )
    if binding.authority_hash != ENGINEERING_AUTHORITY_HASH:
        blockers.append(
            _message(
                BlockerCode.SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH,
                "engineering_authority",
                "engineering_authority_identity_mismatch",
            )
        )
    if blockers:
        raise AuthorityFailure(7, *blockers)


__all__ = [
    "AuthorityFailure",
    "extract_central_spacing",
    "layout_hash_payload",
    "verify_applicability",
    "verify_cross_binding",
    "verify_engineering_authority",
    "verify_task021_layout",
    "verify_task024_result",
]
