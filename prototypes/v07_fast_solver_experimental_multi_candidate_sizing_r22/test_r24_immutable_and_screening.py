"""R24 immutable pinned evidence and screening record integrity tests."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_multi_candidate_sizing import (
    experimental_multi_candidate_sizing,
    experimental_multi_candidate_sizing_from_admitted,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.immutable_pinned_evidence_admission import (
    verify_immutable_pinned_evidence,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.mandatory_screening import (
    execute_experimental_mandatory_screening,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.negative_injection_detailed import (
    run_negative_injection_detailed,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    admit_candidate_b_live_rating,
    admit_second_candidate_live_rating,
)

ROOT = Path(__file__).resolve().parents[2]
REQ = experimental_multi_candidate_sizing_requirement()


def test_immutable_pinned_r19_r21e_admission_pass() -> None:
    b = admit_candidate_b_live_rating(ROOT)
    second = admit_second_candidate_live_rating(ROOT)
    assert verify_immutable_pinned_evidence(ROOT, b) is None
    assert verify_immutable_pinned_evidence(ROOT, second) is None


def test_forged_screening_rule_provenance_blocked() -> None:
    b, second = admit_candidate_b_live_rating(ROOT), admit_second_candidate_live_rating(ROOT)
    expected = execute_experimental_mandatory_screening((b, second), REQ)
    records = list(expected.rule_records)
    records[1] = records[1].model_copy(
        update={"provenance": (("candidate_id", records[1].provenance[0][1]), ("tampered", "1"))}
    )
    forged = expected.model_copy(update={"rule_records": tuple(records)})
    result = experimental_multi_candidate_sizing_from_admitted(
        REQ,
        (b, second),
        evidence_root=ROOT,
        screening=forged,
    )
    assert result.status == "BLOCKED"
    assert result.blocked_code == "FORGED_MANDATORY_SCREENING_OUTCOME"


def test_negative_injection_detailed_all_pass() -> None:
    rows = run_negative_injection_detailed(ROOT)
    assert all(row["RESULT"] == "PASS" for row in rows)


def test_determinism_two_sizing_runs() -> None:
    a = experimental_multi_candidate_sizing(ROOT, REQ)
    b = experimental_multi_candidate_sizing(ROOT, REQ)
    assert a.result_hash == b.result_hash
    assert a.recommended_candidate_id == b.recommended_candidate_id
