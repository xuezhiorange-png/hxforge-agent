"""Mass-flow authority replay and Decimal positivity tests."""

from dataclasses import replace
from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_flow_state import validate_request
from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
    mass_flow_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.models import BlockerCode
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import parse_request

from . import copy_request


def test_t032_aut_003_mass_flow_authority_hash_replay() -> None:
    raw = copy_request()
    raw["mass_flow_authority"]["authority_hash"] = "0" * 64
    result = validate_request(raw)
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S04"
    assert result.blockers[0].code == BlockerCode.SSFS_MASS_FLOW_AUTHORITY_HASH_MISMATCH

    authority = parse_request(copy_request()).mass_flow_authority
    assert mass_flow_authority_hash(authority) == authority.authority_hash


def test_t032_mfa_001_positive_finite_decimal_mass_flow_only() -> None:
    valid = parse_request(copy_request()).mass_flow_authority
    assert type(valid.mass_flow_rate_kg_s) is Decimal
    for value in ("0.0000000", "-1.0000000"):
        raw = copy_request()
        raw["mass_flow_authority"]["mass_flow_rate_kg_s"] = value
        mutated = replace(valid, mass_flow_rate_kg_s=Decimal(value))
        raw["mass_flow_authority"]["authority_hash"] = mass_flow_authority_hash(mutated)
        result = validate_request(raw)
        assert result.blocked_result is not None
        assert result.blocked_result.failure_stage == "S04"
        assert result.blockers[0].code == BlockerCode.SSFS_MASS_FLOW_NON_POSITIVE
