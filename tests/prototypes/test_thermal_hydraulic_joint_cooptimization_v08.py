"""Joint thermal-hydraulic screen: no silent pass on duty or high-K."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.recovered_shell_052_full_chain_v08 import (
    FROZEN_SHELL_052_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import _cp_kg_s
from prototypes.v08_thermal_rating.v08_epsilon_ntu_required_ua_v08 import (
    required_ua_w_k_for_duty,
)
from prototypes.v08_thermal_rating.v08_thermal_hydraulic_cooptimization_recovery_v08 import (
    run_thermal_hydraulic_cooptimization_recovery,
)


def test_required_ua_exceeds_fouled_baseline_for_330kw() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_thermal_hydraulic_cooptimization_recovery(
        normalized, handoff, provider=provider, max_valid=8
    )
    assert report.provenance.material_hash_reuse_corrected is True
    assert report.fouled.epsilon_ntu_q_w is not None
    assert Decimal(report.fouled.epsilon_ntu_q_w) < normalized.target_duty_w
    assert report.required_ua_w_k is not None
    if report.fouled.ua_w_k:
        assert Decimal(report.required_ua_w_k) > Decimal(report.fouled.ua_w_k)


def test_joint_does_not_count_high_k_only_as_full_pass() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_thermal_hydraulic_cooptimization_recovery(
        normalized, handoff, provider=provider, max_valid=8
    )
    assert (
        report.joint.all_scenario_prescreen_pass_count
        <= report.joint.mid_thermal_hydraulic_prescreen_pass_count
    )
    if report.joint.best and report.joint.best.classification == "THERMAL_PASS_HYDRAULIC_FAIL":
        assert report.joint.best.clean_thermal.status == "INDICATIVE_PASS"
        assert report.joint.best.hydraulic is not None
        assert report.joint.best.hydraulic.scenario_robustness != "PASS"


def test_frozen_052_geometry_unchanged_in_identity() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_thermal_hydraulic_cooptimization_recovery(
        normalized, handoff, provider=provider, max_valid=8
    )
    assert FROZEN_SHELL_052_GEOMETRY_V2.startswith("aba31610")
    assert report.clean.epsilon_ntu_q_w is not None
    t_ti = Decimal(str(normalized.tube_side.inlet_temperature_k))
    t_si = Decimal(str(normalized.shell_side.inlet_temperature_k))
    c_t = (
        _cp_kg_s(
            provider, _fluid="", t_k=t_ti, p_pa=Decimal(str(normalized.tube_side.inlet_pressure_pa))
        )
        * normalized.tube_side.mass_flow_kg_s
    )
    c_s = (
        _cp_kg_s(
            provider,
            _fluid="",
            t_k=t_si,
            p_pa=Decimal(str(normalized.shell_side.inlet_pressure_pa)),
        )
        * normalized.shell_side.mass_flow_kg_s
    )
    req = required_ua_w_k_for_duty(
        target_q_w=normalized.target_duty_w,
        c_hot=c_t,
        c_cold=c_s,
        t_hot_in=t_ti,
        t_cold_in=t_si,
    )
    assert req is not None
