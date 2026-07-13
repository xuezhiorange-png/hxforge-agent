from __future__ import annotations

import dataclasses
from copy import deepcopy

from hexagent.exchangers.shell_tube.models import ConstructionFamily
from hexagent.exchangers.shell_tube.tube_layout import (
    ValidationStatus,
    validate_request,
)
from tests.exchangers.shell_tube.tube_layout._builders import (
    make_configuration,
    make_request,
)


def test_valid_request_produces_layout_and_counts() -> None:
    result = validate_request(make_request(), software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.VALID
    assert result.layout is not None
    assert result.layout.tube_hole_count == result.layout.physical_tube_count
    assert result.layout.blockers == ()
    assert result.blocked_result_hash is None


def test_candidate_capacity_blocks_before_generation() -> None:
    result = validate_request(make_request(maximum=1), software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_ENUMERATION_LIMIT_EXCEEDED" for item in result.blockers)
    assert result.layout is None


def test_blocked_result_hash_changes_only_with_blockers_or_warnings() -> None:
    """Regression: equal blocker/warning sets yield the same blocked_result_hash."""

    a = validate_request(make_request(maximum=1), software_version="0.1.0", git_commit="abc")
    b = validate_request(make_request(maximum=1), software_version="0.1.0", git_commit="abc")
    assert a.blocked_result_hash == b.blocked_result_hash
    assert a.blocked_result_hash is not None


def test_unknown_field_uses_failure_stage_one() -> None:
    payload = deepcopy(make_request())
    payload["not_a_real_field"] = "boom"
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_UNKNOWN_FIELD" for item in result.blockers)


def test_request_schema_version_blocked_at_stage_three() -> None:
    payload = deepcopy(make_request())
    payload["schema_version"] = "wrong.schema-version.v9"
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_SCHEMA_VERSION_UNSUPPORTED" for item in result.blockers)


def test_task020_configuration_identity_mismatch_blocks_stage_four() -> None:
    payload = deepcopy(make_request())
    config = make_configuration()
    wrong = dataclasses.replace(config, configuration_id="stale-id", configuration_hash="0" * 64)
    payload["configuration"] = wrong
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(
        item.code == "STL_TASK020_CONFIGURATION_IDENTITY_MISMATCH" for item in result.blockers
    )
    # Stage 4 alone gates §11.7 (tube_pass_count not yet verified).
    assert all(item.code != "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" for item in result.warnings)


def test_authority_mode_mismatch_blocks_stage_five() -> None:
    payload = deepcopy(make_request())
    payload["layout_rule_authority"]["authority_mode"] = "APPROVED_RULE_PACK"
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_AUTHORITY_MODE_MISMATCH" for item in result.blockers)


def test_geometry_block_carries_eligible_warnings_from_stage_seven() -> None:
    payload = deepcopy(make_request())
    payload["tube_geometry"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH" for item in result.blockers)
    codes = {item.code for item in result.warnings}
    # §11.5: layout-rule auth chain verified at stage 6+ → eligible at stage 7+.
    # §11.7: configuration tube_pass_count verified at stage 4+ → eligible at stage 7+.
    # §11.6: envelope NOT verified yet (envelope happens at stage 8) → NOT eligible.
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in codes
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in codes
    assert "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER" not in codes


def test_envelope_invalid_blocks_stage_eight_with_internals_eligible() -> None:
    payload = deepcopy(make_request())
    payload["placement_envelope"]["tube_center_envelope_diameter_m"] = "0.005"
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_ENVELOPE_INVALID" for item in result.blockers)
    codes = {item.code for item in result.warnings}
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in codes
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in codes
    # §11.6 still gated by stage 8 success.
    assert "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER" not in codes


def test_origin_axis_authorization_blocks_stage_nine() -> None:
    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        sha256_hex,
    )

    payload = deepcopy(make_request())
    rule = payload["layout_rule_authority"]
    # Re-snapshot the rule with only CENTER_ON_PRIMITIVE_CELL allowed
    rule["allowed_origin_modes"] = ["CENTER_ON_PRIMITIVE_CELL"]
    # Reconstruct the snapshot_hash manually because we are modifying the raw
    # payload before it reaches the validator.
    rule["snapshot_hash"] = sha256_hex({k: v for k, v in rule.items() if k != "snapshot_hash"})
    payload["origin_mode"] = "CENTER_ON_LATTICE_POINT"
    payload["u_tube_pairing_plan"] = None  # ensure precheck doesn't preempt
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    codes = {item.code for item in result.blockers}
    assert "STL_ORIGIN_MODE_NOT_AUTHORIZED" in codes, codes
    # Stage 9 ⇒ envelope was verified at stage 8 ⇒ §11.6 warning eligible.
    warning_codes = {item.code for item in result.warnings}
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in warning_codes
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in warning_codes
    assert "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER" in warning_codes


def test_utube_required_precheck_blocks_stage_eleven() -> None:
    payload = deepcopy(make_request())
    payload["configuration"] = make_configuration(ConstructionFamily.U_TUBE)
    payload["u_tube_pairing_plan"] = None
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_UTUBE_PAIRING_REQUIRED" for item in result.blockers)


def test_blocked_result_identity_is_deterministic_per_inputs() -> None:
    """Regression: identical inputs produce identical blocked_result_hash."""

    payload_a = deepcopy(make_request(maximum=1))
    payload_b = deepcopy(make_request(maximum=1))
    r_a = validate_request(payload_a, software_version="0.1.0", git_commit="abc")
    r_b = validate_request(payload_b, software_version="0.1.0", git_commit="abc")
    assert r_a.blocked_result_hash == r_b.blocked_result_hash


def test_blocked_result_hash_is_software_version_independent() -> None:
    """Regression: §12.8 blocked_result_hash is independent of software_version.

    software_version and git_commit influence the FINAL stage-19 provenance
    projection, NOT the §12.8 blocked-result identity. So changing them with
    all else equal must NOT change blocked_result_hash.
    """

    base = make_request(maximum=1)
    r_a = validate_request(base, software_version="0.1.0", git_commit="abc")
    r_b = validate_request(deepcopy(base), software_version="0.2.0", git_commit="xyz")
    assert r_a.blocked_result_hash == r_b.blocked_result_hash


def test_blocked_result_hash_changes_with_different_blockers() -> None:
    """Regression: distinct blocker sets produce distinct blocked_result_hash."""

    payload_a = deepcopy(make_request(maximum=1))
    r_a = validate_request(payload_a, software_version="0.1.0", git_commit="abc")
    payload_b = deepcopy(make_request(maximum=1))
    payload_b["not_a_real_field"] = "boom"
    r_b = validate_request(payload_b, software_version="0.1.0", git_commit="abc")
    assert r_a.blocked_result_hash != r_b.blocked_result_hash


def test_envelope_version_blocked_has_no_eligible_warnings_before_stage_four() -> None:
    """At stage 3 (schema versions), no warning is eligible (TASK-020 unverified)."""

    payload = deepcopy(make_request())
    payload["placement_envelope"]["schema_version"] = "wrong.envelope.v9"
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert all(item.code != "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" for item in result.warnings)


def test_zone_duplicate_blocks_at_stage_ten() -> None:
    """Stage 10 (exclusion-zone duplicate ID) blocks with STL_EXCLUSION_ZONE_DUPLICATE_ID."""

    payload = deepcopy(make_request())
    # Inject two zones with same zone_id but different shape (one rect one circle).
    payload["exclusion_zones"] = [
        {
            "zone_id": "dup-zone",
            "zone_type": "AXIS_ALIGNED_RECTANGLE",
            "center_x_m": "0.01",
            "center_y_m": "0.01",
            "clearance_m": "0",
            "reason_code": "shared",
            "evidence_refs": ["zone-ev-a"],
            "width_m": "0.005",
            "height_m": "0.005",
            "radius_m": None,
        },
        {
            "zone_id": "dup-zone",
            "zone_type": "CIRCLE",
            "center_x_m": "0.02",
            "center_y_m": "0.02",
            "clearance_m": "0",
            "reason_code": "shared",
            "evidence_refs": ["zone-ev-b"],
            "width_m": None,
            "height_m": None,
            "radius_m": "0.005",
        },
    ]
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_EXCLUSION_ZONE_DUPLICATE_ID" for item in result.blockers)
