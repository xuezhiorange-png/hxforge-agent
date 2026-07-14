from __future__ import annotations

import pytest

from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    BlockerCode,
    ValidationStatus,
    validate_request,
)

from ._builders import make_request


def test_public_entry_point_requires_explicit_provenance_inputs() -> None:
    with pytest.raises(ValueError):
        validate_request(make_request(), software_version="", git_commit="abc")
    with pytest.raises(ValueError):
        validate_request(make_request(), software_version="tests", git_commit="")


def test_valid_result_shape_is_complete() -> None:
    result = validate_request(
        make_request(), software_version="tests", git_commit="abc"
    )
    assert result.status is ValidationStatus.VALID
    assert result.geometry is not None
    assert result.blockers == ()
    assert result.blocked_result_hash is None
    assert len(result.deferred_capabilities) == 19


def test_position_capacity_guard_blocks() -> None:
    result = validate_request(
        make_request(maximum_position_count=1),
        software_version="tests",
        git_commit="abc",
    )
    assert result.status is ValidationStatus.BLOCKED
    assert result.geometry is None
    assert BlockerCode.SBG_LAYOUT_POSITION_COUNT_EXCEEDED.value in {
        item.code for item in result.blockers
    }


def test_decimal_objects_are_rejected_at_public_boundary() -> None:
    from decimal import Decimal

    payload = make_request()
    payload["bundle_peripheral_allowance_m"] = Decimal("0.005")
    result = validate_request(payload, software_version="tests", git_commit="abc")
    assert result.geometry is None
    assert result.blockers[0].code == BlockerCode.SBG_RAW_TYPE_INVALID.value
