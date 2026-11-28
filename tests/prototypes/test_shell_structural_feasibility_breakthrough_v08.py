"""Structural feasibility breakthrough search (limited discrete authorities)."""

from __future__ import annotations

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.shell_structural_feasibility_breakthrough_v08 import (
    run_shell_structural_feasibility_breakthrough,
)
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    collect_larger_shell_task168_rejections,
)


def test_larger_shell_rejections_have_per_row_evidence() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    rows = collect_larger_shell_task168_rejections(normalized, handoff)
    assert rows
    shells = {r.shell_inside_diameter_m for r in rows}
    assert "0.52" in shells
    for row in rows:
        assert row.failure_stage
        assert row.blocker_code or row.message


def test_breakthrough_search_no_mid_pass_documents_exhaustion() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_shell_structural_feasibility_breakthrough(normalized, handoff, provider=provider)
    assert report.larger_shell_failures_verified is True
    assert report.task168_binding_defect is False
    assert report.mid_full_path_feasible_count == 0
    assert report.design_decision == "EXISTING_MODEL_SPACE_EXHAUSTED"
    assert report.minimum_shell_full_path_dp_pa is not None
    assert float(report.minimum_shell_full_path_dp_pa) > 1180.0
    assert report.best is not None
    assert report.best.baffle_cut_fraction in ("0.35", "0.49", "0.25")
