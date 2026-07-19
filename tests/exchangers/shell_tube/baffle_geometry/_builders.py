"""Deterministic upstream-graph builders for TASK-024 Round 4 tests.

This module is **test-only**. It provides fixed-shape, fixed-hash
``ShellAndTubeConfiguration``, ``TubeLayout``, ``ShellBundleGeometry``,
``CallerSuppliedBaffleAxialSpan``, ``CallerSuppliedBaffleDesignAuthority``,
and ``BaffleGeometryRequest`` instances. Each builder runs the
upstream canonical pipeline once at construction time so the stored
hashes / ids are by construction byte-equivalent to the recomputed
values, which is what Round-4 ``authority.validate_authority_foundation``
will assert on the happy path.

The builders produce **synthetic** numeric values. None of the values
are engineering recommendations, vendor specifications, or standard
references.
"""

from __future__ import annotations

from typing import Any, cast

from hexagent.exchangers.shell_tube import canonical as _task020_canonical
from hexagent.exchangers.shell_tube.baffle_geometry import (
    canonical as _t024_canonical,
)
from hexagent.exchangers.shell_tube.baffle_geometry import (
    models as _t024,
)
from hexagent.exchangers.shell_tube.models import (
    AuthorityMode as _Task020AuthorityMode,
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
from hexagent.exchangers.shell_tube.shell_bundle_geometry.canonical import (
    sha256_hex as _task022_sha256_hex,
)
from hexagent.exchangers.shell_tube.shell_bundle_geometry.models import (
    ShellBundleGeometryRuleAuthoritySnapshot,
    ShellInsideDiameterAuthorityMode,
)
from hexagent.exchangers.shell_tube.tube_layout import canonical as _task021_canonical
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    force_frozen_canonical,
    internal_frozen_to_primitive,
)
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    sha256_hex as _task021_sha256_hex,
)
from hexagent.exchangers.shell_tube.tube_layout.models import (
    ApprovedTubeGeometrySnapshot,
    CircularTubeCenterEnvelope,
    LayoutRuleAuthoritySnapshot,
    OriginMode,
    PatternFamily,
    ProvenancePreHashProjection,
    SourceBindingSnapshot,
    TubeLayout,
    TubePosition,
)
from hexagent.exchangers.shell_tube.tube_layout.models import (
    AuthorityMode as _Task021AuthorityMode,
)

# ---------------------------------------------------------------------------
# TASK-020 ShellAndTubeConfiguration.
# ---------------------------------------------------------------------------

_REVISION_ID: str = "rev-task024-001"
_CASE_PAYLOAD_HASH: str = "a" * 64
_CASE_DOMAIN_HASH: str = "b" * 64
_TUBE_GEOMETRY_RECORD_HASH: str = "c" * 64
_RULE_ARTIFACT_HASH: str = "d" * 64
_TASK024_NAMESPACES: dict[str, str] = {}


def _t024_namespace(name: str) -> str:
    digest = _t024_canonical.sha256_canonical(name).hex()
    return digest[:32]


def make_shell_and_tube_configuration(
    *,
    construction_family: ConstructionFamily = ConstructionFamily.FIXED_TUBESHEET,
    shell_pass_count: int = 1,
    tube_pass_count: int = 2,
    orientation: Orientation = Orientation.HORIZONTAL,
) -> ShellAndTubeConfiguration:
    case = CaseRevisionAuthority(
        revision_id=_REVISION_ID,
        payload_hash=_CASE_PAYLOAD_HASH,
        domain_snapshot_hash=_CASE_DOMAIN_HASH,
        revision_status=CaseRevisionStatus.COMMITTED,
    )
    binding = ConfigurationAuthorityBinding(
        authority_mode=_Task020AuthorityMode.INTERNAL_GENERIC,
        standard_system_id=None,
        case_authority=case,
        evaluated_rule_pack_authority=None,
        case_authority_evidence_refs=("task024-case-ref",),
    )
    base = ShellAndTubeConfiguration(
        schema_version="task020.configuration.v1",
        configuration_id="",
        configuration_hash="",
        equipment_family=EquipmentFamily.SHELL_AND_TUBE,
        authority_mode=_Task020AuthorityMode.INTERNAL_GENERIC,
        standard_claim_status=StandardClaimStatus.NO_STANDARD_CLAIM,
        construction_family=construction_family,
        orientation=orientation,
        shell_pass_count=shell_pass_count,
        tube_pass_count=tube_pass_count,
        component_tokens=ComponentTokens(front_head="A", shell="E", rear_head="L"),
        authority_binding=binding,
        case_authority=case,
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
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
            "front_head": base.component_tokens.front_head,
            "shell": base.component_tokens.shell,
            "rear_head": base.component_tokens.rear_head,
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
            "case_authority_evidence_refs": ["task024-case-ref"],
        },
    }
    payload = _task020_canonical.canonical_payload(
        primitive,
        case_authority=cast(Any, primitive["case_authority"]),
        evaluated_rule_pack_authority=None,
        canonical_warnings=(),
        canonical_blockers=(),
        deferred_capabilities=cast(Any, primitive["deferred_capabilities"]),
        authority_binding=cast(Any, primitive["authority_binding"]),
        schema_version=base.schema_version,
    )
    config_hash = _task020_canonical.configuration_hash(payload)
    config_id = _task020_canonical.configuration_id(config_hash)
    return ShellAndTubeConfiguration(
        **{
            **base.__dict__,
            "configuration_hash": config_hash,
            "configuration_id": config_id,
        }
    )


