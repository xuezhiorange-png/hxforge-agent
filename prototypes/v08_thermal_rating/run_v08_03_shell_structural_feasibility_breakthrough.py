#!/usr/bin/env python3
"""TASK_ID=V08_03_SHELL_STRUCTURAL_FEASIBILITY_BREAKTHROUGH delivery runner."""
# ruff: noqa: E402

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import BVP_PROTOTYPE_ROUTE
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330
from prototypes.v08_thermal_rating.shell_structural_feasibility_breakthrough_v08 import (
    run_shell_structural_feasibility_breakthrough,
)

PR_NUMBER = 325


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _ci_status() -> str:
    try:
        out = subprocess.check_output(
            [
                "gh",
                "run",
                "list",
                "--repo",
                "xuezhiorange-png/hxforge-agent",
                "--branch",
                "cursor/v08-03-live-thermal-rating-1201",
                "--limit",
                "1",
                "--json",
                "conclusion,status,number",
            ],
            cwd=_REPO,
            text=True,
        )
        row = json.loads(out)[0]
        if row.get("status") != "completed":
            return f"in_progress_{row.get('number', '?')}"
        return str(row.get("conclusion") or "unknown")
    except Exception:
        return "unknown"


def _json_ready(value: Any) -> Any:
    from decimal import Decimal

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_shell_structural_feasibility_breakthrough.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_shell_structural_feasibility_breakthrough(normalized, handoff, provider=provider)
    best = report.best

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_SHELL_STRUCTURAL_FEASIBILITY_BREAKTHROUGH",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "CASE_ID": CASE_330KW_ID,
        "LARGER_SHELL_FAILURES_VERIFIED": report.larger_shell_failures_verified,
        "TASK168_BINDING_DEFECT": report.task168_binding_defect,
        "TASK168_GEOMETRY_DEFECT": report.task168_geometry_defect,
        "DISTINCT_CANDIDATES_EVALUATED": report.distinct_candidates_evaluated,
        "STRUCTURALLY_VALID_COUNT": report.structurally_valid_count,
        "MID_FULL_PATH_FEASIBLE_COUNT": report.mid_full_path_feasible_count,
        "HIGH_FULL_PATH_FEASIBLE_COUNT": report.high_full_path_feasible_count,
        "BEST_CANDIDATE_ID": best.candidate_id if best else "none",
        "BEST_GEOMETRY_HASH": best.geometry_projection_hash if best else "none",
        "BEST_SHELL_DIAMETER_M": best.shell_inside_diameter_m if best else "none",
        "BEST_TUBE_LENGTH_M": best.tube_length_m if best else "none",
        "BEST_BAFFLE_CUT": best.baffle_cut_fraction if best else "none",
        "BEST_BAFFLE_COUNT": best.baffle_count if best else "none",
        "BEST_BAFFLE_SPACING_M": best.baffle_spacing_m if best else "none",
        "BEST_BELL_DP_PA": best.bell_dp_pa if best else "none",
        "BEST_TUBE_FULL_PATH_DP_PA": best.mid_tube_full_path_dp_pa if best else "not_run",
        "BEST_SHELL_FULL_PATH_DP_PA": best.mid_shell_full_path_dp_pa if best else "not_run",
        "BEST_SHELL_MINIMUM_DP_PA": best.shell_minimum_full_path_dp_pa if best else "none",
        "NOZZLE_VELOCITY_CHECK": best.nozzle_velocity_check if best else "not_run",
        "THERMAL_DUTY_STATUS": "NOT_EVALUATED",
        "MANUFACTURING_AUTHORITY": best.manufacturing_geometry_authority if best else "none",
        "DESIGN_DECISION": report.design_decision,
        "NEXT_REQUIRED_STRUCTURAL_CHANGE": report.next_required_structural_change,
        "MINIMUM_SHELL_FULL_PATH_DP_PA": report.minimum_shell_full_path_dp_pa,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "larger_shell_rejection_sample": [
            _json_ready(asdict(r)) for r in report.larger_shell_rejection_sample
        ],
        "candidate_rows": [_json_ready(asdict(r)) for r in report.rows],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "out": str(out),
                "DESIGN_DECISION": report.design_decision,
                "MINIMUM_SHELL_FULL_PATH_DP_PA": report.minimum_shell_full_path_dp_pa,
            }
        )
    )


if __name__ == "__main__":
    main()
