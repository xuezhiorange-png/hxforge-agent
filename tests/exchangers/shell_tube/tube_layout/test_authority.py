from __future__ import annotations

from copy import deepcopy

import pytest

from hexagent.exchangers.shell_tube.tube_layout import (
    ValidationStatus,
    validate_request,
)
from hexagent.exchangers.shell_tube.tube_layout.authority import (
    AuthorityFailure,
    verify_authority_mode_match,
    verify_layout_rule_profile,
)
from hexagent.exchangers.shell_tube.tube_layout.schema import (
    parse_geometry,
    parse_layout_rule,
)
from tests.exchangers.shell_tube.tube_layout._builders import make_request


def test_geometry_snapshot_hash_mismatch_blocks() -> None:
    payload = deepcopy(make_request())
    payload["tube_geometry"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH" for item in result.blockers)


def test_layout_rule_snapshot_hash_mismatch_blocks() -> None:
    payload = deepcopy(make_request())
    payload["layout_rule_authority"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH" for item in result.blockers)


def test_authority_mode_match_passes_for_matching_modes() -> None:
    """Stage 5 — INTERNAL_GENERIC matches INTERNAL_GENERIC raises nothing."""

    payload = make_request()
    rule = parse_layout_rule(payload["layout_rule_authority"])
    config = payload["configuration"]
    verify_authority_mode_match(rule, config)


def test_authority_mode_match_raises_on_mismatch() -> None:
    """Stage 5 — APPROVED_RULE_PACK rule with INTERNAL_GENERIC config raises."""

    payload = make_request()
    config = payload["configuration"]
    mismatched_rule = parse_layout_rule(
        {**payload["layout_rule_authority"], "authority_mode": "APPROVED_RULE_PACK"}
    )
    with pytest.raises(AuthorityFailure):
        verify_authority_mode_match(mismatched_rule, config)


def test_layout_rule_profile_passes_for_valid_request() -> None:
    """Stage 6 — full layout-rule profile verification passes on a buildable request."""

    payload = make_request()
    rule = parse_layout_rule(payload["layout_rule_authority"])
    config = payload["configuration"]
    geometry = parse_geometry(payload["tube_geometry"])
    verify_layout_rule_profile(rule, config, geometry)


def test_stage_seven_block_keeps_other_blockers_out_of_set() -> None:
    """Regression: stage-7 BLOCKED result does not silently carry stage-5 blockers."""

    payload = deepcopy(make_request())
    payload["tube_geometry"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    codes = {item.code for item in result.blockers}
    assert "STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH" in codes
    assert "STL_AUTHORITY_MODE_MISMATCH" not in codes
