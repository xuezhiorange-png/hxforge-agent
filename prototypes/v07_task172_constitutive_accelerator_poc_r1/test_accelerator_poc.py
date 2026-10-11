"""POC tests: hash parity on frozen fixtures when memoization is transparent."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.task172_local_runtime import validate_request
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_task172_constitutive_accelerator_poc_r1.accelerator import (
    compare_outcomes,
    solve_with_memoized_eval_trial,
)
from tests.exchangers.shell_tube.test_task172_local_runtime import _request


def test_memoized_solve_matches_production_hash_on_frozen_fixture() -> None:
    request = _request()
    provider = CoolPropProvider(cache_size=512)
    baseline = validate_request(request, provider)
    report = solve_with_memoized_eval_trial(request, provider)
    comparison = compare_outcomes(baseline, report.outcome)
    assert comparison["same_outcome_type"]
    assert comparison["result_hash_parity"] is True
    assert report.stats.cache_hits >= 0
    assert report.stats.production_eval_calls <= report.stats.trial_invocations
