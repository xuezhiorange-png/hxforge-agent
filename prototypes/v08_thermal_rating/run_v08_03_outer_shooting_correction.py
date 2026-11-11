#!/usr/bin/env python3
"""TASK_ID=V08_03_OUTER_SHOOTING_ALGORITHM_CORRECTION delivery runner."""
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
    closeout_one_candidate,
    enumerate_structural_bundles,
    load_case_bindings,
    solve_isolated_outer_boundary,
)
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330


def _git_head() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()
    )


def _mesh_status(result: Any) -> str:
    if result.status == "ACCEPTED":
        return "CLOSED"
    if result.best_valid_run is not None:
        return f"BLOCKED:{result.failure_code or result.status}"
    return f"BLOCKED:{result.failure_code or result.status}"


def _hydraulic_pass(bindings: Any) -> dict[str, str]:
    req = bindings.rating_request
    tube_dp = req.task174_result.modeled_total_tube_side_pressure_drop_pa
    shell_dp = req.task174_result.bell_total_shell_pressure_drop_pa
    max_tube = bindings.normalized.max_tube_side_pressure_drop_pa
    max_shell = bindings.normalized.max_shell_side_pressure_drop_pa
    tube_pass = "true" if tube_dp <= max_tube else "false"
    shell_pass = "true" if shell_dp <= max_shell else "false"
    return {
        "TUBE_DP_PASS": tube_pass,
        "SHELL_DP_PASS": shell_pass,
        "NOZZLE_VELOCITY_PASS": "unresolved",
        "modeled_tube_dp_pa": str(tube_dp),
        "modeled_shell_dp_pa": str(shell_dp),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-production", action="store_true")
    parser.add_argument("--max-candidates", type=int, default=2)
    args = parser.parse_args()
    out = Path("/opt/cursor/artifacts/v08_03_outer_shooting_correction.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID
    space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=2
    )

    candidates_out: list[dict[str, Any]] = []
    search_traces: list[dict[str, Any]] = []
    best_q: str | None = None

    for idx, bundle in enumerate(bundles[: args.max_candidates], start=1):
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
        n1 = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
        n2 = n4 = None
        if n1.status == "ACCEPTED":
            n2 = solve_isolated_outer_boundary(bindings, provider, subdivisions=2)
            n4 = solve_isolated_outer_boundary(bindings, provider, subdivisions=4)

        closeout = closeout_one_candidate(
            bindings, provider, run_production=not args.skip_production
        )
        phys = closeout.physical
        prod = closeout.production
        run = n1.accepted_run or n1.best_valid_run
        hyd = _hydraulic_pass(bindings)

        if idx == 1:
            search_traces.append(
                {
                    "candidate_id": bindings.rating_request.candidate_id,
                    "search_trace": [asdict(step) for step in n1.search_trace],
                    "h_low_final": n1.h_low_final,
                    "h_high_final": n1.h_high_final,
                    "float_h_low_hex": n1.float_h_low_hex,
                    "float_h_high_hex": n1.float_h_high_hex,
                }
            )

        if run is not None and phys.n1_status == "CLOSED":
            best_q = str(run.observables.total_duty_w)

        candidates_out.append(
            {
                "candidate_index": idx,
                "candidate_id": bindings.rating_request.candidate_id,
                "geometry_projection_hash": bindings.geometry_projection_hash,
                "N1_TERMINAL_RESIDUAL_K": phys.terminal_boundary_residual_k,
                "N1_TERMINAL_RESIDUAL_J_KG": (
                    str(run.observables.terminal_boundary_residual_j_kg) if run else None
                ),
                "N1_PHYSICAL_CLOSURE": phys.n1_status,
                "N1_Q_W": phys.total_duty_w,
                "N1_TUBE_OUTLET_K": (
                    str(run.observables.tube_outlet_temperature_k) if run else None
                ),
                "N1_SHELL_OUTLET_K": (
                    str(run.observables.shell_outlet_temperature_k) if run else None
                ),
                "N1_ENERGY_RESIDUAL_W": phys.energy_balance_residual_w,
                "N1_TASK172_HOLES": phys.task172_numerical_hole_count,
                "CANDIDATE_N1": _mesh_status(n1),
                "CANDIDATE_N2": _mesh_status(n2) if n2 else "not_run",
                "CANDIDATE_N4": _mesh_status(n4) if n4 else "not_run",
                "GEOMETRY_DUTY_INSUFFICIENT": phys.geometry_duty_insufficient,
                "ORIGINAL_TASK173_GATE": prod.failure_code or prod.outcome,
                **hyd,
                "physical_first_blocker": phys.first_blocker,
            }
        )

    payload = {
        "TASK_ID": "V08_03_OUTER_SHOOTING_ALGORITHM_CORRECTION",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": "pending_local_gates",
        "OUTER_SEARCH_DIRECTION_FIXED": True,
        "OUTER_HIGH_BOUND_CORRECTED": True,
        "EXPERIMENTAL_NOT_APPROVED": True,
        "CANDIDATE_1_N1": candidates_out[0]["CANDIDATE_N1"] if candidates_out else "not_run",
        "CANDIDATE_1_N2": candidates_out[0]["CANDIDATE_N2"] if candidates_out else "not_run",
        "CANDIDATE_1_N4": candidates_out[0]["CANDIDATE_N4"] if candidates_out else "not_run",
        "CANDIDATE_2_N1": candidates_out[1]["CANDIDATE_N1"] if len(candidates_out) > 1 else "not_run",
        "CANDIDATE_2_N2": candidates_out[1]["CANDIDATE_N2"] if len(candidates_out) > 1 else "not_run",
        "CANDIDATE_2_N4": candidates_out[1]["CANDIDATE_N4"] if len(candidates_out) > 1 else "not_run",
        "BEST_PHYSICALLY_CLOSED_Q_W": best_q or "not_available",
        "TARGET_330KW_MET": "false" if candidates_out else "unresolved",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "REMAINING_BLOCKER": (
            candidates_out[0]["physical_first_blocker"] if candidates_out else "NO_CANDIDATE"
        ),
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "candidates": candidates_out,
        "candidate_1_search_evidence": search_traces,
    }
    if candidates_out and all(c.get("GEOMETRY_DUTY_INSUFFICIENT") for c in candidates_out):
        payload["TARGET_330KW_MET"] = "false"
    if candidates_out:
        payload["TUBE_DP_PASS"] = candidates_out[0]["TUBE_DP_PASS"]
        payload["SHELL_DP_PASS"] = candidates_out[0]["SHELL_DP_PASS"]
        payload["NOZZLE_VELOCITY_PASS"] = candidates_out[0]["NOZZLE_VELOCITY_PASS"]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "HEAD_SHA": payload["HEAD_SHA"]}))


if __name__ == "__main__":
    main()
