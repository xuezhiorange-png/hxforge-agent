"""Kern applicability and strict Reynolds domain tests."""

from dataclasses import replace
from decimal import Decimal

import pytest

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
