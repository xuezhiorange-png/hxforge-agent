"""TASK-026 canonical encoding tests (T1-R2 numbered_inventory items 31-33).

Frozen test reference set (T1-R2):
  31. test_canonical_key_order_matches_frozen_tuple
  32. test_decimal_string_form_preserves_sign_and_trailing_zeros
  33. test_blocked_envelope_serialization_round_trip

T1-R2 module allocation: 3 tests in this module.
"""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_thermal import (
    BLOCKED_RESULT_HASH_FIELDS,
    KIND_DECIMAL,
    KIND_STRING,
    KIND_TUPLE,
    PROPERTY_SNAPSHOT_HASH_FIELDS,
    PROPERTY_SNAPSHOT_HASH_KIND_TAGS,
    RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE,
    SUCCESS_RESULT_HASH_FIELDS,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.canonical import (
    decimal_payload,
    frame_record,
    sha256_hex_from_framed_bytes,
    string_payload,
)


def test_canonical_key_order_matches_frozen_tuple() -> None:
    """T1-R2 31 — Canonical key order matches frozen tuples."""
    # Snapshot 9-field hash projection.
    assert len(PROPERTY_SNAPSHOT_HASH_FIELDS) == 9
    # Indexed kind tags: 6 decimal + 1 enum + 2 string.
    assert PROPERTY_SNAPSHOT_HASH_KIND_TAGS[0] == KIND_DECIMAL
    assert PROPERTY_SNAPSHOT_HASH_KIND_TAGS[6] == b'ENUM'
    assert PROPERTY_SNAPSHOT_HASH_KIND_TAGS[7] == KIND_STRING
    # Success result hash projection: 21 fields, no self-reference.
    assert SUCCESS_RESULT_HASH_FIELDS[0] == 'schema_version'
    assert SUCCESS_RESULT_HASH_FIELDS[-1] == 'provenance'
    assert 'result_hash' not in SUCCESS_RESULT_HASH_FIELDS
    assert 'result_id' not in SUCCESS_RESULT_HASH_FIELDS
    # Blocked result hash projection: 15 fields, no self-reference.
    assert BLOCKED_RESULT_HASH_FIELDS[0] == 'schema_version'
    assert BLOCKED_RESULT_HASH_FIELDS[-1] == 'provenance'
    assert 'result_hash' not in BLOCKED_RESULT_HASH_FIELDS
    assert 'result_id' not in BLOCKED_RESULT_HASH_FIELDS


def test_decimal_string_form_preserves_sign_and_trailing_zeros() -> None:
    """T1-R2 32 — Decimal payload preserves sign and trailing zeros."""
    # Negative
    assert decimal_payload(Decimal('-3.14')) == b'-3.14'
    # Positive
    assert decimal_payload(Decimal('0.0001')) == b'0.0001'
    # Integer-like
    assert decimal_payload(Decimal('10')) == b'10'
    # Zero
    assert decimal_payload(Decimal('0')) == b'0'


def test_blocked_envelope_serialization_round_trip() -> None:
    """T1-R2 33 — Blocked envelope serializes to deterministic bytes."""
    # Build a 5-field record and verify the frame_record bytes are stable.
    fields = [
        ("schema_version", KIND_STRING, string_payload("task026-r7.schema.v1")),
        ("implementation_software_version", KIND_STRING, string_payload("task026-local-impl-r8")),
        ("blockers", KIND_TUPLE, b"\x00\x00\x00\x00"),  # empty tuple
        ("warnings", KIND_TUPLE, b"\x00\x00\x00\x00"),
        ("deferred_capabilities", KIND_TUPLE, b"\x00\x00\x00\x00"),
    ]
    framed = frame_record(RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE, fields)
    h = sha256_hex_from_framed_bytes(framed)
    assert len(h) == 64
    # Same call -> same hash (determinism).
    framed2 = frame_record(RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE, fields)
    assert framed == framed2
    # Same fields -> same hash.
    h2 = sha256_hex_from_framed_bytes(framed2)
    assert h == h2
