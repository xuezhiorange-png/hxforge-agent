#!/usr/bin/env python3
"""TASK_ID=V08_03_SHELL_HYDRAULIC_REDIRECTION delivery runner."""
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
from prototypes.v08_thermal_rating.shell_hydraulic_redirection_v08 import (
    run_shell_hydraulic_redirection,
)

PR_NUMBER = 325
BASELINE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"


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
    out = Path("/opt/cursor/artifacts/v08_03_shell_hydraulic_redirection.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_shell_hydraulic_redirection(
        normalized, handoff, provider=provider, baseline_candidate_id=BASELINE_ID
    )
    base_mid = next(
        s for s in report.baseline_lower_bound.scenarios if s.scenario_key == "mid_band"
    )
    high_mid = next(
        s
        for s in report.baseline_lower_bound.scenarios
        if s.scenario_key == "high_loss_sensitivity"
    )
    best = report.best_new
    best_row = best
    if best and best.candidate_id == BASELINE_ID:
        others = [
            r
            for r in report.rows
            if r.geometry_projection_hash != report.baseline_geometry_hash
        ]
        best_row = others[0] if others else best

    def _transition_sum(s: Any) -> str:
        return str(
            float(s.shell_inlet_transition_dp_pa) + float(s.shell_outlet_transition_dp_pa)
        )

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_SHELL_HYDRAULIC_REDIRECTION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "CASE_ID": CASE_330KW_ID,
        "BASELINE_SHELL_BELL_DP_PA": base_mid.shell_bell_internal_dp_pa,
        "BASELINE_SHELL_NOZZLE_PAIR_DP_PA": base_mid.shell_nozzle_pair_min_dp_pa,
        "BASELINE_SHELL_TRANSITION_DP_PA": _transition_sum(base_mid),
        "BASELINE_SHELL_FULL_PATH_DP_PA": base_mid.shell_full_path_dp_pa
        or str(
            float(base_mid.shell_bell_internal_dp_pa) + float(base_mid.shell_external_min_dp_pa)
        ),
        "MID_SHELL_INTERNAL_DP_BUDGET_PA": base_mid.remaining_internal_budget_pa,
        "HIGH_SHELL_INTERNAL_DP_BUDGET_PA": high_mid.remaining_internal_budget_pa,
        "UPSTREAM_HYDRAULIC_AUTHORITY_VALID": report.upstream_hydraulic_authority_valid,
        "DUPLICATE_DP_COMPONENTS": report.duplicate_dp_components,
        "TOTAL_SEARCH_RECORDS": report.total_search_records,
        "DISTINCT_STRUCTURAL_GEOMETRIES": report.distinct_structural_geometries,
        "NEW_EXPERIMENTAL_DISTINCT_GEOMETRIES": report.new_experimental_distinct_geometries,
        "STRUCTURAL_VALID_COUNT": report.structural_valid_count,
        "TASK174_PARTIAL_FEASIBLE_COUNT": report.task174_partial_feasible_count,
        "FULL_PATH_MID_FEASIBLE_COUNT": report.full_path_mid_feasible_count,
        "FULL_PATH_ALL_SCENARIO_FEASIBLE_COUNT": report.full_path_all_scenario_feasible_count,
        "BEST_NEW_CANDIDATE_ID": best_row.candidate_id if best_row else "none",
        "BEST_NEW_GEOMETRY_HASH": best_row.geometry_projection_hash if best_row else "none",
        "BEST_NEW_SHELL_INTERNAL_DP_PA": (
            next(
                s.shell_bell_internal_dp_pa
                for s in best_row.lower_bound.scenarios
                if s.scenario_key == "mid_band"
            )
            if best_row
            else "none"
        ),
        "BEST_NEW_SHELL_FULL_PATH_DP_PA": best_row.mid_shell_full_path_dp_pa
        if best_row and best_row.mid_shell_full_path_dp_pa
        else "none",
        "BEST_NEW_TUBE_FULL_PATH_DP_PA": best_row.mid_tube_full_path_dp_pa
        if best_row and best_row.mid_tube_full_path_dp_pa
        else "none",
        "THERMAL_DUTY_STATUS": "THERMAL_DUTY=NOT_EVALUATED",
        "MANUFACTURING_AUTHORITY": (
            best_row.manufacturing_geometry_authority if best_row else "none"
        ),
        "BELL_REDUCTION_REQUIRED_FOR_MID_FEASIBILITY_PA": (
            report.baseline_lower_bound.bell_reduction_required_for_mid_feasibility_pa
        ),
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "design_gap_notes": list(report.design_gap_notes),
        "baseline_lower_bound": _json_ready(asdict(report.baseline_lower_bound)),
        "candidate_rows_head": [_json_ready(asdict(r)) for r in report.rows[:10]],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "out": str(out),
                "BASELINE_SHELL_BELL_DP_PA": payload["BASELINE_SHELL_BELL_DP_PA"],
                "FULL_PATH_MID_FEASIBLE_COUNT": report.full_path_mid_feasible_count,
            }
        )
    )


if __name__ == "__main__":
    main()