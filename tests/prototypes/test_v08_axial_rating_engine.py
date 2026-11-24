"""V08-03 isolated axial engine: 330 kW primary, 250 kW regression isolation."""

from __future__ import annotations

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CASE_330KW_ID,
    closeout_one_candidate,
    load_case_bindings,
)
from prototypes.v08_thermal_rating.case_identity_v08 import (
    CASE_250KW_ID,
    FIXTURE_250,
    FIXTURE_330,
    build_case_identity_bundle,
)
from tests.prototypes.conftest_v08_axial_330 import Fixture330EngineContext

pytest_plugins = ["tests.prototypes.conftest_v08_axial_330"]


def test_330kw_primary_fixture_identity_distinct_from_250kw() -> None:
    bundle = build_case_identity_bundle()
    assert bundle["CASE_CROSS_CONTAMINATION"] is False
    row_330 = bundle["CASE_330KW_IDENTITY"]
    row_250 = bundle["CASE_250KW_IDENTITY"]
    assert row_330["engineering_case_id"] == CASE_330KW_ID
    assert row_250["case_label"] == CASE_250KW_ID
    assert row_330["normalized_input_hash"] != row_250["normalized_input_hash"]


@pytest.mark.timeout(1800)
def test_330kw_outer_search_direction_and_n1_closeout(
    fixture_330_engine_context: Fixture330EngineContext,
) -> None:
    """Corrected outer search must UPDATE_H_HIGH on VALID, not inflate h_low."""
    ctx = fixture_330_engine_context
    assert ctx.normalized.engineering_case_id == CASE_330KW_ID
    n1 = ctx.n1
    decisions = {step.decision_update for step in n1.search_trace}
    assert "UPDATE_H_HIGH" in decisions or "UPDATE_H_HIGH_BINARY64_STEP" in decisions
    assert "INITIAL_HIGH_ENDPOINT" in decisions
    assert not any(d == "UPDATE_H_LOW_VALID" for d in decisions)
    closeout = closeout_one_candidate(ctx.bindings, ctx.provider, run_production=False)
    phys = closeout.physical
    assert phys.energy_balance_pass is True
    assert phys.task172_numerical_hole_count == 0
    assert phys.total_duty_w is not None
    assert phys.duty_vs_target in {"AT_OR_ABOVE_TARGET", "BELOW_TARGET"}
    assert phys.evidence  # includes before/after terminal residual strings


def test_250kw_regression_fixture_not_mixed_with_330kw() -> None:
    """250 kW regression uses its own normalized hash; no shared rating structure with 330 kW."""
    provider = CoolPropProvider()
    _n250, h250, _ = load_case_bindings(FIXTURE_250, provider=provider)
    _n330, h330, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert h250.normalized_input_hash != h330.normalized_input_hash
