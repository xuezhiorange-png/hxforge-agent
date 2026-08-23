"""Stage ordering and fail-closed validation tests."""

from dataclasses import replace

from hexagent.exchangers.shell_tube.shell_side_flow_state import validate_request, validation
from hexagent.exchangers.shell_tube.shell_side_flow_state.blocker_registry import (
    TASK032_BLOCKER_EARLIEST_STAGE,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
    mass_flow_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.models import (
    BlockerCode,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import parse_request

from . import copy_request


def test_t032_val_001_earliest_stage_map() -> None:
    assert len(TASK032_BLOCKER_EARLIEST_STAGE) == 33
    assert TASK032_BLOCKER_EARLIEST_STAGE[BlockerCode.SSFS_RAW_TYPE_INVALID] == "S00"
    assert (
        TASK032_BLOCKER_EARLIEST_STAGE[BlockerCode.SSFS_RESULT_IDENTITY_FINALIZATION_FAILED]
        == "S12"
    )
    assert TASK032_BLOCKER_EARLIEST_STAGE[BlockerCode.SSFS_PARTIAL_RESULT_FORBIDDEN] == "S10"


def test_t032_val_002_first_failing_stage_accumulation() -> None:
    raw = copy_request()
    raw["mass_flow_authority"]["rheology_model"] = "NON_NEWTONIAN"
    raw["mass_flow_authority"]["property_state_role"] = "NOT_BULK_STATE"
    raw["mass_flow_authority"]["authority_hash"] = mass_flow_authority_hash(
        replace(
            parse_request(copy_request()).mass_flow_authority,
            rheology_model="NON_NEWTONIAN",
            property_state_role="NOT_BULK_STATE",
        )
    )
    result = validate_request(raw)
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S06"
    assert {item.code for item in result.blockers} == {
        BlockerCode.SSFS_RHEOLOGY_MODEL_UNSUPPORTED,
        BlockerCode.SSFS_PROPERTY_STATE_ROLE_UNSUPPORTED,
    }
    assert all(item.stage == "S06" for item in result.blockers)


def test_t032_val_003_s12_result_identity_fail_closed(monkeypatch) -> None:
    original = validation.result_id
    calls = 0

    def fail_once(result_hash: str) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("simulated UUID finalization failure")
        return original(result_hash)

    monkeypatch.setattr(validation, "result_id", fail_once)
    result = validate_request(copy_request())
    assert result.flow_state is None
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S12"
    assert result.blockers[0].code == BlockerCode.SSFS_RESULT_IDENTITY_FINALIZATION_FAILED
    assert result.blocked_result.result_hash
    assert result.blocked_result.result_id
