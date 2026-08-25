"""Same-case and upstream identity bindings."""

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import authority as authority_module
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validation as validation_module
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.canonical import task033_request_hash
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import (
    TYPED_BLOCKED_RESULT_FIELDS,
)
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    make_valid_raw_request,
)


def _codes(raw):
    return {item.code for item in validate_request(raw).blockers}


def _first_blocker(raw):
    result = validate_request(raw)
    assert result.status == "BLOCKED"
    assert result.blocked_result is not None
    assert len(result.blocked_result.blockers) == 1
    return result.blocked_result.blockers[0], result.blocked_result.failure_stage


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


def test_precedence_case_a_s04_precedes_s05():
    raw = make_valid_raw_request()
    raw["task033_result_hash"] = "0" * 64
    raw["task033_request_hash"] = "1" * 64
    blocker, stage = _first_blocker(raw)
    assert blocker.code == "SSPD_TASK033_RESULT_HASH_MISMATCH"
    assert stage == "S04"


def test_precedence_case_b_s05_precedes_s06():
    raw = make_valid_raw_request()
    raw["task033_request_hash"] = "0" * 64
    raw["task031_request_hash"] = "1" * 64
    blocker, stage = _first_blocker(raw)
    assert blocker.code == "SSPD_TASK033_REQUEST_HASH_MISMATCH"
    assert stage == "S05"


def test_precedence_case_c_s06_precedes_s07():
    raw = make_valid_raw_request()
    raw["task031_request_hash"] = "0" * 64
    raw["task031_geometry_hash"] = "1" * 64
    blocker, stage = _first_blocker(raw)
    assert blocker.code == "SSPD_TASK031_REQUEST_HASH_MISMATCH"
    assert stage == "S06"


def test_precedence_case_d_s07_precedes_s08():
    raw = make_valid_raw_request()
    raw["task031_geometry_hash"] = "0" * 64
    raw["shell_inside_diameter_m"] = "1.201"
    blocker, stage = _first_blocker(raw)
    assert blocker.code == "SSPD_TASK031_GEOMETRY_HASH_MISMATCH"
    assert stage == "S07"


def test_precedence_case_e_s08_precedes_s09():
    raw = make_valid_raw_request()
    raw["shell_inside_diameter_m"] = "1.201"
    raw["wall_property_authority_hash"] = "0" * 64
    blocker, stage = _first_blocker(raw)
    assert blocker.code == "SSPD_SHELL_INSIDE_DIAMETER_MISMATCH"
    assert stage == "S08"


def test_precedence_case_f_s09_precedes_s10():
    raw = make_valid_raw_request()
    raw["wall_property_authority_hash"] = "0" * 64
    raw["shell_side_case_id"] = "wrong"
    blocker, stage = _first_blocker(raw)
    assert blocker.code == "SSPD_WALL_PROPERTY_AUTHORITY_MISMATCH"
    assert stage == "S09"


def test_precedence_case_g_s10_precedes_s11():
    raw = make_valid_raw_request()
    raw["shell_side_case_id"] = "wrong"
    raw["task033_upstream_evidence"]["task032_flow_state"]["phase_region"] = "SINGLE_PHASE_GAS"
    raw["task033_request_hash"] = task033_request_hash(raw["task033_upstream_evidence"])
    blocker, stage = _first_blocker(raw)
    assert blocker.code == "SSPD_CASE_ID_MISMATCH"
    assert stage == "S10"


def _s05_request_identity_with_upstream_fault(field: str):
    raw = make_valid_raw_request()
    flow = raw["task033_upstream_evidence"]["task032_flow_state"]
    if field in {"phase_region", "rheology_model"}:
        flow.pop(field)
    elif field == "reynolds":
        flow["shell_side_reynolds_number"] = "400"
    else:
        raw["task033_upstream_evidence"].pop(field)
    raw["task033_request_hash"] = "0" * 64
    return _first_blocker(raw)


