"""V07 delivery: R27H classification must match authorized full_path_feasible."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    _constraint_summary,
)
from prototypes.v07_general_rating_sizing_mvp.r27h_candidate_space_extension import (
    _classify_r27h_final,
    build_r27h_selection,
    load_r27h_engineering_case,
)


def test_5e78f6a8_mid_band_not_mislabeled_infeasible() -> None:
    raw = json.loads(
        Path("tests/fixtures/R27H_CANDIDATE_SPACE_EXTENSION.json").read_text(encoding="utf-8")
    )
    row = next(c for c in raw["candidates"] if c["candidate_id_prefix"] == "5e78f6a8")
    mid = row["loss_scenario_results"]["mid_band"]
    assert mid["full_path_feasible"] is True
    case = load_r27h_engineering_case()
    sel = build_r27h_selection(case)
    rec = next(r for r in sel.records if r.candidate_id == row["candidate_id"])
    gf = row.get("geometry_fingerprint") or row.get("table_row") or row.get("phase_a")
    multi_row = {
        "FULL_RATING_CONVERGED": True,
        "rating_participation_status": "FULLY_RATED",
        "duty_w_at_finest_mesh": row["constraints"]["duty_w_at_finest_mesh"],
        "live_thermal_state_hydraulic_postpass": {"correlation_applicability_status": "APPLICABLE"},
        "NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE": True,
        "candidate_geometry_authority": gf,
    }
    constraints = _constraint_summary(multi_row, target_duty_w=case.target_duty_w)
    assert constraints["duty_constraint"] == "SATISFIED"
    cls = _classify_r27h_final(
        record=rec,
        table_row=row["table_row"],
        phase_a=row["phase_a"],
        multi_row=multi_row,
        scenario_results=row["loss_scenario_results"],
        case=case,
    )
    assert cls["outcome_class"] in (
        "MID_BAND_FEASIBLE_ASSUMPTION_BASED",
        "MID_BAND_AUTHORIZED_NUMERIC_EDGE",
    )
    audit = cls["sensitivity"]["max_nozzle_velocity_audit"]
    assert float(audit["tube_full_path_modeled_dp_pa"]) == pytest.approx(718.25, rel=1e-3)
    assert float(audit["shell_full_path_modeled_dp_pa"]) == pytest.approx(1166.327, rel=1e-3)
