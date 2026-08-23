"""Upstream identity and engineering-authority replay tests."""

from dataclasses import replace

from hexagent.exchangers.shell_tube.shell_side_flow_state import authority, validate_request
from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
    mass_flow_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.engineering_authority_snapshot import (
    ENGINEERING_AUTHORITY_HASH,
    ENGINEERING_AUTHORITY_ID,
    recompute_engineering_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.models import (
    BlockerCode,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import parse_request

from . import copy_request


def test_t032_aut_001_task031_identity_replay() -> None:
    request = parse_request(copy_request())
    geometry = authority.verify_task031_result(request.task031_result)
    assert geometry.geometry_id == request.mass_flow_authority.task031_geometry_id
    assert geometry.geometry_hash == request.mass_flow_authority.task031_geometry_hash

    invalid = copy_request()
    invalid["task031_result"]["geometry"]["geometry_hash"] = "0" * 64
    result = validate_request(invalid)
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S02"
    assert result.blockers[0].code == BlockerCode.SSFS_TASK031_IDENTITY_MISMATCH


def test_t032_aut_004_same_case_binding() -> None:
    raw = copy_request()
    request = parse_request(raw)
    mutated = replace(
        request.mass_flow_authority,
        task031_geometry_id="urn:wrong-geometry",
    )
    raw["mass_flow_authority"]["task031_geometry_id"] = mutated.task031_geometry_id
    raw["mass_flow_authority"]["authority_hash"] = mass_flow_authority_hash(mutated)
    result = validate_request(raw)
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S05"
    assert result.blockers[0].code == BlockerCode.SSFS_SAME_CASE_BINDING_MISMATCH


def test_t032_aut_005_aggregate_engineering_authority_hash_id_replay() -> None:
    assert recompute_engineering_authority_hash() == ENGINEERING_AUTHORITY_HASH
    assert ENGINEERING_AUTHORITY_ID.endswith(ENGINEERING_AUTHORITY_HASH)
    authority.verify_engineering_authority()
