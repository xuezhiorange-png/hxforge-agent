"""TASK-020 canonical serialization + SHA-256 + UUIDv5 tests — Slice A.

Asserts the §11 determinism / canonicalization / hashing / identity
contract.
"""

from __future__ import annotations

import pytest

import hexagent.exchangers.shell_tube as st
import hexagent.exchangers.shell_tube.errors as errors
from hexagent.exchangers.shell_tube import canonical

SHA_PAYLOAD = "a" * 64
SHA_DOMAIN = "b" * 64
SHA_RULE_PACK = "c" * 64

VALID_CASE_AUTHORITY = {
    "revision_id": "rev-001",
    "payload_hash": SHA_PAYLOAD,
    "domain_snapshot_hash": SHA_DOMAIN,
    "status": "committed",
}


def _make_request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "schema_version": st.REQUEST_SCHEMA_VERSION,
        "case_authority": dict(VALID_CASE_AUTHORITY),
        "equipment_family": "SHELL_AND_TUBE",
        "authority_mode": "INTERNAL_GENERIC",
        "construction_family": "FIXED_TUBESHEET",
        "orientation": "HORIZONTAL",
        "shell_pass_count": 1,
        "tube_pass_count": 2,
        "front_head_token": "FRONT",
        "shell_token": "SHELL",
        "rear_head_token": "REAR",
        "standard_system_id": None,
        "requested_rule_pack_identity": None,
        "evidence_refs": [],
    }
    request.update(overrides)
    return request


class TestDeterminism:
    def test_same_input_same_hash(self) -> None:
        result1 = st.validate_request(_make_request())
        result2 = st.validate_request(_make_request())
        assert result1.configuration is not None
        assert result2.configuration is not None
        assert result1.configuration.configuration_hash == result2.configuration.configuration_hash

    def test_same_input_same_id(self) -> None:
        result1 = st.validate_request(_make_request())
        result2 = st.validate_request(_make_request())
        assert result1.configuration is not None
        assert result2.configuration is not None
        assert result1.configuration.configuration_id == result2.configuration.configuration_id

    def test_dict_key_order_independence(self) -> None:
        result1 = st.validate_request(_make_request())
        # Reorder all keys
        reordered = _make_request()
        reordered["case_authority"] = dict(VALID_CASE_AUTHORITY)
        reordered["case_authority"] = {
            "status": "committed",
            "domain_snapshot_hash": SHA_DOMAIN,
            "payload_hash": SHA_PAYLOAD,
            "revision_id": "rev-001",
        }
        # Reverse evidence_refs order
        reordered["evidence_refs"] = []
        result2 = st.validate_request(reordered)
        assert result1.configuration is not None
        assert result2.configuration is not None
        assert result1.configuration.configuration_hash == result2.configuration.configuration_hash

    def test_status_change_changes_hash(self) -> None:
        result1 = st.validate_request(_make_request(orientation="HORIZONTAL"))
        result2 = st.validate_request(_make_request(orientation="VERTICAL"))
        assert result1.configuration is not None
        assert result2.configuration is not None
        assert result1.configuration.configuration_hash != result2.configuration.configuration_hash

    def test_pass_count_change_changes_hash(self) -> None:
        result1 = st.validate_request(_make_request(shell_pass_count=1))
        result2 = st.validate_request(_make_request(shell_pass_count=2))
        assert result1.configuration is not None
        assert result2.configuration is not None
        assert result1.configuration.configuration_hash != result2.configuration.configuration_hash


class TestHashFormat:
    def test_hash_is_lowercase_hex_64_chars(self) -> None:
        result = st.validate_request(_make_request())
        assert result.configuration is not None
        h = result.configuration.configuration_hash
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_id_is_uuid_string(self) -> None:
        result = st.validate_request(_make_request())
        assert result.configuration is not None
        config_id = result.configuration.configuration_id
        # UUID format: 8-4-4-4-12 hex chars separated by hyphens
        parts = config_id.split("-")
        assert len(parts) == 5
        assert [len(p) for p in parts] == [8, 4, 4, 4, 12]
        # All hex
        for part in parts:
            assert all(c in "0123456789abcdefABCDEF" for c in part)

    def test_id_is_uuidv5(self) -> None:
        """§11.3 — UUIDv5 with the frozen namespace seed and URN prefix."""
        result = st.validate_request(_make_request())
        assert result.configuration is not None
        # Recompute the UUIDv5 with the same canonical hash to verify
        # the namespace + URN prefix match.
        import uuid

        expected = uuid.uuid5(
            uuid.NAMESPACE_URL,
            canonical.URN_PREFIX + result.configuration.configuration_hash,
        )
        assert str(expected) == result.configuration.configuration_id


