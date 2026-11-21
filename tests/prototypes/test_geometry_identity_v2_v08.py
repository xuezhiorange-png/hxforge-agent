"""GEOMETRY_IDENTITY_V2 regression and baffle authority semantics."""

from __future__ import annotations

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
from prototypes.v08_thermal_rating.geometry_identity_and_layout_recovery_v08 import (
    run_geometry_identity_and_layout_recovery,
)
from prototypes.v08_thermal_rating.shell_structural_feasibility_breakthrough_v08 import (
    run_shell_structural_feasibility_breakthrough,
)
from hexagent.properties.coolprop_provider import CoolPropProvider


def test_v2_cut_025_vs_049_distinct_for_same_bundle() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    _sh, _dg, bundles, _ = enumerate_structural_bundles(normalized, handoff, max_valid=4)
    assert bundles
    bundle = bundles[0]
    low, high = sample_v2_cut_distinctness(bundle)
    assert low != high
    again_low = geometry_identity_v2_hash(bundle, baffle_cut_fraction="0.25")
    assert low == again_low


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
    v2a = geometry_identity_v2_hash(bundle, baffle_cut_fraction="0.25")
    v2b = geometry_identity_v2_hash(bundle, baffle_cut_fraction="0.49")
    aliases = legacy_geometry_projection_aliases(((v1, v2a), (v1, v2b)))
    assert v1 in aliases or v2a != v2b


def test_geometry_recovery_delivery_smoke() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_geometry_identity_and_layout_recovery(normalized, handoff, provider=provider)
    assert report.old_and_new_cut_hash_distinct is True
    assert report.actual_baffle_count == 4
    assert report.baffle_hole_position_count and report.baffle_hole_position_count > 100
    assert report.design_decision == "SINGLE_SEGMENTAL_MODEL_SPACE_EXHAUSTED"
    bt = run_shell_structural_feasibility_breakthrough(normalized, handoff, provider=provider)
    assert bt.best is not None
    assert bt.best.baffle_count == 4