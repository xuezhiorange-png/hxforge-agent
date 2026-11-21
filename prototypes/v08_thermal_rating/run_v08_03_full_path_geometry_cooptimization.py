#!/usr/bin/env python3
"""TASK_ID=V08_03_FULL_PATH_GEOMETRY_COOPTIMIZATION delivery runner."""
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
from prototypes.v08_thermal_rating.experimental_geometry_discrete_space_v08 import (
    EXPERIMENTAL_GEOMETRY_LABEL,
)
from prototypes.v08_thermal_rating.full_path_geometry_cooptimization_v08 import (
    run_full_path_geometry_cooptimization,
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
    out = Path("/opt/cursor/artifacts/v08_03_full_path_geometry_cooptimization.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_full_path_geometry_cooptimization(normalized, handoff, provider=provider)
    best = report.best
    rep = best.hydraulic_report if best else None
    mid = next(s for s in rep.scenarios if s.scenario_key == "mid_band") if rep else None
    tube_port = rep.ports[0].inside_diameter_m if rep else None
    shell_port = rep.ports[2].inside_diameter_m if rep else None

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_FULL_PATH_GEOMETRY_COOPTIMIZATION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "BASELINE_FULL_PATH_RESULTS_CORRECTED": report.baseline_full_path_results_corrected,
        "NOZZLE_SAME_GEOMETRY_ALL_SCENARIOS": bool(rep.nozzle_same_geometry_all_scenarios)
        if rep
        else True,
        "EXPERIMENTAL_GEOMETRY_COUNT": report.experimental_geometry_count,
        "STRUCTURALLY_ADMITTED_COUNT": report.structurally_admitted_count,
        "FULL_PATH_MID_FEASIBLE_COUNT": report.full_path_mid_feasible_count,
        "FULL_PATH_ALL_SCENARIO_FEASIBLE_COUNT": report.full_path_all_scenario_feasible_count,
        "DISTINCT_FULL_PATH_FEASIBLE_GEOMETRIES": report.distinct_full_path_feasible_geometries,
        "BEST_CANDIDATE_ID": best.candidate_id if best else "none",
        "BEST_GEOMETRY_HASH": best.geometry_projection_hash if best else "none",
        "BEST_TUBE_DP_PA": mid.tube_full_path_dp_pa if mid else None,
        "BEST_SHELL_DP_PA": mid.shell_full_path_dp_pa if mid else None,
        "BEST_TUBE_NOZZLE_D_MM": f"{float(tube_port) * 1000:.3f}" if tube_port else "none",
        "BEST_SHELL_NOZZLE_D_MM": f"{float(shell_port) * 1000:.3f}" if shell_port else "none",
        "BEST_DUTY_SCREEN": best.duty_screen if best else "none",
        "MECHANICAL_INSTALLATION_AUTHORITY": (
            asdict(rep.installation) if rep else {"manufacturing_size_authority": "PROVISIONAL"}
        ),
        "MANUFACTURING_GEOMETRY_AUTHORITY": (
            best.manufacturing_geometry_authority if best else EXPERIMENTAL_GEOMETRY_LABEL
        ),
        "FIRST_REMAINING_HYDRAULIC_BLOCKER": report.first_remaining_hydraulic_blocker,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "CASE_ID": CASE_330KW_ID,
        "gap_notes": list(report.gap_notes),
        "best_first_blocker": best.first_hydraulic_blocker if best else None,
        "candidate_rows_head": [_json_ready(asdict(r)) for r in report.rows[:12]],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "out": str(out),
                "FULL_PATH_MID_FEASIBLE_COUNT": report.full_path_mid_feasible_count,
            }
        )
    )


if __name__ == "__main__":
    main()
