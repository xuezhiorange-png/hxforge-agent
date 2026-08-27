"""Frozen raw-boundary blocker reachability and eight-field identity."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.blocker_registry import BLOCKER_CODES
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import (
    RAW_BOUNDARY_BLOCKED_RESULT_FIELDS,
)
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    make_valid_raw_request,
)


def _codes(value):
    return {item.code for item in validate_request(value).blockers}


def test_b001_sspd_raw_request_type_invalid():
    assert "SSPD_RAW_REQUEST_TYPE_INVALID" in _codes(None)


def test_b002_sspd_raw_binary_float_forbidden():
    raw = make_valid_raw_request()
    raw["baffle_count"] = 1.0
    assert "SSPD_RAW_BINARY_FLOAT_FORBIDDEN" in _codes(raw)


def test_b003_sspd_raw_unsupported_primitive():
    raw = make_valid_raw_request()
    raw["evidence_refs"] = {"unsupported"}
    assert "SSPD_RAW_UNSUPPORTED_PRIMITIVE" in _codes(raw)


def test_b004_sspd_raw_canonicalization_failure():
    raw = make_valid_raw_request()
    raw[1] = "non-string-key"
    assert "SSPD_RAW_CANONICALIZATION_FAILURE" in _codes(raw)


def test_x003_raw_blocked_projection_identity():
    first = validate_request(None).raw_boundary_blocked_result
    second = validate_request(None).raw_boundary_blocked_result
    assert first is not None and second is not None
    assert first.blocked_result_hash == second.blocked_result_hash


def test_x009_raw_blocked_hash_self_exclusion():
    assert "blocked_result_hash" not in (
        "schema_version",
        "profile_id",
        "request_hash",
        "blockers",
        "warnings",
        "deferred_capabilities",
        "raw_projection",
    )
    assert len(RAW_BOUNDARY_BLOCKED_RESULT_FIELDS) == 8


def test_x012_raw_boundary_8_field_schema():
    assert tuple(RAW_BOUNDARY_BLOCKED_RESULT_FIELDS) == (
        "schema_version",
        "profile_id",
        "request_hash",
        "blocked_result_hash",
        "blockers",
        "warnings",
        "deferred_capabilities",
        "raw_projection",
    )
    assert len(BLOCKER_CODES) == 58