def test_s05_request_identity_precedes_missing_phase():
    blocker, stage = _s05_request_identity_with_upstream_fault("phase_region")
    assert blocker.code == "SSPD_TASK033_REQUEST_HASH_MISMATCH"
    assert stage == "S05"


def test_s05_request_identity_precedes_missing_rheology():
    blocker, stage = _s05_request_identity_with_upstream_fault("rheology_model")
    assert blocker.code == "SSPD_TASK033_REQUEST_HASH_MISMATCH"
    assert stage == "S05"


def test_s05_request_identity_precedes_missing_construction_family():
    blocker, stage = _s05_request_identity_with_upstream_fault("construction_family")
    assert blocker.code == "SSPD_TASK033_REQUEST_HASH_MISMATCH"
    assert stage == "S05"


def test_s05_request_identity_precedes_missing_shell_pass():
    blocker, stage = _s05_request_identity_with_upstream_fault("shell_pass_count")
    assert blocker.code == "SSPD_TASK033_REQUEST_HASH_MISMATCH"
    assert stage == "S05"


def test_s05_request_identity_precedes_missing_baffle_type():
    blocker, stage = _s05_request_identity_with_upstream_fault("baffle_type")
    assert blocker.code == "SSPD_TASK033_REQUEST_HASH_MISMATCH"
    assert stage == "S05"


def test_s05_request_identity_precedes_missing_pattern_family():
    blocker, stage = _s05_request_identity_with_upstream_fault("pattern_family")
    assert blocker.code == "SSPD_TASK033_REQUEST_HASH_MISMATCH"
    assert stage == "S05"


def test_s05_request_identity_precedes_missing_baffle_cut():
    blocker, stage = _s05_request_identity_with_upstream_fault("baffle_cut")
    assert blocker.code == "SSPD_TASK033_REQUEST_HASH_MISMATCH"
    assert stage == "S05"


def test_s05_request_identity_precedes_reynolds_domain_failure():
    blocker, stage = _s05_request_identity_with_upstream_fault("reynolds")
    assert blocker.code == "SSPD_TASK033_REQUEST_HASH_MISMATCH"
    assert stage == "S05"


def test_b018_runtime_target_is_validate_task032_identity_join(monkeypatch):
    calls = []
    original = authority_module.validate_task032_identity_join

    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(authority_module, "validate_task032_identity_join", spy)
    raw = make_valid_raw_request()
    raw["task032_result_id"] = "wrong"
    blocker, stage = _first_blocker(raw)
    assert calls
    assert blocker.code == "SSPD_TASK032_RESULT_ID_MISMATCH"
    assert stage == "S04"


def test_b019_runtime_target_is_validate_task032_identity_join(monkeypatch):
    calls = []
    original = authority_module.validate_task032_identity_join

    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(authority_module, "validate_task032_identity_join", spy)
    raw = make_valid_raw_request()
    raw["task032_result_hash"] = "0" * 64
    blocker, stage = _first_blocker(raw)
    assert calls
    assert blocker.code == "SSPD_TASK032_RESULT_HASH_MISMATCH"
    assert stage == "S04"


def test_b024_runtime_target_is_verify_auxiliary_bindings(monkeypatch):
    calls = []
    original = validation_module.verify_auxiliary_bindings

    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(validation_module, "verify_auxiliary_bindings", spy)
    raw = make_valid_raw_request()
    raw["property_snapshot_hash"] = "0" * 64
    blocker, stage = _first_blocker(raw)
    assert calls
    assert blocker.code == "SSPD_PROPERTY_SNAPSHOT_HASH_MISMATCH"
    assert stage == "S08"


def test_b025_runtime_target_is_verify_auxiliary_bindings(monkeypatch):
    calls = []
    original = validation_module.verify_auxiliary_bindings

    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(validation_module, "verify_auxiliary_bindings", spy)
    raw = make_valid_raw_request()
    raw["mass_flow_authority_hash"] = "0" * 64
    blocker, stage = _first_blocker(raw)
    assert calls
    assert blocker.code == "SSPD_MASS_FLOW_AUTHORITY_HASH_MISMATCH"
    assert stage == "S08"
