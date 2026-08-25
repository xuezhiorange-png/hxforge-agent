"""Closed registry and B046-B053 reachability binding."""

from dataclasses import replace

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validation as validation_module
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.blocker_registry import (
    BLOCKER_CODES,
    make_blocker,
    validate_blocker_token,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import DEFERRED_CAPABILITIES
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.warning_registry import (
    WARNING_CODES,
    validate_deferred_token,
    validate_warning_token,
)
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    make_valid_raw_request,
)


def _codes(raw):
    return {item.code for item in validate_request(raw).blockers}


def test_b046_sspd_partial_result_forbidden():
    result = validate_request(make_valid_raw_request()).pressure_drop
    assert result is not None
    partial = replace(
        result,
        blockers=(make_blocker("SSPD_PARTIAL_RESULT_FORBIDDEN", stage="S17"),),
    )
    try:
        validation_module.finalize_result_identity(partial)
    except validation_module.ResultIdentityFinalizationError as failure:
        assert failure.blocker_code == "SSPD_PARTIAL_RESULT_FORBIDDEN"
    else:
        raise AssertionError("partial result was accepted")


def test_b047_sspd_deferred_capability_token_invalid():
    result = validate_request(make_valid_raw_request()).pressure_drop
    assert result is not None
    invalid = replace(result, deferred_capabilities=DEFERRED_CAPABILITIES + ("UNKNOWN",))
    try:
        validation_module.finalize_result_identity(invalid)
    except validation_module.ResultIdentityFinalizationError as failure:
        assert failure.blocker_code == "SSPD_DEFERRED_CAPABILITY_TOKEN_INVALID"
    else:
        raise AssertionError("unknown deferred capability was accepted")


def test_b048_sspd_shell_inside_diameter_mismatch():
    raw = make_valid_raw_request()
    raw["shell_inside_diameter_m"] = "1.201"
    assert "SSPD_SHELL_INSIDE_DIAMETER_MISMATCH" in _codes(raw)


def test_b049_sspd_baffle_count_mismatch():
    raw = make_valid_raw_request()
    raw["baffle_count"] = 13
    assert "SSPD_BAFFLE_COUNT_MISMATCH" in _codes(raw)


def test_b050_sspd_spacing_sequence_mismatch():
    raw = make_valid_raw_request()
    raw["uniform_spacing_sequence_m"] = ["0.120", "0.121"]
    assert "SSPD_SPACING_SEQUENCE_MISMATCH" in _codes(raw)


def test_b051_sspd_tube_pitch_mismatch():
    raw = make_valid_raw_request()
    raw["tube_pitch_m"] = "0.026"
    assert "SSPD_TUBE_PITCH_MISMATCH" in _codes(raw)


def test_b052_sspd_tube_outer_diameter_mismatch():
    raw = make_valid_raw_request()
    raw["tube_outer_diameter_m"] = "0.021"
    assert "SSPD_TUBE_OUTER_DIAMETER_MISMATCH" in _codes(raw)


def test_b053_sspd_pattern_family_mismatch():
    raw = make_valid_raw_request()
    raw["pattern_family"] = "SQUARE_45"
    assert "SSPD_PATTERN_FAMILY_MISMATCH" in _codes(raw)


def test_x013_all_53_exact_predicates():
    assert len(BLOCKER_CODES) == 53 and len(set(BLOCKER_CODES)) == 53
    assert all(validate_blocker_token(code) == code for code in BLOCKER_CODES)
    assert len(WARNING_CODES) == 5 and len(DEFERRED_CAPABILITIES) == 16
    validate_warning_token(WARNING_CODES[0])
    validate_deferred_token(DEFERRED_CAPABILITIES[0])
