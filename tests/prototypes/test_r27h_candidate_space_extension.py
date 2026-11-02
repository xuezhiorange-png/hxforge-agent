"""R27H: Task168 extension table, 0.65 classification corrections, phased search."""

from __future__ import annotations

from prototypes.v07_general_rating_sizing_mvp.r27e_targeted_recovery import (
    FOUR_065_SHELL_CANDIDATE_IDS,
)
from prototypes.v07_general_rating_sizing_mvp.r27h_candidate_space_extension import (
    R27H_EXPERIMENTAL_GEOMETRY_TABLE,
    _axial_span_ok,
    _record_for_fingerprint,
    build_r27h_selection,
    corrected_r27g_065_outcome_class,
    load_r27h_engineering_case,
    phase_a_r27h_screen,
)


def test_r27h_geometry_table_satisfies_baffle_span_rule() -> None:
    for row in R27H_EXPERIMENTAL_GEOMETRY_TABLE:
        assert _axial_span_ok(row["tube_length_m"], row["baffle_spacing_m"])


def test_r27h_065_correction_not_structural_blocked() -> None:
    for cid in FOUR_065_SHELL_CANDIDATE_IDS:
        corr = corrected_r27g_065_outcome_class(cid)
        assert corr["corrected_outcome_class"] == "THERMAL_MODEL_BLOCKED"
        assert corr["frozen_r27g_label"] == "STRUCTURAL_BLOCKED"


def test_r27h_c20fb684_enthalpy_mechanism() -> None:
    cid = next(c for c in FOUR_065_SHELL_CANDIDATE_IDS if c.startswith("c20fb684"))
    corr = corrected_r27g_065_outcome_class(cid)
    assert corr["mechanism"] == "PROPERTY_ENTHALPY_DOMAIN_EXIT"


def test_r27h_phase_a_new_056_shell_eligible() -> None:
    case = load_r27h_engineering_case()
    sel = build_r27h_selection(case)
    row = next(r for r in R27H_EXPERIMENTAL_GEOMETRY_TABLE if r["tube_length_m"] == "5.15")
    rec = _record_for_fingerprint(
        sel, row["shell_inside_diameter_m"], row["tube_length_m"], row["baffle_spacing_m"]
    )
    assert rec is not None and rec.rating_request_ready
    pa = phase_a_r27h_screen(case=case, record=rec, table_row=row, selection=sel)
    assert pa["phase_a_status"] == "ELIGIBLE_FOR_N1_SCREEN"


def test_r27h_phase_a_058_shell_baffle_geometry_blocked() -> None:
    case = load_r27h_engineering_case()
    sel = build_r27h_selection(case)
    row = next(
        r
        for r in R27H_EXPERIMENTAL_GEOMETRY_TABLE
        if r["shell_inside_diameter_m"] == "0.58" and r["tube_length_m"] == "4.85"
    )
    rec = _record_for_fingerprint(
        sel, row["shell_inside_diameter_m"], row["tube_length_m"], row["baffle_spacing_m"]
    )
    assert rec is not None
    pa = phase_a_r27h_screen(case=case, record=rec, table_row=row, selection=sel)
    assert pa["phase_a_status"] in ("TASK168_CHAIN_BLOCKED", "TASK174_NOT_READY")
