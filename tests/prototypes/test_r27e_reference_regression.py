"""R27E: seven-candidate numeric regression vs frozen R27D baseline fixture."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.r27e_reference_regression import (
    capture_reference_metrics,
    compare_reference_metrics,
    load_reference_fixture,
)
from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/r27e_r27d_seven_reference_baseline.json"


@pytest.mark.slow
def test_r27e_seven_reference_candidates_match_r27d_baseline() -> None:
    if not _FIXTURE.is_file():
        pytest.skip("R27D exact-head baseline missing: P0-2 NOT VERIFIED")
    baseline = load_reference_fixture(_FIXTURE)
    current = capture_reference_metrics(shared_r26e_engineering_case())
    deltas = compare_reference_metrics(baseline, current)
    assert not deltas, deltas


def _synthetic_seven_reference_snapshots() -> tuple[dict, dict]:
    levels = {
        str(n): {
            "status": "EXPERIMENTAL_ENGINEERING_NUMERIC_VALID",
            "duty_w": 350000.0,
            "tube_outlet_temperature_k": 303.0,
            "shell_outlet_temperature_k": 299.0,
            "energy_balance_relative_error": 1e-12,
            "max_cell_thermal_residual_w": 1e-4,
            "max_inner_wall_outer_closure_residual_w": 2e-4,
        }
        for n in (1, 2, 4)
    }
    rows = [
        {
            "candidate_id": f"candidate-{i}",
            "candidate_hash": f"hash-{i}",
            "geometry_projection_hash": f"geometry-{i}",
            "n1_status": "EXPERIMENTAL_ENGINEERING_NUMERIC_VALID",
            "n1_duty_w": 350000.0,
            "energy_balance_relative_error_n1": 1e-12,
            "max_cell_thermal_residual_w_n1": 1e-4,
            "max_closure_residual_w_n1": 2e-4,
            "FULL_RATING_CONVERGED": True,
            "mesh_ladder": deepcopy(levels),
            "N4_DUTY_W": 350000.0,
            "N4_TUBE_OUTLET_K": 303.0,
            "N4_SHELL_OUTLET_K": 299.0,
            "LIVE_TUBE_DP_PA": "782.0",
            "LIVE_SHELL_DP_PA": "955.0",
        }
        for i in range(7)
    ]
    baseline = {
        "schema_version": "hxforge.r27e-r27d-seven-reference-regression.v27e",
        "baseline_provenance": {
            "source_pr_number": 310,
            "source_commit_sha": "e320aaf5840812eafe86a0e7d6fef97bf8062544",
            "capture_mode": "ISOLATED_R27D_WORKTREE",
        },
        "candidates": rows,
    }
    current = deepcopy(baseline)
    current.pop("baseline_provenance")
    return baseline, current


def test_r27e_regression_comparator_accepts_exact_equal_verified_seven() -> None:
    baseline, current = _synthetic_seven_reference_snapshots()
    assert compare_reference_metrics(baseline, current) == []


def test_r27e_regression_comparator_refuses_self_captured_baseline() -> None:
    baseline, current = _synthetic_seven_reference_snapshots()
    baseline["baseline_provenance"]["source_commit_sha"] = (
        "e9a56b0c636b6afdb284ccff1627752565eebfaa"
    )
    errors = compare_reference_metrics(baseline, current)
    assert any(d.get("error") == "unverified_r27d_baseline_origin" for d in errors)


def test_r27e_regression_comparator_detects_n2_energy_and_closure_drift() -> None:
    baseline, current = _synthetic_seven_reference_snapshots()
    current["candidates"][0]["mesh_ladder"]["2"]["energy_balance_relative_error"] = 1e-5
    current["candidates"][0]["mesh_ladder"]["2"]["max_cell_thermal_residual_w"] = 1.0
    changed = {d.get("field") for d in compare_reference_metrics(baseline, current)}
    assert "N2.energy_balance_relative_error" in changed
    assert "N2.max_cell_thermal_residual_w" in changed


def test_r27e_regression_comparator_refuses_missing_mesh_and_dp() -> None:
    baseline, current = _synthetic_seven_reference_snapshots()
    del current["candidates"][0]["mesh_ladder"]["4"]
    current["candidates"][1]["LIVE_TUBE_DP_PA"] = None
    errors = compare_reference_metrics(baseline, current)
    assert any(d.get("error") == "missing_mesh_metrics" for d in errors)
    assert any(
        d.get("field") == "LIVE_TUBE_DP_PA"
        and d.get("error") == "missing_numeric_metric"
        for d in errors
    )
