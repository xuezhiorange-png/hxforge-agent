"""0.85/0.90 envelope combo rejection attribution and Task027 Re root cause."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    SHELL_052_PROBE_M,
    enumerate_shell_052_bounded_local_combos,
)
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    baffle_spacing_for_length_m,
    find_rejection_for_candidate_spec,
)
from prototypes.v08_thermal_rating.tube_side_replay_root_cause_v08 import (
    run_tube_side_replay_root_cause_analysis,
)
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import _with_envelope_override
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    BREAKTHROUGH_DISCRETE_SPACE_PATH,
)


def test_rejection_match_not_first_row_for_6m_combo() -> None:
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=CoolPropProvider())
    outcome = _with_envelope_override(
        normalized,
        handoff,
        discrete_path=BREAKTHROUGH_DISCRETE_SPACE_PATH,
        shell_m=SHELL_052_PROBE_M,
        envelope_scale=Decimal("0.85"),
    )
    first = outcome.rejections[0].evidence.get("tube_length_m")
    matched = find_rejection_for_candidate_spec(
        outcome.rejections,
        shell_inside_diameter_m=SHELL_052_PROBE_M,
        tube_length_m=Decimal("6.0"),
        baffle_spacing_m=baffle_spacing_for_length_m(Decimal("6.0")),
    )
    assert first in ("5.5", "5.50")
    assert matched is not None
    assert Decimal(str(matched.evidence.get("tube_length_m"))) == Decimal("6")


def test_four_combos_task027_reynolds_regime_not_binding_defect() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_tube_side_replay_root_cause_analysis(normalized, handoff, provider=provider)
    assert report.incorrect_rejection_attribution_fixed is True
    assert report.binding_defect_confirmed is False
    assert report.physical_applicability_blocker_confirmed is True
    assert report.new_tube_geometry_authority_required == "not_proven"
    assert len(report.combos) == 4
    for combo in report.combos:
        assert combo.task021_status == "PASS"
        assert combo.task025_status == "PASS"
        assert combo.task026_status == "PASS"
        assert combo.task027_blocker_code == "BL_T027_UNSUPPORTED_REYNOLDS_REGIME"


def test_bounded_local_blockers_include_candidate_id() -> None:
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=CoolPropProvider())
    _bundles, blockers = enumerate_shell_052_bounded_local_combos(normalized, handoff)
    blocked_085 = [b for b in blockers if "scale=0.85" in b]
    assert blocked_085
    assert "candidate=" in blocked_085[0]
    assert "TUBE_SIDE_REPLAY_FAILED" in blocked_085[0]
