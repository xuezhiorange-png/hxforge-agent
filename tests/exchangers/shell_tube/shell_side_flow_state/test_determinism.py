"""Repeat-run deterministic identity contract."""

from hexagent.exchangers.shell_tube.shell_side_flow_state import validate_request

from . import copy_request


def test_t032_det_001_repeat_run_identity() -> None:
    first = validate_request(copy_request())
    second = validate_request(copy_request())
    assert first.flow_state is not None
    assert second.flow_state is not None
    assert first.flow_state.result_id == second.flow_state.result_id
    assert first.flow_state.result_hash == second.flow_state.result_hash
    assert first.flow_state.provenance == second.flow_state.provenance
    assert first.flow_state.warnings == second.flow_state.warnings
