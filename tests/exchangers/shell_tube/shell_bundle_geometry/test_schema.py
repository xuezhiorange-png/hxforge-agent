from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    BlockerCode,
    validate_request,
)

from ._builders import make_request


def _blocked(payload):
    return validate_request(payload, software_version="tests", git_commit="abc")


def test_unknown_top_level_field_blocks() -> None:
    payload = make_request()
    payload["extra"] = True
    result = _blocked(payload)
    assert result.geometry is None
    assert {item.code for item in result.blockers} == {
        BlockerCode.SBG_UNKNOWN_FIELD.value
    }


def test_raw_tuple_evidence_is_not_silently_coerced() -> None:
    payload = make_request()
    payload["evidence_refs"] = ("x",)
    result = _blocked(payload)
    assert result.geometry is None
    assert result.blockers[0].code == BlockerCode.SBG_RAW_TYPE_INVALID.value


def test_partial_upstream_projection_is_rejected() -> None:
    payload = make_request()
    payload["configuration"] = {
        "configuration_id": payload["configuration"].configuration_id
    }
    result = _blocked(payload)
    assert result.geometry is None
    assert (
        result.blockers[0].message_key
        == "complete_task020_configuration_instance_required"
    )


def test_duplicate_evidence_refs_block() -> None:
    payload = make_request()
    payload["minimum_clearance_evidence_refs"] = ["dup", "dup"]
    result = _blocked(payload)
    assert result.geometry is None
    assert result.blockers[0].code == BlockerCode.SBG_RAW_TYPE_INVALID.value
