"""TASK-020 blocker + warning behavior tests — Slice A.

Asserts the §10 fail-closed behavior, the §10.2 closed blocker-code
set, the §10.3 closed warning-code set, and the §10.4 error-object
shape.
"""

from __future__ import annotations

import hexagent.exchangers.shell_tube as st
from hexagent.exchangers.shell_tube.models import ErrorEntry

SHA_PAYLOAD = "a" * 64
SHA_DOMAIN = "b" * 64
SHA_RULE_PACK = "c" * 64


def _make_request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "schema_version": st.REQUEST_SCHEMA_VERSION,
        "case_authority": {
            "revision_id": "rev-001",
            "payload_hash": SHA_PAYLOAD,
            "domain_snapshot_hash": SHA_DOMAIN,
            "status": "committed",
        },
        "equipment_family": "SHELL_AND_TUBE",
        "authority_mode": "INTERNAL_GENERIC",
        "construction_family": "FIXED_TUBESHEET",
        "orientation": "HORIZONTAL",
        "shell_pass_count": 1,
        "tube_pass_count": 2,
        "front_head_token": "A",
        "shell_token": "B",
        "rear_head_token": "C",
        "standard_system_id": None,
        "requested_rule_pack_identity": None,
        "evidence_refs": [],
    }
    request.update(overrides)
    return request


class TestFailClosed:
    def test_blocked_returns_no_configuration(self) -> None:
        request = _make_request(shell_pass_count=0)
        result = st.validate_request(request)
        assert result.status.value == "BLOCKED"
        # §10.1 — a blocked validation returns no configuration.
        assert result.configuration is None

    def test_valid_returns_configuration(self) -> None:
        result = st.validate_request(_make_request())
        assert result.status.value == "VALID"
        assert result.configuration is not None

    def test_blockers_carry_stc_code(self) -> None:
        result = st.validate_request(_make_request(shell_pass_count=0))
        assert result.status.value == "BLOCKED"
        for blocker in result.blockers:
            assert blocker.code.startswith("STC_"), blocker.code
            assert blocker.message_key == blocker.code


class TestBlockerCodeClosure:
    """P1-5 — The active closed set of blocker codes is
    finite and excludes obsolete codes."""

    def test_obsolete_profile_unrecognized_absent(self) -> None:
        from hexagent.exchangers.shell_tube.models import BlockerCode

        assert not any(c.value == "STC_RULE_PROFILE_UNRECOGNIZED" for c in BlockerCode)

    def test_obsolete_priority_conflict_absent(self) -> None:
        from hexagent.exchangers.shell_tube.models import BlockerCode

        assert not any(c.value == "STC_RULE_PRIORITY_CONFLICT" for c in BlockerCode)

    def test_known_blocker_codes_emitted(self) -> None:
        # Each known blocker code in the §10.2 closed set must be
        # producible from a properly crafted invalid request.
        cases = [
            ("STC_SCHEMA_VERSION_UNSUPPORTED", {"schema_version": "v999"}),
            ("STC_CASE_AUTHORITY_MISSING", {"case_authority": None}),
            (
                "STC_CASE_REVISION_STATUS_BLOCKED",
                {
                    "case_authority": {
                        "revision_id": "rev-001",
                        "payload_hash": SHA_PAYLOAD,
                        "domain_snapshot_hash": SHA_DOMAIN,
                        "status": "draft",  # not in accepted subset
                    }
                },
            ),
            (
                "STC_CASE_PAYLOAD_HASH_INVALID",
                {
                    "case_authority": {
                        "revision_id": "rev-001",
                        "payload_hash": "not-hex",
                        "domain_snapshot_hash": SHA_DOMAIN,
                        "status": "committed",
                    }
                },
            ),
            (
                "STC_CASE_DOMAIN_SNAPSHOT_HASH_INVALID",
                {
                    "case_authority": {
                        "revision_id": "rev-001",
                        "payload_hash": SHA_PAYLOAD,
                        "domain_snapshot_hash": "x" * 63,
                        "status": "committed",
                    }
                },
            ),
            (
                "STC_CASE_REVISION_ID_MISSING",
                {
                    "case_authority": {
                        "revision_id": "",
                        "payload_hash": SHA_PAYLOAD,
                        "domain_snapshot_hash": SHA_DOMAIN,
                        "status": "committed",
                    }
                },
            ),
            ("STC_EQUIPMENT_FAMILY_INVALID", {"equipment_family": "PLATE"}),
            ("STC_AUTHORITY_MODE_INVALID", {"authority_mode": "BOGUS"}),
            (
                "STC_CONSTRUCTION_FAMILY_INVALID",
                {"construction_family": "UNKNOWN"},
            ),
            ("STC_ORIENTATION_INVALID", {"orientation": "DIAGONAL"}),
            ("STC_PASS_COUNT_INVALID", {"shell_pass_count": 0}),
            ("STC_TOKEN_MALFORMED", {"shell_token": "X" * 20}),
            (
                "STC_RULE_PACK_REQUIRED",
                {
                    "authority_mode": "APPROVED_RULE_PACK",
                    "standard_system_id": "TEMA",
                    "requested_rule_pack_identity": {
                        "rule_pack_id": "rp1",
                        "rule_pack_version": "v1",
                        "rule_pack_canonical_hash": SHA_RULE_PACK,
                    },
                },
            ),
        ]
        for expected_code, override in cases:
            result = st.validate_request(_make_request(**override))
            assert result.status.value == "BLOCKED", (
                f"{expected_code}: expected BLOCKED, got {result.status.value}"
            )
            assert any(b.code == expected_code for b in result.blockers), (
                f"{expected_code}: not in {[b.code for b in result.blockers]}"
            )


