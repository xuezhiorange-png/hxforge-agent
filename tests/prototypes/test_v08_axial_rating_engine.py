"""V08-03 isolated axial engine: 330 kW primary, 250 kW regression isolation."""

from __future__ import annotations

import os

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CASE_330KW_ID,
    build_candidate_rating_bindings,
    closeout_one_candidate,
    enumerate_structural_bundles,
    load_case_bindings,
)
from prototypes.v08_thermal_rating.case_identity_v08 import (
    CASE_250KW_ID,
    FIXTURE_250,
    FIXTURE_330,
    build_case_identity_bundle,
)


def test_330kw_primary_fixture_identity_distinct_from_250kw() -> None:
    bundle = build_case_identity_bundle()
    assert bundle["CASE_CROSS_CONTAMINATION"] is False
    row_330 = bundle["CASE_330KW_IDENTITY"]
    row_250 = bundle["CASE_250KW_IDENTITY"]
    assert row_330["engineering_case_id"] == CASE_330KW_ID
    assert row_250["case_label"] == CASE_250KW_ID
    assert row_330["normalized_input_hash"] != row_250["normalized_input_hash"]


@pytest.mark.timeout(1800)
def test_330kw_isolated_n1_vs_production_split_first_candidate() -> None:
    """One structure: physics-layer N1 trial vs production C-ULP (no VALIDATED claim)."""
    os.environ["V08_AXIAL_BRACKET_MAX_ITER"] = "12"
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID
    space_hash, t168_digest, bundles = enumerate_structural_bundles(
        normalized, handoff, max_valid=1
    )
    bindings = build_candidate_rating_bindings(
        bundles[0],
        space_hash=space_hash,
        t168_digest=t168_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
    )
    assert bindings is not None
    closeout = closeout_one_candidate(bindings, provider, run_production=False)
    phys = closeout.physical
    assert phys.energy_balance_pass is True
    assert phys.task172_numerical_hole_count == 0
    assert phys.total_duty_w is not None
    assert phys.duty_vs_target == "BELOW_TARGET"
    assert phys.terminal_within_production_tolerance is False
    assert closeout.delivery == "B"
    assert "TERMINAL_BOUNDARY" in phys.first_blocker or "TOTAL_DUTY" in phys.first_blocker


def test_250kw_regression_fixture_not_mixed_with_330kw() -> None:
    """250 kW regression uses its own normalized hash; no shared rating structure with 330 kW."""
    provider = CoolPropProvider()
    _n250, h250, _ = load_case_bindings(FIXTURE_250, provider=provider)
    _n330, h330, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert h250.normalized_input_hash != h330.normalized_input_hash
