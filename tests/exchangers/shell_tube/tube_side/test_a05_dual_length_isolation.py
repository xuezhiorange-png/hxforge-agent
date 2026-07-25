"""§A05 — Dual-length isolation tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

import hexagent.exchangers.shell_tube.tube_side as ts


def _build_dual_lengths() -> tuple[ts.InternalFlowLengthAuthority, ts.HeatTransferLengthAuthority]:
    flow_hash = ts.internal_flow_authority_length_hash(
        Decimal("4.85000000"),
        ts.canonical_internal_flow_pair(),
        ts.canonical_internal_flow_pair(),
        ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
    )
    heat_hash = ts.heat_transfer_authority_length_hash(
        Decimal("4.85000000"),
        ts.canonical_heat_transfer_pair(),
        ts.canonical_heat_transfer_pair(),
        ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
    )
    flow = ts.InternalFlowLengthAuthority(
        length_id="L-IFA-001",
        length_m=Decimal("4.85000000"),
        start_plane=ts.canonical_internal_flow_pair(),
        end_plane=ts.canonical_internal_flow_pair(),
        authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        length_hash=flow_hash,
    )
    heat = ts.HeatTransferLengthAuthority(
        length_id="L-HTA-001",
        length_m=Decimal("4.85000000"),
        start_plane=ts.canonical_heat_transfer_pair(),
        end_plane=ts.canonical_heat_transfer_pair(),
        authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        length_hash=heat_hash,
    )
    return flow, heat


def test_a05_dual_lengths_have_separate_hashes() -> None:
    flow, heat = _build_dual_lengths()
    assert flow.length_hash != heat.length_hash


def test_a05_dual_lengths_cross_pair_rejected() -> None:
    with pytest.raises(ValueError):
        ts.InternalFlowLengthAuthority(
            length_id="L-IFA-001",
            length_m=Decimal("4.85000000"),
            start_plane=ts.canonical_heat_transfer_pair(),
            end_plane=ts.canonical_heat_transfer_pair(),
            authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            length_hash="0" * 64,
        )


def test_a05_length_non_positive_rejected() -> None:
    with pytest.raises(ValueError):
        ts.InternalFlowLengthAuthority(
            length_id="L-IFA-001",
            length_m=Decimal("0"),
            start_plane=ts.canonical_internal_flow_pair(),
            end_plane=ts.canonical_internal_flow_pair(),
            authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            length_hash="0" * 64,
        )


def test_a05_length_hash_64hex() -> None:
    with pytest.raises(ValueError):
        ts.InternalFlowLengthAuthority(
            length_id="L-IFA-001",
            length_m=Decimal("4.85000000"),
            start_plane=ts.canonical_internal_flow_pair(),
            end_plane=ts.canonical_internal_flow_pair(),
            authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            length_hash="not-hex",
        )