# ---------------------------------------------------------------------------
# TASK-021 TubeLayout.
# ---------------------------------------------------------------------------


def _make_tube_geometry_snapshot() -> ApprovedTubeGeometrySnapshot:
    source = SourceBindingSnapshot(
        source_id="task024-geometry-source",
        source_type="approved-record",
        source_revision="1",
        source_location="memory://task024/synthetic",
        evidence_ref="task024-geometry-evidence",
        approved_by="test-authority",
        approved_at="2026-07-19T00:00:00Z",
    )
    payload = {
        "geometry_id": "task024-tube-od-20mm",
        "geometry_type": "tube",
        "revision": "1",
        "approval_state": "approved",
        "outer_diameter_m": "0.02",
        "inner_diameter_m": "0.016",
        "wall_thickness_m": "0.002",
        "record_hash": _TUBE_GEOMETRY_RECORD_HASH,
        "source_binding": {
            "source_id": source.source_id,
            "source_type": source.source_type,
            "source_revision": source.source_revision,
            "source_location": source.source_location,
            "evidence_ref": source.evidence_ref,
            "approved_by": source.approved_by,
            "approved_at": source.approved_at,
        },
    }
    payload["snapshot_hash"] = _task021_sha256_hex(
        {k: v for k, v in payload.items() if k != "snapshot_hash"}
    )
    return ApprovedTubeGeometrySnapshot(
        geometry_id=cast(Any, payload["geometry_id"]),
        geometry_type=cast(Any, payload["geometry_type"]),
        revision=cast(Any, payload["revision"]),
        approval_state=cast(Any, payload["approval_state"]),
        outer_diameter_m=cast(Any, payload["outer_diameter_m"]),
        inner_diameter_m=cast(Any, payload["inner_diameter_m"]),
        wall_thickness_m=cast(Any, payload["wall_thickness_m"]),
        record_hash=cast(Any, payload["record_hash"]),
        snapshot_hash=cast(Any, payload["snapshot_hash"]),
        source_binding=source,
    )


def _task020_case_authority_primitive(case: Any) -> dict[str, Any]:
    return {
        "revision_id": case.revision_id,
        "payload_hash": case.payload_hash,
        "domain_snapshot_hash": case.domain_snapshot_hash,
        "revision_status": case.revision_status.value,
    }


def _make_layout_rule_snapshot() -> LayoutRuleAuthoritySnapshot:
    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        force_frozen_canonical,
        internal_frozen_to_primitive,
    )

    rule_pack = None
    license_evidence = force_frozen_canonical({"status": "NO_STANDARD_CLAIM"})
    payload: dict[str, Any] = {
        "profile_id": "hxforge.shell_tube.tube_layout.v1",
        "authority_mode": _Task021AuthorityMode.INTERNAL_GENERIC.value,
        "rule_id": "generic-task024-layout",
        "rule_version": "1",
        "rule_artifact_canonical_hash": _RULE_ARTIFACT_HASH,
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "license_evidence": license_evidence,
        "approval_status": "approved",
        "provenance_edge_ids": ["edge-1"],
        "evidence_refs": ["task024-rule-evidence"],
        "rule_pack_identity": rule_pack,
        "pattern_family": PatternFamily.SQUARE.value,
        "pitch_m": "0.03",
        "edge_clearance_m": "0",
        "allowed_origin_modes": [
            OriginMode.CENTER_ON_LATTICE_POINT.value,
            OriginMode.CENTER_ON_PRIMITIVE_CELL.value,
        ],
        "allowed_axis_orientations": ["PRIMARY_AXIS_X", "PRIMARY_AXIS_Y"],
        "allowed_exclusion_zone_types": [
            "AXIS_ALIGNED_RECTANGLE",
            "CIRCLE",
        ],
        "maximum_candidate_positions": 100000,
        "snapshot_hash": "",
    }
    license_evidence_dict = internal_frozen_to_primitive(payload["license_evidence"])
    payload["snapshot_hash"] = _task021_sha256_hex(
        {k: v for k, v in payload.items() if k != "snapshot_hash"}
        | {"license_evidence": license_evidence_dict}
    )
    return LayoutRuleAuthoritySnapshot(
        profile_id=payload["profile_id"],
        authority_mode=_Task021AuthorityMode.INTERNAL_GENERIC,
        rule_id=payload["rule_id"],
        rule_version=payload["rule_version"],
        rule_artifact_canonical_hash=payload["rule_artifact_canonical_hash"],
        source_class=payload["source_class"],
        license_evidence=payload["license_evidence"],
        approval_status=payload["approval_status"],
        provenance_edge_ids=tuple(payload["provenance_edge_ids"]),
        evidence_refs=tuple(payload["evidence_refs"]),
        rule_pack_identity=None,
        pattern_family=PatternFamily.SQUARE,
        pitch_m=payload["pitch_m"],
        edge_clearance_m=payload["edge_clearance_m"],
        allowed_origin_modes=(
            OriginMode.CENTER_ON_LATTICE_POINT,
            OriginMode.CENTER_ON_PRIMITIVE_CELL,
        ),
        allowed_axis_orientations=cast(Any, ("PRIMARY_AXIS_X", "PRIMARY_AXIS_Y")),
        allowed_exclusion_zone_types=cast(Any, ("AXIS_ALIGNED_RECTANGLE", "CIRCLE")),
        maximum_candidate_positions=payload["maximum_candidate_positions"],
        snapshot_hash=payload["snapshot_hash"],
    )


