"""Failure-injection tests for fail-closed experimental rating."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalRatingBlocked,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_rate_candidate import (
    experimental_rate_candidate,
)
from prototypes.v07_fast_solver_replay_n8_r6.strict_replay import strict_replay_level

ROOT = pytest.importorskip("pathlib").Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def cached_replay_pair() -> tuple[dict, object, dict, object]:
    """One strict replay pair for fast fail-closed injection (module-scoped)."""
    from hexagent.properties.coolprop_provider import CoolPropProvider
    from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
        R9_RESULT_JSON_REL,
        R10_RESULT_JSON_REL,
    )
    from prototypes.v07_fast_solver_rating_authority_admission_r11 import (
        experimental_rate_candidate as rate_mod,
    )
    from prototypes.v07_fast_solver_rating_authority_admission_r11.evidence_chain import (
        verify_candidate_b_evidence_chain,
    )

    chain = verify_candidate_b_evidence_chain()
    request = rate_mod._load_frozen_candidate_request(CANDIDATE_B_ID)
    request_hash = t173.candidate_rating_request_hash(request)
    context = t173._candidate_context(request)
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    try:
        n32 = strict_replay_level(
            32,
            chain["r9_n32_body"],
            ROOT / R9_RESULT_JSON_REL,
            provider,
            context.shell_authority,
            rating_request_hash=request_hash,
        )
        n64 = strict_replay_level(
            64,
            chain["r10_n64_body"],
            ROOT / R10_RESULT_JSON_REL,
            provider,
            context.shell_authority,
            rating_request_hash=request_hash,
        )
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
    n32_run = n32.pop("_mesh_run")
    n64_run = n64.pop("_mesh_run")
    return n32, n32_run, n64, n64_run


def _replay_stub(
    subdivisions: int,
    body: dict,
    path: object,
    provider: object,
    shell_authority: object,
    *,
    rating_request_hash: str,
    cached_replay_pair: tuple[dict, object, dict, object],
) -> dict:
    n32_meta, n32_run, n64_meta, n64_run = cached_replay_pair
    if subdivisions == 32:
        return {**n32_meta, "_mesh_run": n32_run}
    return {**n64_meta, "_mesh_run": n64_run}


def _make_replay_fn(cached_replay_pair: tuple[dict, object, dict, object]):
    def _fn(*args: object, **kwargs: object) -> dict:
        return _replay_stub(*args, **kwargs, cached_replay_pair=cached_replay_pair)

    return _fn


def test_trajectory_projection_failure_blocks(
    cached_replay_pair: tuple[dict, object, dict, object],
) -> None:
    stub = _make_replay_fn(cached_replay_pair)
    patch_target = (
        "prototypes.v07_fast_solver_rating_authority_admission_r11"
        ".experimental_rate_candidate.build_accepted_trajectory_projection"
    )
    with patch(
        patch_target,
        side_effect=t173._Stage3Failure("INJECTED_TRAJECTORY_FAILURE"),
    ):
        outcome = experimental_rate_candidate(CANDIDATE_B_ID, _replay_fn=stub)
    assert isinstance(outcome, ExperimentalRatingBlocked)
    assert outcome.blocked_code == "ACCEPTED_TRAJECTORY_PROJECTION_FAILED"


def test_cell_count_failure_blocks(
    cached_replay_pair: tuple[dict, object, dict, object],
) -> None:
    stub = _make_replay_fn(cached_replay_pair)
    with patch(
        (
            "prototypes.v07_fast_solver_rating_authority_admission_r11"
            ".experimental_rate_candidate.verify_accepted_cell_count"
        ),
        return_value=False,
    ):
        outcome = experimental_rate_candidate(CANDIDATE_B_ID, _replay_fn=stub)
    assert isinstance(outcome, ExperimentalRatingBlocked)
    assert outcome.blocked_code == "ACCEPTED_CELL_COUNT_MISMATCH"


def test_wall_extrema_failure_blocks(
    cached_replay_pair: tuple[dict, object, dict, object],
) -> None:
    stub = _make_replay_fn(cached_replay_pair)
    with patch(
        (
            "prototypes.v07_fast_solver_rating_authority_admission_r11"
            ".experimental_rate_candidate.verify_wall_extrema_from_cells"
        ),
        return_value=False,
    ):
        outcome = experimental_rate_candidate(CANDIDATE_B_ID, _replay_fn=stub)
    assert isinstance(outcome, ExperimentalRatingBlocked)
    assert outcome.blocked_code == "CELL_ENERGY_OR_WALL_VERIFICATION_FAILED"
