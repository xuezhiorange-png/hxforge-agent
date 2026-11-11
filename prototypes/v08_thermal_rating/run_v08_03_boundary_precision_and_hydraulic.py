#!/usr/bin/env python3
"""TASK_ID=V08_03_BOUNDARY_PRECISION_AND_HYDRAULIC_FEASIBILITY delivery runner."""
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
    CandidateMeshCloseout,
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
    experimental_mesh_converged,
    load_case_bindings,
    production_distinct_fully_converged,
    run_candidate_mesh_closeout,
)
from prototypes.v08_thermal_rating.boundary_precision_audit_v1 import run_boundary_precision_audit
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330
from prototypes.v08_thermal_rating.hydraulic_feasibility_v08 import run_hydraulic_feasibility_screen


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
                "pr",
                "view",
                "325",
                "--repo",
                "xuezhiorange-png/hxforge-agent",
                "--json",
                "statusCheckRollup",
            ],
            cwd=_REPO,
            text=True,
        )
        rollup = json.loads(out).get("statusCheckRollup", [])
        pending = [c for c in rollup if c.get("status") not in ("COMPLETED",)]
        failed = [
            c
            for c in rollup
            if c.get("conclusion") in ("FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED")
        ]
        if pending:
            return "in_progress"
        if failed:
            return "failure"
        return "success"
    except Exception:
        return "unknown"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-production", action="store_true")
    parser.add_argument("--hydraulic-max", type=int, default=64)
    parser.add_argument("--thermal-max", type=int, default=2)
    args = parser.parse_args()

    out = Path("/opt/cursor/artifacts/v08_03_boundary_precision_and_hydraulic.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID

    hydraulic = run_hydraulic_feasibility_screen(
        normalized, handoff, provider=provider, max_candidates=args.hydraulic_max
    )

    space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=max(1, args.thermal_max)
    )
    closeouts: list[CandidateMeshCloseout] = []
    precision_audit: dict[str, Any] | None = None

    for i, bundle in enumerate(bundles[: args.thermal_max]):
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
        closeouts.append(closeout)
        if i == 0:
            audit = run_boundary_precision_audit(bindings, provider, subdivisions=1)
            precision_audit = asdict(audit)

    closeout_rows = [asdict(c) for c in closeouts]

    def _row0(key: str, default: str = "") -> str:
        if not closeout_rows:
            return default
        return str(closeout_rows[0].get(key, default))

    cand1_close = closeout_rows[0] if closeout_rows else {}
    n1v = cand1_close.get("n1_verification", {})

    exp_mesh = sum(1 for c in closeouts if experimental_mesh_converged(c))

    prod_hashes: set[str] = set()
    for c in closeouts:
        if production_distinct_fully_converged(c) and c.geometry_projection_hash:
            prod_hashes.add(c.geometry_projection_hash)

    term_rec = False
    first_blocker = "unverified"
    if precision_audit:
        term_rec = bool(precision_audit.get("terminal_precision_recovered"))
        first_blocker = str(precision_audit.get("first_numerical_blocker", "unverified"))

    feasible_hydraulic = [_json_ready(asdict(r)) for r in hydraulic.rows if r.hydraulic_pass]

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_BOUNDARY_PRECISION_AND_HYDRAULIC_FEASIBILITY",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "TERMINAL_PRECISION_RECOVERED": term_rec,
        "FIRST_NUMERICAL_BLOCKER": first_blocker,
        "CANDIDATE_1_N1": _row0("n1", "BLOCKED"),
        "CANDIDATE_1_N2_N4": f"n2={_row0('n2', 'not_run')};n4={_row0('n4', 'not_run')}",
        "CANDIDATE_1_SHELL_DP_PASS": cand1_close.get("shell_dp_pass", False),
        "CANDIDATE_1_TUBE_DP_PASS": cand1_close.get("tube_dp_pass", False),
        "HYDRAULIC_FEASIBLE_CANDIDATES": hydraulic.hydraulic_feasible_count,
        "DISTINCT_HYDRAULIC_FEASIBLE_GEOMETRY": hydraulic.distinct_hydraulic_feasible_geometry,
        "NOZZLE_VELOCITY_CHECK": hydraulic.rows[0].nozzle_velocity_note
        if hydraulic.rows
        else "no_candidates",
        "THERMAL_VALIDATED_CANDIDATES": 0,
        "EXPERIMENTAL_MESH_CONVERGED": exp_mesh,
        "DISTINCT_FULLY_CONVERGED": len(prod_hashes),
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "ORIGINAL_TASK172_GATE": (
            "NOT_INFERRED_FROM_ISOLATED_TASK172_HOLES; "
            "see boundary_precision_audit.task172_identity_hashes_on_accepted"
        ),
        "ORIGINAL_TASK173_GATE": (
            "skipped_by_flag"
            if args.skip_production
            else _row0("production_task173_gate", "not_run")
        ),
        "N1_ACCEPTED_RUN_HASH": n1v.get("N1_ACCEPTED_RUN_HASH"),
        "precision_audit_candidate1": _json_ready(precision_audit) if precision_audit else None,
        "hydraulic_screen": {
            "candidates_screened": hydraulic.candidates_screened,
            "rows_head": [_json_ready(asdict(r)) for r in hydraulic.rows[:8]],
            "feasible": feasible_hydraulic[:8],
        },
        "thermal_closeouts": [_json_ready(r) for r in closeout_rows],
    }

    blockers: list[str] = []
    if not term_rec:
        blockers.append(first_blocker)
    if cand1_close.get("shell_dp_pass") is False:
        blockers.append("CANDIDATE_1_SHELL_DP_EXCEEDS_CASE_LIMIT")
    if hydraulic.hydraulic_feasible_count == 0:
        blockers.append("NO_HYDRAULIC_FEASIBLE_STRUCTURE_IN_SCREENED_SET")
    else:
        blockers.append(
            f"HYDRAULIC_ALTERNATIVE_EXISTS({hydraulic.distinct_hydraulic_feasible_geometry}_distinct_geometry)"
        )
    if len(prod_hashes) == 0:
        blockers.append("NO_PRODUCTION_DISTINCT_FULLY_CONVERGED")
    payload["REMAINING_BLOCKER"] = (
        "; ".join(blockers) if blockers else "ENGINEERING_ACCEPTANCE_BLOCKED"
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out),
                "HEAD_SHA": payload["HEAD_SHA"],
                "HYDRAULIC": hydraulic.hydraulic_feasible_count,
            }
        )
    )


if __name__ == "__main__":
    main()
