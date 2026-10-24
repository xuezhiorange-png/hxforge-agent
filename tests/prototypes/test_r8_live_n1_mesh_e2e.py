"""R8 live n=1 mesh E2E (long-running; isolated CI shard)."""

from __future__ import annotations

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
    run_mesh_numeric_with_profile,
)

R7_CASE = (
    __import__("pathlib").Path(__file__).resolve().parents[2]
    / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_tube_hot_shell_cold_r7.json"
)


def test_case_b_n1_mesh_numeric_valid() -> None:
    case = load_general_engineering_case_json(R7_CASE.read_text(encoding="utf-8"))
    sel = enumerate_experimental_rating_candidates(case)
    native = build_native_cell_context(case, selection=sel)
    mesh, _profile, _obs = run_mesh_numeric_with_profile(
        native,
        subdivisions=1,
        case=case,
        enable_live_thermal_boundary=True,
        enable_ephemeral_tp_cache=False,
    )
    assert mesh["status"] == "NUMERIC_VALID"
    assert mesh["low_mesh_numeric_valid"] is True
