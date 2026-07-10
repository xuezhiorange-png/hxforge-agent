"""TASK-020 schema validation tests — Slice A.

Asserts the §8 / §10.2 / §10.3 schema contract for the
TASK-020 configuration schema pipeline. Tests do NOT exercise any
engineering numerical behavior, do NOT load any rule pack, and
do NOT mutate any frozen TASK-001..TASK-019 contract file.
"""

from __future__ import annotations

import pytest

import hexagent.exchangers.shell_tube as st


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


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
    """Return a fresh copy of the canonical valid request payload."""
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


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestSchemaVersion:
    def test_valid_schema_version_accepted(self) -> None:
        result = st.validate_request(_make_request())
        assert result.status.value == "VALID"

    def test_unsupported_schema_version_blocked(self) -> None:
        result = st.validate_request(
            _make_request(schema_version="task020.configuration-request.v2")
        )
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_SCHEMA_VERSION_UNSUPPORTED" for b in result.blockers
        )

    def test_missing_schema_version_blocked(self) -> None:
        result = st.validate_request(_make_request(schema_version=""))
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_SCHEMA_VERSION_UNSUPPORTED" for b in result.blockers
        )


class TestUnknownField:
    def test_unknown_top_level_field_blocked(self) -> None:
        result = st.validate_request(
            _make_request(unexpected_field="boom")
        )
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_UNKNOWN_FIELD" for b in result.blockers)

    def test_legacy_rule_pack_id_field_blocked(self) -> None:
        result = st.validate_request(_make_request(rule_pack_id="rp1"))
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_UNKNOWN_FIELD" for b in result.blockers)

    def test_legacy_rule_pack_version_blocked(self) -> None:
        result = st.validate_request(_make_request(rule_pack_version="v1"))
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_UNKNOWN_FIELD" for b in result.blockers)

    def test_legacy_rule_pack_canonical_hash_blocked(self) -> None:
        result = st.validate_request(_make_request(rule_pack_canonical_hash=SHA_RULE_PACK))
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_UNKNOWN_FIELD" for b in result.blockers)

    def test_legacy_evaluated_rule_pack_authority_blocked(self) -> None:
        result = st.validate_request(
            _make_request(evaluated_rule_pack_authority={"foo": "bar"})
        )
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_UNKNOWN_FIELD" for b in result.blockers)

    def test_legacy_selected_rule_ids_blocked(self) -> None:
        result = st.validate_request(
            _make_request(selected_rule_ids=["rule-a"])
        )
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_UNKNOWN_FIELD" for b in result.blockers)

    def test_legacy_selected_rule_artifact_hashes_blocked(self) -> None:
        result = st.validate_request(
            _make_request(selected_rule_artifact_hashes=[SHA_RULE_PACK])
        )
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_UNKNOWN_FIELD" for b in result.blockers)

    def test_legacy_content_hash_blocked(self) -> None:
        result = st.validate_request(_make_request(content_hash=SHA_RULE_PACK))
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_UNKNOWN_FIELD" for b in result.blockers)

    def test_legacy_rule_pack_hash_blocked(self) -> None:
        result = st.validate_request(_make_request(rule_pack_hash=SHA_RULE_PACK))
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_UNKNOWN_FIELD" for b in result.blockers)


class TestCaseAuthority:
    def test_case_authority_missing_blocked(self) -> None:
        request = _make_request()
        request["case_authority"] = None
        result = st.validate_request(request)
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_CASE_AUTHORITY_MISSING" for b in result.blockers)

    def test_case_authority_revision_id_missing_blocked(self) -> None:
        request = _make_request()
        request["case_authority"] = dict(VALID_CASE_AUTHORITY)
        request["case_authority"]["revision_id"] = ""
        result = st.validate_request(request)
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_CASE_REVISION_ID_MISSING" for b in result.blockers
        )

    def test_case_authority_payload_hash_invalid_blocked(self) -> None:
        request = _make_request()
        request["case_authority"] = dict(VALID_CASE_AUTHORITY)
        request["case_authority"]["payload_hash"] = "not-hex"
        result = st.validate_request(request)
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_CASE_PAYLOAD_HASH_INVALID" for b in result.blockers
        )

    def test_case_authority_payload_hash_uppercase_blocked(self) -> None:
        request = _make_request()
        request["case_authority"] = dict(VALID_CASE_AUTHORITY)
        request["case_authority"]["payload_hash"] = SHA_PAYLOAD.upper()
        result = st.validate_request(request)
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_CASE_PAYLOAD_HASH_INVALID" for b in result.blockers
        )

    def test_case_authority_domain_snapshot_hash_invalid_blocked(self) -> None:
        request = _make_request()
        request["case_authority"] = dict(VALID_CASE_AUTHORITY)
        request["case_authority"]["domain_snapshot_hash"] = "x" * 63
        result = st.validate_request(request)
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_CASE_DOMAIN_SNAPSHOT_HASH_INVALID"
            for b in result.blockers
        )

    @pytest.mark.parametrize(
        "status_value",
        ["draft", "validated", "tombstoned", "rejected"],
    )
    def test_case_authority_status_outside_acceptance_subset_blocked(
        self, status_value: str
    ) -> None:
        request = _make_request()
        request["case_authority"] = dict(VALID_CASE_AUTHORITY)
        request["case_authority"]["status"] = status_value
        result = st.validate_request(request)
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_CASE_REVISION_STATUS_BLOCKED" for b in result.blockers
        )

    @pytest.mark.parametrize(
        "status_value", ["committed", "superseded", "archived"]
    )
    def test_case_authority_status_accepted(
        self, status_value: str
    ) -> None:
        request = _make_request()
        request["case_authority"] = dict(VALID_CASE_AUTHORITY)
        request["case_authority"]["status"] = status_value
        result = st.validate_request(request)
        assert result.status.value == "VALID"