def _make_request_hash(
    configuration_id: str,
    tube_geometry_snapshot_hash: str,
) -> str:
    payload = {
        "configuration_id": configuration_id,
        "tube_geometry_snapshot_hash": tube_geometry_snapshot_hash,
    }
    return _task021_sha256_hex(payload)


def make_tube_layout(
    configuration: ShellAndTubeConfiguration,
    *,
    position_count: int = 4,
) -> TubeLayout:
    geometry = _make_tube_geometry_snapshot()
    rule_snapshot = _make_layout_rule_snapshot()
    positions: list[TubePosition] = []
    for index in range(position_count):
        u = index
        v = 0
        x_m = f"{0.01 * (index + 1):.6f}"
        y_m = "0.000000"
        position_id = _task021_position_id_for(
            configuration.configuration_id, geometry.snapshot_hash, u, v
        )
        positions.append(
            TubePosition(
                position_id=position_id,
                u=u,
                v=v,
                x_m=x_m,
                y_m=y_m,
            )
        )
    request_hash = _make_request_hash(configuration.configuration_id, geometry.snapshot_hash)
    layout_provenance_pre_hash = _make_layout_provenance_pre_hash(
        configuration, geometry, rule_snapshot, request_hash
    )
    layout_hash_payload = {
        "schema_version": "task021.tube-layout.v1",
        "request_hash": request_hash,
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
        "tube_hole_count": position_count,
        "physical_tube_count": position_count,
        "boundary_rejection_count": 0,
        "exclusion_rejection_count": 0,
        "exclusion_audit": [],
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
        "provenance_pre_hash": layout_provenance_pre_hash,
    }
    layout_hash = _task021_sha256_hex(layout_hash_payload)
    layout_id = _task021_layout_id_for(layout_hash)
    # ``layout_hash_payload`` itself is hashed with the pre-hash
    # fragment; the stored provenance fragment MUST NOT carry
    # ``layout_hash`` (the value is folded into the layout-hash
    # itself, not into the pre-hash payload that participates in
    # the layout-hash computation).
    provenance_frozen = force_frozen_canonical(layout_provenance_pre_hash)
    case_authority_frozen = force_frozen_canonical(
        _task020_case_authority_primitive(configuration.case_authority)
    )
    return TubeLayout(
        schema_version="task021.tube-layout.v1",
        layout_id=layout_id,
        layout_hash=layout_hash,
        request_hash=request_hash,
        task020_configuration_id=configuration.configuration_id,
        task020_configuration_hash=configuration.configuration_hash,
        case_authority=case_authority_frozen,
        construction_family=configuration.construction_family.value,
        equipment_orientation=cast(Any, configuration.orientation.value),
        shell_pass_count=configuration.shell_pass_count,
        tube_pass_count=configuration.tube_pass_count,
        tube_geometry=geometry,
        layout_rule_authority=rule_snapshot,
        placement_envelope=CircularTubeCenterEnvelope(
            schema_version="task021.placement-envelope.v1",
            tube_center_envelope_diameter_m="0.5",
            evidence_refs=("task024-envelope-evidence",),
        ),
        origin_mode=OriginMode.CENTER_ON_LATTICE_POINT,
        axis_orientation=cast(Any, "PRIMARY_AXIS_X"),
        exclusion_zones=(),
        positions=tuple(positions),
        tube_hole_count=position_count,
        physical_tube_count=position_count,
        boundary_rejection_count=0,
        exclusion_rejection_count=0,
        exclusion_audit=(),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=provenance_frozen,
    )


def _task021_position_id_for(request_hash: str, snapshot_hash: str, u: int, v: int) -> str:
    payload = {
        "request_hash": request_hash,
        "snapshot_hash": snapshot_hash,
        "u": u,
        "v": v,
    }
    return _task021_sha256_hex(payload)


def _task021_layout_id_for(layout_hash: str) -> str:
    return _task021_canonical.layout_id(layout_hash)