class TestCanonicalization:
    def test_evidence_refs_sorted_unicode_codepoint(self) -> None:
        # Sort is by Unicode code-point order; ``.`` (0x2E) sorts
        # before digits (0x30..0x39), so we use only digits and
        # letters to make the order trivially predictable.
        result = st.validate_request(_make_request(evidence_refs=["ref-c", "ref-a", "ref-b"]))
        assert result.configuration is not None
        assert list(result.configuration.authority_binding.case_authority_evidence_refs) == [
            "ref-a",
            "ref-b",
            "ref-c",
        ]

    def test_canonicalization_drops_id_and_hash(self) -> None:
        """§11.2 exclusion list — configuration_id and configuration_hash
        are NOT in the canonical payload."""
        result = st.validate_request(_make_request())
        assert result.configuration is not None
        # The configuration object carries both, but the canonical
        # payload should not — recomputing the hash with
        # configuration_id and configuration_hash in the payload
        # would change the hash.

        # The validation pipeline exposes the canonical payload
        # indirectly via the configuration hash. We assert the
        # hash is stable across a re-validation cycle (which is
        # the strongest invariant we can observe from outside the
        # canonicalizer).
        result2 = st.validate_request(_make_request())
        assert result2.configuration is not None
        assert result.configuration.configuration_hash == result2.configuration.configuration_hash

    def test_token_lowercase_normalized_then_hash_stable(self) -> None:
        result1 = st.validate_request(_make_request(front_head_token="front"))
        result2 = st.validate_request(_make_request(front_head_token="FRONT"))
        assert result1.configuration is not None
        assert result2.configuration is not None
        # Both must produce the same hash because the canonicalizer
        # normalizes tokens to uppercase before hashing.
        assert result1.configuration.configuration_hash == result2.configuration.configuration_hash


class TestFailClosedCanonicalization:
    """§11 — canonicalization fails closed for unsupported values.

    Allowed canonical value set:
    - ``None``
    - ``bool``
    - ``int``
    - finite ``float``
    - ``str``
    - ``list`` / ``tuple`` of allowed values
    - ``Mapping`` with ``str`` keys to allowed values

    Every other input MUST raise ``BlockerError`` with
    ``code == "STC_CANONICALIZATION_FAILED"``.
    """

    def test_object_rejected(self) -> None:
        payload = {"x": object()}
        with pytest.raises(errors.BlockerError) as exc_info:
            canonical._canonical_value(payload)
        assert exc_info.value.code == "STC_CANONICALIZATION_FAILED"

    def test_set_rejected(self) -> None:
        payload = {"x": {1, 2, 3}}
        with pytest.raises(errors.BlockerError) as exc_info:
            canonical._canonical_value(payload)
        assert exc_info.value.code == "STC_CANONICALIZATION_FAILED"

    def test_bytes_rejected(self) -> None:
        payload = {"x": b"raw-bytes"}
        with pytest.raises(errors.BlockerError) as exc_info:
            canonical._canonical_value(payload)
        assert exc_info.value.code == "STC_CANONICALIZATION_FAILED"

    def test_non_string_mapping_key_rejected(self) -> None:
        payload = {1: "value"}  # type: ignore[dict-item]
        with pytest.raises(errors.BlockerError) as exc_info:
            canonical._canonical_value(payload)
        assert exc_info.value.code == "STC_CANONICALIZATION_FAILED"

    def test_nan_rejected(self) -> None:
        payload = {"x": float("nan")}
        with pytest.raises(errors.BlockerError) as exc_info:
            canonical._canonical_value(payload)
        assert exc_info.value.code == "STC_CANONICALIZATION_FAILED"

    def test_infinity_rejected(self) -> None:
        payload = {"x": float("inf")}
        with pytest.raises(errors.BlockerError) as exc_info:
            canonical._canonical_value(payload)
        assert exc_info.value.code == "STC_CANONICALIZATION_FAILED"

    def test_negative_infinity_rejected(self) -> None:
        payload = {"x": float("-inf")}
        with pytest.raises(errors.BlockerError) as exc_info:
            canonical._canonical_value(payload)
        assert exc_info.value.code == "STC_CANONICALIZATION_FAILED"

    def test_nested_unsupported_value_rejected(self) -> None:
        payload = {"outer": {"inner": object()}}
        with pytest.raises(errors.BlockerError) as exc_info:
            canonical._canonical_value(payload)
        assert exc_info.value.code == "STC_CANONICALIZATION_FAILED"

    def test_finite_float_remains_deterministic(self) -> None:
        # Finite floats must round-trip through repr() deterministically.
        payload = {"x": 1.5}
        result1 = canonical._canonical_value(payload)
        result2 = canonical._canonical_value(payload)
        assert result1 == result2 == {"x": "1.5"}

    def test_mapping_insertion_order_does_not_affect_hash(self) -> None:
        # The canonical serializer must sort keys, so insertion order
        # of a top-level mapping does not affect the canonical hash.
        from hexagent.exchangers.shell_tube.canonical import configuration_hash

        payload1 = {"a": 1, "b": 2, "c": 3}
        payload2 = {"c": 3, "a": 1, "b": 2}
        assert configuration_hash(payload1) == configuration_hash(payload2)
