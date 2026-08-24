"""TASK033 repeat-run identity tests."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_heat_transfer import validate_request
from hexagent.exchangers.shell_tube.shell_side_heat_transfer.canonical import canonical_bytes
from tests.exchangers.shell_tube.shell_side_heat_transfer.test_task033_models import copy_request


def test_success_identity_repeatability() -> None:
    """T033-026_SUCCESS_IDENTITY_REPEATABILITY."""
    first = validate_request(copy_request()).heat_transfer
    second = validate_request(copy_request()).heat_transfer
    assert first is not None and second is not None
    assert (first.result_hash, first.result_id) == (second.result_hash, second.result_id)


def test_typed_blocked_identity_repeatability() -> None:
    """T033-027_TYPED_BLOCKED_IDENTITY_REPEATABILITY."""
    raw = copy_request()
    raw["task032_flow_state"]["result_hash"] = "0" * 64
    first = validate_request(raw).blocked_result
    second = validate_request(raw).blocked_result
    assert first is not None and second is not None
    assert first.blocked_result_hash == second.blocked_result_hash


def test_raw_blocked_projection_identity_repeatability() -> None:
    """T033-028_RAW_BLOCKED_PROJECTION_IDENTITY_REPEATABILITY."""
    first = validate_request(None).raw_boundary_blocked_result
    second = validate_request(None).raw_boundary_blocked_result
    assert first is not None and second is not None
    assert first.blocked_result_hash == second.blocked_result_hash
    assert first.raw_projection == second.raw_projection


def test_provenance_identity_repeatability() -> None:
    """T033-029_PROVENANCE_IDENTITY_REPEATABILITY."""
    first = validate_request(copy_request()).heat_transfer
    second = validate_request(copy_request()).heat_transfer
    assert first is not None and second is not None
    assert first.provenance == second.provenance
    assert canonical_bytes(b"task033.provenance.v1", first.provenance) == canonical_bytes(
        b"task033.provenance.v1", second.provenance
    )
