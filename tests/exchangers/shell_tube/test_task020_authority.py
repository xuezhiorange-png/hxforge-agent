"""TASK-020 authority binding tests — Slice A.

Asserts the §6.3 / §7.3 / §7.5 authority contract. Tests do NOT load
any rule pack; rule-pack loading is Slice B.
"""

from __future__ import annotations

import dataclasses

import pytest

from hexagent.exchangers.shell_tube.authority import (
    bind_request_to_configuration_authority,
    finalize_selected_rule_authority,
    from_case_revision_payload,
    from_requested_rule_pack_identity,
    is_valid_sha256_hex,
    is_valid_structural_token,
    sorted_selected_rule_authorities,
)
from hexagent.exchangers.shell_tube.errors import BlockerError
from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    CaseRevisionStatus,
    SelectedRuleAuthority,
)

SHA_PAYLOAD = "a" * 64
SHA_DOMAIN = "b" * 64
SHA_RULE_PACK = "c" * 64


class TestSha256Hex:
    def test_valid_64_lowercase_hex(self) -> None:
        assert is_valid_sha256_hex("a" * 64) is True

    def test_rejects_63_chars(self) -> None:
        assert is_valid_sha256_hex("a" * 63) is False

    def test_rejects_65_chars(self) -> None:
        assert is_valid_sha256_hex("a" * 65) is False

    def test_rejects_uppercase(self) -> None:
        assert is_valid_sha256_hex("A" * 64) is False

    def test_rejects_non_string(self) -> None:
        assert is_valid_sha256_hex(123) is False  # type: ignore[arg-type]
        assert is_valid_sha256_hex(None) is False  # type: ignore[arg-type]


class TestStructuralToken:
    def test_valid_token(self) -> None:
        assert is_valid_structural_token("ABC") is True
        assert is_valid_structural_token("A1B2C3") is True
        assert is_valid_structural_token("A.B_C-D") is True

    def test_too_long_token(self) -> None:
        assert is_valid_structural_token("X" * 17) is False

    def test_too_long_16_chars_max(self) -> None:
        # §8.2: ``[A-Z0-9._-]{0,15}`` ⇒ max 16 characters total.
        assert is_valid_structural_token("X" * 16) is True

    def test_lowercase_rejected(self) -> None:
        # The core schema does not interpret lowercase tokens; the
        # pattern requires uppercase only.
        assert is_valid_structural_token("abc") is False

    def test_empty_token_rejected(self) -> None:
        assert is_valid_structural_token("") is False


class TestCaseRevisionAuthorityFactory:
    def test_valid_constructs(self) -> None:
        cra = from_case_revision_payload(
            revision_id="rev-001",
            payload_hash=SHA_PAYLOAD,
            domain_snapshot_hash=SHA_DOMAIN,
            status="committed",
        )
        assert cra.revision_id == "rev-001"
        assert cra.revision_status == CaseRevisionStatus.COMMITTED

    def test_empty_revision_id_raises(self) -> None:
        with pytest.raises(BlockerError) as exc_info:
            from_case_revision_payload(
                revision_id="",
                payload_hash=SHA_PAYLOAD,
                domain_snapshot_hash=SHA_DOMAIN,
                status="committed",
            )
        assert exc_info.value.code == "STC_CASE_REVISION_ID_MISSING"

    def test_invalid_payload_hash_raises(self) -> None:
        with pytest.raises(BlockerError) as exc_info:
            from_case_revision_payload(
                revision_id="rev-001",
                payload_hash="not-hex",
                domain_snapshot_hash=SHA_DOMAIN,
                status="committed",
            )
        assert exc_info.value.code == "STC_CASE_PAYLOAD_HASH_INVALID"

    def test_invalid_domain_snapshot_hash_raises(self) -> None:
        with pytest.raises(BlockerError) as exc_info:
            from_case_revision_payload(
                revision_id="rev-001",
                payload_hash=SHA_PAYLOAD,
                domain_snapshot_hash="tooshort",
                status="committed",
            )
        assert exc_info.value.code == "STC_CASE_DOMAIN_SNAPSHOT_HASH_INVALID"

    def test_status_outside_acceptance_subset_raises(self) -> None:
        with pytest.raises(BlockerError) as exc_info:
            from_case_revision_payload(
                revision_id="rev-001",
                payload_hash=SHA_PAYLOAD,
                domain_snapshot_hash=SHA_DOMAIN,
                status="draft",
            )
        assert exc_info.value.code == "STC_CASE_REVISION_STATUS_BLOCKED"

    @pytest.mark.parametrize("status_value", ["committed", "superseded", "archived"])
    def test_status_in_acceptance_subset_accepted(self, status_value: str) -> None:
        from_case_revision_payload(
            revision_id="rev-001",
            payload_hash=SHA_PAYLOAD,
            domain_snapshot_hash=SHA_DOMAIN,
            status=status_value,
        )


class TestRequestedRulePackIdentityFactory:
    def test_valid_constructs(self) -> None:
        rrpi = from_requested_rule_pack_identity(
            rule_pack_id="rp1",
            rule_pack_version="v1",
            rule_pack_canonical_hash=SHA_RULE_PACK,
        )
        assert rrpi.rule_pack_id == "rp1"
        assert rrpi.rule_pack_version == "v1"
        assert rrpi.rule_pack_canonical_hash == SHA_RULE_PACK

    def test_empty_rule_pack_id_raises(self) -> None:
        with pytest.raises(BlockerError):
            from_requested_rule_pack_identity(
                rule_pack_id="",
                rule_pack_version="v1",
                rule_pack_canonical_hash=SHA_RULE_PACK,
            )

    def test_invalid_canonical_hash_raises(self) -> None:
        with pytest.raises(BlockerError) as exc_info:
            from_requested_rule_pack_identity(
                rule_pack_id="rp1",
                rule_pack_version="v1",
                rule_pack_canonical_hash="not-hex",
            )
        assert exc_info.value.code == "STC_RULE_PACK_CANONICAL_HASH_MISMATCH"


