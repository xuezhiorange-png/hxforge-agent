"""TASK-024 Round 6 public validation producer tests."""

from __future__ import annotations

import dataclasses
from typing import Any

from hexagent.exchangers.shell_tube.baffle_geometry import models as _models
from hexagent.exchangers.shell_tube.baffle_geometry.validation import (
    GIT_COMMIT,
    IMPLEMENTATION_SOFTWARE_VERSION,
    validate_request,
)
from tests.exchangers.shell_tube.baffle_geometry import _builders as _b


def _raw_from_request(request: _models.BaffleGeometryRequest) -> dict[str, Any]:
    design = request.design_authority
    axial = request.axial_span
    return {
        "schema_version": request.schema_version,
        "configuration": request.configuration,
        "tube_layout": request.tube_layout,
        "shell_bundle_geometry": request.shell_bundle_geometry,
        "axial_span": {
            "schema_version": axial.schema_version,
            "axial_start_coordinate_m": axial.axial_start_coordinate_m,
            "axial_end_coordinate_m": axial.axial_end_coordinate_m,
            "evidence_refs": list(axial.evidence_refs),
            "authority_hash": axial.authority_hash,
        },
        "design_authority": {
            "schema_version": design.schema_version,
            "baffle_type": design.baffle_type,
            "baffle_count": design.baffle_count,
            "baffle_thickness_m": design.baffle_thickness_m,
            "spacing_sequence_m": list(design.spacing_sequence_m),
            "baffle_cut_fraction": design.baffle_cut_fraction,
            "orientation_sequence": list(design.orientation_sequence),
            "shell_to_baffle_diametral_clearance_m": design.shell_to_baffle_diametral_clearance_m,
            "tube_to_baffle_hole_diametral_clearance_m": (
                design.tube_to_baffle_hole_diametral_clearance_m
            ),
            "evidence_refs": list(design.evidence_refs),
            "authority_hash": design.authority_hash,
        },
        "evidence_refs": list(request.evidence_refs),
    }


def test_happy_path_validate_request() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = validate_request(_raw_from_request(request))
    assert result.status is _models.ValidationStatus.VALID
    assert result.geometry is not None
    assert result.blockers == ()
    assert result.blocked_result_hash is None
    assert result.geometry.request_hash
    assert result.geometry.geometry_hash
    assert result.geometry.geometry_id
    assert len(result.geometry.baffle_planes) == 4
    assert result.warnings == result.geometry.warnings
    assert result.deferred_capabilities == result.geometry.deferred_capabilities
    provenance = dict(result.geometry.provenance)
    assert provenance["software_version"] == IMPLEMENTATION_SOFTWARE_VERSION
    assert provenance["git_commit"] == GIT_COMMIT
    assert provenance["request_hash"] == result.geometry.request_hash
    assert provenance["warnings"] == [
        {
            "code": item.code,
            "field_path": item.field_path,
            "message_key": item.message_key,
            "evidence_refs": list(item.evidence_refs),
            "details": [[key, val] for key, val in item.details],
        }
        for item in result.warnings
    ]


def test_hash_and_id_replay_determinism() -> None:
    request = _b.make_geometry_request(position_count=1)
    raw = _raw_from_request(request)
    first = validate_request(raw)
    second = validate_request(raw)
    assert first.status is _models.ValidationStatus.VALID
    assert second.status is _models.ValidationStatus.VALID
    assert first.geometry is not None
    assert second.geometry is not None
    assert first.geometry.request_hash == second.geometry.request_hash
    assert first.geometry.geometry_hash == second.geometry.geometry_hash
    assert first.geometry.geometry_id == second.geometry.geometry_id
    assert first.blocked_result_hash is None
    assert second.blocked_result_hash is None


def test_raw_malformed_blocks_without_exception() -> None:
    result = validate_request(42)
    assert result.status is _models.ValidationStatus.BLOCKED
    assert result.geometry is None
    assert result.blocked_result_hash is not None
    assert any(b.code == "BFG_RAW_TYPE_INVALID" for b in result.blockers)


