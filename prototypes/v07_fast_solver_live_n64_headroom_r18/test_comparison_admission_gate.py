"""Strict comparison admission fail-closed behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    ComparisonAdmissionError,
    ComparisonSourcePin,
    admit_comparison_at_pin,
)

ROOT = Path(__file__).resolve().parents[2]


def test_missing_orchestrator_blocks() -> None:
    pin = ComparisonSourcePin(
        99,
        100,
        "docs/tasks/evidence/DOES-NOT-EXIST.live-orchestrator.json",
        "00" * 32,
        "docs/tasks/evidence/DOES-NOT-EXIST-result.json",
        "00" * 32,
        "deadbeef",
        0,
    )
    with pytest.raises(ComparisonAdmissionError) as exc:
        admit_comparison_at_pin(ROOT, pin)
    assert exc.value.code == "RESULT_ENVELOPE_MISSING"
