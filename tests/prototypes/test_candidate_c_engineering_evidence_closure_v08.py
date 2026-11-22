"""Design C freeze: deep validators, high-K bound, and rank key semantics."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.candidate_c_engineering_evidence_closure_v08 import (
    run_candidate_c_engineering_evidence_closure,
)
from prototypes.v08_thermal_rating.candidate_c_identity_v08 import (
    CANDIDATE_C_SHELL_NOZZLE_ID_MM,
    CANDIDATE_C_TUBE_NOZZLE_ID_MM,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.four_port_nozzle_correction_and_validation_v08 import (
    TrialNozzleEvaluation,
    _rank_key,
)


def test_design_c_deep_validators_and_frozen_identity() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_candidate_c_engineering_evidence_closure(normalized, handoff, provider=provider)
    assert report.candidate_id == FROZEN_FIRST_JOINT_CANDIDATE_ID
    assert report.geometry_v2 == FROZEN_FIRST_JOINT_GEOMETRY_V2
    assert report.structure_identity_replay == "PASS"
    assert report.fixed_nozzle_override_check == "PASS"
    assert report.outlet_property_consistency == "PASS"
    assert report.four_port_strict_velocity_check == "PASS"
    assert report.nozzle_only_high_k_feasibility == "INFEASIBLE_UNDER_ASSUMED_K"
    assert report.mid_joint_prescreen == "PASS"
    assert report.all_scenario_prescreen == "BLOCKED"
    assert Decimal(report.clean_q_w) > Decimal("330000")
    assert Decimal(report.fouled_q_w) < Decimal("330000")
    assert Decimal(report.mid_tube_dp_pa or "0").quantize(Decimal("0.001")) == Decimal(
        "1084.785"
    )
    assert report.design_spec["tube_common_nozzle_id_mm"] == str(CANDIDATE_C_TUBE_NOZZLE_ID_MM)
    assert report.design_spec["shell_common_nozzle_id_mm"] == str(CANDIDATE_C_SHELL_NOZZLE_ID_MM)


def test_rank_key_prefers_higher_min_port_velocity() -> None:
    base = {
        "grid_trial": True,
        "strict_velocity": "PASS",
        "mid_joint_prescreen": "PASS",
        "mid_shell_margin_pa": "10",
        "mid_tube_margin_pa": "10",
        "port_records": [],
    }

    def trial(min_v: str) -> TrialNozzleEvaluation:
        from prototypes.v08_thermal_rating.four_port_nozzle_correction_and_validation_v08 import (
            PortVelocityRecord,
        )

        v = Decimal(min_v)
        rec = PortVelocityRecord(
            port_id="TUBE_INLET",
            inside_diameter_m=Decimal("0.1238"),
            mass_flow_kg_s=Decimal("1"),
            density_kg_m3=Decimal("1000"),
            velocity_m_s=v,
            velocity_basis="INDICATIVE_INLET",
        )
        return TrialNozzleEvaluation(
            tube_id_mm=Decimal("123.80"),
            shell_id_mm=Decimal("159.00"),
            grid_trial=base["grid_trial"],
            strict_velocity=base["strict_velocity"],
            velocity_failures=(),
            port_records=(rec,),
            nozzle_design_hash="h",
            mid_tube_dp_pa=base["mid_tube_margin_pa"],
            mid_shell_dp_pa=base["mid_shell_margin_pa"],
            mid_tube_margin_pa=base["mid_tube_margin_pa"],
            mid_shell_margin_pa=base["mid_shell_margin_pa"],
            high_tube_dp_pa=None,
            high_shell_dp_pa=None,
            mid_joint_prescreen=base["mid_joint_prescreen"],
            high_joint_prescreen="BLOCKED",
            installation_prescreen="PASS",
        )

    hi = trial("2.5")
    lo = trial("1.01")
    assert _rank_key(hi) < _rank_key(lo)