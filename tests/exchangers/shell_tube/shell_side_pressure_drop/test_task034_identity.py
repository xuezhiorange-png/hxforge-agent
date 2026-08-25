"""Same-case and upstream identity bindings."""

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import (
    TYPED_BLOCKED_RESULT_FIELDS,
)
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    make_valid_raw_request,
)


def _codes(raw):
    return {item.code for item in validate_request(raw).blockers}


def test_b018_sspd_task032_result_id_mismatch():
    raw = make_valid_raw_request()
    raw["task032_result_id"] = "wrong"
    assert "SSPD_TASK032_RESULT_ID_MISMATCH" in _codes(raw)


def test_b019_sspd_task032_result_hash_mismatch():
    raw = make_valid_raw_request()
    raw["task032_result_hash"] = "0" * 64
    assert "SSPD_TASK032_RESULT_HASH_MISMATCH" in _codes(raw)


def test_b020_sspd_case_id_mismatch():
    raw = make_valid_raw_request()
    raw["shell_side_case_id"] = "wrong"
    assert "SSPD_CASE_ID_MISMATCH" in _codes(raw)


def test_b021_sspd_stream_id_mismatch():
    raw = make_valid_raw_request()
    raw["shell_side_stream_id"] = "wrong"
    assert "SSPD_STREAM_ID_MISMATCH" in _codes(raw)


def test_b022_sspd_fluid_id_mismatch():
    raw = make_valid_raw_request()
    raw["shell_side_fluid_id"] = "wrong"
    assert "SSPD_FLUID_ID_MISMATCH" in _codes(raw)


def test_b023_sspd_configuration_id_mismatch():
    raw = make_valid_raw_request()
    raw["task020_configuration_id"] = "wrong"
    assert "SSPD_CONFIGURATION_ID_MISMATCH" in _codes(raw)


def test_b024_sspd_property_snapshot_hash_mismatch():
    raw = make_valid_raw_request()
    raw["property_snapshot_hash"] = "0" * 64
    assert "SSPD_PROPERTY_SNAPSHOT_HASH_MISMATCH" in _codes(raw)


def test_b025_sspd_mass_flow_authority_hash_mismatch():
    raw = make_valid_raw_request()
    raw["mass_flow_authority_hash"] = "0" * 64
    assert "SSPD_MASS_FLOW_AUTHORITY_HASH_MISMATCH" in _codes(raw)


def test_b026_sspd_wall_property_authority_missing():
    raw = make_valid_raw_request()
    raw["wall_property_authority_hash"] = None
    assert "SSPD_WALL_PROPERTY_AUTHORITY_MISSING" in _codes(raw)


def test_b027_sspd_wall_property_authority_mismatch():
    raw = make_valid_raw_request()
    raw["wall_property_authority_hash"] = "0" * 64
    assert "SSPD_WALL_PROPERTY_AUTHORITY_MISMATCH" in _codes(raw)


def test_b028_sspd_wall_viscosity_invalid():
    raw = make_valid_raw_request()
    raw["shell_side_wall_dynamic_viscosity_pa_s"] = "0"
    assert "SSPD_WALL_VISCOSITY_INVALID" in _codes(raw)


def test_x002_typed_blocked_schema_identity_repeatability():
    raw = make_valid_raw_request()
    raw["shell_side_case_id"] = "wrong"
    first = validate_request(raw)
    second = validate_request(raw)
    assert first.blocked_result is not None and second.blocked_result is not None
    assert first.blocked_result.blocked_result_hash == second.blocked_result.blocked_result_hash


def test_x008_typed_blocked_hash_self_exclusion():
    assert "blocked_result_hash" not in tuple(
        field for field in TYPED_BLOCKED_RESULT_FIELDS if field != "blocked_result_hash"
    )
