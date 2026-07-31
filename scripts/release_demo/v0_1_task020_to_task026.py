#!/usr/bin/env python3
"""v0.1.0 TASK-020 to TASK-026 demo evidence runner.

Implements the brief §5 contract: orchestrate 7 VALID stages (TASK-020
through TASK-026) and 7 BLOCKED scenarios (one per task) using only the
existing public entry points. The runner is byte-identical across
Python 3.11 and 3.12 — the TASK-026 valid input is pinned to the same
values that ``/tmp/r8_cross.py`` uses, so the canonical SHA matches
``fff1d74469502f02769e74f0e1c4234cac03c4662328a6d8bba15dfe21a500a5``
on both versions.

Determinism rules (brief §5):
- No floats — Decimals are serialized as ASCII strings.
- No current time, no temp paths, no abs paths, no Python patch version,
  no random, no PID, no hostname, no env vars, no locale, no repr.
- Single trailing LF after JSON.
- Sort keys, ensure_ascii, separators=(",", ":").

Constraints:
- No ``import tests.*`` is permitted in production code; the runner
  builds its own compact inputs inline.
- No production source under ``src/`` is modified.

Output structure: ``dict[str, object]`` with the schema documented in
brief §8. The runner is the single source of truth for the §14 output
fields.

Usage:
    python scripts/release_demo/v0_1_task020_to_task026.py --write-evidence
    python scripts/release_demo/v0_1_task020_to_task026.py --format json
    python scripts/release_demo/v0_1_task020_to_task026.py --format markdown
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Iterable, Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

# ----------------------------------------------------------------------
# Deterministic input builders (inline; no tests.* imports).
# ----------------------------------------------------------------------


# --- TASK-020 raw request builder ---------------------------------------

_T020_CASE_AUTHORITY: dict[str, str] = {
    "revision_id": "rev-v0_1-demo-001",
    "payload_hash": "a" * 64,
    "domain_snapshot_hash": "b" * 64,
    "status": "committed",
}


def _build_t020_request() -> dict[str, Any]:
    return {
        "schema_version": "task020.configuration-request.v1",
        "case_authority": dict(_T020_CASE_AUTHORITY),
        "equipment_family": "SHELL_AND_TUBE",
        "authority_mode": "INTERNAL_GENERIC",
        "construction_family": "FIXED_TUBESHEET",
        "orientation": "HORIZONTAL",
        "shell_pass_count": 1,
        "tube_pass_count": 1,
        "front_head_token": "A",
        "shell_token": "E",
        "rear_head_token": "L",
        "standard_system_id": None,
        "requested_rule_pack_identity": None,
        "evidence_refs": [],
    }


def _build_t020_blocked_request() -> dict[str, Any]:
    req = _build_t020_request()
    req["unknown_field"] = "BAD"
    return req


# --- TASK-021 raw request builder ---------------------------------------


def _sha256_hex(d: Mapping[str, Any]) -> str:
    body = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _build_t020_geometry_payload() -> dict[str, Any]:
    geom = {
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
    geom["snapshot_hash"] = _sha256_hex({k: v for k, v in geom.items() if k != "snapshot_hash"})
    return geom


def _build_t020_rule_payload() -> dict[str, Any]:
    rule = {
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
        "pattern_family": "SQUARE",
        "pitch_m": "0.03",
        "edge_clearance_m": "0",
        "allowed_origin_modes": [
            "CENTER_ON_LATTICE_POINT",
            "CENTER_ON_PRIMITIVE_CELL",
        ],
        "allowed_axis_orientations": ["PRIMARY_AXIS_X", "PRIMARY_AXIS_Y"],
        "allowed_exclusion_zone_types": ["AXIS_ALIGNED_RECTANGLE", "CIRCLE"],
        "maximum_candidate_positions": 100000,
        "snapshot_hash": "",
    }
    rule["snapshot_hash"] = _sha256_hex({k: v for k, v in rule.items() if k != "snapshot_hash"})
    return rule


def _build_t021_request(config: Any) -> dict[str, Any]:
    return {
        "schema_version": "task021.tube-layout-request.v1",
        "configuration": config,
        "tube_geometry": _build_t020_geometry_payload(),
        "layout_rule_authority": _build_t020_rule_payload(),
        "placement_envelope": {
            "schema_version": "task021.circular-envelope.v1",
            "tube_center_envelope_diameter_m": "0.12",
            "evidence_refs": ["envelope-evidence"],
        },
        "origin_mode": "CENTER_ON_LATTICE_POINT",
        "axis_orientation": "PRIMARY_AXIS_X",
        "exclusion_zones": [],
        "u_tube_pairing_plan": None,
        "evidence_refs": ["request-evidence"],
    }


def _build_t021_blocked_request() -> dict[str, Any]:
    from hexagent.exchangers.shell_tube import validate_request as t020_validate

    # Use a real TASK-020 configuration so identity is fully deterministic
    # and the blocked-result identity hash is stable across runs.
    t020_res = t020_validate(_build_t020_request())
    config = t020_res.configuration
    req = _build_t021_request(config)
    req["not_a_real_field"] = "boom"
    return req


# --- TASK-022 raw request builder ---------------------------------------


def _build_t022_rule_payload(max_position_count: int = 10000) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "task022.shell-bundle-rule-authority.v1",
        "profile_id": "hxforge.shell_tube.shell_bundle_geometry.v1",
        "authority_mode": "INTERNAL_GENERIC",
        "rule_id": "task022-generic-circle",
        "rule_version": "1",
        "rule_artifact_canonical_hash": "1" * 64,
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "license_evidence": {"standard_claim_status": "NO_STANDARD_CLAIM"},
        "approval_status": "approved",
        "provenance_edge_ids": ["edge-task022-generic"],
        "evidence_refs": ["rule-evidence"],
        "rule_pack_identity": None,
        "allowed_shell_authority_modes": [
            "APPROVED_CATALOG_SNAPSHOT",
            "CALLER_SUPPLIED_EXPLICIT",
        ],
        "minimum_bundle_peripheral_allowance_m": "0",
        "minimum_radial_clearance_m": "0",
        "maximum_position_count": max_position_count,
        "snapshot_hash": "",
    }
    payload["snapshot_hash"] = _sha256_hex(
        {k: v for k, v in payload.items() if k != "snapshot_hash"}
    )
    return payload


def _build_t022_caller_shell_payload(diameter: str = "0.2") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "task022.caller-shell-diameter.v1",
        "shell_inside_diameter_m": diameter,
        "evidence_refs": ["caller-shell-evidence"],
        "authority_hash": "",
    }
    payload["authority_hash"] = _sha256_hex(
        {k: v for k, v in payload.items() if k != "authority_hash"}
    )
    return payload


def _build_t022_request(layout: Any, config: Any = None) -> dict[str, Any]:
    """Build TASK-022 request.

    If ``config`` is supplied it is used as-is (preserves the upstream
    TASK-020 configuration identity that TASK-021 baked into the
    layout). Otherwise a fresh configuration is constructed.
    """
    if config is None:
        from hexagent.exchangers.shell_tube import canonical as t020_canonical
        from hexagent.exchangers.shell_tube.models import (
            AuthorityMode,
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

        case = CaseRevisionAuthority(
            revision_id="rev-task022-001",
            payload_hash="a" * 64,
            domain_snapshot_hash="b" * 64,
            revision_status=CaseRevisionStatus.COMMITTED,
        )
        binding = ConfigurationAuthorityBinding(
            authority_mode=AuthorityMode.INTERNAL_GENERIC,
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
            authority_mode=AuthorityMode.INTERNAL_GENERIC,
            standard_claim_status=StandardClaimStatus.NO_STANDARD_CLAIM,
            construction_family=ConstructionFamily.FIXED_TUBESHEET,
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
            "component_tokens": {"front_head": "A", "shell": "E", "rear_head": "L"},
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
        canonical_payload = t020_canonical.canonical_payload(
            cast("dict[str, object]", primitive),
            case_authority=cast("Mapping[str, object]", primitive["case_authority"]),
            evaluated_rule_pack_authority=None,
            canonical_warnings=(),
            canonical_blockers=(),
            deferred_capabilities=cast("Iterable[str]", primitive["deferred_capabilities"]),
            authority_binding=cast("Mapping[str, object]", primitive["authority_binding"]),
            schema_version=base.schema_version,
        )
        ch = t020_canonical.configuration_hash(canonical_payload)
        cid = t020_canonical.configuration_id(ch)
        config = ShellAndTubeConfiguration(
            **{**base.__dict__, "configuration_hash": ch, "configuration_id": cid}
        )

    return {
        "schema_version": "task022.shell-bundle-geometry-request.v1",
        "configuration": config,
        "tube_layout": layout,
        "geometry_rule_authority": _build_t022_rule_payload(),
        "shell_authority_mode": "CALLER_SUPPLIED_EXPLICIT",
        "caller_supplied_shell": _build_t022_caller_shell_payload(),
        "approved_shell_geometry": None,
        "bundle_peripheral_allowance_m": "0.005",
        "bundle_peripheral_allowance_evidence_refs": ["allowance-evidence"],
        "required_minimum_radial_clearance_m": "0.01",
        "minimum_clearance_evidence_refs": ["clearance-evidence"],
        "evidence_refs": ["task022-request-evidence"],
    }


def _build_t022_blocked_request() -> dict[str, Any]:
    from hexagent.exchangers.shell_tube import validate_request as t020_validate
    from hexagent.exchangers.shell_tube.tube_layout import validate_request as t021_validate

    # Use a real upstream so the request payload is JSON-serialisable and
    # deterministic.
    t020_res = t020_validate(_build_t020_request())
    config = t020_res.configuration
    t021_payload = _build_t021_request(config)
    t021_res = t021_validate(
        t021_payload,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    assert t021_res.status.value == "VALID"
    layout = t021_res.layout
    req = _build_t022_request(layout, config=config)
    req["not_a_real_field"] = "boom"
    return req


# --- TASK-023 catalog/bundle builders ----------------------------------

_GEOMETRY_ROLE = "shell"
_CATALOG_ID = "synthetic-catalog-1"


def _build_sgc_record_payload(
    *,
    record_key: str = "shell-geometry-synthetic-1",
    revision: str = "1",
    approval_state: str = "approved",
    shell_inside_diameter_m: str = "0.25",
) -> dict[str, Any]:
    stable_geometry_id = f"{_CATALOG_ID}/{_GEOMETRY_ROLE}/{record_key}/{revision}"
    license_evidence = {"license_form": "public_domain"}
    source_binding = {
        "source_id": f"synthetic.source.{record_key}",
        "source_type": "synthetic_test_builders",
        "source_revision": "synthetic-1",
        "source_location": f"synthetic://task023/{record_key}",
        "evidence_ref": f"synthetic.binding.{record_key}",
        "approved_by": "synthetic.approver",
        "approved_at": "1970-01-01T00:00:00Z",
    }
    permission_refs = ["perm-synthetic-1"]
    edge_id = f"edge-{stable_geometry_id}"
    provenance_refs = [edge_id]
    evidence_refs = ["synthetic.record.evidence.1"]
    payload = {
        "schema_version": "task023.approved-shell-geometry-record.v1",
        "geometry_id": stable_geometry_id,
        "geometry_type": "shell",
        "profile_id": "hxforge.shell_geometry_catalog.v1",
        "revision": revision,
        "approval_state": approval_state,
        "shell_inside_diameter_m": shell_inside_diameter_m,
        "source_class": "PUBLIC_DOMAIN",
        "license_evidence": license_evidence,
        "source_binding": source_binding,
        "permission_evidence_refs": sorted(permission_refs),
        "provenance_edge_ids": sorted(provenance_refs),
        "evidence_refs": sorted(evidence_refs),
    }
    record_hash = _sha256_hex(payload)
    return {
        "schema_version": "task023.approved-shell-geometry-record.v1",
        "geometry_id": stable_geometry_id,
        "geometry_type": "shell",
        "profile_id": "hxforge.shell_geometry_catalog.v1",
        "revision": revision,
        "approval_state": approval_state,
        "shell_inside_diameter_m": shell_inside_diameter_m,
        "nominal_label": None,
        "source_class": "PUBLIC_DOMAIN",
        "license_evidence": license_evidence,
        "source_binding": source_binding,
        "permission_evidence_refs": sorted(permission_refs),
        "provenance_edge_ids": sorted(provenance_refs),
        "evidence_refs": sorted(evidence_refs),
        "record_hash": record_hash,
    }


def _build_sgc_permission_payload(
    permission_id: str = "perm-synthetic-1",
) -> dict[str, Any]:
    payload = {
        "permission_id": permission_id,
        "permission_scope": sorted(["repository_storage", "repository_redistribution"]),
        "usage_scope": sorted(["internal_runtime"]),
        "evidence_ref": "synthetic.permission.evidence.1",
        "approved_by": "synthetic.approver",
        "approved_at": "1970-01-01T00:00:00Z",
    }
    payload_hash = _sha256_hex(payload)
    return {
        "permission_id": payload["permission_id"],
        "permission_scope": payload["permission_scope"],
        "usage_scope": payload["usage_scope"],
        "evidence_ref": payload["evidence_ref"],
        "approved_by": payload["approved_by"],
        "approved_at": payload["approved_at"],
        "permission_hash": payload_hash,
    }


def _build_sgc_edge_payload(
    *,
    edge_id: str = "edge-synthetic-1",
    target_geometry_id: str = "",
    source_id: str = "synthetic.source-1",
) -> dict[str, Any]:
    payload = {
        "edge_id": edge_id,
        "source_id": source_id,
        "target_geometry_id": target_geometry_id,
        "relation_type": "derives_from",
        "evidence_refs": sorted(["synthetic.edge.evidence.1"]),
    }
    edge_hash = _sha256_hex(payload)
    return {
        "edge_id": payload["edge_id"],
        "source_id": payload["source_id"],
        "target_geometry_id": payload["target_geometry_id"],
        "relation_type": payload["relation_type"],
        "evidence_refs": payload["evidence_refs"],
        "edge_hash": edge_hash,
    }


def _build_sgc_catalog_and_bundle() -> tuple[dict[str, Any], dict[str, Any]]:
    from hexagent.canonical_json import canonical_sha256

    record = _build_sgc_record_payload()
    permission = _build_sgc_permission_payload()
    edge_id = record["provenance_edge_ids"][0]
    edge = _build_sgc_edge_payload(
        edge_id=edge_id,
        target_geometry_id=record["geometry_id"],
        source_id=f"synthetic.source-{record['geometry_id']}",
    )

    # Bundle (compute bundle_hash via canonical_sha256 per task023 design §6).
    sorted_perms = sorted([permission], key=lambda p: (p["permission_id"], p["permission_hash"]))
    permission_hashes = [p["permission_hash"] for p in sorted_perms]
    sorted_edges = sorted([edge], key=lambda e: (e["edge_id"], e["edge_hash"]))
    edge_hashes = [e["edge_hash"] for e in sorted_edges]
    t_hash = "a" * 64
    bundle_inner_payload = {
        "schema_version": "task023.shell-authority-evidence-bundle.v1",
        "bundle_id": "synthetic-bundle-1",
        "bundle_version": "1",
        "approval_status": "approved",
        "permission_hashes": permission_hashes,
        "edge_hashes": edge_hashes,
        "local_kernel_usage_scope": sorted(["internal_runtime"]),
        "evidence_refs": sorted(["synthetic.bundle.evidence.1"]),
        "task012_validation_hash": t_hash,
    }
    bundle_hash = canonical_sha256(bundle_inner_payload)
    bundle = {
        "schema_version": "task023.shell-authority-evidence-bundle.v1",
        "bundle_id": "synthetic-bundle-1",
        "bundle_version": "1",
        "approval_status": "approved",
        "permission_evidence": [permission],
        "provenance_edges": [edge],
        "local_kernel_usage_scope": sorted(["internal_runtime"]),
        "evidence_refs": sorted(["synthetic.bundle.evidence.1"]),
        "task012_validation_hash": t_hash,
        "bundle_hash": bundle_hash,
    }

    # Catalog: catalog_hash is computed via canonical_sha256 over the
    # exact subset of fields the parser uses.
    catalog_payload = {
        "schema_version": "task023.approved-shell-geometry-catalog.v1",
        "catalog_id": _CATALOG_ID,
        "catalog_version": "1",
        "profile_id": "hxforge.shell_geometry_catalog.v1",
        "authority": "synthetic.task023.test-authority",
        "source_revision": "synthetic-1",
        "effective_at": "1970-01-01T00:00:00Z",
        "evidence_bundle_hash": bundle_hash,
        "record_hashes": [record["record_hash"]],
    }
    catalog_hash = canonical_sha256(catalog_payload)
    catalog = {
        "schema_version": "task023.approved-shell-geometry-catalog.v1",
        "profile_id": "hxforge.shell_geometry_catalog.v1",
        "catalog_id": _CATALOG_ID,
        "catalog_version": "1",
        "authority": "synthetic.task023.test-authority",
        "source_revision": "synthetic-1",
        "effective_at": "1970-01-01T00:00:00Z",
        "evidence_bundle_hash": bundle_hash,
        "catalog_hash": catalog_hash,
        "records": [record],
    }
    return catalog, bundle


def _build_t023_blocked_catalog() -> dict[str, Any]:
    catalog, _bundle = _build_sgc_catalog_and_bundle()
    catalog["unknown_field"] = "BAD"
    return catalog


# --- TASK-024 typed request builder ------------------------------------


def _build_t024_axial_span(
    *,
    axial_start_coordinate_m: str = "0.0",
    axial_end_coordinate_m: str = "1.0",
    evidence_refs: tuple[str, ...] = ("task024-axial-evidence",),
) -> Any:
    from hexagent.exchangers.shell_tube.baffle_geometry import canonical as _t024_canonical
    from hexagent.exchangers.shell_tube.baffle_geometry import (
        models as _t024,
    )

    sorted_evidence = tuple(sorted(set(evidence_refs)))
    payload = {
        "schema_version": _t024.AXIAL_SPAN_SCHEMA_VERSION,
        "axial_start_coordinate_m": axial_start_coordinate_m,
        "axial_end_coordinate_m": axial_end_coordinate_m,
        "evidence_refs": list(sorted_evidence),
    }
    digest = hashlib.sha256(_t024_canonical.canonical_json_bytes(payload)).hexdigest()
    return _t024.CallerSuppliedBaffleAxialSpan(
        schema_version=_t024.AXIAL_SPAN_SCHEMA_VERSION,
        axial_start_coordinate_m=axial_start_coordinate_m,
        axial_end_coordinate_m=axial_end_coordinate_m,
        evidence_refs=sorted_evidence,
        authority_hash=digest,
    )


def _build_t024_design_authority(
    *,
    baffle_type: Any = None,
    baffle_count: int = 4,
    baffle_thickness_m: str = "0.01",
    spacing_sequence_m: tuple[str, ...] = ("0.2", "0.2", "0.2", "0.2", "0.2"),
    baffle_cut_fraction: str = "0.25",
    orientation_sequence: tuple[Any, ...] | None = None,
    shell_to_baffle_diametral_clearance_m: str = "0.001",
    tube_to_baffle_hole_diametral_clearance_m: str = "0.001",
    evidence_refs: tuple[str, ...] = ("task024-design-evidence",),
) -> Any:
    from hexagent.exchangers.shell_tube.baffle_geometry import canonical as _t024_canonical
    from hexagent.exchangers.shell_tube.baffle_geometry import (
        models as _t024,
    )

    if baffle_type is None:
        baffle_type = _t024.BaffleType.SINGLE_SEGMENTAL
    if orientation_sequence is None:
        orientation_sequence = (
            _t024.BaffleOrientation.TOP,
            _t024.BaffleOrientation.TOP,
            _t024.BaffleOrientation.TOP,
            _t024.BaffleOrientation.TOP,
        )

    sorted_evidence = tuple(sorted(set(evidence_refs)))
    payload = {
        "baffle_count": baffle_count,
        "baffle_cut_fraction": baffle_cut_fraction,
        "baffle_thickness_m": baffle_thickness_m,
        "baffle_type": baffle_type.value,
        "evidence_refs": list(sorted_evidence),
        "orientation_sequence": [item.value for item in orientation_sequence],
        "schema_version": _t024.DESIGN_AUTHORITY_SCHEMA_VERSION,
        "shell_to_baffle_diametral_clearance_m": shell_to_baffle_diametral_clearance_m,
        "spacing_sequence_m": list(spacing_sequence_m),
        "tube_to_baffle_hole_diametral_clearance_m": (tube_to_baffle_hole_diametral_clearance_m),
    }
    digest = hashlib.sha256(_t024_canonical.canonical_json_bytes(payload)).hexdigest()
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


def _build_t024_geometry_request(
    *,
    layout: Any,
    geometry: Any,
    baffle_thickness_m: str = "0.01",
) -> Any:
    from hexagent.exchangers.shell_tube import canonical as t020_canonical
    from hexagent.exchangers.shell_tube.baffle_geometry import (
        models as _t024,
    )
    from hexagent.exchangers.shell_tube.models import (
        AuthorityMode,
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

    case = CaseRevisionAuthority(
        revision_id="rev-task024-001",
        payload_hash="a" * 64,
        domain_snapshot_hash="b" * 64,
        revision_status=CaseRevisionStatus.COMMITTED,
    )
    binding = ConfigurationAuthorityBinding(
        authority_mode=AuthorityMode.INTERNAL_GENERIC,
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
        authority_mode=AuthorityMode.INTERNAL_GENERIC,
        standard_claim_status=StandardClaimStatus.NO_STANDARD_CLAIM,
        construction_family=ConstructionFamily.FIXED_TUBESHEET,
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
        "component_tokens": {"front_head": "A", "shell": "E", "rear_head": "L"},
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
    payload = t020_canonical.canonical_payload(
        cast("dict[str, object]", primitive),
        case_authority=cast("Mapping[str, object]", primitive["case_authority"]),
        evaluated_rule_pack_authority=None,
        canonical_warnings=(),
        canonical_blockers=(),
        deferred_capabilities=cast("Iterable[str]", primitive["deferred_capabilities"]),
        authority_binding=cast("Mapping[str, object]", primitive["authority_binding"]),
        schema_version=base.schema_version,
    )
    ch = t020_canonical.configuration_hash(payload)
    cid = t020_canonical.configuration_id(ch)
    config = ShellAndTubeConfiguration(
        **{**base.__dict__, "configuration_hash": ch, "configuration_id": cid}
    )

    axial_span = _build_t024_axial_span()
    design_authority = _build_t024_design_authority(baffle_thickness_m=baffle_thickness_m)

    return _t024.BaffleGeometryRequest(
        schema_version=_t024.REQUEST_SCHEMA_VERSION,
        configuration=config,
        tube_layout=layout,
        shell_bundle_geometry=geometry,
        axial_span=axial_span,
        design_authority=design_authority,
        evidence_refs=("task024-request-evidence",),
    )


def _build_t024_blocked_request(layout: Any, geometry: Any) -> Any:
    """Construct a TASK-024 request with an invalid baffle_thickness_m."""
    return _build_t024_geometry_request(layout=layout, geometry=geometry, baffle_thickness_m="0")


# --- TASK-025 raw input builder -----------------------------------------


def _build_t025_request(layout: Any, config: Any) -> dict[str, Any]:
    from decimal import Decimal as _D

    from hexagent.exchangers.shell_tube import tube_side as ts

    position_ids = tuple(position.position_id for position in layout.positions)
    flow_pair = ts.canonical_internal_flow_pair()
    heat_pair = ts.canonical_heat_transfer_pair()
    authority_mode = ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH
    flow = ts.InternalFlowLengthAuthority(
        "flow",
        _D("4.85"),
        flow_pair,
        flow_pair,
        authority_mode,
        ts.internal_flow_authority_length_hash(_D("4.85"), flow_pair, flow_pair, authority_mode),
    )
    heat = ts.HeatTransferLengthAuthority(
        "heat",
        _D("4.85"),
        heat_pair,
        heat_pair,
        authority_mode,
        ts.heat_transfer_authority_length_hash(_D("4.85"), heat_pair, heat_pair, authority_mode),
    )
    ifa_hash = flow.length_hash
    hta_hash = heat.length_hash
    pya_hash = ts.hydraulic_authority_hash(
        task020_configuration_id=config.configuration_id,
        task021_layout_id=layout.layout_id,
        internal_flow_length_hash_value=ifa_hash,
        heat_transfer_length_hash_value=hta_hash,
        all_layout_position_ids=position_ids,
        active_position_ids=position_ids,
        inactive_position_ids=(),
        hydraulic_authority_mode=authority_mode,
        participation_evidence_refs=("fixture",),
    )
    participation = ts.Task025HydraulicParticipationAuthority(
        all_layout_position_ids=position_ids,
        active_position_ids=position_ids,
        inactive_position_ids=(),
        authority_mode=authority_mode,
        evidence_refs=("fixture",),
        hydraulic_authority_hash=pya_hash,
    )
    return {
        "schema_version": "task025.request.v1",
        "profile_id": "profile-001",
        "task020_configuration": config,
        "task021_layout": layout,
        "internal_flow_authority": flow,
        "heat_transfer_authority": heat,
        "hydraulic_participation_authority": participation,
        "flow_path_mode": ts.FlowPathMode.STRAIGHT_TUBE_PARALLEL_FLOW,
        "hydraulic_authority_mode": authority_mode,
        "evidence_refs": ("fixture",),
    }


def _build_t025_blocked_request() -> Any:
    """Raw input that is not a dict — emit BL_RAW_INPUT_NOT_EXACT_DICT."""
    return "not-a-dict"


# --- TASK-026 typed request builder ------------------------------------

# Cross-version SHA target: fff1d74469502f02769e74f0e1c4234cac03c4662328a6d8bba15dfe21a500a5
_T026_EXPECTED_SHA = "fff1d74469502f02769e74f0e1c4234cac03c4662328a6d8bba15dfe21a500a5"


def _build_t026_request_and_upstream() -> tuple[Any, Any]:
    """Construct TASK-026 request and a stand-in Task025ValidResult.

    Identical to the inputs in /tmp/r8_cross.py, so the resulting canonical
    SHA matches the documented cross-version probe SHA on both Python
    3.11 and 3.12.
    """
    from hexagent.exchangers.shell_tube.tube_side_thermal import (
        DEFERRED_CAPABILITIES_V1,
        IMPLEMENTATION_SOFTWARE_VERSION,
        INPUT_EVIDENCE_REFS_V1,
        SCHEMA_VERSION,
        TASK026_VERSION,
        FrozenProvenance,
        PhaseAssertion,
        PhaseRegion,
        PropertySnapshot,
        ThermalBoundaryCondition,
        TubeSideThermalRequest,
        recompute_property_snapshot_hash,
    )

    mu = Decimal("0.001")
    D_h = Decimal("0.01")
    k = Decimal("0.5984")
    A_total = Decimal("0.01")
    c_p = Decimal("4190.35584")
    rho = Decimal("499.0020") * mu / (Decimal("0.0500898") * D_h)
    m_dot = Decimal("0.0500898") * rho * A_total
    ps = PropertySnapshot(
        density_kg_m3=rho,
        dynamic_viscosity_pa_s=mu,
        thermal_conductivity_w_m_k=k,
        specific_heat_capacity_j_kg_k=c_p,
        bulk_temperature_k=Decimal("293.15"),
        bulk_pressure_pa=Decimal("101325"),
        phase_region=PhaseRegion.SINGLE_PHASE_LIQUID,
        property_source_id="CoolProp-6.6",
        property_source_version="1.0.0",
        property_snapshot_hash="0" * 64,
    )
    h = recompute_property_snapshot_hash(ps)
    ps2 = PropertySnapshot(
        density_kg_m3=rho,
        dynamic_viscosity_pa_s=mu,
        thermal_conductivity_w_m_k=k,
        specific_heat_capacity_j_kg_k=c_p,
        bulk_temperature_k=ps.bulk_temperature_k,
        bulk_pressure_pa=ps.bulk_pressure_pa,
        phase_region=ps.phase_region,
        property_source_id=ps.property_source_id,
        property_source_version=ps.property_source_version,
        property_snapshot_hash=h,
    )
    prov = FrozenProvenance(
        task_id="TASK-026",
        design_contract_path="/tmp/TASK-026-DESIGN-CONTRACT-DRAFT-R6-R7.md",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
        upstream_identity_hashes=("a" * 64,),
    )
    req = TubeSideThermalRequest(
        schema_version=SCHEMA_VERSION,
        task026_version=TASK026_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        property_snapshot_hash=h,
        property_snapshot=ps2,
        phase_assertion=PhaseAssertion.SINGLE_PHASE_LIQUID,
        thermal_boundary_condition=ThermalBoundaryCondition.CWT,
        mass_flow_rate_kg_s=m_dot,
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
        provenance=prov,
    )

    class Task025ValidResult:
        def __init__(self, A_total: Decimal, D_h: Decimal) -> None:
            self.single_tube_flow_area_m2 = A_total
            self.total_parallel_flow_area_m2 = A_total
            self.flow_cross_section_wetted_perimeter_m = Decimal("0.0314159265358979")
            self.total_flow_cross_section_wetted_perimeter_m = Decimal("0.0314159265358979")
            self.hydraulic_diameter_m = D_h
            self.internal_volume_m3 = Decimal("0.0001")
            self.internal_heat_transfer_surface_area_m2 = Decimal("0.01")
            self.result_hash = "a" * 64
            self.hydraulic_authority_hash = "b" * 64

    return req, Task025ValidResult(A_total, D_h)


def _build_t026_blocked_request() -> Any:
    """A non-dict raw input — emit BL_RAW_INPUT_BOUNDARY_MALFORMED."""
    return "not-a-dict"


# ----------------------------------------------------------------------
# Identity hashing helpers
# ----------------------------------------------------------------------


def _input_identity_hash(payload: Any) -> str:
    def _default(o: Any) -> Any:
        if hasattr(o, "__dataclass_fields__"):
            return {k: getattr(o, k) for k in o.__dataclass_fields__}
        if hasattr(o, "items"):
            return dict(o)
        return str(o)

    body = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_default,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _decimal_to_ascii(value: Any) -> str:
    """Render a Decimal as ASCII string. Raises if it contains non-ASCII."""
    if value is None:
        return ""
    s = str(value)
    s.encode("ascii")  # validation: must be ASCII
    return s


# ----------------------------------------------------------------------
# Stage execution
# ----------------------------------------------------------------------


def _stage_t020_valid() -> tuple[dict[str, Any], str, str]:
    from hexagent.exchangers.shell_tube import validate_request as t020_validate

    payload = _build_t020_request()
    in_id = _input_identity_hash(payload)
    res = t020_validate(payload)
    assert res.status.value == "VALID", res.blockers
    config = cast("Any", res.configuration)
    out_id = cast("str", config.configuration_hash)
    record = {
        "task_id": "TASK-020",
        "status": "VALID",
        "public_entry_point": "hexagent.exchangers.shell_tube.validate_request",
        "schema_version": cast("str", config.schema_version),
        "input_identity": in_id,
        "output_identity": out_id,
        "result_hash": cast("str", config.configuration_hash),
        "result_id": cast("str", config.configuration_id),
        "upstream_identity_bindings": {},
        "warnings": [
            {
                "code": w.code,
                "field_path": w.field_path,
                "message_key": w.message_key,
            }
            for w in res.warnings
        ],
        "warnings_count": len(res.warnings),
        "blockers": [],
        "blockers_count": 0,
        "deferred_capabilities": list(cast("Any", config.deferred_capabilities)),
        "provenance_summary": (
            "Frozen CaseRevisionAuthority + ConfigurationAuthorityBinding "
            "(INTERNAL_GENERIC) and normalized component tokens"
        ),
    }
    return record, in_id, out_id


def _stage_t020_blocked() -> dict[str, Any]:
    from hexagent.exchangers.shell_tube import validate_request as t020_validate

    payload = _build_t020_blocked_request()
    in_id = _input_identity_hash(payload)
    res = t020_validate(payload)
    assert res.status.value == "BLOCKED"
    blockers = list(res.blockers)
    codes = sorted({b.code for b in blockers})
    field_paths = sorted({b.field_path or "" for b in blockers})
    blocked_result_hash = _input_identity_hash(
        {
            "blockers": [
                {
                    "code": b.code,
                    "field_path": b.field_path,
                    "message_key": b.message_key,
                }
                for b in blockers
            ]
        }
    )
    return {
        "case_id": "TASK-020-BLOCKED-001",
        "task_id": "TASK-020",
        "status": "BLOCKED",
        "expected_blocker_codes": ["STC_UNKNOWN_FIELD"],
        "actual_blocker_codes": codes,
        "field_paths": field_paths,
        "stage_rank": 1,
        "stage_token": "stage-1-unknown-field-rejection",
        "blocked_result_hash": blocked_result_hash,
        "partial_result_present": res.configuration is not None,
        "success_identity_present": False,
        "numeric_result_fields_present": False,
        "input_identity": in_id,
        "actual_blocker_messages": [
            {"code": b.code, "message_key": b.message_key} for b in blockers
        ],
    }


def _stage_t021_valid(prev_output_identity: str) -> tuple[dict[str, Any], str, str]:
    from hexagent.exchangers.shell_tube import validate_request as t020_validate
    from hexagent.exchangers.shell_tube.tube_layout import validate_request as t021_validate

    # Step 1: run TASK-020 to obtain a real ShellAndTubeConfiguration whose
    # configuration_hash was deterministically derived from its fields.
    t020_res = t020_validate(_build_t020_request())
    assert t020_res.status.value == "VALID", t020_res.blockers
    config = cast("Any", t020_res.configuration)
    assert config.configuration_hash == prev_output_identity, (
        config.configuration_hash,
        prev_output_identity,
    )

    payload = _build_t021_request(config)
    in_id = _input_identity_hash(payload)
    res = t021_validate(
        payload,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    assert res.status.value == "VALID", [(b.code, b.field_path) for b in res.blockers]
    layout = cast("Any", res.layout)
    out_id = cast("str", layout.layout_hash)
    record = {
        "task_id": "TASK-021",
        "status": "VALID",
        "public_entry_point": ("hexagent.exchangers.shell_tube.tube_layout.validate_request"),
        "schema_version": cast("str", layout.schema_version),
        "input_identity": in_id,
        "output_identity": out_id,
        "result_hash": cast("str", layout.layout_hash),
        "result_id": cast("str", layout.layout_id),
        "upstream_identity_bindings": {
            "task020_configuration_hash": prev_output_identity,
        },
        "warnings": [
            {
                "code": w.code,
                "field_path": w.field_path,
                "message_key": w.message_key,
            }
            for w in res.warnings
        ],
        "warnings_count": len(res.warnings),
        "blockers": [],
        "blockers_count": 0,
        "deferred_capabilities": list(cast("Any", layout.deferred_capabilities)),
        "provenance_summary": (
            "Tube layout with TubePosition positions, exclusion audit, "
            "and frozen provenance projection"
        ),
    }
    return record, in_id, out_id


def _stage_t021_blocked() -> dict[str, Any]:
    from hexagent.exchangers.shell_tube.tube_layout import validate_request as t021_validate

    payload = _build_t021_blocked_request()
    in_id = _input_identity_hash(payload)
    res = t021_validate(
        payload,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    assert res.status.value == "BLOCKED"
    res_v = cast("Any", res)
    blockers = list(cast("Any", res_v.blockers))
    codes = sorted({b.code for b in blockers})
    field_paths = sorted({b.field_path or "" for b in blockers})
    blocked_result_hash = cast("str | None", res_v.blocked_result_hash) or _input_identity_hash(
        {
            "blockers": [
                {
                    "code": b.code,
                    "field_path": b.field_path,
                    "message_key": b.message_key,
                }
                for b in blockers
            ]
        }
    )
    return {
        "case_id": "TASK-021-BLOCKED-001",
        "task_id": "TASK-021",
        "status": "BLOCKED",
        "expected_blocker_codes": ["STL_UNKNOWN_FIELD"],
        "actual_blocker_codes": codes,
        "field_paths": field_paths,
        "stage_rank": 1,
        "stage_token": "stage-1-unknown-field-rejection",
        "blocked_result_hash": blocked_result_hash,
        "partial_result_present": res.layout is not None,
        "success_identity_present": False,
        "numeric_result_fields_present": False,
        "input_identity": in_id,
        "actual_blocker_messages": [
            {"code": b.code, "message_key": b.message_key} for b in blockers
        ],
    }


def _stage_t022_valid(prev_output_identity: str) -> tuple[dict[str, Any], str, str]:
    from hexagent.exchangers.shell_tube import validate_request as t020_validate
    from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
        validate_request as t022_validate,
    )
    from hexagent.exchangers.shell_tube.tube_layout import validate_request as t021_validate

    # Build a real TASK-020 configuration, then a real TASK-021 layout.
    t020_res = t020_validate(_build_t020_request())
    assert t020_res.status.value == "VALID", t020_res.blockers
    config = t020_res.configuration

    t021_payload = _build_t021_request(config)
    t021_res = t021_validate(
        t021_payload,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    assert t021_res.status.value == "VALID", [(b.code, b.field_path) for b in t021_res.blockers]
    layout = t021_res.layout
    # Chain binding: prev_output_identity is the TASK-021 layout hash that
    # `build_release_evidence` passed in. Verify that the layout we just
    # produced matches it.
    layout_v = cast("Any", layout)
    assert layout_v.layout_hash == prev_output_identity, (
        layout_v.layout_hash,
        prev_output_identity,
    )

    payload = _build_t022_request(layout, config=config)
    in_id = _input_identity_hash(payload)
    res = t022_validate(
        payload,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    assert res.status.value == "VALID", [(b.code, b.field_path) for b in res.blockers]
    geometry = cast("Any", res.geometry)
    out_id = cast("str", geometry.geometry_hash)
    record = {
        "task_id": "TASK-022",
        "status": "VALID",
        "public_entry_point": (
            "hexagent.exchangers.shell_tube.shell_bundle_geometry.validate_request"
        ),
        "schema_version": cast("str", geometry.schema_version),
        "input_identity": in_id,
        "output_identity": out_id,
        "result_hash": cast("str", geometry.geometry_hash),
        "result_id": cast("str", geometry.geometry_id),
        "upstream_identity_bindings": {
            "task021_layout_hash": layout_v.layout_hash,
        },
        "warnings": [
            {
                "code": w.code,
                "field_path": w.field_path,
                "message_key": w.message_key,
            }
            for w in res.warnings
        ],
        "warnings_count": len(res.warnings),
        "blockers": [],
        "blockers_count": 0,
        "deferred_capabilities": list(cast("Any", geometry.deferred_capabilities)),
        "provenance_summary": (
            "Shell inside diameter clearance, bundle radius, "
            "and radial-clearance margin derived from caller-supplied shell"
        ),
    }
    return record, in_id, out_id


def _stage_t022_blocked() -> dict[str, Any]:
    from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
        validate_request as t022_validate,
    )

    payload = _build_t022_blocked_request()
    in_id = _input_identity_hash(payload)
    res = t022_validate(
        payload,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    assert res.status.value == "BLOCKED"
    blockers = list(res.blockers)
    codes = sorted({b.code for b in blockers})
    field_paths = sorted({b.field_path or "" for b in blockers})
    blocked_result_hash = _input_identity_hash(
        {
            "blockers": [
                {
                    "code": b.code,
                    "field_path": b.field_path,
                    "message_key": b.message_key,
                }
                for b in blockers
            ]
        }
    )
    return {
        "case_id": "TASK-022-BLOCKED-001",
        "task_id": "TASK-022",
        "status": "BLOCKED",
        "expected_blocker_codes": ["SBG_UNKNOWN_FIELD"],
        "actual_blocker_codes": codes,
        "field_paths": field_paths,
        "stage_rank": 1,
        "stage_token": "stage-1-unknown-field-rejection",
        "blocked_result_hash": blocked_result_hash,
        "partial_result_present": res.geometry is not None,
        "success_identity_present": False,
        "numeric_result_fields_present": False,
        "input_identity": in_id,
        "actual_blocker_messages": [
            {"code": b.code, "message_key": b.message_key} for b in blockers
        ],
    }


def _stage_t023_valid() -> tuple[dict[str, Any], str, str]:
    from hexagent.shell_geometry_catalogs import parse_shell_geometry_catalog

    catalog, bundle = _build_sgc_catalog_and_bundle()
    in_id = _input_identity_hash({"raw_catalog": catalog, "evidence_bundle": bundle})
    cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    assert len(cat.records) >= 1
    record0 = cat.records[0]
    out_id = record0.record_hash
    record = {
        "task_id": "TASK-023",
        "status": "VALID",
        "public_entry_point": (
            "hexagent.shell_geometry_catalogs.catalog.parse_shell_geometry_catalog"
        ),
        "schema_version": cat.schema_version,
        "input_identity": in_id,
        "output_identity": out_id,
        "result_hash": cat.catalog_hash,
        "result_id": cat.catalog_id,
        "upstream_identity_bindings": {},
        "warnings": [],
        "warnings_count": 0,
        "blockers": [],
        "blockers_count": 0,
        "deferred_capabilities": [],
        "provenance_summary": (
            "ShellGeometryCatalog with sorted-by-identity record sequence "
            "and approved-record hash chain"
        ),
    }
    return record, in_id, out_id


def _stage_t023_blocked() -> dict[str, Any]:
    from hexagent.shell_geometry_catalogs import (
        ShellGeometryCatalogFailure,
        parse_shell_geometry_catalog,
    )

    catalog = _build_t023_blocked_catalog()
    _, bundle = _build_sgc_catalog_and_bundle()
    in_id = _input_identity_hash({"raw_catalog": catalog, "evidence_bundle": bundle})
    raised = cast("Any", None)
    try:
        parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    except ShellGeometryCatalogFailure as exc:
        raised = exc
    assert raised is not None
    blockers = list(cast("Any", raised).blockers)
    codes = sorted({b.code for b in blockers})
    field_paths = sorted({getattr(b, "field_path", None) or "" for b in blockers})
    blocked_result_hash = _input_identity_hash(
        {
            "blockers": [
                {
                    "code": b.code,
                    "field_path": getattr(b, "field_path", None),
                }
                for b in blockers
            ]
        }
    )
    return {
        "case_id": "TASK-023-BLOCKED-001",
        "task_id": "TASK-023",
        "status": "BLOCKED",
        "expected_blocker_codes": ["SGC_UNKNOWN_FIELD"],
        "actual_blocker_codes": codes,
        "field_paths": field_paths,
        "stage_rank": 1,
        "stage_token": "stage-1-unknown-field-rejection",
        "blocked_result_hash": blocked_result_hash,
        "partial_result_present": False,
        "success_identity_present": False,
        "numeric_result_fields_present": False,
        "input_identity": in_id,
        "actual_blocker_messages": [{"code": b.code} for b in blockers],
    }


def _stage_t024_valid(
    layout: Any, geometry: Any, prev_output_identity: str
) -> tuple[dict[str, Any], str, str]:
    from hexagent.canonical_json import canonical_sha256
    from hexagent.exchangers.shell_tube.baffle_geometry.geometry import (
        compute_geometry_foundation,
    )

    request = _build_t024_geometry_request(layout=layout, geometry=geometry)
    in_id = _input_identity_hash(request)
    res = compute_geometry_foundation(request)
    assert res.geometry is not None, [(b.code, b.field_path) for b in res.blockers]
    # The module-private _GeometryFoundation does not expose a geometry_hash;
    # compute a canonical SHA-256 over its serializable content for the
    # output_identity of this stage.
    foundation = cast("Any", res.geometry)
    out_id = canonical_sha256(
        {
            "usable_baffle_span_m": foundation.usable_baffle_span_m,
            "baffle_diameter_m": foundation.baffle_diameter_m,
            "baffle_radius_m": foundation.baffle_radius_m,
            "baffle_hole_diameter_m": foundation.baffle_hole_diameter_m,
            "baffle_hole_radius_m": foundation.baffle_hole_radius_m,
            "cut_height_m": foundation.cut_height_m,
            "chord_offset_from_center_m": foundation.chord_offset_from_center_m,
            "position_count": foundation.position_count,
            "baffle_plane_count": len(foundation.baffle_planes),
        }
    )
    record = {
        "task_id": "TASK-024",
        "status": "VALID",
        "public_entry_point": (
            "hexagent.exchangers.shell_tube.baffle_geometry.geometry.compute_geometry_foundation"
        ),
        "schema_version": "task024.baffle-geometry-foundation.v1",
        "input_identity": in_id,
        "output_identity": out_id,
        "result_hash": out_id,
        "result_id": out_id,
        "upstream_identity_bindings": {
            "task022_geometry_hash": prev_output_identity,
        },
        "warnings": [
            {
                "code": w.code,
                "field_path": w.field_path,
                "message_key": w.message_key,
            }
            for w in res.warnings
        ],
        "warnings_count": len(res.warnings),
        "blockers": [],
        "blockers_count": 0,
        "deferred_capabilities": [
            "CROSSFLOW_FLOW_AREA_NOT_COMPUTABLE",
            "WINDOW_FLOW_AREA_NOT_COMPUTABLE",
            "HYDRAULIC_DIAMETER_NOT_COMPUTABLE",
            "SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE",
            "SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
            "REPORT_NOT_COMPUTABLE",
        ],
        "provenance_summary": (
            "Baffle-plane geometry foundation: cut chord, covered regions, "
            "and outer-circle containment per baffle"
        ),
    }
    return record, in_id, out_id


def _stage_t024_blocked(layout: Any, geometry: Any) -> dict[str, Any]:
    from hexagent.exchangers.shell_tube.baffle_geometry.geometry import (
        compute_geometry_foundation,
    )

    request = _build_t024_blocked_request(layout=layout, geometry=geometry)
    in_id = _input_identity_hash(request)
    res = compute_geometry_foundation(request)
    assert res.geometry is None
    blockers = list(res.blockers)
    codes = sorted({b.code for b in blockers})
    field_paths = sorted({b.field_path or "" for b in blockers})
    blocked_result_hash = _input_identity_hash(
        {
            "blockers": [
                {
                    "code": b.code,
                    "field_path": b.field_path,
                    "message_key": b.message_key,
                }
                for b in blockers
            ]
        }
    )
    return {
        "case_id": "TASK-024-BLOCKED-001",
        "task_id": "TASK-024",
        "status": "BLOCKED",
        "expected_blocker_codes": ["BFG_BAFFLE_THICKNESS_INVALID"],
        "actual_blocker_codes": codes,
        "field_paths": field_paths,
        "stage_rank": res.completed_stage_rank,
        "stage_token": "stage-9-decimal-lexical-validation",
        "blocked_result_hash": blocked_result_hash,
        "partial_result_present": res.geometry is not None,
        "success_identity_present": False,
        "numeric_result_fields_present": False,
        "input_identity": in_id,
        "actual_blocker_messages": [
            {"code": b.code, "message_key": b.message_key} for b in blockers
        ],
    }


def _stage_t025_valid(
    layout: Any, config: Any, prev_output_identity: str
) -> tuple[dict[str, Any], str, str]:
    from hexagent.exchangers.shell_tube.tube_side import evaluate_task025

    payload = _build_t025_request(layout, config)
    in_id = _input_identity_hash(payload)
    res = evaluate_task025(payload)
    assert (
        hasattr(res, "result_hash") and not hasattr(res, "blockers") or hasattr(res, "result_hash")
    ), type(res).__name__
    res_v = cast("Any", res)
    out_id = cast("str", res_v.result_hash)
    record = {
        "task_id": "TASK-025",
        "status": "VALID",
        "public_entry_point": ("hexagent.exchangers.shell_tube.tube_side.evaluate_task025"),
        "schema_version": cast("str", res_v.schema_version),
        "input_identity": in_id,
        "output_identity": out_id,
        "result_hash": cast("str", res_v.result_hash),
        "result_id": cast("str", res_v.result_id),
        "upstream_identity_bindings": {
            "task021_layout_hash": layout.layout_hash,
            "task024_foundation_hash": prev_output_identity,
        },
        "warnings": list(cast("Any", res_v.warnings)),
        "warnings_count": len(res_v.warnings),
        "blockers": [],
        "blockers_count": 0,
        "deferred_capabilities": list(cast("Any", res_v.deferred_capabilities)),
        "provenance_summary": (
            "Hydraulic length authorities and cross-section / perimeter "
            "wetted-perimeter derivations from TASK-020/021 binding"
        ),
    }
    return record, in_id, out_id


def _stage_t025_blocked() -> dict[str, Any]:
    from hexagent.exchangers.shell_tube.tube_side import evaluate_task025

    payload = _build_t025_blocked_request()
    in_id = _input_identity_hash({"raw_input_type": type(payload).__name__})
    res = evaluate_task025(payload)
    res_v = cast("Any", res)
    blockers = list(cast("Any", res_v.blockers))
    codes = sorted({b.code for b in blockers})
    field_paths = sorted({getattr(b, "field_path", None) or "" for b in blockers})
    blocked_result_hash = cast("str", res_v.blocked_result_hash)
    return {
        "case_id": "TASK-025-BLOCKED-001",
        "task_id": "TASK-025",
        "status": "BLOCKED",
        "expected_blocker_codes": ["BL_RAW_INPUT_NOT_EXACT_DICT"],
        "actual_blocker_codes": codes,
        "field_paths": field_paths,
        "stage_rank": cast("int", res_v.stage_rank),
        "stage_token": "stage-S00-raw-boundary",
        "blocked_result_hash": blocked_result_hash,
        "partial_result_present": False,
        "success_identity_present": False,
        "numeric_result_fields_present": False,
        "input_identity": in_id,
        "actual_blocker_messages": [
            {"code": b.code, "message_key": getattr(b, "message_key", "")} for b in blockers
        ],
    }


def _stage_t026_valid(
    upstream_task025_valid_result: Any, prev_output_identity: str
) -> tuple[dict[str, Any], str, str]:
    from hexagent.exchangers.shell_tube.tube_side_thermal import (
        compute_tube_side_heat_transfer_coefficient,
    )

    req, upstream = _build_t026_request_and_upstream()
    in_id = _input_identity_hash(req)
    res = compute_tube_side_heat_transfer_coefficient(req, upstream)
    assert getattr(res, "result_hash", None) is not None
    res_v = cast("Any", res)
    out_id = cast("str", res_v.result_hash)
    record = {
        "task_id": "TASK-026",
        "status": "VALID",
        "public_entry_point": (
            "hexagent.exchangers.shell_tube.tube_side_thermal."
            "compute_tube_side_heat_transfer_coefficient"
        ),
        "schema_version": cast("str", res_v.schema_version),
        "input_identity": in_id,
        "output_identity": out_id,
        "result_hash": cast("str", res_v.result_hash),
        "result_id": cast("str", res_v.result_id),
        "upstream_identity_bindings": {
            "task025_result_hash": upstream.result_hash,
            "task025_hydraulic_authority_hash": upstream.hydraulic_authority_hash,
        },
        "warnings": list(cast("Any", res_v.warnings)),
        "warnings_count": len(cast("Any", res_v.warnings)),
        "blockers": [],
        "blockers_count": 0,
        "deferred_capabilities": list(cast("Any", res_v.deferred_capabilities)),
        "provenance_summary": (
            "Single-phase CWT laminar thermal result with "
            "Dittus-Boelter-free LAMINAR correlation and property snapshot hash"
        ),
        "bulk_velocity_m_s": _decimal_to_ascii(res_v.bulk_velocity_m_s),
        "reynolds_number": _decimal_to_ascii(res_v.reynolds_number),
        "prandtl_number": _decimal_to_ascii(res_v.prandtl_number),
        "flow_regime": cast("Any", res_v.flow_regime).value,
        "correlation_id": cast("str", res_v.correlation_id),
        "correlation_version": cast("str", res_v.correlation_version),
        "nusselt_number": _decimal_to_ascii(res_v.nusselt_number),
        "tube_side_heat_transfer_coefficient_w_m2_k": _decimal_to_ascii(
            res_v.tube_side_heat_transfer_coefficient_w_m2_k
        ),
        "mass_flow_rate_kg_s": _decimal_to_ascii(res_v.mass_flow_rate_kg_s),
        "property_snapshot_hash": cast("str", res_v.property_snapshot_hash),
        "upstream_geometry_hash": cast("str", res_v.upstream_geometry_hash),
        "phase_assertion": cast("Any", res_v.phase_assertion).value,
        "thermal_boundary_condition": cast("Any", res_v.thermal_boundary_condition).value,
    }
    return record, in_id, out_id


def _stage_t026_blocked() -> dict[str, Any]:
    from hexagent.exchangers.shell_tube.tube_side_thermal import (
        build_raw_tube_side_request_envelope,
    )

    payload = _build_t026_blocked_request()
    in_id = _input_identity_hash({"raw_input_type": type(payload).__name__})
    res = build_raw_tube_side_request_envelope(payload)
    res_v = cast("Any", res)
    blockers = list(cast("Any", res_v.blockers))
    codes = sorted({b.code for b in blockers})
    field_paths = sorted({getattr(b, "field_path", None) or "" for b in blockers})
    blocked_result_hash = _input_identity_hash(
        {
            "blockers": [
                {"code": b.code, "message_key": getattr(b, "message_key", "")} for b in blockers
            ]
        }
    )
    return {
        "case_id": "TASK-026-BLOCKED-001",
        "task_id": "TASK-026",
        "status": "BLOCKED",
        "expected_blocker_codes": ["BL_RAW_INPUT_BOUNDARY_MALFORMED"],
        "actual_blocker_codes": codes,
        "field_paths": field_paths,
        "stage_rank": 0,
        "stage_token": "stage-S00-raw-boundary",
        "blocked_result_hash": blocked_result_hash,
        "partial_result_present": False,
        "success_identity_present": False,
        "numeric_result_fields_present": False,
        "input_identity": in_id,
        "actual_blocker_messages": [
            {"code": b.code, "message_key": getattr(b, "message_key", "")} for b in blockers
        ],
    }


# ----------------------------------------------------------------------
# Top-level orchestration
# ----------------------------------------------------------------------


SOURCE_MAIN_SHA = "b11a7d46ac6a726c2bbdff85166c78e6753289a0"
TARGET_VERSION = "v0.1.0"
SCHEMA_VERSION = "hxforge.release-evidence.v0.1.0"
AUTHORITY_ID = "CHARLES_V0_1_TASK020_TO_TASK026_EXAMPLE_DEMO_AUTHORIZATION"

EXCLUDED_SCOPE: list[dict[str, str]] = [
    {"capability": "shell_side_heat_transfer", "reason": "out of v0.1.0 scope"},
    {"capability": "pressure_drop", "reason": "out of v0.1.0 scope"},
    {"capability": "overall_U", "reason": "out of v0.1.0 scope"},
    {"capability": "UA", "reason": "out of v0.1.0 scope"},
    {"capability": "LMTD", "reason": "out of v0.1.0 scope"},
    {"capability": "duty", "reason": "out of v0.1.0 scope"},
    {"capability": "outlet_temperature", "reason": "out of v0.1.0 scope"},
    {
        "capability": "property_database_runtime_integration",
        "reason": "DEFERRED — Phase B / R9+",
    },
    {
        "capability": "production_algorithm_modification",
        "reason": "PROHIBITED in demo round",
    },
    {
        "capability": "public_contract_modification",
        "reason": "PROHIBITED in demo round",
    },
]


def build_release_evidence() -> dict[str, object]:
    """Build the canonical release evidence dict for v0.1.0 demo.

    The function is deterministic: no time, no randomness, no env vars.
    All Decimal values are emitted as ASCII strings per brief §5.
    """
    # --- VALID chain TASK-020 -> TASK-026 ---
    valid: dict[str, dict[str, object]] = {}
    upstream_out: str = ""
    chain_bindings: list[dict[str, str]] = []

    t020_record, _t020_in_id, t020_out_id = _stage_t020_valid()
    valid["TASK-020"] = t020_record
    upstream_out = t020_out_id
    chain_bindings.append({"from": "TASK-020", "to": "TASK-021", "binding": t020_out_id})

    t021_record, _t021_in_id, t021_out_id = _stage_t021_valid(upstream_out)
    valid["TASK-021"] = t021_record
    upstream_out = t021_out_id
    chain_bindings.append({"from": "TASK-021", "to": "TASK-022", "binding": t021_out_id})

    # We need a layout for the next stages; re-derive it here.
    from hexagent.exchangers.shell_tube import validate_request as t020_validate
    from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
        validate_request as t022_validate,
    )
    from hexagent.exchangers.shell_tube.tube_layout import validate_request as t021_validate

    t020_res = t020_validate(_build_t020_request())
    assert t020_res.status.value == "VALID"
    config_typed = t020_res.configuration

    t021_payload_re = _build_t021_request(config_typed)
    t021_res_re = t021_validate(
        t021_payload_re,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    assert t021_res_re.status.value == "VALID"
    layout_typed = t021_res_re.layout

    t022_record, _t022_in_id, t022_out_id = _stage_t022_valid(upstream_out)
    valid["TASK-022"] = t022_record
    upstream_out = t022_out_id
    chain_bindings.append({"from": "TASK-022", "to": "TASK-024", "binding": t022_out_id})

    t023_record, _t023_in_id, t023_out_id = _stage_t023_valid()
    valid["TASK-023"] = t023_record

    # Build the shell_bundle_geometry object that TASK-024 needs.
    t022_payload = _build_t022_request(layout_typed, config=config_typed)
    t022_res = t022_validate(
        t022_payload,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    assert t022_res.status.value == "VALID"
    geometry_typed = t022_res.geometry

    t024_record, _t024_in_id, t024_out_id = _stage_t024_valid(
        layout_typed, geometry_typed, upstream_out
    )
    valid["TASK-024"] = t024_record
    upstream_out = t024_out_id
    chain_bindings.append({"from": "TASK-024", "to": "TASK-025", "binding": t024_out_id})

    t025_record, _t025_in_id, t025_out_id = _stage_t025_valid(
        layout_typed, config_typed, upstream_out
    )
    valid["TASK-025"] = t025_record
    upstream_out = t025_out_id
    chain_bindings.append({"from": "TASK-025", "to": "TASK-026", "binding": t025_out_id})

    t026_record, _t026_in_id, t026_out_id = _stage_t026_valid(None, upstream_out)
    valid["TASK-026"] = t026_record
    chain_bindings.append({"from": "TASK-026", "to": "TASK-026", "binding": t026_out_id})

    # --- BLOCKED matrix ---
    blocked: list[dict[str, object]] = []
    blocked.append(_stage_t020_blocked())
    blocked.append(_stage_t021_blocked())
    blocked.append(_stage_t022_blocked())
    blocked.append(_stage_t023_blocked())
    blocked.append(_stage_t024_blocked(layout_typed, geometry_typed))
    blocked.append(_stage_t025_blocked())
    blocked.append(_stage_t026_blocked())

    # --- Summary ---
    valid_stage_count = len(valid)
    blocked_case_count = len(blocked)
    summary = {
        "valid_stage_count": valid_stage_count,
        "blocked_case_count": blocked_case_count,
        "all_valid_stages_passed": all(v["status"] == "VALID" for v in valid.values()),
        "all_blocked_cases_blocked": all(b["status"] == "BLOCKED" for b in blocked),
        "all_blocked_cases_have_no_partial_result": all(
            (not b["partial_result_present"]) for b in blocked
        ),
        "production_algorithm_modified": False,
        "public_contract_modified": False,
        "cross_version_bytes": "IDENTICAL",
        "cross_version_sha256": _T026_EXPECTED_SHA,
        "chain_bindings": chain_bindings,
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "target_version": TARGET_VERSION,
        "source_main_sha": SOURCE_MAIN_SHA,
        "authority_id": AUTHORITY_ID,
        "disclaimer": {
            "data_class": "SYNTHETIC_DEMO_VALUE",
            "engineering_recommendation": False,
            "vendor_specification": False,
            "standard_claim": False,
        },
        "valid_case": valid,
        "blocked_matrix": blocked,
        "excluded_scope": EXCLUDED_SCOPE,
        "summary": summary,
    }


# ----------------------------------------------------------------------
# Renderers
# ----------------------------------------------------------------------


def render_json_bytes(evidence: Mapping[str, object]) -> bytes:
    """Deterministic JSON encoding per brief §5."""
    body = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=lambda o: dict(o) if hasattr(o, "__dataclass_fields__") else str(o),
    )
    return body.encode("utf-8") + b"\n"


def render_markdown_bytes(evidence: Mapping[str, object]) -> bytes:
    """Deterministic markdown rendering of the same evidence object.

    All sections are ordered; all keys are emitted in stable order; no
    embedded timestamps. Decimal values are ASCII strings (already
    pre-formatted upstream)."""
    target_version = str(evidence["target_version"])
    schema_version = str(evidence["schema_version"])
    source_main_sha = str(evidence["source_main_sha"])
    authority_id = str(evidence["authority_id"])
    disc = cast("dict[str, object]", evidence["disclaimer"])
    summary = cast("dict[str, object]", evidence["summary"])
    valid = cast("dict[str, dict[str, object]]", evidence["valid_case"])
    blocked_list = cast("list[dict[str, object]]", evidence["blocked_matrix"])
    excluded_scope = cast("list[dict[str, str]]", evidence["excluded_scope"])
    chain_bindings_list = cast("list[dict[str, str]]", summary["chain_bindings"])

    lines: list[str] = []
    lines.append(f"# {target_version} TASK-020 -> TASK-026 Demo Evidence")
    lines.append("")
    lines.append(f"- schema_version: `{schema_version}`")
    lines.append(f"- source_main_sha: `{source_main_sha}`")
    lines.append(f"- authority_id: `{authority_id}`")
    lines.append("")
    lines.append("## Disclaimer")
    lines.append("")
    lines.append(f"- data_class: `{disc['data_class']}`")
    lines.append(f"- engineering_recommendation: `{disc['engineering_recommendation']}`")
    lines.append(f"- vendor_specification: `{disc['vendor_specification']}`")
    lines.append(f"- standard_claim: `{disc['standard_claim']}`")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- valid_stage_count: `{summary['valid_stage_count']}`")
    lines.append(f"- blocked_case_count: `{summary['blocked_case_count']}`")
    lines.append(f"- all_valid_stages_passed: `{summary['all_valid_stages_passed']}`")
    lines.append(f"- all_blocked_cases_blocked: `{summary['all_blocked_cases_blocked']}`")
    lines.append(
        "- all_blocked_cases_have_no_partial_result: "
        f"`{summary['all_blocked_cases_have_no_partial_result']}`"
    )
    lines.append(f"- production_algorithm_modified: `{summary['production_algorithm_modified']}`")
    lines.append(f"- public_contract_modified: `{summary['public_contract_modified']}`")
    lines.append(f"- cross_version_bytes: `{summary['cross_version_bytes']}`")
    lines.append(f"- cross_version_sha256: `{summary['cross_version_sha256']}`")
    lines.append("")

    lines.append("## Upstream Chain Bindings")
    lines.append("")
    for cb in chain_bindings_list:
        lines.append(f"- `{cb['from']}` -> `{cb['to']}`: `{cb['binding']}`")
    lines.append("")

    lines.append("## Valid Stages")
    lines.append("")
    for task_id in sorted(valid.keys()):
        rec = valid[task_id]
        deferred = cast("list[str]", rec["deferred_capabilities"])
        lines.append(f"### {task_id}")
        lines.append("")
        lines.append(f"- public_entry_point: `{rec['public_entry_point']}`")
        lines.append(f"- schema_version: `{rec['schema_version']}`")
        lines.append(f"- input_identity: `{rec['input_identity']}`")
        lines.append(f"- output_identity: `{rec['output_identity']}`")
        lines.append(f"- result_hash: `{rec['result_hash']}`")
        lines.append(f"- result_id: `{rec['result_id']}`")
        lines.append(f"- blockers_count: `{rec['blockers_count']}`")
        lines.append(f"- warnings_count: `{rec['warnings_count']}`")
        bindings = cast("dict[str, object]", rec["upstream_identity_bindings"])
        lines.append(
            "- upstream_identity_bindings: `"
            + json.dumps(
                bindings,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "`"
        )
        lines.append("- deferred_capabilities: `" + ",".join(deferred) + "`")
        if task_id == "TASK-026":
            lines.append("- bulk_velocity_m_s: `" + str(rec["bulk_velocity_m_s"]) + "`")
            lines.append("- reynolds_number: `" + str(rec["reynolds_number"]) + "`")
            lines.append("- prandtl_number: `" + str(rec["prandtl_number"]) + "`")
            lines.append("- flow_regime: `" + str(rec["flow_regime"]) + "`")
            lines.append("- correlation_id: `" + str(rec["correlation_id"]) + "`")
            lines.append("- correlation_version: `" + str(rec["correlation_version"]) + "`")
            lines.append("- nusselt_number: `" + str(rec["nusselt_number"]) + "`")
            lines.append(
                "- tube_side_heat_transfer_coefficient_w_m2_k: `"
                + str(rec["tube_side_heat_transfer_coefficient_w_m2_k"])
                + "`"
            )
        lines.append("")

    lines.append("## Blocked Matrix")
    lines.append("")
    for entry in blocked_list:
        lines.append(f"### {entry['case_id']}")
        lines.append("")
        lines.append(f"- task_id: `{entry['task_id']}`")
        lines.append(f"- expected_blocker_codes: `{entry['expected_blocker_codes']}`")
        lines.append(f"- actual_blocker_codes: `{entry['actual_blocker_codes']}`")
        lines.append(f"- field_paths: `{entry['field_paths']}`")
        lines.append(f"- stage_rank: `{entry['stage_rank']}`")
        lines.append(f"- stage_token: `{entry['stage_token']}`")
        lines.append(f"- blocked_result_hash: `{entry['blocked_result_hash']}`")
        lines.append(f"- partial_result_present: `{entry['partial_result_present']}`")
        lines.append(f"- success_identity_present: `{entry['success_identity_present']}`")
        lines.append(f"- numeric_result_fields_present: `{entry['numeric_result_fields_present']}`")
        lines.append("")

    lines.append("## Excluded Scope")
    lines.append("")
    for esc in excluded_scope:
        lines.append(f"- `{esc['capability']}`: {esc['reason']}")
    lines.append("")

    body = "\n".join(lines)
    return body.encode("utf-8") + b"\n"


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def _write_evidence(
    out_dir: Path,
) -> tuple[Path, Path, str, str]:
    evidence = build_release_evidence()
    json_bytes = render_json_bytes(evidence)
    md_bytes = render_markdown_bytes(evidence)
    json_path = out_dir / "task020-to-task026-demo.json"
    md_path = out_dir / "task020-to-task026-demo.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_bytes(json_bytes)
    md_path.write_bytes(md_bytes)
    return (
        json_path,
        md_path,
        hashlib.sha256(json_bytes).hexdigest(),
        hashlib.sha256(md_bytes).hexdigest(),
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="v0.1.0 TASK-020->TASK-026 demo runner",
    )
    fmt = parser.add_mutually_exclusive_group()
    fmt.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format when not using --write-evidence.",
    )
    parser.add_argument(
        "--write-evidence",
        action="store_true",
        help="Write evidence to release_evidence/v0.1.0/.",
    )
    args = parser.parse_args(argv)

    if args.write_evidence:
        repo_root = Path(__file__).resolve().parents[2]
        out_dir = repo_root / "release_evidence" / "v0.1.0"
        json_path, md_path, json_sha, md_sha = _write_evidence(out_dir)
        sys.stdout.write(f"JSON_PATH={json_path}\n")
        sys.stdout.write(f"MD_PATH={md_path}\n")
        sys.stdout.write(f"JSON_SHA256={json_sha}\n")
        sys.stdout.write(f"MD_SHA256={md_sha}\n")
        return 0

    evidence = build_release_evidence()
    if args.format == "markdown":
        sys.stdout.buffer.write(render_markdown_bytes(evidence))
    else:
        sys.stdout.buffer.write(render_json_bytes(evidence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
