"""R27E thermal regime and N1 convergence recovery."""

from __future__ import annotations

import pytest

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_BLOCKED,
    run_experimental_engineering_rating,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context
from prototypes.v07_general_rating_sizing_mvp.r27e_targeted_recovery import (
    R27D_RECOVERY_CANDIDATE_IDS,
    run_r27e_targeted_recovery,
)
from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case


def test_r27e_recovery_candidate_id_list_length() -> None:
    assert len(R27D_RECOVERY_CANDIDATE_IDS) == 5


@pytest.mark.slow
def test_r27e_065_shell_candidate_transition_stays_blocked_without_correlation() -> None:
    """Laminar tube HTC is admitted on MVP boundary; transition Re still blocks."""
    case = shared_r26e_engineering_case()
    sel = enumerate_experimental_rating_candidates(
        case, rating_selection_policy="r27d", rate_all_distinct_task174_ready=True
    )
    cid = "6ec6323f-402b-5d5f-90ef-2aab514d37de"
    native = build_native_cell_context(case, selection=sel, candidate_id=cid)
    n1 = run_experimental_engineering_rating(case, subdivisions=1, native=native)
    assert n1.status == ENGINEERING_BLOCKED
    assert n1.failure_code == "_RuntimeFailure"
    assert any("THERMAL_CORRELATION_UNAVAILABLE" in d for d in n1.diagnostics)


@pytest.mark.slow
def test_r27e_targeted_recovery_runs_five_candidates() -> None:
    report = run_r27e_targeted_recovery(shared_r26e_engineering_case())
    assert len(report["recovery_candidates"]) == 5
    by_id = {row["candidate_id"]: row for row in report["recovery_candidates"]}
    assert by_id["6ec6323f-402b-5d5f-90ef-2aab514d37de"]["recovery_outcome_class"] == (
        "MODEL_NOT_APPLICABLE"
    )
    assert by_id["09dac82a-0a84-5bc2-9b3f-93aaecd30a9e"]["recovery_outcome_class"] == (
        "FULL_RATING_CONVERGED"
    )
