#!/usr/bin/env python3
"""Capture the seven R27D reference candidates from an isolated, exact-head R27D worktree.

Usage:
  cd /path/to/R27D-worktree
  PYTHONPATH="$PWD" python /path/to/R27E/scripts/r27e_capture_r27d_reference.py \
    --output /path/to/R27E/tests/fixtures/r27e_r27d_seven_reference_baseline.json

This script must run against R27D sources, not R27E; it never modifies the worktree.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_R27D_HEAD = "e320aaf5840812eafe86a0e7d6fef97bf8062544"
_SCHEMA = "hxforge.r27e-r27d-seven-reference-regression.v27e"
_RECOVERY_PREFIXES = {"6ec6323f", "5b75a185", "8988992a", "c20fb684", "09dac82a"}
_REFERENCE_PREFIXES = {
    "9aba0e5c", "9c4b84db", "7357afdf", "580fc128",
    "8b05db3b", "3c129a7f", "40d78e67",
}


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=Path.cwd(), text=True, stderr=subprocess.DEVNULL
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_head = _git("rev-parse", "HEAD")
    if source_head != _R27D_HEAD:
        raise SystemExit(
            f"REFUSED: capture requires R27D HEAD {_R27D_HEAD}; got {source_head}"
        )
    if _git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("REFUSED: source worktree has modified tracked files")
    sys.path.insert(0, str(Path.cwd()))

    from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
        enumerate_experimental_rating_candidates,
    )
    from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
        ENGINEERING_NUMERIC_VALID,
        run_experimental_engineering_rating,
    )
    from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
        build_experimental_engineering_rating_live_package,
    )
    from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
        build_native_cell_context,
    )
    from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case

    case = shared_r26e_engineering_case()
    selection = enumerate_experimental_rating_candidates(
        case, rating_selection_policy="r27d", rate_all_distinct_task174_ready=True
    )
    ids = [
        cid for cid in selection.selected_candidate_ids
        if cid[:8] not in _RECOVERY_PREFIXES
    ]
    if len(ids) != 7 or {cid[:8] for cid in ids} != _REFERENCE_PREFIXES:
        raise SystemExit(f"REFUSED: R27D seven candidate selection drift: {ids}")

    rows: list[dict[str, Any]] = []
    for cid in ids:
        record = next(r for r in selection.records if r.candidate_id == cid)
        native = build_native_cell_context(case, selection=selection, candidate_id=cid)
        cache: dict[int, Any] = {}
        n1 = run_experimental_engineering_rating(
            case, subdivisions=1, native=native, mesh_result_cache=cache
        )
        if n1.status != ENGINEERING_NUMERIC_VALID:
            raise SystemExit(f"REFUSED: R27D N1 not valid for {cid}: {n1.failure_code}")
        package = build_experimental_engineering_rating_live_package(
            case,
            native=native,
            run_mesh_ladder=True,
            run_hydraulic_sensitivity=False,
            mesh_result_cache=cache,
        )
        mesh = package.get("mesh_convergence") or {}
        receipt = package.get("engineering_delivery_receipt") or {}
        if mesh.get("FULL_RATING_CONVERGED") is not True:
            raise SystemExit(f"REFUSED: R27D mesh not fully converged for {cid}")
        rows.append({
            "candidate_id": cid,
            "candidate_hash": record.candidate_hash,
            "geometry_projection_hash": record.geometry_projection_hash,
            "n1_status": n1.status,
            "n1_duty_w": n1.duty_w,
            "energy_balance_relative_error_n1": n1.energy_balance_relative_error,
            "max_cell_thermal_residual_w_n1": n1.max_cell_thermal_residual_w,
            "max_closure_residual_w_n1": n1.max_inner_wall_outer_closure_residual_w,
            "FULL_RATING_CONVERGED": mesh.get("FULL_RATING_CONVERGED"),
            "mesh_ladder": {
                str(level): metrics for level, metrics in (mesh.get("per_mesh") or {}).items()
            },
            "N4_DUTY_W": receipt.get("N4_DUTY_W"),
            "N4_TUBE_OUTLET_K": receipt.get("N4_TUBE_OUTLET_K"),
            "N4_SHELL_OUTLET_K": receipt.get("N4_SHELL_OUTLET_K"),
            "LIVE_TUBE_DP_PA": receipt.get("LIVE_TUBE_DP_PA"),
            "LIVE_SHELL_DP_PA": receipt.get("LIVE_SHELL_DP_PA"),
            "experimental_mesh_result_hash": receipt.get("EXPERIMENTAL_MESH_RESULT_HASH"),
        })

    payload = {
        "schema_version": _SCHEMA,
        "reference_candidate_count": len(rows),
        "candidates": rows,
        "baseline_provenance": {
            "source_pr_number": 310,
            "source_commit_sha": source_head,
            "capture_mode": "ISOLATED_R27D_WORKTREE",
        },
        "model_identity": {
            "task172_implementation": "task172_local_runtime.service",
            "tube_regime_isolation": "R27D_ORIGINAL",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({
        "baseline_source_sha": source_head,
        "reference_candidate_count": len(rows),
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
