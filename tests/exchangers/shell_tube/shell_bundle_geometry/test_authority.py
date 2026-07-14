from __future__ import annotations

from dataclasses import replace

from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    BlockerCode,
    validate_request,
    verify_task021_layout,
)

from ._builders import corrupt_layout_hash, make_layout, make_request


def test_complete_task021_layout_identity_verifies() -> None:
    verify_task021_layout(make_layout())


def test_corrupted_task021_layout_hash_blocks() -> None:
    payload = make_request()
    payload["tube_layout"] = corrupt_layout_hash(payload["tube_layout"])
    result = validate_request(payload, software_version="tests", git_commit="abc")
    assert result.geometry is None
    assert BlockerCode.SBG_TASK021_LAYOUT_IDENTITY_MISMATCH.value in {
        item.code for item in result.blockers
    }


def test_cross_binding_mismatch_blocks() -> None:
    payload = make_request()
    payload["tube_layout"] = replace(payload["tube_layout"], task020_configuration_hash="e" * 64)
    result = validate_request(payload, software_version="tests", git_commit="abc")
    assert result.geometry is None
    assert BlockerCode.SBG_TASK021_LAYOUT_IDENTITY_MISMATCH.value in {
        item.code for item in result.blockers
    } or BlockerCode.SBG_LAYOUT_CONFIGURATION_BINDING_MISMATCH.value in {
        item.code for item in result.blockers
    }


def test_rule_snapshot_hash_is_recomputed() -> None:
    payload = make_request()
    payload["geometry_rule_authority"]["snapshot_hash"] = "0" * 64
    result = validate_request(payload, software_version="tests", git_commit="abc")
    assert result.geometry is None
    assert BlockerCode.SBG_RULE_SNAPSHOT_HASH_MISMATCH.value in {
        item.code for item in result.blockers
    }


def test_mutually_exclusive_shell_authorities_block() -> None:
    payload = make_request()
    payload["approved_shell_geometry"] = {
        "schema_version": "task022.approved-shell-geometry.v1",
        "geometry_id": "shell-1",
        "geometry_type": "shell",
        "revision": "1",
        "approval_state": "approved",
        "shell_inside_diameter_m": "0.2",
        "record_hash": "a" * 64,
        "source_binding": {
            "source_id": "x",
            "source_type": "test",
            "source_revision": "1",
            "source_location": "memory://x",
            "evidence_ref": "e",
            "approved_by": "a",
            "approved_at": "recorded",
        },
        "snapshot_hash": "0" * 64,
    }
    result = validate_request(payload, software_version="tests", git_commit="abc")
    assert result.geometry is None
    assert BlockerCode.SBG_APPROVED_SHELL_GEOMETRY_NOT_EXPECTED.value in {
        item.code for item in result.blockers
    }
