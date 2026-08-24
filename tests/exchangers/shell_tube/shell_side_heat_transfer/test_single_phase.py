"""TASK033 applicability and strict Reynolds-domain tests."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_heat_transfer import validate_request
from tests.exchangers.shell_tube.shell_side_heat_transfer.test_models import (
    copy_request,
    refresh_geometry_identity,
    refresh_task032_identity,
)


def test_upstream_applicability_mismatch() -> None:
    """T033-015_UPSTREAM_APPLICABILITY_MISMATCH."""
    raw = copy_request()
    raw["task032_flow_state"]["rheology_model"] = "NON_NEWTONIAN"
    refresh_task032_identity(raw)
    result = validate_request(raw)
    assert any(item.code == "SSHT_RHEOLOGY_MODEL_UNSUPPORTED" for item in result.blockers)


def test_flow_region_mismatch() -> None:
    """T033-016_FLOW_REGION_MISMATCH."""
    raw = copy_request()
    raw["task032_request_evidence"]["task031_result"]["geometry"]["flow_region_identity"] = "OTHER"
    refresh_geometry_identity(raw)
    result = validate_request(raw)
    assert any(item.code == "SSHT_FLOW_REGION_UNSUPPORTED" for item in result.blockers)


def test_reynolds_lower_bound_is_exclusive() -> None:
    """T033-017_REYNOLDS_LOWER_BOUND_EXCLUSIVE."""
    raw = copy_request()
    raw["task032_flow_state"]["shell_side_reynolds_number"] = "2000"
    refresh_task032_identity(raw)
    result = validate_request(raw)
    assert result.heat_transfer is None
    assert any(item.code == "SSHT_REYNOLDS_OUTSIDE_CORRELATION_DOMAIN" for item in result.blockers)


def test_reynolds_upper_bound_is_exclusive() -> None:
    """T033-018_REYNOLDS_UPPER_BOUND_EXCLUSIVE."""
    raw = copy_request()
    raw["task032_flow_state"]["shell_side_reynolds_number"] = "1000000"
    refresh_task032_identity(raw)
    result = validate_request(raw)
    assert result.heat_transfer is None
    assert any(item.code == "SSHT_REYNOLDS_OUTSIDE_CORRELATION_DOMAIN" for item in result.blockers)
