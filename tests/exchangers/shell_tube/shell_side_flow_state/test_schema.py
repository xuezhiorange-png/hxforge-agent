"""Closed raw-boundary and nested schema tests."""

from collections import UserDict
from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_flow_state import validate_request
from hexagent.exchangers.shell_tube.shell_side_flow_state.models import (
    BlockerCode,
    ValidationStatus,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import parse_request

from . import copy_request


def test_t032_sch_001_raw_top_level_closed_shape() -> None:
    raw = copy_request()
    raw["unknown_field"] = "blocked"
    result = validate_request(raw)
    assert result.status is ValidationStatus.BLOCKED
    assert result.raw_boundary_blocked_result is not None
    assert any(item.code == BlockerCode.SSFS_UNKNOWN_FIELD for item in result.blockers)

    non_builtin = UserDict(copy_request())
    result = validate_request(non_builtin)
    assert result.raw_boundary_blocked_result is not None
    assert result.blockers[0].code == BlockerCode.SSFS_RAW_TYPE_INVALID


def test_t032_sch_002_nested_raw_shapes_and_decimal_lexical_domain() -> None:
    request = parse_request(copy_request())
    assert request.evidence_refs == ("request-a", "request-z")
    assert request.mass_flow_authority.evidence_refs == ("mass-a", "mass-z")
    assert isinstance(request.property_snapshot.density_kg_m3, Decimal)
    assert request.property_snapshot.density_kg_m3 == Decimal("998.2000")

    invalid = copy_request()
    invalid["property_snapshot"]["density_kg_m3"] = "9.982e2"
    result = validate_request(invalid)
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S03"
    assert result.blockers[0].code == BlockerCode.SSFS_DECIMAL_LEXICAL_INVALID


def test_t032_sch_003_profile_id_rejection() -> None:
    raw = copy_request()
    raw["profile_id"] = "hxforge.shell_tube.other_profile.v1"
    result = validate_request(raw)
    assert result.raw_boundary_blocked_result is not None
    assert any(item.code == BlockerCode.SSFS_PROFILE_ID_UNSUPPORTED for item in result.blockers)