def _make_layout_provenance_pre_hash(
    configuration: ShellAndTubeConfiguration,
    geometry: ApprovedTubeGeometrySnapshot,
    rule_snapshot: LayoutRuleAuthoritySnapshot,
    request_hash: str,
) -> dict[str, Any]:
    return {
        "task_id": "task021",
        "design_contract_path": "docs/tasks/TASK-021-shell-and-tube-tube-layout.md",
        "task020_configuration_id": configuration.configuration_id,
        "task020_configuration_hash": configuration.configuration_hash,
        "task020_case_authority": {
            "revision_id": configuration.case_authority.revision_id,
            "payload_hash": configuration.case_authority.payload_hash,
            "domain_snapshot_hash": configuration.case_authority.domain_snapshot_hash,
            "revision_status": configuration.case_authority.revision_status.value,
        },
        "geometry_id": geometry.geometry_id,
        "geometry_revision": geometry.revision,
        "geometry_record_hash": geometry.record_hash,
        "tube_geometry_snapshot_hash": geometry.snapshot_hash,
        "geometry_source_binding": {
            "source_id": geometry.source_binding.source_id,
            "source_type": geometry.source_binding.source_type,
            "source_revision": geometry.source_binding.source_revision,
            "source_location": geometry.source_binding.source_location,
            "evidence_ref": geometry.source_binding.evidence_ref,
            "approved_by": geometry.source_binding.approved_by,
            "approved_at": geometry.source_binding.approved_at,
        },
        "layout_rule_profile_id": rule_snapshot.profile_id,
        "layout_rule_id": rule_snapshot.rule_id,
        "layout_rule_version": rule_snapshot.rule_version,
        "rule_artifact_canonical_hash": rule_snapshot.rule_artifact_canonical_hash,
        "layout_rule_snapshot_hash": rule_snapshot.snapshot_hash,
        "source_class": rule_snapshot.source_class,
        "approval_status": rule_snapshot.approval_status,
        "provenance_edge_ids": list(rule_snapshot.provenance_edge_ids),
        "layout_rule_evidence_refs": list(rule_snapshot.evidence_refs),
        "rule_pack_identity": None,
        "envelope_evidence_refs": ["task024-envelope-evidence"],
        "exclusion_zone_evidence_refs": [],
        "u_tube_pairing_evidence_refs": None,
        "software_version": "task024-test",
        "git_commit": "test-only",
        "request_hash": request_hash,
        "warnings": [],
        "deferred_capabilities": [],
    }


def _make_layout_provenance(
    configuration: ShellAndTubeConfiguration,
    geometry: ApprovedTubeGeometrySnapshot,
    rule_snapshot: LayoutRuleAuthoritySnapshot,
    request_hash: str,
    layout_hash: str,
) -> ProvenancePreHashProjection:
    pre_hash = _make_layout_provenance_pre_hash(
        configuration, geometry, rule_snapshot, request_hash
    )
    pre_hash_with_layout = dict(pre_hash)
    pre_hash_with_layout["layout_hash"] = layout_hash
    return ProvenancePreHashProjection(
        task_id=pre_hash["task_id"],
        design_contract_path=pre_hash["design_contract_path"],
        task020_configuration_id=pre_hash["task020_configuration_id"],
        task020_configuration_hash=pre_hash["task020_configuration_hash"],
        task020_case_authority=force_frozen_canonical(pre_hash["task020_case_authority"]),
        geometry_id=pre_hash["geometry_id"],
        geometry_revision=pre_hash["geometry_revision"],
        geometry_record_hash=pre_hash["geometry_record_hash"],
        tube_geometry_snapshot_hash=pre_hash["tube_geometry_snapshot_hash"],
        geometry_source_binding=force_frozen_canonical(pre_hash["geometry_source_binding"]),
        layout_rule_profile_id=pre_hash["layout_rule_profile_id"],
        layout_rule_id=pre_hash["layout_rule_id"],
        layout_rule_version=pre_hash["layout_rule_version"],
        rule_artifact_canonical_hash=pre_hash["rule_artifact_canonical_hash"],
        layout_rule_snapshot_hash=pre_hash["layout_rule_snapshot_hash"],
        source_class=pre_hash["source_class"],
        approval_status=pre_hash["approval_status"],
        provenance_edge_ids=tuple(pre_hash["provenance_edge_ids"]),
        layout_rule_evidence_refs=tuple(pre_hash["layout_rule_evidence_refs"]),
        rule_pack_identity=None,
        envelope_evidence_refs=tuple(pre_hash["envelope_evidence_refs"]),
        exclusion_zone_evidence_refs=tuple(),
        u_tube_pairing_evidence_refs=None,
        software_version=pre_hash["software_version"],
        git_commit=pre_hash["git_commit"],
        request_hash=pre_hash["request_hash"],
        warnings=(),
        deferred_capabilities=(),
    )


# ---------------------------------------------------------------------------
# TASK-022 ShellBundleGeometry.
# ---------------------------------------------------------------------------


def _make_geometry_rule_authority() -> ShellBundleGeometryRuleAuthoritySnapshot:
    payload: dict[str, Any] = {
        "schema_version": "task022.shell-bundle-geometry-rule-authority.v1",
        "profile_id": "hxforge.shell_tube.shell_bundle_geometry.v1",
        "authority_mode": "INTERNAL_GENERIC",
        "rule_id": "generic-task024-geometry",
        "rule_version": "1",
        "rule_artifact_canonical_hash": "e" * 64,
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "license_evidence": {"status": "NO_STANDARD_CLAIM"},
        "approval_status": "approved",
        "provenance_edge_ids": ["edge-1"],
        "evidence_refs": ["task024-geometry-rule-evidence"],
        "rule_pack_identity": None,
        "allowed_shell_authority_modes": [
            ShellInsideDiameterAuthorityMode.CALLER_SUPPLIED_EXPLICIT.value,
        ],
        "minimum_bundle_peripheral_allowance_m": "0.001",
        "minimum_radial_clearance_m": "0.001",
        "maximum_position_count": 1000,
        "snapshot_hash": "",
    }
    payload["snapshot_hash"] = _task022_sha256_hex(
        {k: v for k, v in payload.items() if k != "snapshot_hash"}
    )
    return ShellBundleGeometryRuleAuthoritySnapshot(
        schema_version=payload["schema_version"],
        profile_id=payload["profile_id"],
        authority_mode=cast(Any, "INTERNAL_GENERIC"),
        rule_id=payload["rule_id"],
        rule_version=payload["rule_version"],
        rule_artifact_canonical_hash=payload["rule_artifact_canonical_hash"],
        source_class=payload["source_class"],
        license_evidence=payload["license_evidence"],
        approval_status=payload["approval_status"],
        provenance_edge_ids=tuple(payload["provenance_edge_ids"]),
        evidence_refs=tuple(payload["evidence_refs"]),
        rule_pack_identity=None,
        allowed_shell_authority_modes=(ShellInsideDiameterAuthorityMode.CALLER_SUPPLIED_EXPLICIT,),
        minimum_bundle_peripheral_allowance_m=payload["minimum_bundle_peripheral_allowance_m"],
        minimum_radial_clearance_m=payload["minimum_radial_clearance_m"],
        maximum_position_count=payload["maximum_position_count"],
        snapshot_hash=payload["snapshot_hash"],
    )


