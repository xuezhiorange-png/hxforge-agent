"""§A06 — Reference plane closed set tests."""

from __future__ import annotations

import pytest

import hexagent.exchangers.shell_tube.tube_side as ts


def test_a06_internal_flow_pair_accepted() -> None:
    pair = ts.canonical_internal_flow_pair()
    assert pair.start == ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE
    assert pair.end == ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_END_PLANE


def test_a06_heat_transfer_pair_accepted() -> None:
    pair = ts.canonical_heat_transfer_pair()
    assert pair.start == ts.ReferencePlaneToken.TUBE_HEAT_TRANSFER_START_PLANE
    assert pair.end == ts.ReferencePlaneToken.TUBE_HEAT_TRANSFER_END_PLANE


def test_a06_cross_pair_rejected() -> None:
    with pytest.raises(ValueError):
        ts.ReferencePlanePair(
            ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE,
            ts.ReferencePlaneToken.TUBE_HEAT_TRANSFER_END_PLANE,
        )


def test_a06_swapped_rejected() -> None:
    with pytest.raises(ValueError):
        ts.ReferencePlanePair(
            ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_END_PLANE,
            ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE,
        )


def test_a06_unknown_token_rejected() -> None:
    """§2.6 — only ReferencePlaneToken is accepted as start/end."""
    # The construction rejects any non-ReferencePlaneToken inputs.
    with pytest.raises(ValueError):
        ts.ReferencePlanePair("start", "end")  # type: ignore[arg-type]