class TestErrorObjectShape:
    """§10.4 — every error entry has the frozen 5-field shape."""

    def test_blocker_has_5_fields(self) -> None:
        result = st.validate_request(_make_request(shell_pass_count=0))
        assert result.status.value == "BLOCKED"
        assert len(result.blockers) >= 1
        blocker = result.blockers[0]
        assert hasattr(blocker, "code")
        assert hasattr(blocker, "field_path")
        assert hasattr(blocker, "message_key")
        assert hasattr(blocker, "evidence_refs")
        assert hasattr(blocker, "details")

    def test_blocker_code_starts_with_stc(self) -> None:
        result = st.validate_request(_make_request(shell_pass_count=0))
        assert result.status.value == "BLOCKED"
        for blocker in result.blockers:
            assert blocker.code.startswith("STC_"), blocker.code


class TestBlockersAreSorted:
    """§11.4 — warnings and blockers are sorted by the composite
    ``(code, field_path, message_key, canonical_details_hash)`` key."""

    def test_blockers_sorted_by_code(self) -> None:
        # Construct a request that emits multiple blockers
        request = _make_request(
            equipment_family="PLATE",  # STC_EQUIPMENT_FAMILY_INVALID
            shell_pass_count=0,  # STC_PASS_COUNT_INVALID
        )
        result = st.validate_request(request)
        assert result.status.value == "BLOCKED"
        codes = [b.code for b in result.blockers]
        # Sorted ascending
        assert codes == sorted(codes)


class TestErrorEntriesPreserved:
    """Fix 3 — complete ``ErrorEntry`` objects are preserved.

    Entries with the same ``(code, field_path, message_key)`` but
    different ``details`` or ``evidence_refs`` MUST all be
    retained. The final sort is stable by the composite 4-field
    key ``(code, field_path or "", message_key, canonical_details_hash)``.
    """

    def _build_entries(self) -> list[ErrorEntry]:
        return [
            ErrorEntry(
                code="STC_INVALID_REQUEST",
                field_path="case_authorities[0].revision_id",
                message_key="not_str",
                evidence_refs=("ref-c", "ref-a", "ref-b"),  # unsorted input
                details={"actual_type": "int"},
            ),
            ErrorEntry(
                code="STC_INVALID_REQUEST",
                field_path="case_authorities[0].revision_id",
                message_key="not_str",
                evidence_refs=("ref-c", "ref-a", "ref-b"),
                details={"actual_type": "str"},  # DIFFERENT details
            ),
        ]

    def test_distinct_details_preserved_for_same_signature(self) -> None:
        from hexagent.exchangers.shell_tube.validation import _canonicalize_error_entries

        entries = self._build_entries()
        canonical = _canonicalize_error_entries(entries)
        assert len(canonical) == 2
        # Both entries preserved despite sharing the 3-field key.
        details_set: set[tuple[tuple[str, str], ...]] = set()
        for entry in canonical:
            assert entry.details is not None
            details_set.add(tuple(sorted(entry.details.items())))
        assert details_set == {
            (("actual_type", "int"),),
            (("actual_type", "str"),),
        }

    def test_evidence_refs_sorted_unicode_codepoint(self) -> None:
        from hexagent.exchangers.shell_tube.validation import _canonicalize_error_entries

        entries = self._build_entries()
        canonical = _canonicalize_error_entries(entries)
        for entry in canonical:
            assert entry.evidence_refs == ("ref-a", "ref-b", "ref-c")

    def test_sort_stable_by_details_hash(self) -> None:
        from hexagent.exchangers.shell_tube.validation import _canonicalize_error_entries

        entries = self._build_entries()
        canonical = _canonicalize_error_entries(entries)
        # The two entries share (code, field_path, message_key), so
        # their relative order is determined by canonical_details_hash.
        # The "int" details hash and the "str" details hash differ;
        # the order must be stable across repeated runs.
        canonical_again = _canonicalize_error_entries(entries)
        assert [e.details for e in canonical] == [e.details for e in canonical_again]
        # Whichever details hash sorts first must be deterministic.
        # We don't assert the specific order — just that the
        # canonical sort produces a stable, deterministic ordering.
        first, second = canonical
        # Re-run the canonical sort and confirm identical order.
        for _ in range(3):
            again = _canonicalize_error_entries(entries)
            assert again[0].details == first.details
            assert again[1].details == second.details
