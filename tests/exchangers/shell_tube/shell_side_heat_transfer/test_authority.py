"""TASK033 upstream replay and same-case authority tests."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_heat_transfer import validate_request
from tests.exchangers.shell_tube.shell_side_heat_transfer.test_models import (
    copy_request,
    refresh_task032_identity,
)


def _blocked(raw: dict[str, object], code: str):
    result = validate_request(raw)
    assert result.heat_transfer is None
    assert any(item.code == code for item in result.blockers)
    return result


def test_task032_flow_state_type_invalid() -> None:
    """T033-006_TASK032_FLOW_STATE_TYPE_INVALID."""
    raw = copy_request()
    raw["task032_flow_state"] = []
    _blocked(raw, "SSHT_TASK032_FLOW_STATE_INVALID")


def test_task032_result_hash_mismatch() -> None:
    """T033-007_TASK032_RESULT_HASH_MISMATCH."""
    raw = copy_request()
    raw["task032_flow_state"]["result_hash"] = "0" * 64
    _blocked(raw, "SSHT_TASK032_RESULT_HASH_MISMATCH")


def test_task032_result_id_mismatch() -> None:
    """T033-008_TASK032_RESULT_ID_MISMATCH."""
    raw = copy_request()
    raw["task032_flow_state"]["result_id"] = "00000000-0000-0000-0000-000000000000"
    _blocked(raw, "SSHT_TASK032_RESULT_ID_MISMATCH")


def test_task032_request_evidence_missing() -> None:
    """T033-009_TASK032_REQUEST_EVIDENCE_MISSING."""
    raw = copy_request()
    raw["task032_request_evidence"] = None
    _blocked(raw, "SSHT_TASK032_REQUEST_EVIDENCE_INVALID")


def test_task032_request_hash_mismatch() -> None:
    """T033-010_TASK032_REQUEST_HASH_MISMATCH."""
    raw = copy_request()
    raw["task032_flow_state"]["request_hash"] = "0" * 64
    _blocked(raw, "SSHT_TASK032_REQUEST_HASH_MISMATCH")


def test_task031_geometry_replay_mismatch() -> None:
    """T033-011_TASK031_GEOMETRY_REPLAY_MISMATCH."""
    raw = copy_request()
    raw["task032_request_evidence"]["task031_result"]["geometry"]["geometry_id"] = "0" * 64
    refresh_task032_identity(raw)
    _blocked(raw, "SSHT_TASK031_GEOMETRY_REPLAY_MISMATCH")


def test_property_snapshot_hash_mismatch() -> None:
    """T033-012_PROPERTY_SNAPSHOT_HASH_MISMATCH."""
    raw = copy_request()
    raw["task032_request_evidence"]["property_snapshot"]["thermal_conductivity_w_m_k"] = "0.5990000"
    refresh_task032_identity(raw)
    _blocked(raw, "SSHT_PROPERTY_SNAPSHOT_HASH_MISMATCH")


def test_mass_flow_authority_hash_mismatch() -> None:
    """T033-013_MASS_FLOW_AUTHORITY_HASH_MISMATCH."""
    raw = copy_request()
    raw["task032_request_evidence"]["mass_flow_authority"]["mass_flow_rate_kg_s"] = "60.1"
    refresh_task032_identity(raw)
    _blocked(raw, "SSHT_MASS_FLOW_AUTHORITY_HASH_MISMATCH")


def test_same_case_binding_mismatch() -> None:
    """T033-014_SAME_CASE_BINDING_MISMATCH."""
    raw = copy_request()
    raw["task032_request_evidence"]["mass_flow_authority"]["shell_side_case_id"] = "OTHER"
    refresh_task032_identity(raw, refresh_mass_authority=True)
    _blocked(raw, "SSHT_SAME_CASE_BINDING_MISMATCH")
