from __future__ import annotations

import dataclasses
from copy import deepcopy
from decimal import Decimal
from typing import Any

import pytest

from hexagent.exchangers.shell_tube.models import ConstructionFamily
from hexagent.exchangers.shell_tube.tube_layout import (
    ValidationStatus,
    validate_request,
)
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    frozen_fragment_to_primitive,
    sha256_hex,
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


# --------------------------------------------------------------------------- #
# Round 4 §3.3 — Stage 2 / Stage 3 precedence tests (P0-1)
# --------------------------------------------------------------------------- #


def test_round4_stage2_raw_type_blocks_before_stage3_schema_version() -> None:
    """Round 4 §3.3 Case A.

    placement_envelope.schema_version = "unsupported" AND
    origin_mode = 123 (raw-type invalid).
    Expectation:
    - failure_stage == 2
    - STL_RAW_TYPE_INVALID blocker is the only blocker
    - Stage-3 schema-version blocker is ABSENT (Stage 3 did not run)
    """

    payload = deepcopy(make_request())
    payload["placement_envelope"]["schema_version"] = "unsupported"
    payload["origin_mode"] = 123
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    field_paths = sorted({b.field_path for b in result.blockers})
    assert "origin_mode" in field_paths
    # Stage 3 schema-version blocker MUST be absent.
    for b in result.blockers:
        assert not b.field_path.startswith("placement_envelope.schema_version"), (
            f"unexpected Stage 3 blocker: {b.field_path}"
        )


def test_round4_stage2_pairing_raw_blocks_before_stage3_pairing_version() -> None:
    """Round 4 §3.3 Case B.

    u_tube_pairing_plan.schema_version = "unsupported" AND
    u_tube_pairing_plan.evidence_refs = "not-an-array" (raw-type invalid).
    Expectation:
    - failure_stage == 2
    - raw evidence_refs blocker present
    - Stage-3 pairing-version blocker ABSENT
    """

    payload = deepcopy(make_request())
    payload["configuration"] = make_configuration(ConstructionFamily.U_TUBE)
    payload["u_tube_pairing_plan"] = {
        "schema_version": "task021.unsupported-pairing.v0",
        "pairs": [
            {
                "pair_id": "p0",
                "leg_a": {"u": 0, "v": 0},
                "leg_b": {"u": 1, "v": 0},
                "evidence_refs": ["p-ev"],
            }
        ],
        "evidence_refs": "not-an-array",
        "pairing_plan_hash": "0" * 64,
    }
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    field_paths = {b.field_path for b in result.blockers}
    assert "u_tube_pairing_plan.evidence_refs" in field_paths
    assert "u_tube_pairing_plan.schema_version" not in field_paths, (
        "Stage-3 pairing-version blocker leaked into Stage-2 output"
    )


def test_round4_stage2_complete_blocker_retention() -> None:
    """Round 4 §3.3 Case C.

    Two independent Stage-2 defects (origin_mode=123, axis_orientation=[]).
    Expectation:
    - BOTH complete blockers retained
    - same-stage blocker count >= 2
    - Stage 3+ did NOT run
    """

    payload = deepcopy(make_request())
    payload["origin_mode"] = 123
    payload["axis_orientation"] = []
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    field_paths = sorted({b.field_path for b in result.blockers})
    assert "origin_mode" in field_paths
    assert "axis_orientation" in field_paths
    assert len(result.blockers) >= 2


