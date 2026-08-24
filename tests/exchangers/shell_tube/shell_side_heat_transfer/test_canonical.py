"""TASK033 canonical kind-tag and namespace closure tests."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_heat_transfer import canonical


def test_kind_tags_are_frozen() -> None:
    assert {
        canonical.NULL_KIND,
        canonical.BOOL_KIND,
        canonical.INTEGER_KIND,
        canonical.STRING_KIND,
        canonical.DECIMAL_KIND,
        canonical.STRING_TUPLE_KIND,
        canonical.STRING_MAPPING_KIND,
        canonical.PROPERTY_SNAPSHOT_KIND,
        canonical.MASS_FLOW_AUTHORITY_KIND,
        canonical.TASK031_RESULT_KIND,
        canonical.BLOCKER_TUPLE_KIND,
        canonical.BLOCKER_ENTRY_KIND,
        canonical.TASK032_FLOW_STATE_KIND,
        canonical.TASK032_REQUEST_EVIDENCE_KIND,
        canonical.PROVENANCE_KIND,
    } == {b"n", b"b", b"i", b"s", b"d", b"t", b"m", b"p", b"a", b"h", b"k", b"c", b"f", b"q", b"v"}


def test_hash_namespaces_are_distinct() -> None:
    values = {
        canonical.REQUEST_HASH_NAMESPACE,
        canonical.SUCCESS_RESULT_HASH_NAMESPACE,
        canonical.TYPED_BLOCKED_RESULT_HASH_NAMESPACE,
        canonical.RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE,
        canonical.PROVENANCE_HASH_NAMESPACE,
        canonical.RAW_PROJECTION_HASH_NAMESPACE,
    }
    assert len(values) == 6
