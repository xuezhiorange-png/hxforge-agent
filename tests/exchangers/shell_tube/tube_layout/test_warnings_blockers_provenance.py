"""Tests for §11.4-11.8 warning emission and provenance projection."""

from __future__ import annotations

from copy import deepcopy

from hexagent.exchangers.shell_tube.models import ConstructionFamily
from hexagent.exchangers.shell_tube.tube_layout import validate_request
from tests.exchangers.shell_tube.tube_layout._builders import (
    make_configuration,
    make_request,
)


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


def test_valid_warnings_are_sorted_per_canonical_composite_key() -> None:
    """Regression: warning order matches §11.4 (same composite key as §11.3)."""

    result = validate_request(make_request(), software_version="0.1.0", git_commit="abc")
    assert result.layout is not None
    warnings = result.warnings
    for i in range(len(warnings) - 1):
        a, b = warnings[i], warnings[i + 1]
        ka = (a.code, a.field_path or "", a.message_key)
        kb = (b.code, b.field_path or "", b.message_key)
        assert ka <= kb


def test_eligibility_filter_excludes_pre_stage_warnings_before_stage_four() -> None:
    """At stage-3 BLOCKED (schema version), no §11.7 warning is eligible."""

    payload = deepcopy(make_request())
    payload["schema_version"] = "wrong.schema-version.v9"
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.status.value == "BLOCKED"
    assert all(item.code != "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" for item in result.warnings)


def test_eligibility_emits_internals_but_not_envelope_at_stage_seven() -> None:
    payload = deepcopy(make_request())
    payload["tube_geometry"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    codes = {item.code for item in result.warnings}
    assert "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM" in codes
    assert "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED" in codes
    assert "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER" not in codes


def test_utube_bend_warning_gated_by_pairing_validation_completion() -> None:
    """§11.8 fires only after stage-16 pairing hash verification completes."""

    # Geometry-stage blocker fires before pairing — §11.8 not eligible.
    payload = deepcopy(make_request())
    payload["configuration"] = make_configuration(ConstructionFamily.U_TUBE)
    payload["tube_geometry"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert all(item.code != "STL_UTUBE_BEND_GEOMETRY_DEFERRED" for item in result.warnings)


def test_blocked_result_has_no_partial_layout() -> None:
    """Regression: blocked result carries no partial layout object."""

    payload = deepcopy(make_request())
    payload["tube_geometry"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is None
    assert result.blockers
    assert result.blocked_result_hash is not None
