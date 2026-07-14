from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    WarningCode,
    validate_request,
)

from ._builders import make_request


def test_valid_warning_set_has_only_closed_codes_and_family_warning() -> None:
    result = validate_request(
        make_request(), software_version="tests", git_commit="abc"
    )
    assert result.geometry is not None
    codes = {item.code for item in result.warnings}
    assert codes <= {item.value for item in WarningCode}
    assert WarningCode.SBG_INTERNAL_GENERIC_NO_STANDARD_CLAIM.value in codes
    assert (
        WarningCode.SBG_CALLER_SUPPLIED_SHELL_DIAMETER_NO_CATALOG_SELECTION.value
        in codes
    )
    assert WarningCode.SBG_BAFFLE_GEOMETRY_DEFERRED.value in codes
    assert WarningCode.SBG_PASS_PARTITION_ASSIGNMENT_DEFERRED.value in codes


def test_provenance_has_no_runtime_now_or_host_fields() -> None:
    result = validate_request(
        make_request(), software_version="tests", git_commit="abc"
    )
    assert result.geometry is not None
    text = repr(result.geometry.provenance)
    for forbidden in ("hostname", "process_id", "runtime_now", "filesystem_path"):
        assert forbidden not in text
    assert "geometry_hash" in text
    assert "task021_layout_hash" in text


def test_blocked_hash_changes_when_complete_blocker_details_change() -> None:
    first = validate_request(
        make_request(shell_diameter="0.01"), software_version="tests", git_commit="abc"
    )
    second = validate_request(
        make_request(shell_diameter="0.02"), software_version="tests", git_commit="abc"
    )
    assert first.geometry is None and second.geometry is None
    assert first.blocked_result_hash != second.blocked_result_hash
