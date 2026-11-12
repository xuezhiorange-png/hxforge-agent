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
    load_case_bindings,
    resolve_candidate_bindings_by_id,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.counterflow_fixed_inlet_bvp_recovery_v08 import (
    run_counterflow_fixed_inlet_bvp_recovery,
)
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


def _bvp_label(result: Any | None) -> str:
    if result is None:
        return "BLOCKED"
    return "PASS" if result.original_task172_gate == "PASS" else "BLOCKED"


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_counterflow_fixed_inlet_bvp_recovery.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    if bindings is None:
        raise SystemExit(f"candidate {FROZEN_CANDIDATE_ID} not found")
    assert bindings.geometry_projection_hash == FROZEN_GEOMETRY_HASH

    recovery = run_counterflow_fixed_inlet_bvp_recovery(bindings, provider)
    n4 = recovery["n4"]
    decision = recovery["numerical_decision"]

    prod = assess_production_culp_rating(bindings, provider)
    prod_diag = build_production_rating_diagnostic(prod)

    mesh_conv = "BLOCKED"
    shooting_gates = recovery.get("isolated_shooting_gates") or {}
    if shooting_gates.get("1") == "ACCEPTED" and shooting_gates.get("2") == "ACCEPTED":
        mesh_conv = "BLOCKED" if shooting_gates.get("4") != "ACCEPTED" else "not_production_task173"

    eng_ok = False

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_COUNTERFLOW_FIXED_INLET_BVP_RECOVERY",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "CASE_ID": CASE_330KW_ID,
        "CANDIDATE_ID": FROZEN_CANDIDATE_ID,
        "GEOMETRY_HASH": FROZEN_GEOMETRY_HASH,
        "BVP_N1": _bvp_label(recovery.get("n1_bvp")),
        "BVP_N2": _bvp_label(recovery.get("n2_bvp")),
        "BVP_N4": _bvp_label(n4),
        "N4_ORIGINAL_TASK172_GATE": n4.original_task172_gate,
        "N4_MAX_R1_RATIO": recovery["n4_max_r1_ratio"],
        "N4_MAX_R2_RATIO": recovery["n4_max_r2_ratio"],
        "N4_MAX_R3_RATIO": recovery["n4_max_r3_ratio"],
        "N4_TOTAL_Q_W": n4.outcome.total_q_w,
        "N4_TUBE_OUTLET_K": n4.outcome.tube_outlet_temperature_k,
        "N4_SHELL_OUTLET_K": n4.outcome.shell_outlet_temperature_k,
        "N4_ENERGY_BALANCE_W": n4.outcome.energy_balance_residual_w,
        "ORIGINAL_TASK173_GATE": prod_diag.PRODUCTION_TASK173_STATUS,
        "ORIGINAL_MESH_CONVERGENCE": mesh_conv,
        "NUMERICAL_DECISION": decision,
        "NUMERICAL_DECISION_NOTE": recovery["numerical_decision_note"],
        "DISTINCT_FULLY_CONVERGED": 1 if eng_ok else 0,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "REMAINING_BLOCKER": recovery["numerical_decision_note"],
        "PRODUCTION_SOLVER_REPLACED": False,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "MERGE_AUTHORIZED": False,
        "ISOLATED_SHOOTING_N1": shooting_gates.get("1", "unknown"),
        "ISOLATED_SHOOTING_N2": shooting_gates.get("2", "unknown"),
        "ISOLATED_SHOOTING_N4": shooting_gates.get("4", "unknown"),
        "shooting_vs_bvp": _json_ready(
            {k: asdict(v) for k, v in recovery["shooting_comparison"].items()}
        ),
        "n4_cell_gate_rows": [_json_ready(asdict(r)) for r in n4.cell_gate_rows],
        "q_seed_sum_w": recovery["q_seed_sum_w"],
        "bvp_n4_diagnostics": list(n4.outcome.diagnostics),
        "PRODUCTION_FIRST_BLOCKER": prod_diag.PRODUCTION_FIRST_BLOCKER,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps({"out": str(out), "NUMERICAL_DECISION": decision, "BVP_N4": payload["BVP_N4"]})
    )


if __name__ == "__main__":
    main()
