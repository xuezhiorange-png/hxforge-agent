"""Read-only shared R26E case + Task168/Task174 selection for R26G / R26G-A fast tests."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    EngineeringCase,
    load_general_engineering_case_json,
)

R26E_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures/r26e_multi_candidate_engineering_sizing_case.json"
)
R26G_MIDDLE_CANDIDATE_ID = "3c129a7f-eba7-5b5a-9b86-5b2ce9629dae"


@lru_cache(maxsize=1)
def shared_r26e_engineering_case() -> EngineeringCase:
    return load_general_engineering_case_json(R26E_FIXTURE_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def shared_r26e_experimental_rating_selection() -> CandidateSelectionOutcome:
    return enumerate_experimental_rating_candidates(shared_r26e_engineering_case())