def make_shell_bundle_geometry(
    configuration: ShellAndTubeConfiguration,
    layout: TubeLayout,
    *,
    shell_inside_diameter_m: str = "0.5",
    shell_radius_m: str = "0.25",
    bare_tube_bundle_radius_m: str = "0.2",
    bare_tube_bundle_diameter_m: str = "0.4",
    bundle_peripheral_allowance_m: str = "0.005",
    bundle_outer_envelope_radius_m: str = "0.205",
    bundle_outer_envelope_diameter_m: str = "0.41",
    shell_to_bundle_radial_clearance_m: str = "0.045",
    shell_to_bundle_diametral_clearance_m: str = "0.09",
    required_minimum_radial_clearance_m: str = "0.001",
    radial_clearance_margin_m: str = "0.044",
    limiting_position_ids: tuple[str, ...] = (),
    request_hash: str | None = None,
) -> Any:
    from hexagent.exchangers.shell_tube.shell_bundle_geometry.models import (
        ShellBundleGeometry,
    )

    if request_hash is None:
        request_hash = layout.request_hash
    geometry_rule = _make_geometry_rule_authority()
    geometry_payload = {
        "schema_version": "task022.shell-bundle-geometry.v1",
        "request_hash": request_hash,
        "task020_configuration_id": configuration.configuration_id,
        "task020_configuration_hash": configuration.configuration_hash,
        "task021_layout_id": layout.layout_id,
        "task021_layout_hash": layout.layout_hash,
        "tube_geometry_snapshot_hash": layout.tube_geometry.snapshot_hash,
        "shell_inside_diameter_m": shell_inside_diameter_m,
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
        "provenance_pre_hash": _make_geometry_provenance_pre_hash(
            configuration=configuration,
            layout=layout,
            geometry_rule=geometry_rule,
            shell_inside_diameter_m=shell_inside_diameter_m,
            shell_radius_m=shell_radius_m,
            bare_tube_bundle_radius_m=bare_tube_bundle_radius_m,
            bare_tube_bundle_diameter_m=bare_tube_bundle_diameter_m,
            bundle_peripheral_allowance_m=bundle_peripheral_allowance_m,
            bundle_outer_envelope_radius_m=bundle_outer_envelope_radius_m,
            bundle_outer_envelope_diameter_m=bundle_outer_envelope_diameter_m,
            shell_to_bundle_radial_clearance_m=shell_to_bundle_radial_clearance_m,
            shell_to_bundle_diametral_clearance_m=shell_to_bundle_diametral_clearance_m,
            required_minimum_radial_clearance_m=required_minimum_radial_clearance_m,
            radial_clearance_margin_m=radial_clearance_margin_m,
            limiting_position_ids=limiting_position_ids,
            position_count=len(layout.positions),
        ),
    }
    geometry_hash = _task022_sha256_hex(geometry_payload)
    geometry_id = _task022_geometry_id_for(geometry_hash)
    _raw_prov = geometry_payload["provenance_pre_hash"]
    provenance_with_hash: dict[str, Any] = {}
    provenance_with_hash.update(cast(Any, _raw_prov))
    provenance_with_hash["geometry_hash"] = geometry_hash
    return ShellBundleGeometry(
        schema_version="task022.shell-bundle-geometry.v1",
        geometry_id=geometry_id,
        geometry_hash=geometry_hash,
        request_hash=request_hash,
        task020_configuration_id=configuration.configuration_id,
        task020_configuration_hash=configuration.configuration_hash,
        task021_layout_id=layout.layout_id,
        task021_layout_hash=layout.layout_hash,
        construction_family=configuration.construction_family.value,
        equipment_orientation=cast(Any, configuration.orientation.value),
        shell_pass_count=configuration.shell_pass_count,
        tube_pass_count=configuration.tube_pass_count,
        tube_geometry_snapshot_hash=layout.tube_geometry.snapshot_hash,
        geometry_rule_authority=geometry_rule,
        shell_authority_mode=cast(Any, "CALLER_SUPPLIED_EXPLICIT"),
        caller_supplied_shell=None,
        approved_shell_geometry=None,
        shell_inside_diameter_m=shell_inside_diameter_m,
        shell_radius_m=shell_radius_m,
        bare_tube_bundle_radius_m=bare_tube_bundle_radius_m,
        bare_tube_bundle_diameter_m=bare_tube_bundle_diameter_m,
        bundle_peripheral_allowance_m=bundle_peripheral_allowance_m,
        bundle_outer_envelope_radius_m=bundle_outer_envelope_radius_m,
        bundle_outer_envelope_diameter_m=bundle_outer_envelope_diameter_m,
        shell_to_bundle_radial_clearance_m=shell_to_bundle_radial_clearance_m,
        shell_to_bundle_diametral_clearance_m=shell_to_bundle_diametral_clearance_m,
        required_minimum_radial_clearance_m=required_minimum_radial_clearance_m,
        radial_clearance_margin_m=radial_clearance_margin_m,
        limiting_position_ids=limiting_position_ids,
        position_count=len(layout.positions),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=provenance_with_hash,
    )


