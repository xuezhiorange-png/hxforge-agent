"""R13 variable shell bundle selection (no mesh)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection_policy import (
    VARIABLE_SHELL_POLICY,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_live_scope import (
    check_experimental_live_rating_scope,
)
from prototypes.v07_general_rating_sizing_mvp.r12_25m_task174_blocker_analysis import (
    analyze_r12_25m_05m_task174_blocker,
)

REPO = Path(__file__).resolve().parents[2]
R13_CASE = REPO / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_variable_bundle_r13.json"
R12_CASE = REPO / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_target_directed_r12.json"


@pytest.fixture(scope="module")
def r13_case() -> Any:
    return load_general_engineering_case_json(R13_CASE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def r13_selection_outcome(r13_case: Any) -> CandidateSelectionOutcome:
    return enumerate_experimental_rating_candidates(r13_case)


def test_r13_scope_allows_non_c3_variable_shell(r13_case: Any) -> None:
    assert check_experimental_live_rating_scope(r13_case) == ("IN_SCOPE", None)
    assert r13_case.bind_task172_c3_reference_geometry is False


def test_r13_task174_ready_candidates_have_distinct_tube_counts(
    r13_selection_outcome: CandidateSelectionOutcome,
) -> None:
    sel = r13_selection_outcome
    assert sel.selection_reason == VARIABLE_SHELL_POLICY
    ready = [r for r in sel.records if r.rating_request_ready]
    tube_counts = {r.physical_tube_count for r in ready}
    assert len(tube_counts) >= 2
    shells = {r.shell_inside_diameter_m for r in ready}
    assert len(shells) >= 2


def test_r13_min_area_selection_excludes_r12_fingerprint(
    r13_selection_outcome: CandidateSelectionOutcome,
) -> None:
    sel = r13_selection_outcome
    selected = [r for r in sel.records if r.selected_for_rating]
    assert len(selected) == 2
    for row in selected:
        assert not (
            row.tube_length_m == "3.0"
            and row.baffle_spacing_m == "0.6"
            and row.shell_inside_diameter_m == "0.5"
            and row.physical_tube_count == 253
        )
    tube_counts = {r.physical_tube_count for r in selected}
    assert len(tube_counts) == 2


def test_r12_25m_blocker_is_pressure_domain_not_silent_pass() -> None:
    case = load_general_engineering_case_json(R12_CASE.read_text(encoding="utf-8"))
    doc = analyze_r12_25m_05m_task174_blocker(case)
    assert doc["task174_status"] == "BLOCKED"
    codes = [item["code"] for item in doc.get("blockers") or []]
    assert any("PRESSURE" in code or "PROPERTY" in code for code in codes)
