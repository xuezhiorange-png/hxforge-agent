"""GEOMETRY_IDENTITY_V2 regression and baffle authority semantics."""

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_identity_v2_hash,
    geometry_projection_hash_v1,
    legacy_geometry_projection_aliases,
    resolve_baffle_authority,
    sample_v2_cut_distinctness,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    enumerate_structural_bundles,
    load_case_bindings,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.recovered_shell_052_full_chain_v08 import (
    run_recovered_shell_052_full_chain,
)
from prototypes.v08_thermal_rating.shell_structural_feasibility_breakthrough_v08 import (
    run_shell_structural_feasibility_breakthrough,
)
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    BREAKTHROUGH_DISCRETE_SPACE_PATH,
    _enumerate_with_payload,
)


def test_v2_cut_distinct_across_authoritative_bundles() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    _sh, _dg, r1_bundles, _ = enumerate_structural_bundles(normalized, handoff, max_valid=4)
    assert r1_bundles
    _, _d, cut035_valid, _ = _enumerate_with_payload(
        normalized,
        handoff,
        discrete_path=BREAKTHROUGH_DISCRETE_SPACE_PATH,
        baffle_cut_override=Decimal("0.35"),
    )
    assert cut035_valid
    low, high = sample_v2_cut_distinctness(r1_bundles[0], cut035_valid[0])
    assert low != high


def test_v2_deterministic_for_same_bundle() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    _sh, _dg, bundles, _ = enumerate_structural_bundles(normalized, handoff, max_valid=4)
    bundle = bundles[0]
    assert geometry_identity_v2_hash(bundle) == geometry_identity_v2_hash(bundle)


def test_baffle_count_is_four_not_position_count() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    _sh, _dg, bundles, _ = enumerate_structural_bundles(normalized, handoff, max_valid=4)
    bundle = bundles[0]
    auth = resolve_baffle_authority(candidate=bundle.candidate, bundle=bundle.bundle)
    assert auth.baffle_count_authoritative == 4
    assert auth.baffle_hole_position_count > 4


def test_legacy_v1_can_alias_different_v2_cuts() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    _sh, _dg, bundles, _ = enumerate_structural_bundles(normalized, handoff, max_valid=4)
    bundle = bundles[0]
    v1 = geometry_projection_hash_v1(bundle)
    v2a = geometry_identity_v2_hash(bundle)
    _, _d, other_valid, _ = _enumerate_with_payload(
        normalized,
        handoff,
        discrete_path=BREAKTHROUGH_DISCRETE_SPACE_PATH,
        baffle_cut_override=Decimal("0.35"),
    )
    v2b = geometry_identity_v2_hash(other_valid[0])
    legacy_geometry_projection_aliases(((v1, v2a), (v1, v2b)))
    assert v2a != v2b


def test_recovered_shell_052_full_chain_smoke() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_recovered_shell_052_full_chain(normalized, handoff, provider=provider)
    assert report.shell_052_task168 == "PASS"
    assert report.geometry_identity_v2 is not None
    assert report.physical_tube_count is not None
    assert report.baffle_count == 4
    assert report.recovered is not None
    assert str(report.recovered.structural_bundle.shell_record.shell_inside_diameter_m) == "0.52"
    assert report.design_decision in (
        "MID_FEASIBLE_FOUND",
        "RECOVERED_LAYOUT_HYDRAULIC_BLOCKED",
    )
    bt = run_shell_structural_feasibility_breakthrough(normalized, handoff, provider=provider)
    assert bt.best is not None
    assert bt.best.baffle_count == 4
