#!/usr/bin/env python3
"""TASK_ID=V08_03_BVP_ROUTE_STOP_AND_CLOSEOUT — frozen baseline, no BVP re-run."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import (
    BVP_PHYSICAL_INFEASIBILITY_PROVEN,
    BVP_PROTOTYPE_ROUTE,
    frozen_route_closeout_decision,
)

CANDIDATE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"
GEOMETRY_HASH = "1d5cfed590c20aacb2224df020fd7fc88866c551b9ac6d813812d40b9a0a874f"
CASE_ID = "HXFORGE_330KW_STRICT_DP"

# Frozen cell0 production gate audit (V08_03_BVP_EVIDENCE_INTEGRITY_AND_SOLVER_GO_NO_GO).
FROZEN_CELL0 = {
    "gate_evidence": "VALID_PRODUCTION_GATE",
    "property_domain_status": "OK",
    "production_gate_pass": False,
    "r1_ratio": 449.51618265054026,
    "r2_ratio": 95.02621352991264,
    "r3_ratio": 352.09315504640887,
    "task172_request_hash": "6eb035d2329486f2b3547f0a2e8d0250ae314c986ab6922004f4379c16751982",
}


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
                "conclusion,status",
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
    out = Path("/opt/cursor/artifacts/v08_03_bvp_route_stop_and_closeout.json")
    dec, note, route, _ = frozen_route_closeout_decision()
    assert route == BVP_PROTOTYPE_ROUTE == "STOP"
    assert dec == "B" and not BVP_PHYSICAL_INFEASIBILITY_PROVEN

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_BVP_ROUTE_STOP_AND_CLOSEOUT",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "CASE_ID": CASE_ID,
        "CANDIDATE_ID": CANDIDATE_ID,
        "GEOMETRY_HASH": GEOMETRY_HASH,
        "CELL0_PRODUCTION_GATE": "VALID",
        "CELL0_R1_RATIO": FROZEN_CELL0["r1_ratio"],
        "CELL0_R2_RATIO": FROZEN_CELL0["r2_ratio"],
        "CELL0_R3_RATIO": FROZEN_CELL0["r3_ratio"],
        "NUMERICAL_DECISION": dec,
        "NUMERICAL_DECISION_NOTE": note,
        "CURRENT_BVP_ROUTE": route,
        "BVP_PHYSICAL_INFEASIBILITY_PROVEN": BVP_PHYSICAL_INFEASIBILITY_PROVEN,
        "BVP_N1": "NOT_RUN",
        "BVP_N2": "NOT_RUN",
        "BVP_N4": "BLOCKED",
        "SHOOTING_N1": "ACCEPTED",
        "SHOOTING_N2": "ACCEPTED",
        "SHOOTING_N4": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "EXPERIMENTAL_Q_TOTAL_W": 395267.23466398794,
        "TUBE_DP_PA": "1105.970",
        "SHELL_DP_PA": "1177.102",
        "NOZZLE_VELOCITY": "UNRESOLVED",
        "DISTINCT_FULLY_CONVERGED": 0,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "NEXT_ARCHITECTURE_WORK": "TASK173_OUTER_ENTHALPY_NUMERICAL_REPRESENTATION",
        "PRODUCTION_SOLVER_REPLACED": False,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "MERGE_AUTHORIZED": False,
        "BVP_PROTOTYPE_STATUS": "HISTORICAL_EXPERIMENT_NOT_FOR_PRODUCTION",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "CURRENT_BVP_ROUTE": route}))


if __name__ == "__main__":
    main()