def _task022_geometry_id_for(geometry_hash: str) -> str:
    from hexagent.exchangers.shell_tube.shell_bundle_geometry.canonical import (
        geometry_id as _task022_geometry_id,
    )

    return _task022_geometry_id(geometry_hash)


def _make_geometry_provenance_pre_hash(
    *,
    configuration: ShellAndTubeConfiguration,
    layout: TubeLayout,
    geometry_rule: ShellBundleGeometryRuleAuthoritySnapshot,
    shell_inside_diameter_m: str,
    shell_radius_m: str,
    bare_tube_bundle_radius_m: str,
    bare_tube_bundle_diameter_m: str,
    bundle_peripheral_allowance_m: str,
    bundle_outer_envelope_radius_m: str,
    bundle_outer_envelope_diameter_m: str,
    shell_to_bundle_radial_clearance_m: str,
    shell_to_bundle_diametral_clearance_m: str,
    required_minimum_radial_clearance_m: str,
    radial_clearance_margin_m: str,
    limiting_position_ids: tuple[str, ...],
    position_count: int,
) -> dict[str, Any]:
    return {
        "task_id": "task022",
        "design_contract_path": ("docs/tasks/TASK-022-shell-and-tube-shell-bundle-geometry.md"),
        "task020_configuration_id": configuration.configuration_id,
        "task020_configuration_hash": configuration.configuration_hash,
        "task021_layout_id": layout.layout_id,
        "task021_layout_hash": layout.layout_hash,
        "task020_case_authority": {
            "revision_id": configuration.case_authority.revision_id,
            "payload_hash": configuration.case_authority.payload_hash,
            "domain_snapshot_hash": configuration.case_authority.domain_snapshot_hash,
            "revision_status": configuration.case_authority.revision_status.value,
        },
        "tube_geometry_snapshot_hash": layout.tube_geometry.snapshot_hash,
        "geometry_source_binding": {
            "source_id": layout.tube_geometry.source_binding.source_id,
            "source_type": layout.tube_geometry.source_binding.source_type,
            "source_revision": layout.tube_geometry.source_binding.source_revision,
            "source_location": layout.tube_geometry.source_binding.source_location,
            "evidence_ref": layout.tube_geometry.source_binding.evidence_ref,
            "approved_by": layout.tube_geometry.source_binding.approved_by,
            "approved_at": layout.tube_geometry.source_binding.approved_at,
        },
        "shell_authority_mode": "CALLER_SUPPLIED_EXPLICIT",
        "caller_supplied_shell": None,
        "approved_shell_geometry": None,
        "geometry_rule_authority": {
            "schema_version": geometry_rule.schema_version,
            "profile_id": geometry_rule.profile_id,
            "authority_mode": geometry_rule.authority_mode,
            "rule_id": geometry_rule.rule_id,
            "rule_version": geometry_rule.rule_version,
            "rule_artifact_canonical_hash": (geometry_rule.rule_artifact_canonical_hash),
            "source_class": geometry_rule.source_class,
            "license_evidence": internal_frozen_to_primitive(geometry_rule.license_evidence),
            "approval_status": geometry_rule.approval_status,
            "provenance_edge_ids": list(geometry_rule.provenance_edge_ids),
            "evidence_refs": list(geometry_rule.evidence_refs),
            "rule_pack_identity": None,
            "allowed_shell_authority_modes": list(geometry_rule.allowed_shell_authority_modes),
            "minimum_bundle_peripheral_allowance_m": (
                geometry_rule.minimum_bundle_peripheral_allowance_m
            ),
            "minimum_radial_clearance_m": (geometry_rule.minimum_radial_clearance_m),
            "maximum_position_count": geometry_rule.maximum_position_count,
            "snapshot_hash": geometry_rule.snapshot_hash,
        },
        "shell_inside_diameter_m": shell_inside_diameter_m,
        "shell_radius_m": shell_radius_m,
        "bare_tube_bundle_radius_m": bare_tube_bundle_radius_m,
        "bare_tube_bundle_diameter_m": bare_tube_bundle_diameter_m,
        "bundle_peripheral_allowance_m": bundle_peripheral_allowance_m,
        "bundle_outer_envelope_radius_m": bundle_outer_envelope_radius_m,
        "bundle_outer_envelope_diameter_m": bundle_outer_envelope_diameter_m,
        "shell_to_bundle_radial_clearance_m": shell_to_bundle_radial_clearance_m,
        "shell_to_bundle_diametral_clearance_m": shell_to_bundle_diametral_clearance_m,
        "required_minimum_radial_clearance_m": required_minimum_radial_clearance_m,
        "radial_clearance_margin_m": radial_clearance_margin_m,
        "limiting_position_ids": list(limiting_position_ids),
        "position_count": position_count,
        "warnings": [],
        "deferred_capabilities": [],
        "software_version": "task024-test",
        "git_commit": "test-only",
    }


