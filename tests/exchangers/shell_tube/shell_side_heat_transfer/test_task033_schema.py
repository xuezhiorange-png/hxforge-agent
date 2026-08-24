"""TASK033 raw boundary schema tests."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_heat_transfer import validate_request
from tests.exchangers.shell_tube.shell_side_heat_transfer.test_task033_models import copy_request


def test_raw_request_rejects_mapping_like_boundary() -> None:
    """T033-001_RAW_TYPE_INVALID."""

    class DictSubclass(dict[str, object]):
        pass

    result = validate_request(DictSubclass(copy_request()))
    assert result.blocked_result is None
    assert result.raw_boundary_blocked_result is not None
    assert result.blockers[0].code == "SSHT_RAW_TYPE_INVALID"


def test_nested_envelopes_are_not_partial() -> None:
    """T033-002_REQUIRED_FIELD_MISSING."""
    raw = copy_request()
    del raw["task032_flow_state"]["shell_side_prandtl_number"]
    result = validate_request(raw)
    assert result.heat_transfer is None
    assert result.blockers
    assert result.blockers[0].code in {"SSHT_RAW_TYPE_INVALID", "SSHT_TASK032_FLOW_STATE_INVALID"}


def test_unknown_top_level_field_is_rejected() -> None:
    """T033-003_UNKNOWN_FIELD_REJECTED."""
    raw = copy_request()
    raw["unknown"] = 1
    result = validate_request(raw)
    assert result.heat_transfer is None
    assert any(item.code == "SSHT_UNKNOWN_FIELD" for item in result.blockers)


def test_schema_and_profile_are_exact() -> None:
    """T033-004_SCHEMA_VERSION_MISMATCH and T033-005_PROFILE_ID_MISMATCH."""
    raw = copy_request()
    raw["schema_version"] = "wrong"
    assert validate_request(raw).blockers[0].code == "SSHT_SCHEMA_VERSION_UNSUPPORTED"
    raw = copy_request()
    raw["profile_id"] = "wrong"
    assert validate_request(raw).blockers[0].code == "SSHT_PROFILE_ID_UNSUPPORTED"
