from __future__ import annotations

from dataclasses import replace
from typing import Any

from hexagent.exchangers.shell_tube.models import ConstructionFamily
from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    CALLER_SHELL_SCHEMA_VERSION,
    PROFILE_ID,
    REQUEST_SCHEMA_VERSION,
    RULE_SNAPSHOT_SCHEMA_VERSION,
    CallerSuppliedShellInsideDiameter,
    ShellBundleGeometryRuleAuthoritySnapshot,
    ShellInsideDiameterAuthorityMode,
    RuleAuthorityMode,
    sha256_hex,
)
from hexagent.exchangers.shell_tube.tube_layout import (
    validate_request as validate_layout,
)
from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout
from tests.exchangers.shell_tube.tube_layout._builders import (
    make_request as make_layout_request,
)


def make_layout(
    construction_family: ConstructionFamily = ConstructionFamily.FIXED_TUBESHEET,
) -> TubeLayout:
    result = validate_layout(
        make_layout_request(construction_family=construction_family),
        software_version="test-suite",
        git_commit="4faef775",
    )
    assert result.layout is not None, result.blockers
    return result.layout


def rule_payload(*, maximum_position_count: int = 10000) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": RULE_SNAPSHOT_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "authority_mode": RuleAuthorityMode.INTERNAL_GENERIC.value,
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
            ShellInsideDiameterAuthorityMode.APPROVED_CATALOG_SNAPSHOT.value,
            ShellInsideDiameterAuthorityMode.CALLER_SUPPLIED_EXPLICIT.value,
        ],
        "minimum_bundle_peripheral_allowance_m": "0",
        "minimum_radial_clearance_m": "0",
        "maximum_position_count": maximum_position_count,
        "snapshot_hash": "",
    }
    payload["snapshot_hash"] = sha256_hex(
        {key: value for key, value in payload.items() if key != "snapshot_hash"}
    )
    return payload


def caller_shell_payload(diameter: str = "0.2") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": CALLER_SHELL_SCHEMA_VERSION,
        "shell_inside_diameter_m": diameter,
        "evidence_refs": ["caller-shell-evidence"],
        "authority_hash": "",
    }
    payload["authority_hash"] = sha256_hex(
        {key: value for key, value in payload.items() if key != "authority_hash"}
    )
    return payload


def make_request(
    *,
    construction_family: ConstructionFamily = ConstructionFamily.FIXED_TUBESHEET,
    shell_diameter: str = "0.2",
    allowance: str = "0.005",
    minimum_clearance: str = "0.01",
    maximum_position_count: int = 10000,
) -> dict[str, Any]:
    layout = make_layout(construction_family)
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "configuration": layout_to_configuration(layout),
        "tube_layout": layout,
        "geometry_rule_authority": rule_payload(
            maximum_position_count=maximum_position_count
        ),
        "shell_authority_mode": ShellInsideDiameterAuthorityMode.CALLER_SUPPLIED_EXPLICIT.value,
        "caller_supplied_shell": caller_shell_payload(shell_diameter),
        "approved_shell_geometry": None,
        "bundle_peripheral_allowance_m": allowance,
        "bundle_peripheral_allowance_evidence_refs": ["allowance-evidence"],
        "required_minimum_radial_clearance_m": minimum_clearance,
        "minimum_clearance_evidence_refs": ["clearance-evidence"],
        "evidence_refs": ["task022-request-evidence"],
    }


def layout_to_configuration(layout: TubeLayout):
    # The full TASK-020 object is preserved inside the upstream request builder.
    # Rebuild it deterministically using the same construction family.
    from tests.exchangers.shell_tube.tube_layout._builders import make_configuration

    return make_configuration(ConstructionFamily(layout.construction_family))


def corrupt_layout_hash(layout: TubeLayout) -> TubeLayout:
    return replace(layout, layout_hash="f" * 64)


def parsed_rule_snapshot(
    payload: dict[str, Any],
) -> ShellBundleGeometryRuleAuthoritySnapshot:
    return ShellBundleGeometryRuleAuthoritySnapshot(
        schema_version=payload["schema_version"],
        profile_id=payload["profile_id"],
        authority_mode=RuleAuthorityMode(payload["authority_mode"]),
        rule_id=payload["rule_id"],
        rule_version=payload["rule_version"],
        rule_artifact_canonical_hash=payload["rule_artifact_canonical_hash"],
        source_class=payload["source_class"],
        license_evidence=payload["license_evidence"],
        approval_status=payload["approval_status"],
        provenance_edge_ids=tuple(payload["provenance_edge_ids"]),
        evidence_refs=tuple(payload["evidence_refs"]),
        rule_pack_identity=None,
        allowed_shell_authority_modes=tuple(
            ShellInsideDiameterAuthorityMode(item)
            for item in sorted(payload["allowed_shell_authority_modes"])
        ),
        minimum_bundle_peripheral_allowance_m=payload[
            "minimum_bundle_peripheral_allowance_m"
        ],
        minimum_radial_clearance_m=payload["minimum_radial_clearance_m"],
        maximum_position_count=payload["maximum_position_count"],
        snapshot_hash=payload["snapshot_hash"],
    )


def parsed_caller(payload: dict[str, Any]) -> CallerSuppliedShellInsideDiameter:
    return CallerSuppliedShellInsideDiameter(
        schema_version=payload["schema_version"],
        shell_inside_diameter_m=payload["shell_inside_diameter_m"],
        evidence_refs=tuple(payload["evidence_refs"]),
        authority_hash=payload["authority_hash"],
    )
