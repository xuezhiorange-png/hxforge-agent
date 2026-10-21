"""R11 constraint-aware experimental sizing (unit + frozen R10 offline)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_ranking import (
    build_experimental_ranking,
    build_offline_duty_scenarios,
)
from prototypes.v07_general_rating_sizing_mvp.low_mesh_result import low_mesh_result_document

REPO_ROOT = Path(__file__).resolve().parents[2]
R10_CASE = REPO_ROOT / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_multi_candidate_r10.json"
R9_CASE = (
    REPO_ROOT / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_tube_hot_shell_cold_r9.json"
)
_R10_EVIDENCE = "docs/tasks/evidence/V07-GENERAL-MULTI-CANDIDATE-LIVE-RATING-R10"
R10_FROZEN = REPO_ROOT / _R10_EVIDENCE / "CANDIDATE_RATING_RESULTS.json"


def _load_frozen_r10_rows() -> list[dict]:
    if R10_FROZEN.is_file():
        doc = json.loads(R10_FROZEN.read_text(encoding="utf-8"))
        return doc["candidates"]
    proc = subprocess.run(
        [
            "git",
            "show",
            "origin/cursor/v07-general-rating-sizing-e2e-mvp-r1-1201:"
            "docs/tasks/evidence/V07-GENERAL-MULTI-CANDIDATE-LIVE-RATING-R10/"
            "CANDIDATE_RATING_RESULTS.json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)["candidates"]


def test_low_mesh_result_includes_status_from_mesh_status() -> None:
    row = {"mesh_status": "NUMERIC_VALID", "total_duty_w": "1", "mesh_result_hash": "abc"}
    doc = low_mesh_result_document(row)
    assert doc["status"] == "NUMERIC_VALID"
    assert doc["mesh_status"] == "NUMERIC_VALID"


def test_pareto_default_no_preferred_candidate() -> None:
    case = load_general_engineering_case_json(R10_CASE.read_text(encoding="utf-8"))
    rows = _load_frozen_r10_rows()
    ranking = build_experimental_ranking(case, rows, objective="PARETO_ONLY")
    assert ranking["EXPERIMENTAL_COMPARISON_AVAILABLE"] is True
    assert ranking["preferred_candidate_id"] is None
    assert ranking["EXPERIMENTAL_RANKING_STATUS"] == "COMPARISON_ONLY"
    assert len(ranking["pareto_frontier_candidate_ids"]) == 2


def test_max_duty_prefers_higher_duty_candidate() -> None:
    case = load_general_engineering_case_json(R10_CASE.read_text(encoding="utf-8"))
    rows = _load_frozen_r10_rows()
    ranking = build_experimental_ranking(case, rows, objective="MAX_DUTY")
    assert ranking["preferred_candidate_id"] == ranking["ranked_candidate_ids"][0]
    duties = {r["candidate_id"]: Decimal(str(r["total_duty_w"])) for r in rows}
    assert duties[ranking["preferred_candidate_id"]] == max(duties.values())


def test_min_nominal_area_prefers_shorter_tube_candidate() -> None:
    case = load_general_engineering_case_json(R10_CASE.read_text(encoding="utf-8"))
    rows = _load_frozen_r10_rows()
    for row in rows:
        if "nominal_geometry" not in row:
            row["nominal_geometry"] = {
                "nominal_tube_outer_area_m2": (
                    "12.0" if row["candidate_id"].startswith("5a73903d") else "12.5"
                ),
                "area_kind": "NOMINAL_TUBE_OUTER_AREA_PROXY",
            }
    ranking = build_experimental_ranking(case, rows, objective="MIN_NOMINAL_TUBE_AREA")
    assert ranking["preferred_candidate_id"].startswith("5a73903d")


def test_offline_scenarios_duty_thresholds() -> None:
    case = load_general_engineering_case_json(R10_CASE.read_text(encoding="utf-8"))
    rows = _load_frozen_r10_rows()
    doc = build_offline_duty_scenarios(
        case,
        rows,
        scenario_targets_w=(Decimal("9500"), Decimal("38000"), Decimal("38500")),
    )
    by_target = {s["target_duty_w"]: s for s in doc["scenarios"]}
    assert len(by_target["9500"]["feasible_candidate_ids"]) == 2
    assert len(by_target["38000"]["feasible_candidate_ids"]) == 2
    assert len(by_target["38500"]["feasible_candidate_ids"]) == 1


def test_r9_mesh_result_schema_subprocess() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "prototypes.v07_general_rating_sizing_mvp",
                "--input",
                str(R9_CASE),
                "--output",
                str(out),
                "--mode",
                "experimental-live-rating",
                "--mesh",
                "1",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        mesh = json.loads((out / "REAL_N1_MESH_RESULT.json").read_text(encoding="utf-8"))
        assert mesh["status"] == "NUMERIC_VALID"
        assert mesh["mesh_status"] == "NUMERIC_VALID"


@pytest.mark.timeout(1200)
def test_r10_cli_pareto_no_forced_preference() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "prototypes.v07_general_rating_sizing_mvp",
                "--input",
                str(R10_CASE),
                "--output",
                str(out),
                "--mode",
                "experimental-live-rating",
                "--mesh",
                "1",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        ranking = json.loads((out / "EXPERIMENTAL_RANKING_RESULT.json").read_text(encoding="utf-8"))
        assert ranking["preferred_candidate_id"] is None
        report = json.loads((out / "ENGINEERING_REPORT.json").read_text(encoding="utf-8"))
        assert report["experimental_ranking_status"] == ranking["EXPERIMENTAL_RANKING_STATUS"]
        elig = report["experimental_candidate_eligibility"]
        assert all(e["RATING_STATUS"] == "NUMERIC_VALID" for e in elig)
        mesh = json.loads((out / "REAL_N1_MESH_RESULT.json").read_text(encoding="utf-8"))
        assert "status" in mesh
