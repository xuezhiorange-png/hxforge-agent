#!/usr/bin/env python3
"""TASK_ID=V08_03_GEOMETRY_IDENTITY_AND_LAYOUT_RECOVERY delivery runner."""
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
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    legacy_geometry_projection_aliases,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import BVP_PROTOTYPE_ROUTE
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330
from prototypes.v08_thermal_rating.geometry_identity_and_layout_recovery_v08 import (
    run_geometry_identity_and_layout_recovery,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head

PR_NUMBER = 325


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


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
    out = Path("/opt/cursor/artifacts/v08_03_geometry_identity_and_layout_recovery.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_geometry_identity_and_layout_recovery(normalized, handoff, provider=provider)
    legacy_aliases = legacy_geometry_projection_aliases(
        tuple((r.geometry_projection_hash_v1, r.geometry_identity_v2) for r in report.rows)
    )
    best = report.best_new
    br = best.breakthrough if best else None

    head = _git_head()
    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_GEOMETRY_IDENTITY_AND_LAYOUT_RECOVERY",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "CASE_ID": CASE_330KW_ID,
        "BAFFLE_COUNT_CORRECTED": report.baffle_count_corrected,
        "ACTUAL_BAFFLE_COUNT": report.actual_baffle_count,
        "BAFFLE_HOLE_POSITION_COUNT": report.baffle_hole_position_count,
        "GEOMETRY_IDENTITY_V2": report.geometry_identity_v2_sample or "none",
        "OLD_AND_NEW_CUT_HASH_DISTINCT": report.old_and_new_cut_hash_distinct,
        "LEGACY_HASH_COLLISION_RESOLVED": report.legacy_hash_collision_resolved,
        "LEGACY_GEOMETRY_PROJECTION_ALIAS_V1_HASHES": sorted(legacy_aliases),
        "NEW_STRUCTURALLY_VALID_COUNT": report.new_structurally_valid_count,
        "DISTINCT_V2_GEOMETRY_COUNT": report.distinct_v2_geometry_count,
        "LARGER_SHELL_LAYOUT_RECOVERED": report.larger_shell_layout_recovered,
        "TASK168_RESULT": report.task168_result,
        "TASK166_APPLICABILITY": report.task166_applicability,
        "MID_FULL_PATH_FEASIBLE_COUNT": report.mid_full_path_feasible_count,
        "HIGH_FULL_PATH_FEASIBLE_COUNT": report.high_full_path_feasible_count,
        "BEST_NEW_GEOMETRY_V2": best.geometry_identity_v2 if best else "none",
        "BEST_NEW_SHELL_DIAMETER_M": br.shell_inside_diameter_m if br else "none",
        "BEST_NEW_BAFFLE_CUT": br.baffle_cut_fraction if br else "none",
        "BEST_NEW_BELL_DP_PA": br.bell_dp_pa if br else "none",
        "BEST_NEW_TUBE_FULL_PATH_DP_PA": br.mid_tube_full_path_dp_pa if br else "none",
        "BEST_NEW_SHELL_FULL_PATH_DP_PA": br.mid_shell_full_path_dp_pa if br else "none",
        "THERMAL_PRESCREEN": best.thermal.status if best else "NOT_EVALUATED",
        "ESTIMATED_UA_W_K": best.thermal.ua_w_per_k if best else "unavailable",
        "ESTIMATED_Q_W": best.thermal.epsilon_ntu_q_w if best else "unavailable",
        "DESIGN_DECISION": report.design_decision,
        "NEXT_REQUIRED_ENGINEERING_CHANGE": report.next_required_engineering_change,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "candidate_rows": [
            _json_ready(
                {
                    **asdict(r.breakthrough),
                    "geometry_identity_v2": r.geometry_identity_v2,
                    "geometry_projection_hash_v1": r.geometry_projection_hash_v1,
                    "baffle_hole_position_count": r.baffle_hole_position_count,
                    "thermal_prescreen": r.thermal.status,
                    "estimated_ua_w_k": r.thermal.ua_w_per_k,
                    "estimated_q_w": r.thermal.epsilon_ntu_q_w,
                }
            )
            for r in report.rows
        ],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
