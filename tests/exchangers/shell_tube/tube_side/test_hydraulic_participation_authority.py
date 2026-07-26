"""§5.4 / §9.4 — Hydraulic participation authority tests."""

from __future__ import annotations

import pytest

import hexagent.exchangers.shell_tube.tube_side as ts


def test_participation_authority_constructed() -> None:
    pa = ts.Task025HydraulicParticipationAuthority(
        all_layout_position_ids=("P000", "P001", "P002"),
        active_position_ids=("P000", "P001"),
        inactive_position_ids=("P002",),
        authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        evidence_refs=("ref1",),
        hydraulic_authority_hash="0" * 64,
    )
    assert pa.active_position_ids == ("P000", "P001")


def test_participation_authority_empty_evidence_rejected() -> None:
    with pytest.raises(ValueError):
        ts.Task025HydraulicParticipationAuthority(
            all_layout_position_ids=("P000",),
            active_position_ids=("P000",),
            inactive_position_ids=(),
            authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            evidence_refs=("",),  # type: ignore[arg-type]
            hydraulic_authority_hash="0" * 64,
        )


def test_participation_authority_invalid_hash_rejected() -> None:
    with pytest.raises(ValueError):
        ts.Task025HydraulicParticipationAuthority(
            all_layout_position_ids=("P000",),
            active_position_ids=("P000",),
            inactive_position_ids=(),
            authority_mode=ts.HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
            evidence_refs=("ref",),
            hydraulic_authority_hash="not-hex",
        )


def test_participation_authority_non_owned_mode_rejected() -> None:
    with pytest.raises(ValueError):
        ts.Task025HydraulicParticipationAuthority(
            all_layout_position_ids=("P000",),
            active_position_ids=("P000",),
            inactive_position_ids=(),
            authority_mode="BAD",  # type: ignore[arg-type]
            evidence_refs=("ref",),
            hydraulic_authority_hash="0" * 64,
        )
