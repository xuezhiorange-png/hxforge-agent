"""Kern applicability and strict Reynolds domain tests."""

from dataclasses import replace
from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.authority import (
    AuthorityFailure,
    replay_task032_and_upstreams,
    verify_applicability,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.schema import parse_request
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    make_valid_raw_request,
)


def _direct_mutation(field: str, value):
    raw = make_valid_raw_request()
    request = parse_request(raw)
    identity = replay_task032_and_upstreams(request)
    if field in {"phase_region", "rheology_model", "shell_side_reynolds_number"}:
        identity.flow[field] = value
    else:
        request.task033_upstream_evidence[field] = value
    with pytest.raises(AuthorityFailure) as failure:
        verify_applicability(request, identity)
    return failure.value.blockers[0].code


def _missing_upstream_field(field: str):
    raw = make_valid_raw_request()
    if field in {"phase_region", "rheology_model"}:
        raw["task033_upstream_evidence"]["task032_flow_state"].pop(field)
    else:
        raw["task033_upstream_evidence"].pop(field)
    result = validate_request(raw)
    assert result.status == "BLOCKED"
    assert result.blocked_result is not None
    assert len(result.blocked_result.blockers) == 1
    return result.blocked_result.blockers[0], result.blocked_result.failure_stage


def test_b029_sspd_unsupported_phase():
    assert _direct_mutation("phase_region", "SINGLE_PHASE_GAS") == "SSPD_UNSUPPORTED_PHASE"


def test_b030_sspd_unsupported_rheology():
    assert _direct_mutation("rheology_model", "NON_NEWTONIAN") == "SSPD_UNSUPPORTED_RHEOLOGY"


def test_b031_sspd_unsupported_shell_type():
    assert (
        _direct_mutation("construction_family", "FIXED_TUBESHEET") == "SSPD_UNSUPPORTED_SHELL_TYPE"
    )


def test_b032_sspd_unsupported_shell_pass_count():
    assert _direct_mutation("shell_pass_count", 2) == "SSPD_UNSUPPORTED_SHELL_PASS_COUNT"


def test_b033_sspd_unsupported_baffle_type():
    assert _direct_mutation("baffle_type", "DOUBLE_SEGMENTAL") == "SSPD_UNSUPPORTED_BAFFLE_TYPE"


def test_b034_sspd_unsupported_tube_layout():
    assert _direct_mutation("pattern_family", "SQUARE_45") == "SSPD_UNSUPPORTED_TUBE_LAYOUT"


def test_b035_sspd_unsupported_baffle_cut():
    assert _direct_mutation("baffle_cut", "VARIABLE") == "SSPD_UNSUPPORTED_BAFFLE_CUT"


def test_b036_sspd_unsupported_baffle_spacing():
    raw = make_valid_raw_request()
    request = parse_request(raw)
    identity = replay_task032_and_upstreams(request)
    request = replace(request, uniform_spacing_sequence_m=(Decimal("0.120"), Decimal("0.121")))
    with pytest.raises(AuthorityFailure) as failure:
        verify_applicability(request, identity)
    assert failure.value.blockers[0].code == "SSPD_UNSUPPORTED_BAFFLE_SPACING"


def test_b037_sspd_reynolds_outside_domain():
    assert _direct_mutation("shell_side_reynolds_number", "400") == "SSPD_REYNOLDS_OUTSIDE_DOMAIN"


def test_phase_region_missing_blocks_at_s11():
    blocker, stage = _missing_upstream_field("phase_region")
    assert blocker.code == "SSPD_UNSUPPORTED_PHASE"
    assert stage == "S11"


def test_rheology_model_missing_blocks_at_s11():
    blocker, stage = _missing_upstream_field("rheology_model")
    assert blocker.code == "SSPD_UNSUPPORTED_RHEOLOGY"
    assert stage == "S11"


def test_construction_family_missing_blocks_at_s11():
    blocker, stage = _missing_upstream_field("construction_family")
    assert blocker.code == "SSPD_UNSUPPORTED_SHELL_TYPE"
    assert stage == "S11"


def test_shell_pass_count_missing_blocks_at_s11():
    blocker, stage = _missing_upstream_field("shell_pass_count")
    assert blocker.code == "SSPD_UNSUPPORTED_SHELL_PASS_COUNT"
    assert stage == "S11"


def test_baffle_type_missing_blocks_at_s11():
    blocker, stage = _missing_upstream_field("baffle_type")
    assert blocker.code == "SSPD_UNSUPPORTED_BAFFLE_TYPE"
    assert stage == "S11"


def test_pattern_family_missing_blocks_at_s11():
    blocker, stage = _missing_upstream_field("pattern_family")
    assert blocker.code == "SSPD_UNSUPPORTED_TUBE_LAYOUT"
    assert stage == "S11"


def test_baffle_cut_missing_blocks_at_s11():
    blocker, stage = _missing_upstream_field("baffle_cut")
    assert blocker.code == "SSPD_UNSUPPORTED_BAFFLE_CUT"
    assert stage == "S11"
