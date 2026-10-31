"""R16: live multi-mesh rating on pinned real candidate."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.live_multi_mesh_rating import (
    R13_EVIDENCE_PINNED_CANDIDATE_ID,
    build_live_multi_mesh_analysis,
    highest_numeric_valid_mesh_row,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_R13_EVIDENCE = REPO_ROOT / (
    "docs/tasks/evidence/V07-GENERAL-VARIABLE-BUNDLE-GEOMETRY-SIZING-R13/"
    "CANDIDATE_RATING_RESULTS.json"
)
_KNOWN_N1_DUTY = Decimal("32528.427903428549")


def test_mesh_analysis_marks_convergence_not_established_when_only_n1() -> None:
    n1_row = {
        "mesh_level": 1,
        "mesh_status": "NUMERIC_VALID",
        "total_duty_w": "1000",
        "terminal_boundary_residual_k": "0.01",
    }
    analysis = build_live_multi_mesh_analysis(
        candidate_id="cid",
        rating_request_hash="hash",
        mesh_level_rows=[n1_row],
        coarse_obs=None,
        fine_obs=None,
    )
    assert analysis["MESH_CONVERGENCE_STATUS"] == "MESH_CONVERGENCE_NOT_ESTABLISHED"
    assert analysis["HIGHEST_VALID_MESH_LEVEL"] == 1


def test_mesh_analysis_comparison_available_when_n1_and_n2_valid() -> None:
    class _Obs:
        def __init__(self, duty: str, tube: str, shell: str, terminal: str) -> None:
            self.total_duty_w = Decimal(duty)
            self.tube_outlet_temperature_k = Decimal(tube)
            self.shell_outlet_temperature_k = Decimal(shell)
            self.terminal_boundary_residual_k = Decimal(terminal)
            self.duty_roundoff_floor_w = Decimal("0.001")

    n1 = {
        "mesh_level": 1,
        "mesh_status": "NUMERIC_VALID",
        "mesh_result_hash": "h1",
        "total_duty_w": "32500",
        "terminal_boundary_residual_k": "0.001",
        "task172_local_evaluation_count": 10,
        "wall_seconds": "100",
    }
    n2 = {
        "mesh_level": 2,
        "mesh_status": "NUMERIC_VALID",
        "mesh_result_hash": "h2",
        "total_duty_w": "32510",
        "terminal_boundary_residual_k": "0.0008",
        "task172_local_evaluation_count": 20,
        "wall_seconds": "200",
    }
    analysis = build_live_multi_mesh_analysis(
        candidate_id="cid",
        rating_request_hash="hash",
        mesh_level_rows=[n1, n2],
        coarse_obs=_Obs("32500", "290", "280", "0.001"),
        fine_obs=_Obs("32510", "290.1", "280.05", "0.0008"),
    )
    assert analysis["MESH_CONVERGENCE_STATUS"] == "MESH_COMPARISON_AVAILABLE"
    assert analysis["n1_n2_comparison"] is not None
    assert analysis["full_rating_converged"] is False


def test_highest_mesh_prefers_n2_over_n1() -> None:
    rows = [
        {"mesh_level": 1, "mesh_status": "NUMERIC_VALID"},
        {"mesh_level": 2, "mesh_status": "NUMERIC_VALID"},
    ]
    assert int(highest_numeric_valid_mesh_row(rows)["mesh_level"]) == 2


def test_n1_duty_matches_r13_evidence_within_tolerance() -> None:
    doc = json.loads(_R13_EVIDENCE.read_text(encoding="utf-8"))
    row = next(
        c for c in doc["candidates"] if c["candidate_id"] == R13_EVIDENCE_PINNED_CANDIDATE_ID
    )
    evidence_duty = Decimal(str(row["total_duty_w"]))
    rel = abs(evidence_duty - _KNOWN_N1_DUTY) / evidence_duty
    assert rel < Decimal("1e-9")
