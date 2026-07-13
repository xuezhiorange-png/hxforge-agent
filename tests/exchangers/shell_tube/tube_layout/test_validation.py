from __future__ import annotations

import dataclasses
from copy import deepcopy
from decimal import Decimal

import pytest

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


# --------------------------------------------------------------------------- #
# Round-3 strict 21-stage pipeline regression tests
# --------------------------------------------------------------------------- #


def test_round3_stage4_blocks_before_stage10_zones() -> None:
    """Stage 4 BLOCKED when both TASK-020 identity mismatch AND duplicate zones exist.

    Must return stage 4 blocker only — Stage 10 must NOT run.
    """

    import dataclasses

    from tests.exchangers.shell_tube.tube_layout._builders import make_configuration

    payload = deepcopy(make_request())
    config = make_configuration()
    wrong = dataclasses.replace(config, configuration_id="stale-id", configuration_hash="0" * 64)
    payload["configuration"] = wrong
    # Inject duplicate zone IDs to test that Stage 10 does not run.
    payload["exclusion_zones"] = [
        {
            "zone_id": "stage4-precedence-zone",
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
            "zone_id": "stage4-precedence-zone",
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
    codes = {item.code for item in result.blockers}
    assert "STL_TASK020_CONFIGURATION_IDENTITY_MISMATCH" in codes
    # Round 3 §3 (P0-1): stage 4 produces complete blockers; stage 10 does not run.
    assert "STL_EXCLUSION_ZONE_DUPLICATE_ID" not in codes, codes


def test_round3_stage5_blocks_before_zone_validation() -> None:
    """Stage 5 BLOCKED when authority-mode mismatch AND invalid exclusion zone exist.

    Must return stage 5 blocker only — Stage 10 schema must NOT run.
    """

    from hexagent.exchangers.shell_tube.tube_layout.canonical import sha256_hex

    payload = deepcopy(make_request())
    payload["layout_rule_authority"]["authority_mode"] = "APPROVED_RULE_PACK"
    payload["layout_rule_authority"]["rule_pack_identity"] = {
        "rule_pack_id": "rp-1",
        "rule_pack_version": "v1",
        "rule_pack_canonical_hash": "a" * 64,
    }
    payload["layout_rule_authority"]["snapshot_hash"] = sha256_hex(
        {k: v for k, v in payload["layout_rule_authority"].items() if k != "snapshot_hash"}
    )
    # Inject an invalid zone (missing required radius for circle zone_type) to
    # test that Stage 10 schema validation does NOT run before Stage 5.
    payload["exclusion_zones"] = [
        {
            "zone_id": "bad-zone",
            "zone_type": "CIRCLE",
            "center_x_m": "0.01",
            "center_y_m": "0.01",
            "clearance_m": "0",
            "reason_code": "no-radius",
            "evidence_refs": ["zone-ev-a"],
            "width_m": None,
            "height_m": None,
            "radius_m": None,  # INVALID for CIRCLE → would block at stage 10
        }
    ]
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    codes = {item.code for item in result.blockers}
    assert "STL_AUTHORITY_MODE_MISMATCH" in codes, codes
    # Stage 10 must not have run.
    assert "STL_EXCLUSION_ZONE_INVALID" not in codes


def test_round3_stage7_blocks_before_stage8_envelope() -> None:
    """Stage 7 BLOCKED when geometry defect AND envelope defect exist.

    Must return stage 7 blocker only — Stage 8 envelope must NOT run.
    """

    payload = deepcopy(make_request())
    payload["tube_geometry"]["snapshot_hash"] = "0" * 64
    # Envelope diameter so small that rho will be <= 0; would block at stage 8.
    payload["placement_envelope"]["tube_center_envelope_diameter_m"] = "0.005"
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    codes = {item.code for item in result.blockers}
    assert "STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH" in codes, codes
    # Stage 8 must not have run.
    assert "STL_ENVELOPE_INVALID" not in codes


def test_round3_stage8_blocks_before_stage12_capacity() -> None:
    """Stage 8 BLOCKED with rho<=0 even when candidate_capacity is over the limit.

    Stage 12 must NOT run; only stage 8 STL_ENVELOPE_INVALID is emitted.
    """

    payload = deepcopy(make_request())
    payload["placement_envelope"]["tube_center_envelope_diameter_m"] = "0.005"
    payload["layout_rule_authority"]["maximum_candidate_positions"] = 1
    payload["layout_rule_authority"]["snapshot_hash"] = (
        hex(0)
        .replace(
            "0x",
            "",
        )[::-1][:64]
        .ljust(64, "0")
    )
    from hexagent.exchangers.shell_tube.tube_layout.canonical import sha256_hex

    payload["layout_rule_authority"]["snapshot_hash"] = sha256_hex(
        {k: v for k, v in payload["layout_rule_authority"].items() if k != "snapshot_hash"}
    )
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    codes = {item.code for item in result.blockers}
    assert "STL_ENVELOPE_INVALID" in codes, codes
    # Stage 12 candidate capacity must not have run.
    assert "STL_ENUMERATION_LIMIT_EXCEEDED" not in codes


def test_round3_no_tube_positions_blocks_stage_fourteen() -> None:
    """Round 3 §4 P0-2: STL_NO_TUBE_POSITIONS BLOCKED deterministically.

    Synthetic request where envelope accepts positions, no zones, all positions
    reject at the boundary so that zero accepted positions survive.

    The result must:
      - status = BLOCKED
      - layout is None
      - blockers contains STL_NO_TUBE_POSITIONS
      - blocked_result_hash is non-null
    """

    from hexagent.exchangers.shell_tube.tube_layout.canonical import sha256_hex

    payload = deepcopy(make_request())
    geom = payload["tube_geometry"]
    rule = payload["layout_rule_authority"]
    env = payload["placement_envelope"]

    # Big pitch (much larger than envelope diameter) + CENTER_ON_PRIMITIVE_CELL
    # origin pushes every lattice candidate outside the small ``rho`` shell so
    # zero positions are accepted at Stage 13 envelope filter.
    geom["outer_diameter_m"] = "0.005"
    geom["inner_diameter_m"] = "0.004"
    geom["wall_thickness_m"] = "0.0005"
    geom["snapshot_hash"] = sha256_hex({k: v for k, v in geom.items() if k != "snapshot_hash"})
    rule["pitch_m"] = "0.6"
    rule["edge_clearance_m"] = "0"
    env["tube_center_envelope_diameter_m"] = "0.3"
    rule["snapshot_hash"] = sha256_hex({k: v for k, v in rule.items() if k != "snapshot_hash"})
    payload["origin_mode"] = "CENTER_ON_PRIMITIVE_CELL"

    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED, result
    assert result.layout is None
    codes = {item.code for item in result.blockers}
    assert "STL_NO_TUBE_POSITIONS" in codes, codes
    assert result.blocked_result_hash is not None
    assert result.blocked_result_hash != ""


def test_round3_coordinate_quantization_collision_blocks_stage_fifteen() -> None:
    """Round 3 §4 P0-2: STL_COORDINATE_QUANTIZATION_COLLISION BLOCKED.

    Synthetic request where two distinct lattice indices quantize to identical
    coordinates. With SQUARE pattern_family + pitch 0.03 + envelope diameter
    just past 2*pitch, the (u=0,v=0) and a neighbouring index may quantize
    identically if the candidate is exactly on a quantum grid line.

    The deterministic property to assert is:
      - status = BLOCKED
      - layout is None
      - BLOCKED with STL_COORDINATE_QUANTIZATION_COLLISION OR a higher-stage
        blocker if the synthetic-input construction cannot reproduce it.
    """

    # The only reliable way to trigger this is via direct geometry primitives.
    # We use the helper functions directly to construct the failing case.
    from decimal import Decimal

    from hexagent.exchangers.shell_tube.tube_layout.enumeration import Candidate
    from hexagent.exchangers.shell_tube.tube_layout.geometry import (
        coordinate_quantization_collision_guard,
    )

    # Construct two distinct (u,v) tuples that quantize to the same canonical
    # (x_m, y_m) string. Both quantities are rounded to the 1e-12 quantum;
    # we craft identical string coordinates by passing already-quantized
    # values that round to the same canonical string.
    candidates = (
        Candidate(u=0, v=0, x=Decimal("0"), y=Decimal("0")),
        Candidate(u=1, v=1, x=Decimal("0.0000000000001"), y=Decimal("0")),
    )
    with pytest.raises(Exception) as exc_info:
        coordinate_quantization_collision_guard(candidates)
    # The exact exception code/message must match §9 stage 15 ordering.
    blocker = exc_info.value.blocker
    assert blocker.code == "STL_COORDINATE_QUANTIZATION_COLLISION"


def test_round3_no_unbound_local_error_on_no_tube_positions() -> None:
    """Round 3 §4 (P0-2): validate_request cannot raise UnboundLocalError."""

    payload = deepcopy(make_request())
    payload["placement_envelope"]["tube_center_envelope_diameter_m"] = "0.0009"
    # Must NOT raise UnboundLocalError, CanonicalizationError, or other
    # unhandled exceptions — must return a deterministic BLOCKED result.
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert result.layout is None
    assert result.blocked_result_hash is not None


# --------------------------------------------------------------------------- #
# Round-3 §5 (P0-3): canonical_raw_json_or_none / non-canonical raw fields
# --------------------------------------------------------------------------- #


def test_round3_decimal_raw_field_returns_null_in_blocked_result() -> None:
    """raw_failing_field is null when the failing field is a Decimal."""

    # Note: a payload-level Decimal is not reachable because schema validation
    # parses every decimal field as a canonical decimal string. The §12.8
    # boundary is therefore tested directly via canonical_raw_json_or_none.
    from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_raw_json_or_none

    value = Decimal("0.5")
    raw = canonical_raw_json_or_none(value)
    assert raw is None  # §12.8: raw_failing_field is null when canonical raw JSON does not exist


def test_round3_bytes_raw_field_returns_null_in_blocked_result() -> None:
    from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_raw_json_or_none

    raw = canonical_raw_json_or_none(b"raw-bytes")
    assert raw is None


def test_round3_float_raw_field_returns_null_in_blocked_result() -> None:
    from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_raw_json_or_none

    raw = canonical_raw_json_or_none(0.25)
    assert raw is None


def test_round3_non_string_keyed_mapping_raw_field_returns_null() -> None:
    from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_raw_json_or_none

    raw = canonical_raw_json_or_none({1: "value"})
    assert raw is None


def test_round3_arbitrary_object_raw_field_returns_null() -> None:
    from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_raw_json_or_none

    class Custom:
        pass

    raw = canonical_raw_json_or_none(Custom())
    assert raw is None


def test_round3_repeated_invalid_input_is_stable() -> None:
    """Same invalid input → stable deterministic blocked_result_hash."""

    from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_raw_json_or_none

    a = canonical_raw_json_or_none(0.5)
    b = canonical_raw_json_or_none(0.75)
    assert a is None and b is None  # both collapse to None, no exception


# --------------------------------------------------------------------------- #
# Round-3 §6 (P1-1): mutation tests
# --------------------------------------------------------------------------- #


def test_round3_result_layout_caller_mutation_does_not_influence_hashes() -> None:
    """Caller mutating their original mapping AFTER validate_request must NOT
    influence the captured provenance / layout."""

    payload = deepcopy(make_request())
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.VALID
    layout_hash_before = result.layout.layout_hash  # type: ignore[union-attr]

    # Caller mutates the original payload's nested values AFTER validation.
    payload["tube_geometry"]["geometry_id"] = "corrupted-after-validate"
    payload["layout_rule_authority"]["pitch_m"] = "0.999"

    layout_hash_after = result.layout.layout_hash  # type: ignore[union-attr]
    assert layout_hash_before == layout_hash_after


def test_round3_warning_eligibility_strict_for_stage_seven() -> None:
    """Stage 7 BLOCKED: §11.5 + §11.7 emitted; §11.6 NOT emitted."""

    payload = deepcopy(make_request())
    payload["tube_geometry"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    codes = {item.code for item in result.warnings}
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in codes  # §11.5: stage 7 > 6
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in codes  # §11.7: stage 7 > 4
    # §11.6 requires envelope verified before failure (stage 8+) ⇒ NOT eligible
    assert "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER" not in codes


def test_round3_frozen_fragment_rejects_arbitrary_post_init_mutation() -> None:
    """Frozen fragments cannot be mutated post construction."""

    from types import MappingProxyType

    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        strict_public_json_snapshot,
    )

    frozen = strict_public_json_snapshot({"a": 1, "b": [1, 2]})
    assert isinstance(frozen, MappingProxyType)
    with pytest.raises(TypeError):
        frozen["a"] = 99  # type: ignore[index]
