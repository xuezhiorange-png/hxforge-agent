#!/usr/bin/env python3
"""TASK_ID=V08_03_330KW_TERMINAL_AND_MESH_CLOSEOUT — 330 kW terminal + N1/N2/N4 closeout."""
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
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
    load_case_bindings,
    run_candidate_mesh_closeout,
)
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-production", action="store_true")
    parser.add_argument("--max-candidates", type=int, default=2)
    args = parser.parse_args()
    out = Path("/opt/cursor/artifacts/v08_03_330kw_terminal_mesh_closeout.json")

    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID
    space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=max(2, args.max_candidates)
    )

    rows: list[dict[str, Any]] = []
    for bundle in bundles[: args.max_candidates]:
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=space_hash,
            t168_digest=t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
            geometry_projection_hash=geom.get(bundle.candidate.candidate_id, ""),
        )
        if bindings is None:
            continue
        closeout = run_candidate_mesh_closeout(
            bindings, provider, run_production_gate=not args.skip_production
        )
        rows.append(asdict(closeout))

    def _cand(i: int, key: str, default: str = "not_run") -> str:
        if i >= len(rows):
            return default
        return str(rows[i].get(key, default))

    def _n1(i: int) -> str:
        return _cand(i, "n1", "BLOCKED")

    any_target_true = any(r.get("target_330kw_met") == "true" for r in rows)
    any_unresolved = any(r.get("target_330kw_met") == "unresolved" for r in rows)
    target_met: str
    if any_target_true:
        target_met = "true"
    elif rows and not any_unresolved:
        target_met = "false"
    else:
        target_met = "unresolved"

    n1v = rows[0]["n1_verification"] if rows else {}

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_330KW_TERMINAL_AND_MESH_CLOSEOUT",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": "pending_local_gates",
        "CASE_ID": CASE_330KW_ID,
        "EXPERIMENTAL_NOT_APPROVED": True,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "CANDIDATE_1_GEOMETRY_HASH": _cand(0, "geometry_projection_hash", ""),
        "CANDIDATE_1_N1": _n1(0),
        "CANDIDATE_1_N2": _cand(0, "n2"),
        "CANDIDATE_1_N4": _cand(0, "n4"),
        "CANDIDATE_2_GEOMETRY_HASH": _cand(1, "geometry_projection_hash", ""),
        "CANDIDATE_2_N1": _n1(1),
        "CANDIDATE_2_N2": _cand(1, "n2"),
        "CANDIDATE_2_N4": _cand(1, "n4"),
        "N1_TERMINAL_RESIDUAL_K": n1v.get("N1_TERMINAL_RESIDUAL_K"),
        "N1_TERMINAL_RESIDUAL_J_KG": n1v.get("N1_TERMINAL_RESIDUAL_J_KG"),
        "N1_TERMINAL_GATE": n1v.get("N1_TERMINAL_GATE", "BLOCKED"),
        "N1_TERMINAL_TOLERANCE_PASS": n1v.get("N1_TERMINAL_TOLERANCE_PASS"),
        "N1_OUTER_STATUS": n1v.get("N1_OUTER_STATUS"),
        "N1_ACCEPTED_RUN_HASH": n1v.get("N1_ACCEPTED_RUN_HASH"),
        "Q_TOTAL_W": n1v.get("N1_TOTAL_DUTY_W", "unverified"),
        "TARGET_330KW_MET": target_met,
        "TUBE_DP_PA": _cand(0, "tube_dp_pa", ""),
        "SHELL_DP_PA": _cand(0, "shell_dp_pa", ""),
        "NOZZLE_VELOCITIES": _cand(0, "nozzle_velocities", "unresolved"),
        "ORIGINAL_TASK173_GATE": _cand(0, "production_task173_gate", "not_run"),
        "ORIGINAL_TASK172_GATE": "isolated_trajectory_holes=0 when mesh ACCEPTED",
        "DISTINCT_FULLY_CONVERGED": sum(
            1
            for r in rows
            if r.get("n1") == "ACCEPTED" and r.get("n2") == "ACCEPTED" and r.get("n4") == "ACCEPTED"
        ),
        "candidates": rows,
    }
    if rows:
        payload["REMAINING_BLOCKER"] = (
            "production Task173 validate_candidate_rating not VALIDATED"
            if payload["ORIGINAL_TASK173_GATE"] not in ("RATING_SUCCESS", None)
            else (
                "isolated N1 terminal or mesh gate"
                if rows[0].get("n1") != "ACCEPTED"
                else "awaiting N2/N4 or hydraulic/nozzle binding"
            )
        )
    else:
        payload["REMAINING_BLOCKER"] = "NO_CANDIDATE"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"out": str(out), "TARGET_330KW_MET": target_met, "HEAD_SHA": payload["HEAD_SHA"]}
        )
    )


if __name__ == "__main__":
    main()
