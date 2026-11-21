"""Task037 + ε-NTU + margin validation for frozen 0.52 m shell."""

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    resolve_recovered_shell_052_bundle,
)
from prototypes.v08_thermal_rating.recovered_shell_052_full_chain_v08 import (
    FROZEN_SHELL_052_CANDIDATE_ID,
    FROZEN_SHELL_052_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.shell_052_thermal_authority_and_margin_v08 import (
    run_shell_052_thermal_authority_and_margin,
)
from prototypes.v08_thermal_rating.v08_shell_052_task037_authority_v08 import (
    evaluate_shell_052_task037,
)


def test_frozen_shell_052_task037_success() -> None:
    normalized, handoff, _ = load_case_bindings(
        FIXTURE_330, provider=CoolPropProvider()
    )
    recovered = resolve_recovered_shell_052_bundle(normalized, handoff)
    assert recovered is not None
    assert recovered.structural_bundle.candidate.candidate_id == FROZEN_SHELL_052_CANDIDATE_ID
    ev = evaluate_shell_052_task037(recovered)
    assert ev.status == "SUCCESS"
    assert ev.identity_replay_ok is True
    assert ev.wall_conductivity_w_m_k == "14.0"


def test_shell_052_thermal_margin_closure() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_shell_052_thermal_authority_and_margin(normalized, handoff, provider=provider)
    assert report.geometry_v2 == FROZEN_SHELL_052_GEOMETRY_V2
    assert report.geometry_identity_replay == "PASS"
    assert report.task037_status == "SUCCESS"
    assert report.ua_w_k is not None
    assert report.epsilon_ntu_q_w is not None
    assert float(report.epsilon_ntu_q_w) < float(normalized.target_duty_w)
    assert report.thermal_prescreen == "INDICATIVE_FAIL"
    assert report.mid_hydraulic_mathematical_pass is True
    assert report.high_hydraulic == "BLOCKED"
    assert Decimal(report.tube_dp_margin_pa) < Decimal("0.01")
    assert report.design_decision == "THERMAL_OR_MARGIN_BLOCKED"