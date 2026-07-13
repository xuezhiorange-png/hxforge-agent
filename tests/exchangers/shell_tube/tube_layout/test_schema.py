from __future__ import annotations

from copy import deepcopy

from hexagent.exchangers.shell_tube.tube_layout import (
    ValidationStatus,
    validate_request,
)
from tests.exchangers.shell_tube.tube_layout._builders import make_request


def test_unknown_field_blocks() -> None:
    payload = make_request()
    payload["unexpected"] = True
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert result.blockers[0].code == "STL_UNKNOWN_FIELD"


def test_boolean_integer_rejected() -> None:
    payload = deepcopy(make_request())
    payload["layout_rule_authority"]["maximum_candidate_positions"] = True
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status is ValidationStatus.BLOCKED
    assert any(item.code == "STL_RAW_TYPE_INVALID" for item in result.blockers)
