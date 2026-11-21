#!/usr/bin/env python3
"""TASK_ID=V08_03_FEASIBLE_CANDIDATE_THERMAL_BRIDGE delivery runner."""
# ruff: noqa: E402, E501

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
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    engineering_distinct_fully_converged,
    load_case_bindings,
)
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330
from prototypes.v08_thermal_rating.feasible_candidate_thermal_bridge_v08 import (
    run_feasible_candidate_thermal_bridge,
)


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
                "conclusion,status,number,headSha",
            ],
            cwd=_REPO,
            text=True,
        )
        row = json.loads(out)[0]
        if row.get("status") != "completed":
            return "in_progress"
        return str(row.get("conclusion") or "unknown")
    except Exception:
        return "unknown"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-production", action="store_true")
    parser.add_argument("--max-candidates", type=int, default=64)
    args = parser.parse_args()

    out = Path("/opt/cursor/artifacts/v08_03_feasible_candidate_thermal_bridge.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID

    report = run_feasible_candidate_thermal_bridge(
        normalized,
        handoff,
        provider=provider,
        max_candidates=args.max_candidates,
        run_production=not args.skip_production,
    )

    sel = report.selected
    inv = report.inventory

    tp_ph_delta = "unverified"
    if sel and sel.precision_audit and sel.precision_audit.tp_ph_roundtrip:
        rt = sel.precision_audit.tp_ph_roundtrip
        tp_ph_delta = (
            f"delta_t_k={rt.delta_t_k};delta_h_j_kg={rt.delta_h_j_kg};"
            f"h_last_face_minus_h_inlet={rt.h_last_face_minus_h_inlet_j_kg}"
        )
    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_FEASIBLE_CANDIDATE_THERMAL_BRIDGE",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "MANUFACTURABLE_VALID_COUNT": inv.manufacturable_valid_count,
        "HYDRAULIC_FEASIBLE_COUNT": inv.hydraulic_feasible_count,
        "PRODUCTION_VALIDATED_COUNT": report.production_validated_count,
        "DISTINCT_FULLY_CONVERGED": report.distinct_fully_converged_geometry,
        "EXPERIMENTAL_MESH_CONVERGED": report.experimental_mesh_converged_count,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "candidate_space": _json_ready(asdict(inv)),
        "thermal_runs": _json_ready([asdict(r) for r in report.thermal_runs]),
    }

    if sel is None:
        payload.update(
            {
                "HYDRAULIC_FEASIBLE_CANDIDATE_ID": "none",
                "HYDRAULIC_FEASIBLE_GEOMETRY_HASH": "",
                "TUBE_DP_PA": "",
                "SHELL_DP_PA": "",
                "SELECTED_CANDIDATE_N1": "not_run",
                "SELECTED_CANDIDATE_N2": "not_run",
                "SELECTED_CANDIDATE_N4": "not_run",
                "SELECTED_CANDIDATE_Q_W": "unverified",
                "SELECTED_CANDIDATE_TERMINAL_GATE": "BLOCKED",
                "SELECTED_CANDIDATE_TASK172_GATE": "no_feasible_candidate",
                "SELECTED_CANDIDATE_TASK173_GATE": "no_feasible_candidate",
                "NOZZLE_VELOCITY_STATUS": "UNRESOLVED",
                "TP_PH_RECONSTRUCTION_DELTA": tp_ph_delta,
                "NEXT_BLOCKER": "NO_HYDRAULIC_FEASIBLE_STRUCTURE",
            }
        )
    else:
        m = sel.mesh_closeout
        n1v = m.n1_verification
        q_w = n1v.N1_TOTAL_DUTY_W or "unverified"
        payload.update(
            {
                "HYDRAULIC_FEASIBLE_CANDIDATE_ID": sel.hydraulic_row.candidate_id,
                "HYDRAULIC_FEASIBLE_GEOMETRY_HASH": sel.hydraulic_row.geometry_projection_hash,
                "TUBE_DP_PA": str(sel.hydraulic_row.tube_dp_pa),
                "SHELL_DP_PA": str(sel.hydraulic_row.shell_dp_pa),
                "SELECTED_CANDIDATE_N1": m.n1,
                "SELECTED_CANDIDATE_N2": m.n2,
                "SELECTED_CANDIDATE_N4": m.n4,
                "SELECTED_CANDIDATE_Q_W": q_w,
                "SELECTED_CANDIDATE_TERMINAL_GATE": n1v.N1_TERMINAL_GATE,
                "SELECTED_CANDIDATE_TASK172_GATE": (
                    "NOT_INFERRED_FROM_HOLES; production mesh/Task172 authority on validate_candidate_rating"
                ),
                "SELECTED_CANDIDATE_TASK173_GATE": m.production_task173_gate or "not_run",
                "SELECTED_CANDIDATE_CLASSIFICATION": sel.classification,
                "NOZZLE_VELOCITY_STATUS": sel.nozzle.status,
                "TERMINAL_PRECISION_BLOCKER": sel.precision_blocker,
                "TP_PH_RECONSTRUCTION_DELTA": tp_ph_delta,
            }
        )
        blockers = []
        if sel.classification == "THERMAL_NUMERICAL_BLOCKED":
            blockers.append(sel.precision_blocker or "THERMAL_NUMERICAL_BLOCKED")
        if sel.nozzle.status != "VERIFIED":
            blockers.append("NOZZLE_VELOCITY_UNRESOLVED")
        if not engineering_distinct_fully_converged(
            m, nozzle=sel.nozzle, target_met=m.target_330kw_met
        ):
            blockers.append("NOT_DISTINCT_FULLY_CONVERGED")
        if inv.hydraulic_feasible_count < 2:
            blockers.append("CANDIDATE_SPACE_CANNOT_SUPPLY_TWO_DISTINCT_ACCEPTED_STRUCTURES")
        payload["NEXT_BLOCKER"] = (
            "; ".join(blockers) if blockers else "ENGINEERING_ACCEPTANCE_BLOCKED"
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"out": str(out), "selected": payload.get("HYDRAULIC_FEASIBLE_CANDIDATE_ID")}))


if __name__ == "__main__":
    main()
