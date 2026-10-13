"""Same-run endpoint reuse must not re-march mesh at bracket endpoints."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from prototypes.v07_fast_solver_n16_verified_bracket_r8.narrow_bracket_solver import (
    solve_verified_narrow_bracket_outer_boundary,
)
from prototypes.v07_fast_solver_verified_bracket.same_run_endpoints import (
    SameRunBracketEndpoints,
)


def _high_trial() -> t173._OuterTrial:
    obs = MagicMock()
    obs.terminal_boundary_residual_j_kg = Decimal("1")
    obs.terminal_boundary_residual_k = Decimal("1e-9")
    run = MagicMock()
    run.observables = obs
    run.mesh_result_hash = "highhash"
    return t173._OuterTrial("VALID_TRAJECTORY", Decimal("2"), mesh_run=run, diagnostics=())


def test_reuse_skips_endpoint_classify_calls() -> None:
    endpoints = SameRunBracketEndpoints(
        run_session_id="sess-1",
        authority_id="AUTH",
        subdivisions=8,
        rating_request_hash="rh",
        h_low_j_kg="1",
        h_high_j_kg="2",
        low_trial=t173._OuterTrial("LOW_SIDE_DOMAIN_INFEASIBLE", Decimal("1"), diagnostics=()),
        high_trial=_high_trial(),
    )
    calls: list[Decimal] = []

    def fake_classify(_sub: int, enthalpy: Decimal, *_a: object, **_k: object) -> t173._OuterTrial:
        calls.append(enthalpy)
        return _high_trial()

    with patch(
        "prototypes.v07_fast_solver_n16_verified_bracket_r8.narrow_bracket_solver._classify_fast_trial",
        side_effect=fake_classify,
    ):
        with patch(
            "prototypes.v07_fast_solver_n16_verified_bracket_r8.narrow_bracket_solver._solve_bisection_on_bracket",
            return_value=_high_trial().mesh_run,
        ):
            with patch(
                "prototypes.v07_fast_solver_n16_verified_bracket_r8.narrow_bracket_solver.t173._terminal_tolerance_pass",
                return_value=True,
            ):
                result, rev = solve_verified_narrow_bracket_outer_boundary(
                    8,
                    provider=MagicMock(),
                    shell_authority=MagicMock(),
                    h_low_j_kg="1",
                    h_high_j_kg="2",
                    authority_id="AUTH",
                    rating_request_hash="rh",
                    same_run_endpoints=endpoints,
                    run_session_id="sess-1",
                )
    assert rev["duplicate_endpoint_solves_removed"] is True
    assert Decimal("1") not in calls
    assert Decimal("2") not in calls
    assert result.status == "TERMINAL_ACCEPTED"


def test_reuse_rejects_session_mismatch() -> None:
    endpoints = SameRunBracketEndpoints(
        run_session_id="sess-1",
        authority_id="AUTH",
        subdivisions=8,
        rating_request_hash="rh",
        h_low_j_kg="1",
        h_high_j_kg="2",
        low_trial=t173._OuterTrial("LOW_SIDE_DOMAIN_INFEASIBLE", Decimal("1"), diagnostics=()),
        high_trial=_high_trial(),
    )
    result, rev = solve_verified_narrow_bracket_outer_boundary(
        8,
        provider=MagicMock(),
        shell_authority=MagicMock(),
        h_low_j_kg="1",
        h_high_j_kg="2",
        authority_id="AUTH",
        rating_request_hash="rh",
        same_run_endpoints=endpoints,
        run_session_id="sess-OTHER",
    )
    assert result.status == "BLOCKED"
    assert result.blocked_code == "BRACKET_REVALIDATION_FAILED"
    assert rev["duplicate_endpoint_solves_removed"] is False
