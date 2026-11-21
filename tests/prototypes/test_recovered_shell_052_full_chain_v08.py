"""Full-chain validation for recovered 0.52 m shell layout."""

from __future__ import annotations

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    resolve_recovered_shell_052_bundle,
)
from prototypes.v08_thermal_rating.recovered_shell_052_full_chain_v08 import (
    run_recovered_shell_052_full_chain,
)


def test_recovered_bundle_matches_full_chain_identity() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    recovered = resolve_recovered_shell_052_bundle(normalized, handoff)
    assert recovered is not None
    report = run_recovered_shell_052_full_chain(normalized, handoff, provider=provider)
    assert report.candidate_id == recovered.structural_bundle.candidate.candidate_id
    assert report.placement_envelope_m == recovered.placement_envelope_diameter_m


def test_full_chain_hydraulics_not_none_strings() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_recovered_shell_052_full_chain(normalized, handoff, provider=provider)
    if report.proven_infeasible_lower_bound:
        assert report.shell_full_dp_pa is None
        assert report.first_hydraulic_blocker is not None
    else:
        assert report.shell_full_dp_pa is not None
        assert report.tube_full_dp_pa is not None