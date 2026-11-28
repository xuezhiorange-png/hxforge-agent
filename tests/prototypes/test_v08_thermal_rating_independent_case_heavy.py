"""V08-03 independent-case live Task173 rating (legacy experimental path).

Formal PR CI: skipped — superseded by kernel V1 P2 (`v08_06_kernel_version_acceptance`).
Historical execution: workflow `v08-legacy-task173-experimental.yml` with
`HXFORGE_LEGACY_EXPERIMENTAL_V08_TASK173=1`.
Evidence: `docs/tasks/evidence/V08-07-task173-independent-heavy-supersession-r1.md`
"""

from __future__ import annotations

import os

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.pipeline import run_v08_thermal_rating
from tests.prototypes.v08_thermal_rating_test_support import (
    FIXTURE,
    FIXTURE_ALT,
    assert_full_rating_row,
    ready_handoff,
)

# Node migration: from tests/prototypes/test_v08_thermal_rating.py (pre-partition)


_LEGACY_TASK173_EXPERIMENTAL = (
    os.environ.get("HXFORGE_LEGACY_EXPERIMENTAL_V08_TASK173", "").strip() == "1"
)


@pytest.mark.timeout(7200)
def test_v08_03_independent_case_input_delta() -> None:
    """Non-reference case: target duty and tube inlet differ; handoff carries thermal binding."""
    if not _LEGACY_TASK173_EXPERIMENTAL:
        pytest.skip(
            "SUPERSEDED_BY_V08_KERNEL_P2: independent-case Task173 live rating replaced by "
            "FIXTURE_P2 kernel matrix (see V08-07-task173-independent-heavy-supersession-r1.md); "
            "set HXFORGE_LEGACY_EXPERIMENTAL_V08_TASK173=1 for historical replay"
        )
    n1, h1 = ready_handoff(FIXTURE)
    n2, h2 = ready_handoff(FIXTURE_ALT)
    assert h1.downstream_readiness == "THERMAL_HYDRAULIC_PARAMETERS_READY"
    assert h2.downstream_readiness == "THERMAL_HYDRAULIC_PARAMETERS_READY"
    assert n1.target_duty_w != n2.target_duty_w
    assert n1.tube_side.inlet_temperature_k != n2.tube_side.inlet_temperature_k
    assert h1.normalized_input_hash != h2.normalized_input_hash
    tb1 = h1.thermal_binding or {}
    tb2 = h2.thermal_binding or {}
    assert tb1.get("tube_inlet_temperature_k") != tb2.get("tube_inlet_temperature_k")

    r2 = run_v08_thermal_rating(n2, h2, provider=CoolPropProvider())
    assert str(n2.target_duty_w) == r2.target_duty_w
    if r2.engineering_acceptance == "PASS":
        assert r2.distinct_fully_converged_rating_count >= 2
        for row in r2.candidates_rated:
            if row.rating_outcome == "RATING_SUCCESS" and row.mesh_convergence_n1_n2_n4 == "PASS":
                assert_full_rating_row(row)
    else:
        assert r2.blocked_reason == "ENGINEERING_ACCEPTANCE_RATING"
        assert r2.model_blockers
