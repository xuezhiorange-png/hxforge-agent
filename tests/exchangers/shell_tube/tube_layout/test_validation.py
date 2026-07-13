from __future__ import annotations

from hexagent.exchangers.shell_tube.tube_layout import (
    ValidationStatus,
    validate_request,
)
from tests.exchangers.shell_tube.tube_layout._builders import make_request


def test_valid_request_produces_layout_and_counts() -> None:
    result = validate_request(make_request(), software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.VALID
    assert result.layout is not None
    assert result.layout.tube_hole_count == result.layout.physical_tube_count
    assert result.layout.blockers == ()
    assert result.blocked_result_hash is None


def test_candidate_capacity_blocks_before_generation() -> None:
    result = validate_request(make_request(maximum=1), software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_ENUMERATION_LIMIT_EXCEEDED" for item in result.blockers)
    assert result.layout is None
