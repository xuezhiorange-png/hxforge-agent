"""Fixed nozzle design reused across K scenarios."""

from __future__ import annotations

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    load_case_bindings,
    resolve_candidate_bindings_by_id,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from tests.prototypes.test_v08_frozen_candidate_resolve import FROZEN_ID


def test_same_nozzle_geometry_all_three_k_scenarios() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings is not None
    report = run_autonomous_nozzle_full_path(bindings)
    assert report.nozzle_same_geometry_all_scenarios is True
    assert len(report.scenarios) == 3
    for row in report.scenarios:
        if row.shell_full_path_dp_pa is not None:
            assert row.shell_dp_authority == "VERIFIED_ASSUMPTION_FULL_PATH_DP"
        elif row.tube_full_path_dp_pa is None:
            assert row.shell_dp_authority == "FULL_PATH_NOT_COMPUTED"
    assert report.task174_partial.authority == "TASK174_PARTIAL_DP"
    assert report.installation.manufacturing_size_authority == "PROVISIONAL"
    assert report.installation.mechanical_clearance == "UNRESOLVED"


def test_full_path_not_filled_with_side_model_estimate() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings is not None
    report = run_autonomous_nozzle_full_path(bindings)
    mid = next(s for s in report.scenarios if s.scenario_key == "mid_band")
    assert mid.hydraulic_check == "BLOCKED"
    if mid.shell_full_path_dp_pa is None:
        assert mid.shell_dp_authority == "FULL_PATH_NOT_COMPUTED"
