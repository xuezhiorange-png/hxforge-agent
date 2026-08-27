"""TASK-031/032/033 accepted-evidence replay blockers."""

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.canonical import (
    task033_result_hash,
    task033_result_id,
)
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    make_valid_raw_request,
)


def _codes(raw):
    return {item.code for item in validate_request(raw).blockers}


def _single_blocker(raw):
    result = validate_request(raw)
    assert result.status == "BLOCKED"
    assert result.blocked_result is not None
    assert len(result.blocked_result.blockers) == 1
    return result.blocked_result.blockers[0], result.blocked_result.failure_stage


def _refresh_task033_result_identity(raw, field, value):
    result = raw["task033_upstream_evidence"]["task033_validation_result"]["heat_transfer"]
    result[field] = value
    result_hash = task033_result_hash(result)
    result["result_hash"] = result_hash
    result["result_id"] = task033_result_id(result_hash)
    raw["task033_result_hash"] = result_hash
    raw["task033_result_id"] = result["result_id"]
    return raw


def _assert_only_identity_blocker(raw, expected_code, expected_stage):
    blocker, stage = _single_blocker(raw)
    assert blocker.code == expected_code
    assert stage == expected_stage
    assert blocker.code not in {
        "SSPD_TASK033_RESULT_ID_MISMATCH",
        "SSPD_TASK033_RESULT_HASH_MISMATCH",
        "SSPD_TASK032_RESULT_ID_MISMATCH",
        "SSPD_TASK032_RESULT_HASH_MISMATCH",
    }


def test_b008_sspd_source_authority_mismatch():
    raw = make_valid_raw_request()
    raw["task033_upstream_evidence"]["task033_validation_result"]["heat_transfer"][
        "engineering_source_authority_record_id"
    ] = "wrong"
    assert "SSPD_SOURCE_AUTHORITY_MISMATCH" in _codes(raw)


def test_b009_sspd_task033_upstream_missing():
    raw = make_valid_raw_request()
    raw["task033_upstream_evidence"] = None
    assert "SSPD_TASK033_UPSTREAM_MISSING" in _codes(raw)


def test_b010_sspd_task033_upstream_invalid():
    raw = make_valid_raw_request()
    raw["task033_upstream_evidence"]["task033_validation_result"]["status"] = "BLOCKED"
    assert "SSPD_TASK033_UPSTREAM_INVALID" in _codes(raw)


def test_task033_status_missing_blocks_at_s03():
    raw = make_valid_raw_request()
    raw["task033_upstream_evidence"]["task033_validation_result"].pop("status")
    blocker, stage = _single_blocker(raw)
    assert blocker.code == "SSPD_TASK033_UPSTREAM_INVALID"
    assert stage == "S03"


def test_task033_source_authority_missing_blocks_at_s03():
    raw = make_valid_raw_request()
    raw["task033_upstream_evidence"]["task033_validation_result"]["heat_transfer"].pop(
        "engineering_source_authority_record_id"
    )
    blocker, stage = _single_blocker(raw)
    assert blocker.code == "SSPD_SOURCE_AUTHORITY_MISMATCH"
    assert stage == "S03"


def test_b011_sspd_task033_request_hash_mismatch():
    raw = make_valid_raw_request()
    raw["task033_request_hash"] = "0" * 64
    assert "SSPD_TASK033_REQUEST_HASH_MISMATCH" in _codes(raw)


def test_b011_rejects_task033_result_request_hash_join_mismatch():
    raw = make_valid_raw_request()
    original_request_hash = raw["task033_request_hash"]
    _refresh_task033_result_identity(raw, "request_hash", "f" * 64)
    assert raw["task033_request_hash"] == original_request_hash
    _assert_only_identity_blocker(raw, "SSPD_TASK033_REQUEST_HASH_MISMATCH", "S05")


def test_b012_sspd_task033_result_id_mismatch():
    raw = make_valid_raw_request()
    raw["task033_result_id"] = "0" * 36
    assert "SSPD_TASK033_RESULT_ID_MISMATCH" in _codes(raw)


def test_b013_sspd_task033_result_hash_mismatch():
    raw = make_valid_raw_request()
    raw["task033_result_hash"] = "0" * 64
    assert "SSPD_TASK033_RESULT_HASH_MISMATCH" in _codes(raw)


def test_b014_sspd_task031_request_evidence_missing():
    raw = make_valid_raw_request()
    raw["task031_request_evidence"] = None
    assert "SSPD_TASK031_REQUEST_EVIDENCE_MISSING" in _codes(raw)


def test_b015_sspd_task031_request_hash_mismatch():
    raw = make_valid_raw_request()
    raw["task031_request_hash"] = "0" * 64
    assert "SSPD_TASK031_REQUEST_HASH_MISMATCH" in _codes(raw)


def test_b016_sspd_task031_geometry_id_mismatch():
    raw = make_valid_raw_request()
    raw["task031_geometry_id"] = "wrong"
    assert "SSPD_TASK031_GEOMETRY_ID_MISMATCH" in _codes(raw)


def test_b017_sspd_task031_geometry_hash_mismatch():
    raw = make_valid_raw_request()
    raw["task031_geometry_hash"] = "0" * 64
    assert "SSPD_TASK031_GEOMETRY_HASH_MISMATCH" in _codes(raw)


def test_b016_rejects_task033_result_geometry_id_join_mismatch():
    raw = make_valid_raw_request()
    _refresh_task033_result_identity(
        raw, "task031_geometry_id", "00000000-0000-5000-8000-000000000001"
    )
    _assert_only_identity_blocker(raw, "SSPD_TASK031_GEOMETRY_ID_MISMATCH", "S07")


def test_b017_rejects_task033_result_geometry_hash_join_mismatch():
    raw = make_valid_raw_request()
    _refresh_task033_result_identity(raw, "task031_geometry_hash", "e" * 64)
    _assert_only_identity_blocker(raw, "SSPD_TASK031_GEOMETRY_HASH_MISMATCH", "S07")
