#!/usr/bin/env python3
"""TASK_ID=V08_03_COUNTERFLOW_FIXED_INLET_BVP_RECOVERY — frozen candidate dual-inlet BVP."""
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
    CASE_330KW_ID,
    assess_production_culp_rating,
    isolated_mesh_acceptance_gate,
    load_case_bindings,
    resolve_candidate_bindings_by_id,
    solve_isolated_outer_boundary,
)
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import classify_bvp_go_no_go
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.counterflow_fixed_inlet_bvp_recovery_v08 import run_n4_bvp_only
from prototypes.v08_thermal_rating.production_rating_diagnostics_v08 import (
    build_production_rating_diagnostic,
)

FROZEN_CANDIDATE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"
FROZEN_GEOMETRY_HASH = "1d5cfed590c20aacb2224df020fd7fc88866c551b9ac6d813812d40b9a0a874f"


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
            return "in_progress"
        return str(row.get("conclusion") or "unknown")
    except Exception:
        return "unknown"


def _json_ready(value: Any) -> Any:
    import math
    from decimal import Decimal

    if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_counterflow_fixed_inlet_bvp_recovery.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings and bindings.geometry_projection_hash == FROZEN_GEOMETRY_HASH

    recovery = run_n4_bvp_only(bindings, provider)
    n4 = recovery["n4"]
    cell0 = recovery["cell0"]
    opt_conv = bool(n4.outcome.extra.get("optimizer_actually_converged", False))
    decision, note, route, arch = classify_bvp_go_no_go(
        rows=n4.cell_gate_rows,
        cell0=cell0,
        optimizer_actually_converged=opt_conv,
    )

    n1s = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
    n2s = solve_isolated_outer_boundary(bindings, provider, subdivisions=2)
    n4s = solve_isolated_outer_boundary(bindings, provider, subdivisions=4)
    prod_diag = build_production_rating_diagnostic(
        assess_production_culp_rating(bindings, provider)
    )

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_COUNTERFLOW_FIXED_INLET_BVP_RECOVERY",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "CASE_ID": CASE_330KW_ID,
        "CANDIDATE_ID": FROZEN_CANDIDATE_ID,
        "BVP_N1": "NOT_RUN",
        "BVP_N2": "NOT_RUN",
        "BVP_N4": n4.original_task172_gate,
        "N4_ORIGINAL_TASK172_GATE": n4.original_task172_gate,
        "N4_MAX_R1_RATIO": recovery["n4_max_r1_ratio"],
        "N4_MAX_R2_RATIO": recovery["n4_max_r2_ratio"],
        "N4_MAX_R3_RATIO": recovery["n4_max_r3_ratio"],
        "NUMERICAL_DECISION": decision,
        "NUMERICAL_DECISION_NOTE": note,
        "CURRENT_BVP_ROUTE": route,
        "SHOOTING_N1": isolated_mesh_acceptance_gate(bindings, provider, n1s),
        "SHOOTING_N2": isolated_mesh_acceptance_gate(bindings, provider, n2s),
        "SHOOTING_N4": isolated_mesh_acceptance_gate(bindings, provider, n4s),
        "CELL0_AUDIT": _json_ready(asdict(cell0)),
        "PRODUCTION_TASK173": prod_diag.PRODUCTION_TASK173_STATUS,
        "DISTINCT_FULLY_CONVERGED": 0,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "REMAINING_BLOCKER": note,
        "MERGE_AUTHORIZED": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"out": str(out), "NUMERICAL_DECISION": decision, "CELL0_R1": cell0.r1_ratio}))


if __name__ == "__main__":
    main()