# ---------------------------------------------------------------------------
# Caller-supplied authorities + typed BaffleGeometryRequest.
# ---------------------------------------------------------------------------


def make_axial_span(
    *,
    axial_start_coordinate_m: str = "0.0",
    axial_end_coordinate_m: str = "1.0",
    evidence_refs: tuple[str, ...] = ("task024-axial-evidence",),
) -> _t024.CallerSuppliedBaffleAxialSpan:
    span = _t024.CallerSuppliedBaffleAxialSpan(
        schema_version=_t024.AXIAL_SPAN_SCHEMA_VERSION,
        axial_start_coordinate_m=axial_start_coordinate_m,
        axial_end_coordinate_m=axial_end_coordinate_m,
        evidence_refs=tuple(sorted(set(evidence_refs))),
        authority_hash="",
    )
    import hashlib as _hashlib

    payload = {
        "axial_end_coordinate_m": span.axial_end_coordinate_m,
        "axial_start_coordinate_m": span.axial_start_coordinate_m,
        "evidence_refs": list(span.evidence_refs),
        "schema_version": span.schema_version,
    }
    digest = _hashlib.sha256(_t024_canonical.canonical_json_bytes(payload)).hexdigest()
    return _t024.CallerSuppliedBaffleAxialSpan(
        schema_version=span.schema_version,
        axial_start_coordinate_m=span.axial_start_coordinate_m,
        axial_end_coordinate_m=span.axial_end_coordinate_m,
        evidence_refs=span.evidence_refs,
        authority_hash=digest,
    )


def make_design_authority(
    *,
    baffle_type: _t024.BaffleType = _t024.BaffleType.SINGLE_SEGMENTAL,
    baffle_count: int = 4,
    baffle_thickness_m: str = "0.01",
    spacing_sequence_m: tuple[str, ...] = ("0.25", "0.25", "0.25"),
    baffle_cut_fraction: str = "0.25",
    orientation_sequence: tuple[_t024.BaffleOrientation, ...] = (
        _t024.BaffleOrientation.TOP,
        _t024.BaffleOrientation.TOP,
        _t024.BaffleOrientation.TOP,
    ),
    shell_to_baffle_diametral_clearance_m: str = "0.001",
    tube_to_baffle_hole_diametral_clearance_m: str = "0.001",
    evidence_refs: tuple[str, ...] = ("task024-design-evidence",),
) -> _t024.CallerSuppliedBaffleDesignAuthority:
    # ``spacing_sequence_m`` semantic order and ``orientation_sequence``
    # baffle-index order are preserved exactly as supplied
    # (Section 8.2 of the design contract). Only ``evidence_refs`` are
    # sorted and deduplicated.
    sorted_evidence = tuple(sorted(set(evidence_refs)))
    payload = {
        "baffle_count": baffle_count,
        "baffle_cut_fraction": baffle_cut_fraction,
        "baffle_thickness_m": baffle_thickness_m,
        "baffle_type": baffle_type.value,
        "evidence_refs": list(sorted_evidence),
        "orientation_sequence": [item.value for item in orientation_sequence],
        "schema_version": _t024.DESIGN_AUTHORITY_SCHEMA_VERSION,
        "shell_to_baffle_diametral_clearance_m": (shell_to_baffle_diametral_clearance_m),
        "spacing_sequence_m": list(spacing_sequence_m),
        "tube_to_baffle_hole_diametral_clearance_m": (tube_to_baffle_hole_diametral_clearance_m),
    }
    import hashlib as _hashlib

    digest = _hashlib.sha256(_t024_canonical.canonical_json_bytes(payload)).hexdigest()
    return _t024.CallerSuppliedBaffleDesignAuthority(
        schema_version=_t024.DESIGN_AUTHORITY_SCHEMA_VERSION,
        baffle_type=baffle_type,
        baffle_count=baffle_count,
        baffle_thickness_m=baffle_thickness_m,
        spacing_sequence_m=tuple(spacing_sequence_m),
        baffle_cut_fraction=baffle_cut_fraction,
        orientation_sequence=tuple(orientation_sequence),
        shell_to_baffle_diametral_clearance_m=shell_to_baffle_diametral_clearance_m,
        tube_to_baffle_hole_diametral_clearance_m=(tube_to_baffle_hole_diametral_clearance_m),
        evidence_refs=sorted_evidence,
        authority_hash=digest,
    )


