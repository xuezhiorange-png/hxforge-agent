"""§A11-A14 — Disposition tests."""

from __future__ import annotations

import hexagent.exchangers.shell_tube.tube_side as ts


def test_a11_supported_profile_ids() -> None:
    assert ts.SUPPORTED_PROFILE_IDS == ("profile-001",)


def test_a11_supported_software_version() -> None:
    assert ts.SUPPORTED_SOFTWARE_VERSION == ("0.1.0",)


def test_a12_blockers_tuple_is_empty_in_blocked_results() -> None:
    """§A12 / §6.3 — blocked result blockers is a tuple; warnings is ()."""
    result = ts.evaluate_task025(None)
    assert isinstance(result, ts.Task025BlockedResult)
    assert isinstance(result.blockers, tuple)
    assert result.warnings == ()


def test_a13_software_version_carried_into_blocked() -> None:
    result = ts.evaluate_task025(None)
    assert result.implementation_software_version == "0.1.0"


def test_a14_valid_result_is_task025owned_typed() -> None:
    """§A14 — Task025ValidResult / Task025BlockedResult are the only result types."""
    assert ts.Task025ValidResult is not None
    assert ts.Task025BlockedResult is not None


def test_a14_blocked_result_requires_non_dict_token() -> None:
    """§4.2 — the non-dict branch uses the frozen token."""
    expected = b"task025.top-level-not-exact-dict.v1"
    assert expected == ts.TOP_LEVEL_NOT_EXACT_DICT_TOKEN


def test_a14_deferred_capabilities_v1_tuple() -> None:
    assert isinstance(ts.DEFERRED_CAPABILITIES_V1, tuple)
    assert len(ts.DEFERRED_CAPABILITIES_V1) >= 1
    assert "PRESSURE_DROP_NOT_COMPUTABLE" in ts.DEFERRED_CAPABILITIES_V1


def test_a14_request_fields_tuple_count() -> None:
    assert len(ts.TASK025_REQUEST_FIELDS) == 10


def test_a14_valid_result_fields_tuple_count() -> None:
    assert len(ts.TASK025_VALID_RESULT_FIELDS) == 27


def test_a14_blocked_result_fields_tuple_count() -> None:
    assert len(ts.TASK025_BLOCKED_RESULT_FIELDS) == 14


def test_a14_blocked_hash_fields_tuple_count() -> None:
    # §6.4 — 12 fields; provenance excluded, blocked_result_hash itself excluded.
    assert len(ts.BLOCKED_RESULT_HASH_FIELDS) == 12