class TestConfigurationAuthorityBinding:
    def test_internal_generic_binding_has_null_rpa(self) -> None:
        cra = from_case_revision_payload(
            revision_id="rev-001",
            payload_hash=SHA_PAYLOAD,
            domain_snapshot_hash=SHA_DOMAIN,
            status="committed",
        )
        binding = bind_request_to_configuration_authority(
            request_authority_mode=AuthorityMode.INTERNAL_GENERIC,
            case_authority=cra,
            standard_system_id=None,
            evaluated_rule_pack_authority=None,
        )
        assert binding.authority_mode == AuthorityMode.INTERNAL_GENERIC
        assert binding.standard_system_id is None
        assert binding.evaluated_rule_pack_authority is None
        assert binding.case_authority is cra

    def test_binding_is_frozen(self) -> None:
        cra = from_case_revision_payload(
            revision_id="rev-001",
            payload_hash=SHA_PAYLOAD,
            domain_snapshot_hash=SHA_DOMAIN,
            status="committed",
        )
        binding = bind_request_to_configuration_authority(
            request_authority_mode=AuthorityMode.INTERNAL_GENERIC,
            case_authority=cra,
            standard_system_id=None,
            evaluated_rule_pack_authority=None,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            binding.authority_mode = AuthorityMode.APPROVED_RULE_PACK  # type: ignore[misc]


class TestSelectedRuleAuthorityFinalize:
    def test_finalize_sorts_evidence_refs(self) -> None:
        sra = SelectedRuleAuthority(
            rule_id="r1",
            rule_version="v1",
            rule_artifact_canonical_hash=SHA_RULE_PACK,
            source_class="STANDARD",
            license_evidence=None,
            approval_status="approved",
            evidence_refs=("ref-c", "ref-a", "ref-b"),
        )
        finalized = finalize_selected_rule_authority(sra)
        assert finalized.evidence_refs == ("ref-a", "ref-b", "ref-c")

    def test_finalize_sorts_provenance_edge_ids(self) -> None:
        sra = SelectedRuleAuthority(
            rule_id="r1",
            rule_version="v1",
            rule_artifact_canonical_hash=SHA_RULE_PACK,
            source_class="STANDARD",
            license_evidence=None,
            approval_status="approved",
            provenance_edge_ids=("edge-c", "edge-a", "edge-b"),
        )
        finalized = finalize_selected_rule_authority(sra)
        assert finalized.provenance_edge_ids == ("edge-a", "edge-b", "edge-c")

    def test_finalize_dedups(self) -> None:
        sra = SelectedRuleAuthority(
            rule_id="r1",
            rule_version="v1",
            rule_artifact_canonical_hash=SHA_RULE_PACK,
            source_class="STANDARD",
            license_evidence=None,
            approval_status="approved",
            evidence_refs=("ref-a", "ref-a", "ref-b", "ref-b"),
        )
        finalized = finalize_selected_rule_authority(sra)
        assert finalized.evidence_refs == ("ref-a", "ref-b")


class TestSortSelectedRuleAuthorities:
    def test_sort_by_full_key(self) -> None:
        items = [
            SelectedRuleAuthority(
                rule_id="r2",
                rule_version="v1",
                rule_artifact_canonical_hash=SHA_RULE_PACK,
                source_class="STANDARD",
                license_evidence=None,
                approval_status="approved",
            ),
            SelectedRuleAuthority(
                rule_id="r1",
                rule_version="v1",
                rule_artifact_canonical_hash=SHA_RULE_PACK,
                source_class="STANDARD",
                license_evidence=None,
                approval_status="approved",
            ),
        ]
        sorted_items = sorted_selected_rule_authorities(items)
        assert [s.rule_id for s in sorted_items] == ["r1", "r2"]

    def test_sort_by_rule_artifact_canonical_hash_when_rule_id_same(self) -> None:
        items = [
            SelectedRuleAuthority(
                rule_id="r1",
                rule_version="v1",
                rule_artifact_canonical_hash="f" * 64,
                source_class="STANDARD",
                license_evidence=None,
                approval_status="approved",
            ),
            SelectedRuleAuthority(
                rule_id="r1",
                rule_version="v1",
                rule_artifact_canonical_hash="a" * 64,
                source_class="STANDARD",
                license_evidence=None,
                approval_status="approved",
            ),
        ]
        sorted_items = sorted_selected_rule_authorities(items)
        assert sorted_items[0].rule_artifact_canonical_hash == "a" * 64
        assert sorted_items[1].rule_artifact_canonical_hash == "f" * 64


class TestNoRulePackLoading:
    """P1-1 — TASK-020 Slice A does NOT load or evaluate rule packs."""

    def test_authority_module_does_not_import_rule_packs(self) -> None:
        # The authority module is a read-only value-object factory.
        # It must not import the TASK-012 rule_packs package.
        import hexagent.exchangers.shell_tube.authority as auth

        # Search the module's source for any ``from hexagent.rule_packs``
        # import; this is a structural test, not a behavioral one.
        source_path = auth.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as fh:
            source = fh.read()
        assert "hexagent.rule_packs" not in source
        assert "from hexagent.rule_packs" not in source
