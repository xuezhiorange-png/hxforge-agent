"""R27E: seven-candidate numeric regression vs frozen R27D baseline fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.r27e_reference_regression import (
    capture_reference_metrics,
    compare_reference_metrics,
    load_reference_fixture,
)
from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/r27e_r27d_seven_reference_baseline.json"


@pytest.mark.slow
def test_r27e_seven_reference_candidates_match_r27d_baseline() -> None:
    if not _FIXTURE.is_file():
        pytest.skip("baseline fixture not materialized yet")
    baseline = load_reference_fixture(_FIXTURE)
    current = capture_reference_metrics(shared_r26e_engineering_case())
    deltas = compare_reference_metrics(baseline, current)
    assert not deltas, deltas
