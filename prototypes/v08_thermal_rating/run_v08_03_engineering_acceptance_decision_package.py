#!/usr/bin/env python3
"""TASK_ID=V08_03_ENGINEERING_ACCEPTANCE_DECISION_PACKAGE — frozen evidence, no new solves."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import BVP_PROTOTYPE_ROUTE
from prototypes.v08_thermal_rating.engineering_acceptance_decision_v08 import (
    build_engineering_acceptance_decision,
)
from prototypes.v08_thermal_rating.engineering_error_budget_v08 import (
    build_engineering_error_budget_report,
)
from prototypes.v08_thermal_rating.engineering_physical_evaluator_v08 import (
    assess_engineering_physical_layer,
    load_frozen_330_evidence,
    run_negative_controls_via_evaluator,
)

FROZEN_FIXTURE = _REPO / "tests/fixtures/v08_03_frozen_330kw_engineering_evidence.json"
PR_NUMBER = 325


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


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_engineering_acceptance_decision_package.json")
    ev = load_frozen_330_evidence(FROZEN_FIXTURE)
    tp_status = str(ev.raw.get("tp_ph_query_status", "PASS"))
    physical = assess_engineering_physical_layer(ev, tp_ph_query_status=tp_status)
    negative = run_negative_controls_via_evaluator(ev, tp_ph_query_status=tp_status)
    error_budget = build_engineering_error_budget_report(frozen=ev.raw)

    task172 = str(ev.raw.get("production_task172_gate", "BLOCKED"))
    task173 = str(ev.raw.get("production_task173", "BLOCKED"))

    pkg = build_engineering_acceptance_decision(
        ev=ev,
        physical=physical,
        negative=negative,
        task172_gate=task172,
        task173_gate=task173,
        error_budget=error_budget,
    )

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_ENGINEERING_ACCEPTANCE_DECISION_PACKAGE",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "PRODUCTION_NUMERICAL_STATUS": pkg.production_numerical_status,
        "PRODUCTION_NUMERICAL_DETAIL": pkg.production_numerical_detail,
        "ENGINEERING_PHYSICAL_EVIDENCE": pkg.engineering_physical_evidence,
        "CONTRACT_REVIEW_STATUS": pkg.contract_review_status,
        "CONTRACT_CHANGE_EVIDENCE": pkg.contract_change_evidence,
        "ENGINEERING_ACCEPTANCE": pkg.engineering_acceptance,
        "PRODUCTION_TASK172": pkg.production_task172,
        "PRODUCTION_TASK173": pkg.production_task173,
        "TERMINAL_H_RESIDUAL_J_KG": str(ev.terminal_residual_j_kg),
        "TERMINAL_H_ALLOWED_J_KG": str(ev.terminal_allowed_j_kg),
        "ENGINEERING_ERROR_BUDGET": pkg.engineering_error_budget,
        "LOCAL_RESIDUAL_ERROR_BUDGET": pkg.local_residual_error_budget,
        "MESH_CONVERGENCE_EVIDENCE": pkg.mesh_convergence_evidence,
        "NEGATIVE_CONTROL_TESTS": pkg.negative_control_tests,
        "RECOMMENDED_CONTRACT_CHANGE": pkg.recommended_contract_change,
        "MIGRATION_PROPOSAL_REF": pkg.migration_proposal_ref,
        "NOZZLE_VELOCITY": "UNRESOLVED",
        "DISTINCT_FULLY_CONVERGED": 0,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "CASE_ID": ev.case_id,
        "CANDIDATE_ID": ev.candidate_id,
        "rationale": pkg.rationale,
        "ENGINEERING_ERROR_BUDGET_STATUS": pkg.engineering_error_budget_status,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out),
                "CONTRACT_REVIEW_STATUS": pkg.contract_review_status,
                "NEGATIVE_CONTROL_TESTS": pkg.negative_control_tests,
            }
        )
    )


if __name__ == "__main__":
    main()