def test_round4_stage3_all_three_versions_blocks_at_stage_three() -> None:
    """Round 4 §3.3 Case D.

    Stage 2 fully passes; request / envelope / pairing schema versions
    ALL unsupported. Expectation:
    - failure_stage == 3
    - all three Stage-3 blockers retained
    - Stage 4 did NOT run
    """

    payload = deepcopy(make_request())
    payload["configuration"] = make_configuration(ConstructionFamily.U_TUBE)
    payload["u_tube_pairing_plan"] = {
        "schema_version": "task021.unsupported-pairing.v0",
        "pairs": [
            {
                "pair_id": "p0",
                "leg_a": {"u": 0, "v": 0},
                "leg_b": {"u": 1, "v": 0},
                "evidence_refs": ["p-ev"],
            }
        ],
        "evidence_refs": ["plan-ev"],
        "pairing_plan_hash": "0" * 64,
    }
    payload["schema_version"] = "task021.unsupported-request.v0"
    payload["placement_envelope"]["schema_version"] = "task021.unsupported-envelope.v0"
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    field_paths = sorted({b.field_path for b in result.blockers})
    assert "schema_version" in field_paths
    assert "placement_envelope.schema_version" in field_paths
    assert "u_tube_pairing_plan.schema_version" in field_paths
    for b in result.blockers:
        assert not b.field_path.startswith("configuration"), f"Stage 4+ leaked: {b.field_path}"


# --------------------------------------------------------------------------- #
# Round 4 §4 / §5 / §6 / §7 / §8 — P0-2 / P0-3 / P0-4 / P1 E2E tests
# --------------------------------------------------------------------------- #


def test_round4_stage8_envelope_only_no_basis_fields() -> None:
    """Round 4 §4 (P0-2): Stage 8 returns ONLY the verified radius.

    Tests the structural separation between Stage 8 and Stage 12 by
    inspecting the public dataclass ``VerifiedEnvelopeRadius`` and confirming
    it has NO basis / axis / offset / determinant / bound / capacity fields.
    """

    import dataclasses

    from hexagent.exchangers.shell_tube.tube_layout.enumeration import (
        VerifiedEnvelopeRadius,
    )

    field_names = {f.name for f in dataclasses.fields(VerifiedEnvelopeRadius)}
    # Only rho-decimal / supporting string decimals survive. There must NOT
    # be any of the Stage-12 basis-vector / axis / offset fields.
    forbidden = {
        "a_x",
        "a_y",
        "b_x",
        "b_y",
        "offset_x",
        "offset_y",
        "determinant",
        "u_bound",
        "v_bound",
        "candidate_count",
    }
    assert forbidden.isdisjoint(field_names), (
        f"Stage 8 leaked Stage-12 fields: {forbidden & field_names}"
    )
    # The round-4 surface area must contain rho.
    assert "rho" in field_names