def make_request(
    *,
    construction_family: ConstructionFamily = ConstructionFamily.FIXED_TUBESHEET,
    shell_pass_count: int = 1,
    orientation: Orientation = Orientation.HORIZONTAL,
    position_count: int = 4,
    axial_start_coordinate_m: str = "0.0",
    axial_end_coordinate_m: str = "1.0",
    baffle_type: _t024.BaffleType = _t024.BaffleType.SINGLE_SEGMENTAL,
    baffle_count: int = 4,
    baffle_thickness_m: str = "0.01",
    spacing_sequence_m: tuple[str, ...] = ("0.25", "0.25", "0.25"),
    baffle_cut_fraction: str = "0.25",
    orientation_sequence: tuple[_t024.BaffleOrientation, ...] = (
        _t024.BaffleOrientation.TOP,
        _t024.BaffleOrientation.TOP,
        _t024.BaffleOrientation.TOP,
    ),
    shell_to_baffle_diametral_clearance_m: str = "0.001",
    tube_to_baffle_hole_diametral_clearance_m: str = "0.001",
    evidence_refs: tuple[str, ...] = ("task024-request-evidence",),
) -> _t024.BaffleGeometryRequest:
    configuration = make_shell_and_tube_configuration(
        construction_family=construction_family,
        shell_pass_count=shell_pass_count,
        orientation=orientation,
    )
    layout = make_tube_layout(configuration, position_count=position_count)
    geometry = make_shell_bundle_geometry(configuration, layout)
    axial_span = make_axial_span(
        axial_start_coordinate_m=axial_start_coordinate_m,
        axial_end_coordinate_m=axial_end_coordinate_m,
    )
    design_authority = make_design_authority(
        baffle_type=baffle_type,
        baffle_count=baffle_count,
        baffle_thickness_m=baffle_thickness_m,
        spacing_sequence_m=spacing_sequence_m,
        baffle_cut_fraction=baffle_cut_fraction,
        orientation_sequence=orientation_sequence,
        shell_to_baffle_diametral_clearance_m=(shell_to_baffle_diametral_clearance_m),
        tube_to_baffle_hole_diametral_clearance_m=(tube_to_baffle_hole_diametral_clearance_m),
    )
    return _t024.BaffleGeometryRequest(
        schema_version=_t024.REQUEST_SCHEMA_VERSION,
        configuration=configuration,
        tube_layout=layout,
        shell_bundle_geometry=geometry,
        axial_span=axial_span,
        design_authority=design_authority,
        evidence_refs=tuple(sorted(set(evidence_refs))),
    )


# ---------------------------------------------------------------------------
# Single-field immutable replacement helpers.
# ---------------------------------------------------------------------------


def replace_configuration(
    request: _t024.BaffleGeometryRequest, *, configuration: ShellAndTubeConfiguration
) -> _t024.BaffleGeometryRequest:
    return _t024.BaffleGeometryRequest(
        schema_version=request.schema_version,
        configuration=configuration,
        tube_layout=request.tube_layout,
        shell_bundle_geometry=request.shell_bundle_geometry,
        axial_span=request.axial_span,
        design_authority=request.design_authority,
        evidence_refs=request.evidence_refs,
    )


def replace_layout(
    request: _t024.BaffleGeometryRequest, *, tube_layout: TubeLayout
) -> _t024.BaffleGeometryRequest:
    return _t024.BaffleGeometryRequest(
        schema_version=request.schema_version,
        configuration=request.configuration,
        tube_layout=tube_layout,
        shell_bundle_geometry=request.shell_bundle_geometry,
        axial_span=request.axial_span,
        design_authority=request.design_authority,
        evidence_refs=request.evidence_refs,
    )


def replace_geometry(
    request: _t024.BaffleGeometryRequest, *, shell_bundle_geometry: Any
) -> _t024.BaffleGeometryRequest:
    return _t024.BaffleGeometryRequest(
        schema_version=request.schema_version,
        configuration=request.configuration,
        tube_layout=request.tube_layout,
        shell_bundle_geometry=shell_bundle_geometry,
        axial_span=request.axial_span,
        design_authority=request.design_authority,
        evidence_refs=request.evidence_refs,
    )


def replace_axial_span(
    request: _t024.BaffleGeometryRequest,
    *,
    axial_span: _t024.CallerSuppliedBaffleAxialSpan,
) -> _t024.BaffleGeometryRequest:
    return _t024.BaffleGeometryRequest(
        schema_version=request.schema_version,
        configuration=request.configuration,
        tube_layout=request.tube_layout,
        shell_bundle_geometry=request.shell_bundle_geometry,
        axial_span=axial_span,
        design_authority=request.design_authority,
        evidence_refs=request.evidence_refs,
    )


def replace_design_authority(
    request: _t024.BaffleGeometryRequest,
    *,
    design_authority: _t024.CallerSuppliedBaffleDesignAuthority,
) -> _t024.BaffleGeometryRequest:
    return _t024.BaffleGeometryRequest(
        schema_version=request.schema_version,
        configuration=request.configuration,
        tube_layout=request.tube_layout,
        shell_bundle_geometry=request.shell_bundle_geometry,
        axial_span=request.axial_span,
        design_authority=design_authority,
        evidence_refs=request.evidence_refs,
    )


def replace_evidence_refs(
    request: _t024.BaffleGeometryRequest,
    *,
    evidence_refs: tuple[str, ...],
) -> _t024.BaffleGeometryRequest:
    return _t024.BaffleGeometryRequest(
        schema_version=request.schema_version,
        configuration=request.configuration,
        tube_layout=request.tube_layout,
        shell_bundle_geometry=request.shell_bundle_geometry,
        axial_span=request.axial_span,
        design_authority=request.design_authority,
        evidence_refs=tuple(evidence_refs),
    )


__all__ = [
    "make_request",
    "make_shell_and_tube_configuration",
    "make_tube_layout",
    "make_shell_bundle_geometry",
    "make_axial_span",
    "make_design_authority",
    "replace_configuration",
    "replace_layout",
    "replace_geometry",
    "replace_axial_span",
    "replace_design_authority",
    "replace_evidence_refs",
]
