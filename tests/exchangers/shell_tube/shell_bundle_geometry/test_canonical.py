from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    geometry_id,
    validate_request,
)

from ._builders import make_request


def test_repeated_execution_is_identity_stable() -> None:
    first = validate_request(make_request(), software_version="tests", git_commit="abc")
    second = validate_request(
        make_request(), software_version="tests", git_commit="abc"
    )
    assert first.geometry is not None and second.geometry is not None
    assert first.geometry.request_hash == second.geometry.request_hash
    assert first.geometry.geometry_hash == second.geometry.geometry_hash
    assert first.geometry.geometry_id == second.geometry.geometry_id


def test_geometry_uuid_is_derived_from_geometry_hash() -> None:
    result = validate_request(
        make_request(), software_version="tests", git_commit="abc"
    )
    assert result.geometry is not None
    assert result.geometry.geometry_id == geometry_id(result.geometry.geometry_hash)


def test_evidence_input_order_is_normalized() -> None:
    left = make_request()
    right = make_request()
    left["evidence_refs"] = ["b", "a"]
    right["evidence_refs"] = ["a", "b"]
    first = validate_request(left, software_version="tests", git_commit="abc")
    second = validate_request(right, software_version="tests", git_commit="abc")
    assert first.geometry is not None and second.geometry is not None
    assert first.geometry.request_hash == second.geometry.request_hash
