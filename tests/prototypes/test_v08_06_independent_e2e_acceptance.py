"""V08-06 acceptance matrix (targeted; no multi-hour Task173 campaigns)."""

from __future__ import annotations

from prototypes.v08_thermal_rating.v08_06_independent_e2e_acceptance import (
    TASK_ID,
    run_v08_06_acceptance_matrix,
)


def test_v08_06_task_id() -> None:
    assert TASK_ID == "V08-06"


def test_acceptance_matrix_fast_without_live_rating() -> None:
    payload = run_v08_06_acceptance_matrix(
        attempt_live_rating_r0_only=False,
        max_candidates=24,
    )
    assert payload["V08_06_IMPLEMENTATION_COMPLETE"] is True
    assert payload["V08_06_FORMAL_ACCEPTANCE"] is False
    assert payload["V08_07_READY"] is False
    assert payload["DETERMINISM_STATUS"] is True
    assert payload["SUCCESSFUL_LIVE_E2E_COUNT"] == 0
    assert payload["FALSE_FEASIBLE_COUNT"] == 0
    assert payload["N2_INFEASIBLE_CASE_STATUS"] in (
        "NO_FEASIBLE_DESIGN",
        "OUT_OF_ENVELOPE",
        "INVALID_INPUT",
    )
    assert payload["M1_DUTY_RESPONSE"] is True
    assert len(payload["VERSION_REMAINING_BLOCKERS"]) >= 4


def test_n1_invalid_not_counted_as_design_success() -> None:
    payload = run_v08_06_acceptance_matrix(
        attempt_live_rating_r0_only=False,
        max_candidates=16,
    )
    n1 = payload["case_records"]["N1"]
    assert n1["charter_design_success"] is False
    assert n1["status"] in ("INVALID_INPUT", "OUT_OF_ENVELOPE", "CHAIN_COMPLETED")
