#!/usr/bin/env python3
"""TASK_ID=V08_03_ENGINEERING_EVIDENCE_GRADE_CORRECTION — frozen evidence; no new solves."""
# ruff: noqa: E402

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
    out = Path("/opt/cursor/artifacts/v08_03_engineering_evidence_grade_correction.json")
    ev = load_frozen_330_evidence(FROZEN_FIXTURE)
    tp_status = str(ev.raw.get("tp_ph_query_status", "PASS"))
    physical = assess_engineering_physical_layer(ev, tp_ph_query_status=tp_status)
    negative = run_negative_controls_via_evaluator(ev, tp_ph_query_status=tp_status)
    error_budget = build_engineering_error_budget_report(frozen=ev.raw)

    task172 = str(ev.raw.get("production_task172_gate", "BLOCKED"))
    task173 = str(
        ev.raw.get("production_task173_gate", ev.raw.get("production_task173", "BLOCKED"))
    )

    pkg = build_engineering_acceptance_decision(
        ev=ev,
        physical=physical,
        negative=negative,
        task172_gate=task172,
        task173_gate=task173,
        error_budget=error_budget,
    )

    neg_detail = [
        {
            "scenario": r.scenario,
            "rejected_by_rule": r.rejected_by_rule,
            "perturbation_blocked": r.perturbation_blocked,
        }
        for r in negative.rows
    ]

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_ENGINEERING_EVIDENCE_GRADE_CORRECTION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "DUTY_SCREEN": pkg.duty_screen,
        "HYDRAULIC_SCREEN": pkg.hydraulic_screen,
        "ENERGY_BALANCE": pkg.energy_balance,
        "LOCAL_HEAT_TRANSFER": pkg.local_heat_transfer,
        "MESH_CONVERGENCE": pkg.mesh_convergence,
        "ENGINEERING_PHYSICAL_EVIDENCE": pkg.engineering_physical_evidence,
        "NEGATIVE_CONTROLS_ON_REAL_EVALUATOR": pkg.negative_control_tests,
        "negative_control_detail": neg_detail,
        "ENGINEERING_ERROR_BUDGET_STATUS": pkg.engineering_error_budget_status,
        "ENGINEERING_ERROR_BUDGET": pkg.engineering_error_budget,
        "CONTRACT_REVIEW_STATUS": pkg.contract_review_status,
        "CONTRACT_CHANGE_EVIDENCE": pkg.contract_change_evidence,
        "PRODUCTION_TOLERANCE_CHANGE_APPROVED": pkg.production_tolerance_change_approved,
        "PRODUCTION_NUMERICAL_STATUS": pkg.production_numerical_status,
        "PRODUCTION_TASK172": pkg.production_task172,
        "PRODUCTION_TASK173": pkg.production_task173,
        "ENGINEERING_ACCEPTANCE": pkg.engineering_acceptance,
        "DISTINCT_FULLY_CONVERGED": 0,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_SOLVER_REPLACED": False,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": pkg.production_contract_change_authorized,
        "MERGE_AUTHORIZED": pkg.merge_authorized,
        "CASE_ID": ev.case_id,
        "CANDIDATE_ID": ev.candidate_id,
        "GEOMETRY_HASH": ev.geometry_hash,
        "rationale": pkg.rationale,
        "error_budget_report": {
            "task172_local_residuals": error_budget.task172_local_residuals,
            "task173_terminal_temperature": error_budget.task173_terminal_temperature,
            "task173_terminal_enthalpy": error_budget.task173_terminal_enthalpy,
            "property_computation_error": error_budget.property_computation_error,
            "cell_enthalpy_propagation_j_kg": error_budget.cell_enthalpy_propagation_j_kg,
            "mesh_discretization": error_budget.mesh_discretization,
            "correlation_model_uncertainty": error_budget.correlation_model_uncertainty,
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"out": str(out), "ENGINEERING_PHYSICAL_EVIDENCE": pkg.engineering_physical_evidence}
        )
    )


if __name__ == "__main__":
    main()
