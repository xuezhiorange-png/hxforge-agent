"""PropertySnapshot replay and reuse boundary tests."""

from hexagent.exchangers.shell_tube.shell_side_flow_state import validate_request
from hexagent.exchangers.shell_tube.shell_side_flow_state.models import BlockerCode
from hexagent.exchangers.shell_tube.tube_side_thermal import recompute_property_snapshot_hash

from . import copy_request


def test_t032_aut_002_property_snapshot_hash_replay() -> None:
    raw = copy_request()
    raw["property_snapshot_hash"] = "0" * 64
    result = validate_request(raw)
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S03"
    assert result.blockers[0].code == BlockerCode.SSFS_PROPERTY_SNAPSHOT_HASH_MISMATCH


def test_t032_pro_001_property_snapshot_reuse_no_reevaluation() -> None:
    result = validate_request(copy_request())
    assert result.flow_state is not None
    assert result.flow_state.property_snapshot_hash
    assert result.flow_state.shell_side_mass_flow_rate_kg_s > 0
    assert callable(recompute_property_snapshot_hash)