def test_authority_failure_blocks_without_partial_geometry() -> None:
    request = _b.make_geometry_request(position_count=1)
    bad_span = _models.CallerSuppliedBaffleAxialSpan(
        schema_version=request.axial_span.schema_version,
        axial_start_coordinate_m=request.axial_span.axial_start_coordinate_m,
        axial_end_coordinate_m=request.axial_span.axial_end_coordinate_m,
        evidence_refs=request.axial_span.evidence_refs,
        authority_hash="0" * 64,
    )
    request = _b.replace_axial_span(request, axial_span=bad_span)
    result = validate_request(_raw_from_request(request))
    assert result.status is _models.ValidationStatus.BLOCKED
    assert result.geometry is None
    assert result.blocked_result_hash is not None
    assert any(b.code == "BFG_AXIAL_SPAN_AUTHORITY_HASH_MISMATCH" for b in result.blockers)


def test_geometry_failure_blocks_without_partial_geometry() -> None:
    request = _b.make_geometry_request(
        baffle_thickness_m="0.4",
        position_count=1,
    )
    result = validate_request(_raw_from_request(request))
    assert result.status is _models.ValidationStatus.BLOCKED
    assert result.geometry is None
    assert result.blocked_result_hash is not None
    assert any(b.code == "BFG_BAFFLE_SOLIDS_OVERLAP" for b in result.blockers)


def test_repeat_run_identity() -> None:
    request = _b.make_geometry_request(position_count=1)
    raw = _raw_from_request(request)
    geometry_hashes = {
        validate_request(raw).geometry.geometry_hash  # type: ignore[union-attr]
        for _ in range(5)
    }
    blocked_hashes = {
        validate_request(
            {"schema_version": "task024.baffle-geometry-request.v1"}
        ).blocked_result_hash
        for _ in range(5)
    }
    assert len(geometry_hashes) == 1
    assert len(blocked_hashes) == 1


def test_no_exception_leak_on_invalid_raw_input() -> None:
    invalid_inputs = [
        None,
        [],
        "not-a-mapping",
        {"schema_version": "wrong"},
        {"schema_version": "task024.baffle-geometry-request.v1"},
    ]
    for raw in invalid_inputs:
        result = validate_request(raw)
        assert result.status is _models.ValidationStatus.BLOCKED
        assert result.geometry is None
        assert result.blocked_result_hash is not None


def test_blocked_paths_carry_forward_authority_warnings() -> None:
    request = _b.make_geometry_request(position_count=1)
    bad_span = _models.CallerSuppliedBaffleAxialSpan(
        schema_version=request.axial_span.schema_version,
        axial_start_coordinate_m=request.axial_span.axial_start_coordinate_m,
        axial_end_coordinate_m=request.axial_span.axial_end_coordinate_m,
        evidence_refs=request.axial_span.evidence_refs,
        authority_hash="0" * 64,
    )
    request = _b.replace_axial_span(request, axial_span=bad_span)
    result = validate_request(_raw_from_request(request))
    assert result.status is _models.ValidationStatus.BLOCKED
    warning_codes = {item.code for item in result.warnings}
    assert "BFG_FIXED_TUBESHEET_ONLY_V1" in warning_codes


def test_schema_blocked_uses_raw_projection_identity() -> None:
    raw = {"schema_version": "task024.baffle-geometry-request.v1", "unexpected": 1}
    first = validate_request(raw)
    second = validate_request(raw)
    assert first.status is _models.ValidationStatus.BLOCKED
    assert first.blocked_result_hash == second.blocked_result_hash
    assert first.blocked_result_hash is not None


def test_validate_typed_request_not_exported_from_package() -> None:
    import hexagent.exchangers.shell_tube.baffle_geometry as package

    assert "validate_typed_request" not in package.__all__
    assert "validate_typed_request" not in dir(package)


def test_input_request_not_mutated() -> None:
    request = _b.make_geometry_request(position_count=1)
    raw = _raw_from_request(request)
    before = dataclasses.asdict(request.axial_span)
    validate_request(raw)
    after = dataclasses.asdict(request.axial_span)
    assert before == after
