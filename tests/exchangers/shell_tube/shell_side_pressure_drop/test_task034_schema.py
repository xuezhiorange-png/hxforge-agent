"""Frozen request schema boundary tests."""

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    make_valid_raw_request,
)


def test_b005_sspd_unknown_request_field():
    raw = make_valid_raw_request()
    raw["unknown"] = "x"
    assert "SSPD_UNKNOWN_REQUEST_FIELD" in {b.code for b in validate_request(raw).blockers}


def test_b006_sspd_request_schema_mismatch():
    raw = make_valid_raw_request()
    raw["schema_version"] = "wrong"
    assert "SSPD_REQUEST_SCHEMA_MISMATCH" in {b.code for b in validate_request(raw).blockers}


def test_b007_sspd_profile_id_mismatch():
    raw = make_valid_raw_request()
    raw["profile_id"] = "wrong"
    assert "SSPD_PROFILE_ID_MISMATCH" in {b.code for b in validate_request(raw).blockers}


def test_b058_sspd_shell_type_authority_required_field_missing():
    raw = make_valid_raw_request()
    raw.pop("shell_type_authority")
    result = validate_request(raw)
    assert result.status.value == "BLOCKED"
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S02"
    assert [blocker.code for blocker in result.blocked_result.blockers] == [
        "SSPD_SHELL_TYPE_AUTHORITY_REQUIRED_FIELD_MISSING"
    ]
    assert "shell_type_authority" not in raw
