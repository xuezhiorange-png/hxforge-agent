"""Shell Δp lower bounds and proven infeasibility under R27B."""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    load_case_bindings,
    resolve_candidate_bindings_by_id,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.shell_hydraulic_lower_bound_v08 import (
    analyze_shell_hydraulic_lower_bound,
)
from prototypes.v08_thermal_rating.shell_hydraulic_redirection_v08 import (
    run_shell_hydraulic_redirection,
)
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    task174_hydraulic_postpass_from_bindings,
)
from tests.prototypes.test_v08_frozen_candidate_resolve import FROZEN_ID


def test_frozen_baseline_proven_infeasible_and_budget_magnitudes() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings is not None
    report = analyze_shell_hydraulic_lower_bound(bindings)
    mid = next(s for s in report.scenarios if s.scenario_key == "mid_band")
    assert mid.proven_hydraulic_infeasible_under_assumed_k is True
    assert Decimal(mid.shell_nozzle_pair_min_dp_pa) == pytest.approx(Decimal("498.904"), rel=1e-3)
    assert Decimal(mid.remaining_internal_budget_pa) == pytest.approx(Decimal("635.816"), rel=1e-3)
    high = next(s for s in report.scenarios if s.scenario_key == "high_loss_sensitivity")
    assert Decimal(high.shell_nozzle_pair_min_dp_pa) == pytest.approx(Decimal("598.684"), rel=1e-3)
    assert report.bell_reduction_required_for_mid_feasibility_pa is not None
    assert Decimal(report.bell_reduction_required_for_mid_feasibility_pa) == pytest.approx(
        Decimal("541.285"), rel=1e-3
    )


def test_postpass_does_not_hardcode_sat_hydraulic_constraint() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings is not None
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
    shell_margin = Decimal(postpass["shell_dp_margin_pa"])
    if shell_margin < 0:
        assert postpass["hydraulic_constraint_status"] == "NOT_SATISFIED"
    else:
        assert postpass["hydraulic_constraint_status"] == "SATISFIED"
    assert "ok" in postpass["coolprop_outlet_domain_checks"]["tube"]
    assert postpass["shell_dp_components_pa"]["central_crossflow"]


def test_geometry_dedup_stats_and_no_mid_feasible() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_shell_hydraulic_redirection(normalized, handoff, provider=provider)
    assert report.distinct_structural_geometries <= report.total_search_records
    assert report.full_path_mid_feasible_count == 0
    assert report.upstream_hydraulic_authority_valid is True
    assert report.duplicate_dp_components == 0
    assert all(r.thermal_duty_status == "THERMAL_DUTY=NOT_EVALUATED" for r in report.rows)