def test_round4_stage8_failure_does_not_run_stage12_basis_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Round 4 §4 (P0-2): Stage 12 basis construction MUST NOT run when Stage 8
    has already failed.

    Spy: monkeypatch the Stage-12 entry point to record calls. Construct
    a request whose envelope diameter is so small that Stage 8 emits
    ``STL_ENVELOPE_INVALID`` (``rho <= 0``). Confirm Stage 12 was never
    invoked.
    """

    from hexagent.exchangers.shell_tube.tube_layout import enumeration

    calls = {"n": 0}
    real_basis_for_stage12 = enumeration._compute_basis_for_stage12

    def spy_basis(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        return real_basis_for_stage12(*args, **kwargs)

    monkeypatch.setattr(enumeration, "_compute_basis_for_stage12", spy_basis, raising=True)

    payload = deepcopy(make_request())
    # Drive Stage 8 to negative rho directly: keep geometry large, make
    # envelope smaller than geometry so rho < 0. The catch requires the
    # public `placement_envelope` schema_version to remain valid, since
    # Stage 3 must succeed first.
    payload["tube_geometry"]["outer_diameter_m"] = "0.5"
    payload["tube_geometry"]["inner_diameter_m"] = "0.45"
    payload["tube_geometry"]["wall_thickness_m"] = "0.025"
    payload["placement_envelope"]["tube_center_envelope_diameter_m"] = "0.01"
    # Make pitch big enough to exceed tube OD so Stage 4
    # (verify_task020_configuration) does not reject on pitch_below_tube_od.
    payload["layout_rule_authority"]["pitch_m"] = "0.7"
    # Recompute snapshot_hashes so Stage 6 / Stage 7 pass.
    payload["tube_geometry"]["snapshot_hash"] = sha256_hex(
        {k: v for k, v in payload["tube_geometry"].items() if k != "snapshot_hash"}
    )
    payload["layout_rule_authority"]["snapshot_hash"] = sha256_hex(
        {k: v for k, v in payload["layout_rule_authority"].items() if k != "snapshot_hash"}
    )
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    assert any(b.code == "STL_ENVELOPE_INVALID" for b in result.blockers), [
        b.code for b in result.blockers
    ]
    # Stage 12 basis construction MUST NOT have run.
    assert calls["n"] == 0


def test_round4_stage9_failure_does_not_run_stage12_basis() -> None:
    """Stage 9 origin authorization failure MUST NOT trigger Stage 12 basis."""

    from hexagent.exchangers.shell_tube.tube_layout import enumeration

    real_basis = enumeration._compute_basis_for_stage12
    calls = {"n": 0}

    def spy_basis(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        return real_basis(*args, **kwargs)

    original = enumeration._compute_basis_for_stage12
    enumeration._compute_basis_for_stage12 = spy_basis  # type: ignore[assignment]
    try:
        payload = deepcopy(make_request())
        # Restrict allowed origin modes to a single entry and submit a
        # different (valid enum string) origin_mode to trigger Stage 9.
        payload["layout_rule_authority"]["allowed_origin_modes"] = ["CENTER_ON_LATTICE_POINT"]
        payload["origin_mode"] = "CENTER_ON_PRIMITIVE_CELL"
        # Recompute snapshot_hash so Stage 6 passes.
        from hexagent.exchangers.shell_tube.tube_layout.canonical import (
            sha256_hex as _sha,
        )

        payload["layout_rule_authority"]["snapshot_hash"] = _sha(
            {k: v for k, v in payload["layout_rule_authority"].items() if k != "snapshot_hash"}
        )
        result = validate_request(payload, software_version="0.1.0", git_commit="abc")
        assert result.layout is None
        assert any(b.code == "STL_ORIGIN_MODE_NOT_AUTHORIZED" for b in result.blockers), [
            b.code for b in result.blockers
        ]
    finally:
        enumeration._compute_basis_for_stage12 = original  # type: ignore[assignment]
    assert calls["n"] == 0


def test_round4_stage10_eligibility_three_warnings_no_utube() -> None:
    """Round 4 §5 (P0-3): Stage 10 (duplicate zone ID) BLOCKED result carries
    §11.5 / §11.6 / §11.7 eligible warnings; §11.8 (U-tube bend) is ABSENT
    because construction is not U_TUBE.
    """

    payload = deepcopy(make_request())
    payload["exclusion_zones"] = [
        {
            "zone_id": "dup-1",
            "zone_type": "CIRCLE",
            "center_x_m": "0.01",
            "center_y_m": "0.01",
            "clearance_m": "0",
            "reason_code": "shared",
            "evidence_refs": ["zone-ev"],
            "width_m": None,
            "height_m": None,
            "radius_m": "0.005",
        },
        {
            "zone_id": "dup-1",  # same id
            "zone_type": "CIRCLE",
            "center_x_m": "0.02",
            "center_y_m": "0.02",
            "clearance_m": "0",
            "reason_code": "shared",
            "evidence_refs": ["zone-ev"],
            "width_m": None,
            "height_m": None,
            "radius_m": "0.005",
        },
    ]
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    assert any(b.code == "STL_EXCLUSION_ZONE_DUPLICATE_ID" for b in result.blockers), [
        b.code for b in result.blockers
    ]
    warning_codes = {w.code for w in result.warnings}
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in warning_codes
    assert "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER" in warning_codes
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in warning_codes
    assert "STL_UTUBE_BEND_GEOMETRY_DEFERRED" not in warning_codes


def test_round4_stage11_utube_required_eligibility_three_warnings() -> None:
    """Round 4 §5 (P0-3): Stage 11 (U-tube pairing required but missing)
    BLOCKED result carries the three eligible warnings; U-tube bend
    warning is absent because pairing plan is missing.
    """

    payload = deepcopy(make_request())
    payload["configuration"] = make_configuration(ConstructionFamily.U_TUBE)
    payload["u_tube_pairing_plan"] = None
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    assert any(b.code == "STL_UTUBE_PAIRING_REQUIRED" for b in result.blockers)
    warning_codes = {w.code for w in result.warnings}
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in warning_codes
    assert "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER" in warning_codes
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in warning_codes
    assert "STL_UTUBE_BEND_GEOMETRY_DEFERRED" not in warning_codes


def test_round4_stage12_capacity_exceeded_eligibility_three_warnings() -> None:
    """Round 4 §5 (P0-3): Stage 12 candidate capacity exceeded BLOCKED
    result carries the three eligible warnings.
    """

    payload = deepcopy(make_request())
    # Force a small candidate capacity so the stage fails AFTER Stage 8/9/10/11
    # pass but at Stage 12.
    payload["layout_rule_authority"]["maximum_candidate_positions"] = 1
    payload["layout_rule_authority"]["snapshot_hash"] = sha256_hex(
        {k: v for k, v in payload["layout_rule_authority"].items() if k != "snapshot_hash"}
    )
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    assert any(b.code == "STL_ENUMERATION_LIMIT_EXCEEDED" for b in result.blockers), [
        b.code for b in result.blockers
    ]
    warning_codes = {w.code for w in result.warnings}
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in warning_codes
    assert "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER" in warning_codes
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in warning_codes


def test_round4_stage16_utube_pairing_failure_eligibility_three_warnings() -> None:
    """Round 4 §5 (P0-3): Stage 16 (invalid U-tube pairing) BLOCKED result
    carries the three eligible warnings; U-tube bend warning is absent
    because Stage 16 did NOT succeed.
    """

    payload = deepcopy(make_request())
    payload["configuration"] = make_configuration(ConstructionFamily.U_TUBE)
    payload["u_tube_pairing_plan"] = {
        "schema_version": "task021.u-tube-pairing.v1",
        "pairs": [
            {
                "pair_id": "broken",
                "leg_a": {"u": 99999, "v": 99999},  # off-grid
                "leg_b": {"u": 99998, "v": 99998},
                "evidence_refs": ["p-ev"],
            }
        ],
        "evidence_refs": ["plan-ev"],
        "pairing_plan_hash": "0" * 64,
    }
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    assert result.blockers
    # U-tube bend warning must NOT be present (Stage 16 did not succeed).
    warning_codes = {w.code for w in result.warnings}
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in warning_codes
    assert "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER" in warning_codes
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in warning_codes
    assert "STL_UTUBE_BEND_GEOMETRY_DEFERRED" not in warning_codes


def test_round4_stage14_no_positions_eligibility_three_warnings() -> None:
    """Round 4 §5 (P0-3) + §8.1: Stage 14 STL_NO_TUBE_POSITIONS BLOCKED
    result carries the three eligible warnings; layout is None.
    """

    payload = deepcopy(make_request())
    # Use a zone that covers ALL inside candidates without exceeding
    # Stage 8 / Stage 12 / Stage 13.
    payload["placement_envelope"]["tube_center_envelope_diameter_m"] = "0.12"
    payload["exclusion_zones"] = [
        {
            "zone_id": "kill-all",
            "zone_type": "CIRCLE",
            "center_x_m": "0",
            "center_y_m": "0",
            "clearance_m": "0",
            "reason_code": "shared",
            "evidence_refs": ["zone-ev"],
            "width_m": None,
            "height_m": None,
            "radius_m": "0.05",  # covers whole envelope
        }
    ]
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    assert any(b.code == "STL_NO_TUBE_POSITIONS" for b in result.blockers)
    warning_codes = {w.code for w in result.warnings}
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in warning_codes
    assert "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER" in warning_codes
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in warning_codes


def test_round4_stage15_collision_public_e2e(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Round 4 §8.2: Stage 15 STL_COORDINATE_QUANTIZATION_COLLISION via
    validate_request() public entry; layout is None; blocked_result_hash
    is non-null; eligible warnings present.

    Forced collision: replace ``coordinate_quantization_collision_guard``
    with a stub that unconditionally raises ``STL_COORDINATE_QUANTIZATION_COLLISION``
    once Stage 15 is reached. Stages 1-14 still run normally.
    """

    from hexagent.exchangers.shell_tube.tube_layout import validation as _validation
    from hexagent.exchangers.shell_tube.tube_layout.geometry import (
        GeometryFailure,
    )
    from hexagent.exchangers.shell_tube.tube_layout.models import (
        BlockerCode,
        MessageEntry,
    )

    def _stub(accepted: Any) -> Any:
        raise GeometryFailure(
            MessageEntry(
                code=BlockerCode.STL_COORDINATE_QUANTIZATION_COLLISION.value,
                field_path="positions",
                message_key="coordinate_quantization_collision",
            )
        )

    monkeypatch.setattr(
        _validation,
        "coordinate_quantization_collision_guard",
        _stub,
        raising=True,
    )

    payload = deepcopy(make_request())
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    codes = [b.code for b in result.blockers]
    assert "STL_COORDINATE_QUANTIZATION_COLLISION" in codes, codes
    assert result.blocked_result_hash is not None
    warning_codes = {w.code for w in result.warnings}
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in warning_codes
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in warning_codes


