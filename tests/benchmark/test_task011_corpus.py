from __future__ import annotations

from pathlib import Path

from hexagent.benchmark_cases.corpus import approved_cases
from hexagent.benchmark_cases.validation import validate_corpus


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_task011_approved_benchmark_corpus_validates() -> None:
    validate_corpus(_repo_root())


def test_task011_corpus_contains_exactly_twenty_approved_cases() -> None:
    cases = approved_cases()

    assert len(cases) == 20
    assert all(case["approval_status"] == "approved" for case in cases)
    expected_ids = {f"task011_case_{index:02d}" for index in range(1, 21)}
    actual_ids = {case["case_id"] for case in cases}
    assert actual_ids == expected_ids


def test_task011_synthetic_cases_are_explicitly_marked() -> None:
    synthetic_ids = {
        case["case_id"] for case in approved_cases() if case.get("is_synthetic") is True
    }

    assert synthetic_ids == {
        "task011_case_03",
        "task011_case_06",
        "task011_case_09",
        "task011_case_12",
        "task011_case_15",
        "task011_case_18",
    }
