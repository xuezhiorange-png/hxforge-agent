from __future__ import annotations

from copy import deepcopy

from hexagent.exchangers.shell_tube.tube_layout import (
    ValidationStatus,
    validate_request,
)
from tests.exchangers.shell_tube.tube_layout._builders import make_request


def test_geometry_snapshot_hash_mismatch_blocks() -> None:
    payload = deepcopy(make_request())
    payload["tube_geometry"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(
        item.code == "STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH"
        for item in result.blockers
    )


def test_layout_rule_snapshot_hash_mismatch_blocks() -> None:
    payload = deepcopy(make_request())
    payload["layout_rule_authority"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(
        item.code == "STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH"
        for item in result.blockers
    )
