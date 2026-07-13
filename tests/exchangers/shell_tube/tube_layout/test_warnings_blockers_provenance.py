from __future__ import annotations

from hexagent.exchangers.shell_tube.tube_layout import validate_request
from tests.exchangers.shell_tube.tube_layout._builders import make_request


def test_exact_valid_warning_set_and_provenance_pipeline() -> None:
    result = validate_request(make_request(), software_version="0.1.0", git_commit="abc")
    assert result.layout is not None
    codes = {item.code for item in result.warnings}
    assert codes == {
        "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM",
        "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER",
        "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED",
    }
    provenance = result.layout.provenance
    assert provenance["layout_hash"] == result.layout.layout_hash
    assert "layout_id" not in provenance
    assert provenance["request_hash"] == result.layout.request_hash
    assert provenance["tube_geometry_snapshot_hash"]
    assert provenance["layout_rule_snapshot_hash"]