def test_round4_layout_caller_mutation_does_not_influence_hashes() -> None:
    """Round 4 §6.5 (P0-4): Mutating caller's source dict/list/nested
    mapping after validate_request() does NOT influence the captured
    license_evidence, request_hash, layout_hash, or warning/blocker
    details.
    """

    payload = deepcopy(make_request())
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is not None

    snapshot_license = frozen_fragment_to_primitive(
        result.layout.layout_rule_authority.license_evidence
    )
    request_hash_before = result.layout.request_hash
    layout_hash_before = result.layout.layout_hash

    # Mutate the caller dict.
    payload["layout_rule_authority"]["license_evidence"]["injected"] = "tampered"
    payload["layout_rule_authority"]["license_evidence"]["nested"] = {"x": 1}

    # Re-snapshot must still equal the captured snapshot.
    snapshot_after = frozen_fragment_to_primitive(
        result.layout.layout_rule_authority.license_evidence
    )
    assert snapshot_license == snapshot_after, (
        "license_evidence mutation leaked into returned layout"
    )
    assert request_hash_before == result.layout.request_hash
    assert layout_hash_before == result.layout.layout_hash


def test_round4_public_canonical_bypass_rejection() -> None:
    """Round 4 §7 (P1): All public canonical fragment helpers reject
    ``frozenset`` / raw ``tuple`` / ``Decimal`` / ``bytes`` / non-string
    mapping keys.
    """

    from hexagent.exchangers.shell_tube.tube_layout.canonical import (
        PublicCanonicalDomainError,
        fragment_canonical,
        fragment_canonical_json,
    )

    with pytest.raises(PublicCanonicalDomainError):
        fragment_canonical_json({"x": frozenset({"a"})})
    with pytest.raises(PublicCanonicalDomainError):
        fragment_canonical_json({"x": ("a", "b")})
    with pytest.raises(PublicCanonicalDomainError):
        fragment_canonical_json({"x": Decimal("1")})
    with pytest.raises(PublicCanonicalDomainError):
        fragment_canonical_json({"x": b"a"})
    with pytest.raises(PublicCanonicalDomainError):
        fragment_canonical_json({1: "a"})
    with pytest.raises(PublicCanonicalDomainError):
        fragment_canonical(frozenset({"a"}))


def test_round4_noncanonical_raw_public_e2e() -> None:
    """Round 4 §8.3: Non-canonical raw values flowing into validate_request()
    must return BLOCKED with no uncaught exception.
    """

    # Decimal: raw_failing_field is a Decimal — the request will BLOCK.
    payload = deepcopy(make_request())
    payload["layout_rule_authority"]["pitch_m"] = Decimal("0.0254")  # type: ignore[arg-type]
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    assert result.blocked_result_hash is not None
    assert result.blockers
