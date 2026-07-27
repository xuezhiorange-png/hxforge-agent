"""§A02 / §2.2 — TASK-025 owned enum tests."""

from __future__ import annotations

import pytest

import hexagent.exchangers.shell_tube.tube_side as ts


def test_a02_flow_path_mode_member_count() -> None:
    assert len(ts.FlowPathMode) == 4


def test_a02_hydraulic_authority_mode_member_count() -> None:
    assert len(ts.HydraulicAuthorityMode) == 3


def test_a02_reference_plane_token_member_count() -> None:
    assert len(ts.ReferencePlaneToken) == 4


def test_a02_reference_plane_pair_two_pairs_only() -> None:
    """§2.2 — only the two ordered pairs are accepted."""
    internal_pair = ts.canonical_internal_flow_pair()
    heat_pair = ts.canonical_heat_transfer_pair()
    assert internal_pair.kind == "internal_flow"
    assert heat_pair.kind == "heat_transfer"

    # Cross-pair construction is rejected at __init__.
    with pytest.raises(ValueError):
        ts.ReferencePlanePair(
            ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE,
            ts.ReferencePlaneToken.TUBE_HEAT_TRANSFER_END_PLANE,
        )


def test_a02_reference_plane_pair_swapped_rejected() -> None:
    with pytest.raises(ValueError):
        ts.ReferencePlanePair(
            ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_END_PLANE,
            ts.ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE,
        )


def test_a02_reference_plane_pair_non_token_rejected() -> None:
    with pytest.raises(ValueError):
        ts.ReferencePlanePair("start", "end")  # type: ignore[arg-type]


def test_a02_canonical_bytes_stable() -> None:
    assert (
        ts.FlowPathMode.STRAIGHT_TUBE_PARALLEL_FLOW.canonical_utf8_bytes
        == b"STRAIGHT_TUBE_PARALLEL_FLOW"
    )


# ruff: noqa: E501
