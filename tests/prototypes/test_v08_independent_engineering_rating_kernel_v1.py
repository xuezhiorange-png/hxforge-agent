"""Independent V08 kernel contract tests (not Task173 mesh)."""

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250
from prototypes.v08_thermal_rating.v08_independent_engineering_rating_kernel_v1 import (
    KERNEL_AUTHORITY_ID,
    rate_candidate_engineering_kernel_v1,
)
from prototypes.v08_thermal_rating.v08_kernel_design_chain_bridge import (
    run_kernel_design_chain_for_fixture,
)
from prototypes.v08_thermal_rating.v08_kernel_rating_acceptance_v1 import (
    analytic_parallel_flow_q,
    negative_temperature_cross_blocked,
    property_tp_ph_roundtrip_pass,
)


def test_analytic_parallel_flow_positive_q() -> None:
    q = analytic_parallel_flow_q(
        u_w_m2_k=800.0,
        area_m2=10.0,
        t_hot_in=350.0,
        t_cold_in=290.0,
        m_hot=1.5,
        m_cold=2.0,
        cp_hot=4180.0,
        cp_cold=4180.0,
    )
    assert 1e4 < q < 5e5


def test_negative_temperature_cross_detection() -> None:
    assert negative_temperature_cross_blocked(
        t_tube_in=Decimal("350"),
        t_shell_in=Decimal("300"),
        t_tube_out=Decimal("310"),
        t_shell_out=Decimal("320"),
    )


def test_coolprop_tp_ph_roundtrip() -> None:
    p = CoolPropProvider()
    assert property_tp_ph_roundtrip_pass(p, t_k=305.0, p_pa=200000.0)


def test_kernel_rates_at_least_one_250kw_candidate() -> None:
    report = run_kernel_design_chain_for_fixture(
        FIXTURE_250,
        provider=CoolPropProvider(),
        max_candidates=12,
        include_v08_05_mirror=False,
    )
    assert report.candidates_attempted >= 1
    successes = [r for r in report.records if r.thermal.status == "RATING_SUCCESS"]
    assert successes, "expected at least one kernel RATING_SUCCESS on 250 kW fixture"
    row = successes[0].thermal
    assert row.authority_id == KERNEL_AUTHORITY_ID
    assert row.energy_balance_pass
    assert row.q_w is not None
    assert row.resistance is not None
    assert float(row.q_w) >= float(row.q_target_w) * 0.99


def test_kernel_authority_distinct_from_task173() -> None:
    p = CoolPropProvider()
    from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
        build_candidate_rating_bindings,
        enumerate_structural_bundles,
        load_case_bindings,
    )

    normalized, handoff, _ = load_case_bindings(FIXTURE_250, provider=p)
    space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=4
    )
    bindings = build_candidate_rating_bindings(
        bundles[0],
        space_hash=space_hash,
        t168_digest=t168_digest,
        normalized=normalized,
        handoff=handoff,
        provider=p,
        geometry_projection_hash=geom[bundles[0].candidate.candidate_id],
    )
    assert bindings is not None
    out = rate_candidate_engineering_kernel_v1(bindings, normalized, provider=p)
    assert "TASK173" not in out.authority_id
    assert out.contract_id == "V08_KERNEL_RATING_ACCEPTANCE_V1"