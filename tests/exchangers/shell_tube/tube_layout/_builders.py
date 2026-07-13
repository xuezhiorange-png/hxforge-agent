from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube import canonical as task020_canonical
from hexagent.exchangers.shell_tube.models import (
    AuthorityMode as Task020AuthorityMode,
)
from hexagent.exchangers.shell_tube.models import (
    CaseRevisionAuthority,
    CaseRevisionStatus,
    ComponentTokens,
    ConfigurationAuthorityBinding,
    ConstructionFamily,
    EquipmentFamily,
    Orientation,
    ShellAndTubeConfiguration,
    StandardClaimStatus,
)
from hexagent.exchangers.shell_tube.tube_layout.canonical import sha256_hex
from hexagent.exchangers.shell_tube.tube_layout.models import (
    ENVELOPE_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
)


def make_configuration(
    construction_family: ConstructionFamily = ConstructionFamily.FIXED_TUBESHEET,
) -> ShellAndTubeConfiguration:
    case = CaseRevisionAuthority(
        revision_id="rev-task021-001",
        payload_hash="a" * 64,
        domain_snapshot_hash="b" * 64,
        revision_status=CaseRevisionStatus.COMMITTED,
    )
    binding = ConfigurationAuthorityBinding(
        authority_mode=Task020AuthorityMode.INTERNAL_GENERIC,
        standard_system_id=None,
        case_authority=case,
        evaluated_rule_pack_authority=None,
        case_authority_evidence_refs=("case-ref",),
    )
    base = ShellAndTubeConfiguration(
        schema_version="task020.configuration.v1",
        configuration_id="",
        configuration_hash="",
        equipment_family=EquipmentFamily.SHELL_AND_TUBE,
        authority_mode=Task020AuthorityMode.INTERNAL_GENERIC,
        standard_claim_status=StandardClaimStatus.NO_STANDARD_CLAIM,
        construction_family=construction_family,
        orientation=Orientation.HORIZONTAL,
        shell_pass_count=1,
        tube_pass_count=2,
        component_tokens=ComponentTokens(front_head="A", shell="E", rear_head="L"),
        authority_binding=binding,
        case_authority=case,
        warnings=(),
        blockers=(),
    )
    primitive = {
        "schema_version": base.schema_version,
        "equipment_family": base.equipment_family.value,
        "authority_mode": base.authority_mode.value,
        "standard_claim_status": base.standard_claim_status.value,
        "construction_family": base.construction_family.value,
        "orientation": base.orientation.value,
        "shell_pass_count": base.shell_pass_count,
        "tube_pass_count": base.tube_pass_count,
        "component_tokens": {
            "front_head": "A",
            "shell": "E",
            "rear_head": "L",
        },
        "case_authority": {
            "revision_id": case.revision_id,
            "payload_hash": case.payload_hash,
            "domain_snapshot_hash": case.domain_snapshot_hash,
            "revision_status": case.revision_status.value,
        },
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": list(base.deferred_capabilities),
        "authority_binding": {
            "authority_mode": binding.authority_mode.value,
            "standard_system_id": None,
            "case_authority": {
                "revision_id": case.revision_id,
                "payload_hash": case.payload_hash,
                "domain_snapshot_hash": case.domain_snapshot_hash,
                "revision_status": case.revision_status.value,
            },
            "evaluated_rule_pack_authority": None,
            "case_authority_evidence_refs": ["case-ref"],
        },
    }
    payload = task020_canonical.canonical_payload(
        primitive,
        case_authority=primitive["case_authority"],
        evaluated_rule_pack_authority=None,
        canonical_warnings=(),
        canonical_blockers=(),
        deferred_capabilities=primitive["deferred_capabilities"],
        authority_binding=primitive["authority_binding"],
        schema_version=base.schema_version,
    )
    config_hash = task020_canonical.configuration_hash(payload)
    config_id = task020_canonical.configuration_id(config_hash)
    return ShellAndTubeConfiguration(
        **{
            **base.__dict__,
            "configuration_hash": config_hash,
            "configuration_id": config_id,
        }
    )


def geometry_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "geometry_id": "tube-od-20mm",
        "geometry_type": "tube",
        "revision": "1",
        "approval_state": "approved",
        "outer_diameter_m": "0.02",
        "inner_diameter_m": "0.016",
        "wall_thickness_m": "0.002",
        "record_hash": "c" * 64,
        "snapshot_hash": "",
        "source_binding": {
            "source_id": "geometry-source",
            "source_type": "approved-record",
            "source_revision": "1",
            "source_location": "memory://task021/synthetic",
            "evidence_ref": "geometry-evidence",
            "approved_by": "test-authority",
            "approved_at": "2026-07-13T00:00:00Z",
        },
    }
    payload["snapshot_hash"] = sha256_hex(
        {k: v for k, v in payload.items() if k != "snapshot_hash"}
    )
    return payload


def rule_payload(*, pattern_family: str = "SQUARE", maximum: int = 100000) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "profile_id": "hxforge.shell_tube.tube_layout.v1",
        "authority_mode": "INTERNAL_GENERIC",
        "rule_id": "generic-layout",
        "rule_version": "1",
        "rule_artifact_canonical_hash": "d" * 64,
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "license_evidence": {"status": "NO_STANDARD_CLAIM"},
        "approval_status": "approved",
        "provenance_edge_ids": ["edge-1"],
        "evidence_refs": ["rule-evidence"],
        "rule_pack_identity": None,
        "pattern_family": pattern_family,
        "pitch_m": "0.03",
        "edge_clearance_m": "0",
        "allowed_origin_modes": ["CENTER_ON_LATTICE_POINT", "CENTER_ON_PRIMITIVE_CELL"],
        "allowed_axis_orientations": ["PRIMARY_AXIS_X", "PRIMARY_AXIS_Y"],
        "allowed_exclusion_zone_types": ["AXIS_ALIGNED_RECTANGLE", "CIRCLE"],
        "maximum_candidate_positions": maximum,
        "snapshot_hash": "",
    }
    payload["snapshot_hash"] = sha256_hex(
        {k: v for k, v in payload.items() if k != "snapshot_hash"}
    )
    return payload


def make_request(
    *,
    construction_family: ConstructionFamily = ConstructionFamily.FIXED_TUBESHEET,
    pattern_family: str = "SQUARE",
    maximum: int = 100000,
) -> dict[str, Any]:
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "configuration": make_configuration(construction_family),
        "tube_geometry": geometry_payload(),
        "layout_rule_authority": rule_payload(pattern_family=pattern_family, maximum=maximum),
        "placement_envelope": {
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "tube_center_envelope_diameter_m": "0.12",
            "evidence_refs": ["envelope-evidence"],
        },
        "origin_mode": "CENTER_ON_LATTICE_POINT",
        "axis_orientation": "PRIMARY_AXIS_X",
        "exclusion_zones": [],
        "u_tube_pairing_plan": None,
        "evidence_refs": ["request-evidence"],
    }
