"""Experimental geometry co-optimization search (hydraulic-first)."""

from __future__ import annotations

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.experimental_geometry_discrete_space_v08 import (
    EXPERIMENTAL_GEOMETRY_LABEL,
)
from prototypes.v08_thermal_rating.full_path_geometry_cooptimization_v08 import (
    run_full_path_geometry_cooptimization,
)


def test_cooptimization_generates_experimental_structures() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_full_path_geometry_cooptimization(
        normalized, handoff, provider=provider, max_valid=32
    )
    assert report.baseline_full_path_results_corrected is True
    assert report.experimental_geometry_count > 0
    assert report.structurally_admitted_count >= 3
    exp = [
        r for r in report.rows if r.manufacturing_geometry_authority == EXPERIMENTAL_GEOMETRY_LABEL
    ]
    assert exp
    hashes = {r.geometry_projection_hash for r in report.rows}
    assert len(hashes) >= 3
    assert report.full_path_all_scenario_feasible_count == 0