class TestEquipmentAndAuthority:
    def test_equipment_family_wrong_value_blocked(self) -> None:
        result = st.validate_request(_make_request(equipment_family="PLATE"))
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_EQUIPMENT_FAMILY_INVALID" for b in result.blockers
        )

    def test_authority_mode_invalid_blocked(self) -> None:
        result = st.validate_request(_make_request(authority_mode="BOGUS"))
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_AUTHORITY_MODE_INVALID" for b in result.blockers
        )

    def test_construction_family_invalid_blocked(self) -> None:
        result = st.validate_request(
            _make_request(construction_family="UNKNOWN")
        )
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_CONSTRUCTION_FAMILY_INVALID" for b in result.blockers
        )

    def test_orientation_invalid_blocked(self) -> None:
        result = st.validate_request(_make_request(orientation="DIAGONAL"))
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_ORIENTATION_INVALID" for b in result.blockers
        )

    def test_orientation_unspecified_accepted(self) -> None:
        result = st.validate_request(_make_request(orientation="UNSPECIFIED"))
        assert result.status.value == "VALID"

    @pytest.mark.parametrize("field", ["shell_pass_count", "tube_pass_count"])
    @pytest.mark.parametrize("bad_value", [0, -1])
    def test_pass_count_invalid_blocked(
        self, field: str, bad_value: int
    ) -> None:
        result = st.validate_request(_make_request(**{field: bad_value}))
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_PASS_COUNT_INVALID" for b in result.blockers
        )

    def test_approved_rule_pack_mode_emits_fail_closed_blocker(self) -> None:
        request = _make_request(
            authority_mode="APPROVED_RULE_PACK",
            standard_system_id="TEMA",
            requested_rule_pack_identity={
                "rule_pack_id": "rp1",
                "rule_pack_version": "v1",
                "rule_pack_canonical_hash": SHA_RULE_PACK,
            },
        )
        result = st.validate_request(request)
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_RULE_PACK_REQUIRED" for b in result.blockers
        )
        # Per §10.1: a blocked validation returns no configuration.
        assert result.configuration is None

    def test_approved_rule_pack_mode_without_requested_identity_blocked(
        self,
    ) -> None:
        # Per §8.3, APPROVED_RULE_PACK requires a non-null
        # requested_rule_pack_identity; this is enforced before
        # Slice A's STC_RULE_PACK_REQUIRED.
        request = _make_request(
            authority_mode="APPROVED_RULE_PACK",
            standard_system_id="TEMA",
            requested_rule_pack_identity=None,
        )
        result = st.validate_request(request)
        assert result.status.value == "BLOCKED"


class TestStructuralTokens:
    def test_token_normalized_to_uppercase(self) -> None:
        result = st.validate_request(
            _make_request(front_head_token="front", shell_token="shell")
        )
        assert result.status.value == "VALID"
        assert result.configuration is not None
        assert result.configuration.component_tokens.front_head == "FRONT"
        assert result.configuration.component_tokens.shell == "SHELL"

    def test_token_whitespace_trimmed(self) -> None:
        result = st.validate_request(_make_request(front_head_token="  TRIM  "))
        assert result.status.value == "VALID"
        assert result.configuration is not None
        assert result.configuration.component_tokens.front_head == "TRIM"

    def test_token_too_long_blocked(self) -> None:
        result = st.validate_request(_make_request(shell_token="X" * 17))
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_TOKEN_MALFORMED" for b in result.blockers)

    def test_token_invalid_start_character_blocked(self) -> None:
        # Token must start with [A-Z0-9]; a leading dot is invalid.
        result = st.validate_request(_make_request(front_head_token=".BAD"))
        assert result.status.value == "BLOCKED"
        assert any(b.code == "STC_TOKEN_MALFORMED" for b in result.blockers)

    def test_token_none_accepted(self) -> None:
        result = st.validate_request(
            _make_request(front_head_token=None, shell_token=None, rear_head_token=None)
        )
        assert result.status.value == "VALID"

    def test_internal_generic_must_have_null_requested_identity(self) -> None:
        result = st.validate_request(
            _make_request(
                authority_mode="INTERNAL_GENERIC",
                requested_rule_pack_identity={
                    "rule_pack_id": "rp1",
                    "rule_pack_version": "v1",
                    "rule_pack_canonical_hash": SHA_RULE_PACK,
                },
            )
        )
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_AUTHORITY_FIELDS_INCONSISTENT" for b in result.blockers
        )

    def test_internal_generic_must_have_null_standard_system_id(self) -> None:
        result = st.validate_request(
            _make_request(
                authority_mode="INTERNAL_GENERIC",
                standard_system_id="TEMA",
            )
        )
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_AUTHORITY_FIELDS_INCONSISTENT" for b in result.blockers
        )


class TestEvidenceRefs:
    def test_evidence_refs_sorted(self) -> None:
        result = st.validate_request(
            _make_request(evidence_refs=["ref-c", "ref-a", "ref-b"])
        )
        assert result.status.value == "VALID"
        assert result.configuration is not None
        assert list(
            result.configuration.authority_binding.case_authority_evidence_refs
        ) == ["ref-a", "ref-b", "ref-c"]

    def test_evidence_refs_empty_accepted(self) -> None:
        result = st.validate_request(_make_request(evidence_refs=[]))
        assert result.status.value == "VALID"

    def test_evidence_refs_wrong_type_blocked(self) -> None:
        result = st.validate_request(_make_request(evidence_refs="not-a-list"))
        assert result.status.value == "BLOCKED"
        assert any(
            b.code == "STC_AUTHORITY_FIELDS_INCONSISTENT" for b in result.blockers
        )
